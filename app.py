import streamlit as st
import sqlite3, os, time, hashlib
from datetime import datetime, date, time as dtime
from pathlib import Path
from io import BytesIO

# ================= CONFIG =================
UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)
DB = "viral_file_share.db"

# 🔐 ADMIN PASSWORD (HIDDEN)
ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD") 

# ================= DATABASE =================
conn = sqlite3.connect(DB, check_same_thread=False)
c = conn.cursor()
c.execute("""
CREATE TABLE IF NOT EXISTS files (
    id INTEGER PRIMARY KEY,
    filename TEXT,
    filepath TEXT,
    text_data TEXT,
    password_hash TEXT,
    password_expiry INTEGER,
    view_seconds INTEGER,
    one_time_view INTEGER,
    one_time_download INTEGER,
    max_downloads INTEGER,
    download_count INTEGER DEFAULT 0,
    viewed INTEGER DEFAULT 0,
    upload_country TEXT,
    download_country TEXT,
    upload_time TEXT,
    download_time TEXT
)
""")
conn.commit()

# ================= HELPERS =================
def hash_pwd(p):
    return hashlib.sha256(p.encode()).hexdigest()

def expired(ts):
    return int(time.time()) > ts

# ================= PAGE CONFIG =================
st.set_page_config(
    page_title="🔥 Secure Viral Share | Ghulam Mustafa",
    page_icon="🔐",
    layout="centered"
)

