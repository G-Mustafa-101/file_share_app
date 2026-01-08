import streamlit as st
import sqlite3, os, time, hashlib, requests
from datetime import datetime
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

def country():
    try:
        return requests.get("http://ip-api.com/json", timeout=3).json().get("country","Unknown")
    except:
        return "Unknown"

def expired(ts): 
    return int(time.time()) > ts

# ================= PAGE CONFIG =================
st.set_page_config("🔥 Secure Viral Share | Ghulam Mustafa", layout="centered")

# ================= STYLES =================
st.markdown("""
<style>
.stApp {
    background: linear-gradient(135deg,#667eea,#764ba2);
    animation: bgMove 12s ease infinite;
}
@keyframes bgMove {
    0% {background-position:0% 50%;}
    50% {background-position:100% 50%;}
    100% {background-position:0% 50%;}
}
.card {
    background: rgba(255,255,255,0.18);
    backdrop-filter: blur(18px);
    padding: 2rem;
    border-radius: 20px;
    box-shadow: 0 10px 40px rgba(0,0,0,0.35);
    margin-bottom:1.8rem;
    color:white;
    animation: fadeUp 1s ease;
}
@keyframes fadeUp {
    from {opacity:0; transform:translateY(30px);}
    to {opacity:1; transform:translateY(0);}
}
.title {
    font-size:2.7rem;
    font-weight:900;
    text-align:center;
}
.creator {
    text-align:center;
    font-size:1.2rem;
    letter-spacing:3px;
    margin-top:0.6rem;
    animation: float 3s ease-in-out infinite;
}
@keyframes float {
    0% {transform: translateY(0px);}
    50% {transform: translateY(-10px);}
    100% {transform: translateY(0px);}
}
.footer {
    text-align:center;
    padding:1rem;
    margin-top:3rem;
    color:#fff;
    font-size:1rem;
    letter-spacing:1px;
    animation: pulse 2.5s infinite;
}
@keyframes pulse {
    0% {opacity:0.6;}
    50% {opacity:1;}
    100% {opacity:0.6;}
}
button { border-radius:14px !important; }
</style>
""", unsafe_allow_html=True)

# ================= HEADER =================
st.markdown("""
<div class="card">
    <div class="title">🔐 Secure Viral File & Text Share</div>
    <div class="creator">✨ Crafted with ❤️ by <b>Ghulam Mustafa</b> ✨</div>
</div>
""", unsafe_allow_html=True)

# ================= NAV =================
menu = st.sidebar.radio("📌 Navigation", ["📤 Upload", "🔓 Access", "🛠 Admin"])

# ================= UPLOAD =================
if menu == "📤 Upload":
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("📤 Upload File / Text")

    utype = st.radio("Choose Type", ["File", "Text"])
    password = st.text_input("🔑 Password (6–10 chars)", type="password")
    expiry = st.number_input("⏰ Password expiry (minutes)", 1, 1440, 60)
    expiry_ts = int(time.time()) + expiry * 60

    view = st.checkbox("👁 One-Time View")
    view_sec = st.slider("View Seconds", 1, 600, 10) if view else 0

    one_dl = st.checkbox("⬇ One-Time Download")
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
        if not file:
            st.error("Upload file or enter text")
            st.stop()

        fname, fpath = None, None
        if utype == "File":
            fname = file.name
            fpath = UPLOAD_DIR / f"{int(time.time())}_{fname}"
            with open(fpath,"wb") as f:
                f.write(file.read())

        c.execute("""
        INSERT INTO files VALUES (NULL,?,?,?,?,?,?,?,?,?,?,?, ?,?,?,?)
        """,(fname,str(fpath) if fpath else None,text_data,
             hash_pwd(password),expiry_ts,
             view_sec,int(view),int(one_dl),max_dl,
             0,0,country(),None,str(datetime.now()),None))
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
        if not r: st.error("❌ Invalid password"); st.stop()
        if expired(r[5]): st.error("⏰ Password expired"); st.stop()
        if r[10] >= r[9]: st.error("⬇ Download limit reached"); st.stop()
        if r[7] and r[11]: st.error("👁 View already used"); st.stop()

        if r[6] > 0:
            st.info(f"👁 Viewing for {r[6]} seconds...")
            time.sleep(r[6])
            c.execute("UPDATE files SET viewed=1 WHERE id=?", (r[0],))
            conn.commit()

        if r[1]:
            with open(r[2],"rb") as f:
                st.download_button("⬇ Download File", f, file_name=r[1])
        else:
            st.download_button("⬇ Download Text", r[3], file_name="text.txt")

        c.execute("""
        UPDATE files SET download_count=download_count+1,
        download_country=?, download_time=?
        WHERE id=?
        """,(country(),str(datetime.now()),r[0]))
        conn.commit()
    st.markdown("</div>", unsafe_allow_html=True)

# ================= ADMIN =================
else:
    st.markdown("<div class='card'>", unsafe_allow_html=True)
    st.subheader("🛠 Admin Panel")
    ap = st.text_input("Admin Password", type="password")
    if ADMIN_PASSWORD and ap == ADMIN_PASSWORD:
        st.success("👑 Welcome Admin")
        c.execute("SELECT * FROM files")
        for r in c.fetchall():
            with st.expander(f"📦 File ID {r[0]}"):
                st.write("🌍 Upload:", r[12])
                st.write("🌍 Download:", r[13])
                st.write("⏰ Upload Time:", r[14])
                st.write("⏰ Download Time:", r[15])
                if r[1]:
                    with open(r[2],"rb") as f:
                        st.download_button("⬇ Admin Download", f, file_name=r[1], key=r[0])
                else:
                    st.text_area("Text Content", r[3])
    st.markdown("</div>", unsafe_allow_html=True)

# ================= FOOTER =================
st.markdown("""
<div class="footer">
© 2026 Secure File/Text Share | Crafted with ❤️ by <b>Ghulam Mustafa</b>
</div>
""", unsafe_allow_html=True)
