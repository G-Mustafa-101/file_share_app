import streamlit as st
import sqlite3
import os
import secrets
import string
import time
from datetime import datetime, timedelta
from pathlib import Path
import pandas as pd
from io import BytesIO

# =============================
# 🌐 CONFIGURATION
# =============================
UPLOAD_FOLDER = Path("uploads")
DB_PATH = "files.db"
CODE_LENGTH = 8
MAX_FILE_SIZE_MB = 50

# 🔐 ADMIN PASSWORD (UPDATED)
ADMIN_PASSCODE = "MaLiK.101"

UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# =============================
# 💾 DATABASE SETUP
# =============================
def init_db():
    conn = sqlite3.connect(DB_PATH, check_same_thread=False)
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            code TEXT UNIQUE,
            saved_name TEXT,
            original_name TEXT,
            created_at INTEGER,
            expires_at INTEGER,
            downloaded INTEGER DEFAULT 0,
            one_time INTEGER DEFAULT 1,
            type TEXT DEFAULT 'file'
        )
    """)
    conn.commit()
    return conn

conn = init_db()

# =============================
# 🔧 HELPER FUNCTIONS
# =============================
def generate_code(n=CODE_LENGTH):
    alphabet = string.ascii_letters + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(n))

def cleanup_expired():
    now = int(time.time())
    c = conn.cursor()
    c.execute("SELECT id, saved_name FROM files WHERE expires_at <= ?", (now,))
    rows = c.fetchall()
    for _id, saved_name in rows:
        try:
            fpath = UPLOAD_FOLDER / saved_name
            if fpath.exists():
                fpath.unlink()
        except:
            pass
    c.execute("DELETE FROM files WHERE expires_at <= ?", (now,))
    conn.commit()

def save_file(uploaded_file, expiry_seconds, one_time=True, file_type="file"):
    uploaded_file.seek(0, os.SEEK_END)
    size = uploaded_file.tell()
    uploaded_file.seek(0)

    if size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValueError(f"File exceeds {MAX_FILE_SIZE_MB} MB limit.")

    code = generate_code()
    c = conn.cursor()
    while True:
        c.execute("SELECT 1 FROM files WHERE code=?", (code,))
        if c.fetchone() is None:
            break
        code = generate_code()

    timestamp = int(time.time())
    expires_at = timestamp + int(expiry_seconds)
    saved_name = f"{timestamp}_{secrets.token_hex(8)}_{uploaded_file.name}"

    with open(UPLOAD_FOLDER / saved_name, "wb") as f:
        f.write(uploaded_file.read())

    c.execute("""
        INSERT INTO files
        (code, saved_name, original_name, created_at, expires_at, one_time, type)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (code, saved_name, uploaded_file.name, timestamp, expires_at, int(one_time), file_type))

    conn.commit()
    return code, expires_at

def get_record_by_code(code):
    c = conn.cursor()
    c.execute("""
        SELECT id, saved_name, original_name, expires_at,
               downloaded, one_time, type
        FROM files WHERE code=?
    """, (code,))
    return c.fetchone()

def mark_downloaded_and_maybe_delete(record_id, saved_name, one_time):
    c = conn.cursor()
    c.execute("UPDATE files SET downloaded=1 WHERE id=?", (record_id,))
    conn.commit()

    if one_time:
        try:
            (UPLOAD_FOLDER / saved_name).unlink(missing_ok=True)
        except:
            pass
        c.execute("DELETE FROM files WHERE id=?", (record_id,))
        conn.commit()

def get_all_files():
    c = conn.cursor()
    c.execute("""
        SELECT id, code, original_name, downloaded,
               created_at, expires_at, one_time, type
        FROM files
    """)
    rows = c.fetchall()

    df = pd.DataFrame(rows, columns=[
        "ID","Code","File Name","Downloaded",
        "Created At","Expires At","One-Time","Type"
    ])

    df["Created At"] = df["Created At"].apply(
        lambda t: datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S')
    )
    df["Expires At"] = df["Expires At"].apply(
        lambda t: datetime.utcfromtimestamp(int(t)).strftime('%Y-%m-%d %H:%M:%S')
    )
    df["One-Time"] = df["One-Time"].apply(lambda x: "Yes" if x else "No")
    return df

def delete_file(file_id):
    c = conn.cursor()
    c.execute("SELECT saved_name FROM files WHERE id=?", (file_id,))
    row = c.fetchone()
    if row:
        fpath = UPLOAD_FOLDER / row[0]
        if fpath.exists():
            fpath.unlink()
        c.execute("DELETE FROM files WHERE id=?", (file_id,))
        conn.commit()
        return True
    return False

cleanup_expired()

# =============================
# 🎨 STYLING
# =============================
st.set_page_config(page_title="Secure File/Text Share | G Mustafa", layout="centered")