# ================= STYLES =================
st.markdown("""
<style>
.stApp {background: linear-gradient(135deg,#667eea,#764ba2,#ff758c);background-size: 400% 400%;animation: bgMove 15s ease infinite;}
@keyframes bgMove {0%{background-position:0% 50%;}50%{background-position:100% 50%;}100%{background-position:0% 50%;}}
.card {background: rgba(255,255,255,0.18);backdrop-filter: blur(20px);padding:2rem;border-radius:22px;box-shadow:0 15px 50px rgba(0,0,0,0.4);margin-bottom:2rem;color:white;animation: fadeIn 0.8s ease;}
@keyframes fadeIn {from {opacity:0; transform:translateY(20px);}to {opacity:1; transform:translateY(0);}}
.title {font-size:3rem;font-weight:900;text-align:center;text-shadow:0 0 15px rgba(255,255,255,0.6);}
.creator {text-align:center;font-size:1.2rem;letter-spacing:3px;margin-top:.6rem;}
button {border-radius:16px !important;font-weight:700 !important;}
button:hover {box-shadow:0 0 20px rgba(255,255,255,0.6) !important;transform: scale(1.03);transition:0.3s;}
.footer {text-align:center;padding:1.2rem;margin-top:3rem;color:#fff;opacity:0.9;}
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown(f"""
<div class="card">
  <div class="title">🔐 Secure Viral File & Text Share</div>
  <div class="creator">✨ Crafted with ❤️ by <b>Ghulam Mustafa</b> ✨</div>
  <div style="margin-top:1rem;padding:1rem;background:rgba(255,255,255,0.22);border-radius:16px;text-align:center;font-size:1.1rem;">
  “Education is the most powerful weapon which you can use to change the world.”
  </div>
</div>
""", unsafe_allow_html=True)

# ================= NAVIGATION =================
menu = st.sidebar.radio("📌 Navigation", ["📤 Upload", "🔓 Access", "🛠 Admin"])

# ================= UPLOAD =================
if menu == "📤 Upload":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📤 Upload File / Text")

    utype = st.radio("Choose Type", ["File", "Text"])
    password = st.text_input("🔑 Password (6–10 chars)", type="password")

    expiry_date = st.date_input("📅 Expiry Date", date.today())
    expiry_time = st.time_input("⏰ Expiry Time", dtime(23, 59))

    if expiry_date < date.today():
        st.warning("❌ Expiry date cannot be in the past. Please select today or a future date.")
        st.stop()

    expiry_ts = int(datetime.combine(expiry_date, expiry_time).timestamp())
    one_time_view = st.checkbox("👁 One-Time View")
    view_sec = st.slider("⏱ View Seconds", 1, 600, 10) if one_time_view else 0

    one_dl = int(st.checkbox("⬇ One-Time Download"))
    max_dl = 1 if one_dl else st.number_input("Max Downloads", 1, 50, 3)

    file, text_data = None, None
    if utype == "File":
        file = st.file_uploader("📁 Upload File")
    else:
        txt = st.text_area("📝 Enter Text")
        if txt.strip():
            text_data = txt
            file = BytesIO(txt.encode())
            file.name = f"text_{int(time.time())}.txt"

    if st.button("🚀 Upload Securely"):
        if not (6 <= len(password) <= 10):
            st.error("Password must be 6–10 characters")
            st.stop()

        fname, fpath = None, None
        if utype == "File" and file:
            fname = file.name
            fpath = UPLOAD_DIR / f"{int(time.time())}_{fname}"
            with open(fpath, "wb") as f:
                f.write(file.read())

        c.execute("""
        INSERT INTO files (
            id, filename, filepath, text_data, password_hash,
            password_expiry, view_seconds, one_time_view, one_time_download,
            max_downloads, download_count, viewed, upload_country,
            download_country, upload_time, download_time
        ) VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
        """,
        (
            fname, str(fpath) if fpath else None, text_data,
            hash_pwd(password), expiry_ts,
            view_sec, int(one_time_view),
            int(one_dl), max_dl,
            0, 0,
            "Unknown", None,
            str(datetime.now()), None
        ))
        conn.commit()
        st.success("✅ Uploaded Successfully")
    st.markdown("</div>", unsafe_allow_html=True)

# ================= ACCESS =================
elif menu == "🔓 Access":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🔓 Access File / Text")

    pwd = st.text_input("🔑 Enter Password", type="password")
    if st.button("Access"):
        c.execute("SELECT * FROM files WHERE password_hash=?", (hash_pwd(pwd),))
        r = c.fetchone()
        if not r:
            st.error("❌ Invalid password"); st.stop()
        if expired(r[5]):
            st.error("⏰ Link expired"); st.stop()
        if r[9] != 0 and r[10] >= r[9]:
            st.error("⬇ Download limit reached"); st.stop()

        # ✅ View Before Download Logic
        if not r[11]:  # Not viewed yet
            st.info(f"👁 You must view for {r[6]} seconds before download.")
            if r[1] and os.path.exists(r[2]):
                with open(r[2], "r", encoding="utf-8", errors="ignore") as f:
                    st.text_area("📄 File Preview", f.read(), height=300)
            else:
                st.text_area("📝 Text View", r[3], height=300)

            countdown = st.empty()
            for i in range(r[6], 0, -1):
                countdown.markdown(f"<h3 style='color:#fffa; text-align:center;'>⏱ Viewing ends in {i} seconds</h3>", unsafe_allow_html=True)
                time.sleep(1)
            countdown.empty()
            st.success("✅ View complete! You can now download.")

            c.execute("UPDATE files SET viewed=1 WHERE id=?", (r[0],))
            conn.commit()
            r = list(r)
            r[11] = 1  # Mark viewed in local variable

        # DOWNLOAD
        if r[1] and os.path.exists(r[2]):
            with open(r[2], "rb") as f:
                st.download_button("⬇ Download File", f, file_name=r[1])
        else:
            st.download_button("⬇ Download Text", r[3], file_name="text.txt")

        c.execute("UPDATE files SET download_count=download_count+1, download_time=? WHERE id=?", (str(datetime.now()), r[0]))
        conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

# ================= ADMIN =================
else:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🛠 Admin Panel")
    ap = st.text_input("Admin Password", type="password")
    if ap == ADMIN_PASSWORD:
        st.success("👑 Welcome Admin")
        c.execute("SELECT * FROM files")
        for r in c.fetchall():
            with st.expander(f"📦 File ID {r[0]}"):
                st.write("⏰ Upload Time:", r[14])
                st.write("⏰ Download Time:", r[15] if r[15] else "-")

                if r[1] and os.path.exists(r[2]):
                    with open(r[2], "r", encoding="utf-8", errors="ignore") as f:
                        st.text_area("📄 File Content", f.read(), height=300)
                    with open(r[2], "rb") as f:
                        st.download_button("⬇ Admin Download", f, file_name=r[1])
                else:
                    st.text_area("📝 Text Content", r[3], height=300)

                new_max_dl = st.number_input("Max Downloads", min_value=1, max_value=50, value=max(1, r[9]))
                new_expiry = st.date_input("Expiry Date", datetime.fromtimestamp(r[5]).date())
                new_time = st.time_input("Expiry Time", datetime.fromtimestamp(r[5]).time())
                expiry_ts = int(datetime.combine(new_expiry, new_time).timestamp())

                if st.button("💾 Update Settings", key=f"upd_{r[0]}"):
                    c.execute("UPDATE files SET max_downloads=?, password_expiry=? WHERE id=?", (new_max_dl, expiry_ts, r[0]))
                    conn.commit()
                    st.success("✅ Updated")

                if st.button("🗑 Delete File/Text", key=f"del_{r[0]}"):
                    if r[1] and os.path.exists(r[2]):
                        os.remove(r[2])
                    c.execute("DELETE FROM files WHERE id=?", (r[0],))
                    conn.commit()
                    st.warning("🗑 Deleted Successfully")

    st.markdown("</div>", unsafe_allow_html=True)

# ================= FOOTER =================
st.markdown("""
<div class="footer">
© 2026 Secure File/Text Share | Crafted with ❤️ by <b>Ghulam Mustafa</b>
</div>
""", unsafe_allow_html=True)