st.markdown("""
<style>
body { background-color: #f5f7fa; }
.header {
 text-align:center; padding:1.5rem; font-size:2rem; font-weight:bold;
 color:white; background:linear-gradient(90deg,#0072ff,#00c6ff);
 border-radius:1rem; box-shadow:0 4px 20px rgba(0,0,0,0.2);
 margin-bottom:1rem;
}
.name {
 text-align:center; font-size:1.1rem;
 color:#333; margin-bottom:2rem; font-style:italic;
}
.footer {
 text-align:center; color:#888; font-size:0.9rem;
 margin-top:3rem; border-top:1px solid #ddd; padding-top:0.8rem;
}
.card {
 background:#fff; padding:1rem; border-radius:1rem;
 box-shadow:0 4px 15px rgba(0,0,0,0.1);
 margin-bottom:1rem; text-align:center;
}
.card-title { font-weight:bold; font-size:1.2rem; }
.card-value { font-size:1.5rem; color:#0072ff; font-weight:bold; }
</style>
""", unsafe_allow_html=True)

st.markdown("<div class='header'>🔐 Secure File / Text Share</div>", unsafe_allow_html=True)
st.markdown("<div class='name'>✨ Crafted with ❤️ by <b>G Mustafa</b> ✨</div>", unsafe_allow_html=True)

# =============================
# ⚙️ UPLOAD & DOWNLOAD
# =============================
tab = st.tabs(["📤 Upload", "📥 Download"])

with tab[0]:
    st.subheader("Upload File or Text")
    upload_type = st.radio("Choose type", ["File", "Text"])
    uploaded_file = None
    file_type = "file"

    if upload_type == "File":
        uploaded_file = st.file_uploader("Select a file")
    else:
        text_content = st.text_area("Enter your text")
        if text_content.strip():
            uploaded_file = BytesIO(text_content.encode("utf-8"))
            uploaded_file.name = f"text_{int(time.time())}.txt"
            file_type = "text"

    expiry_date = st.date_input("Expiry Date", value=datetime.today() + timedelta(days=1))
    hour = st.selectbox("Hour", list(range(1,13)))
    minute = st.selectbox("Minute", list(range(0,60)))
    am_pm = st.selectbox("AM / PM", ["AM", "PM"])

    if am_pm == "PM" and hour != 12:
        hour += 12
    if am_pm == "AM" and hour == 12:
        hour = 0

    expiry_dt = datetime.combine(expiry_date, datetime.min.time()) + timedelta(hours=hour, minutes=minute)
    expiry_seconds = int((expiry_dt - datetime.utcnow()).total_seconds())

    one_time = st.checkbox("One-time download", True)

    if st.button("Generate Code"):
        if not uploaded_file:
            st.error("Please select a file or enter text.")
        else:
            code, _ = save_file(uploaded_file, expiry_seconds, one_time, file_type)
            st.success("Uploaded successfully!")
            st.code(code)

with tab[1]:
    st.subheader("Download File or Text")
    code_input = st.text_input("Enter code")

    if st.button("Download"):
        cleanup_expired()
        rec = get_record_by_code(code_input.strip())
        if not rec:
            st.error("Invalid or expired code.")
        else:
            rec_id, saved, orig, expires_at, downloaded, one_time_flag, ftype = rec
            if expires_at <= int(time.time()):
                st.error("Code expired.")
            else:
                path = UPLOAD_FOLDER / saved
                data = path.read_bytes()
                if ftype == "text":
                    st.text(data.decode("utf-8"))
                st.download_button("Download", data, file_name=orig)
                mark_downloaded_and_maybe_delete(rec_id, saved, one_time_flag)

# =============================
# 🛠️ ADMIN PANEL
# =============================
st.sidebar.subheader("🛠️ Admin Panel")

if "is_admin" not in st.session_state:
    st.session_state["is_admin"] = False

if not st.session_state["is_admin"]:
    pwd = st.sidebar.text_input("Admin Password", type="password")
    if st.sidebar.button("Login"):
        if pwd == ADMIN_PASSCODE:
            st.session_state["is_admin"] = True
            st.sidebar.success("Access Granted")
        else:
            st.sidebar.error("Wrong password")

if st.session_state["is_admin"]:
    st.sidebar.success("Welcome Admin 👑")

    st.sidebar.dataframe(get_all_files(), use_container_width=True)

    fid = st.sidebar.number_input("File ID to delete", min_value=1, step=1)
    if st.sidebar.button("Delete File"):
        if delete_file(fid):
            st.sidebar.success("Deleted")
        else:
            st.sidebar.error("Not found")

# =============================
# 🧾 FOOTER
# =============================
st.markdown(
    "<div class='footer'>© 2025 Secure File/Text Share | Admin Enabled | Created by G Mustafa</div>",
    unsafe_allow_html=True
)
