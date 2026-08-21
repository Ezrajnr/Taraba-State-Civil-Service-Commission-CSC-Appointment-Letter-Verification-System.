import streamlit as st
import pandas as pd
import hashlib
import json
import datetime
import sqlite3
import qrcode
from io import BytesIO

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION & STYLING
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Taraba State CSC - Appointment Verification",
    page_icon="📜",
    layout="wide"
)

st.markdown("""
    <style>
    .main-header {
        font-size: 26px;
        font-weight: bold;
        color: #1B5E20;
        text-align: center;
        margin-bottom: 5px;
    }
    .sub-header {
        font-size: 16px;
        color: #333333;
        text-align: center;
        margin-bottom: 25px;
    }
    </style>
""", unsafe_allow_html=True)

st.markdown('<div class="main-header">GOVERNMENT OF TARABA STATE OF NIGERIA</div>', unsafe_allow_html=True)
st.markdown('<div class="sub-header">Civil Service Commission, P.M.B. 1024, Jalingo, Taraba State<br><b>Document Authenticity & Fake Appointment Letter Detection System</b></div>', unsafe_allow_html=True)
st.markdown("---")

# -----------------------------------------------------------------------------
# DATABASE MANAGEMENT (SQLITE)
# -----------------------------------------------------------------------------
DB_FILE = "csc_database.db"

def init_db():
    """Initializes the SQLite database tables and seeds default records if empty."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    
    # Master Registry Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS registry (
            cssn TEXT PRIMARY KEY,
            file_no TEXT,
            full_name TEXT,
            mda TEXT,
            cadre TEXT,
            grade_level TEXT,
            date_issued TEXT,
            status TEXT,
            doc_hash TEXT
        )
    ''')
    
    # Audit Logs Table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT,
            search_query TEXT,
            verdict TEXT,
            details TEXT
        )
    ''')
    
    conn.commit()
    
    # Seed default data if table is completely empty
    cursor.execute("SELECT COUNT(*) FROM registry")
    count = cursor.fetchone()[0]
    
    if count == 0:
        seed_records = [
            ("TSCSC/2025/APT/0104", "TS/CSC/P/18204", "Danladi Musa Ibrahim", "Ministry of Finance, Budget & Economic Planning", "Administrative Officer II", "GL 08", "2025-03-15", "ACTIVE", generate_document_hash("TS/CSC/P/18204", "Danladi Musa Ibrahim", "Ministry of Finance, Budget & Economic Planning", "GL 08", "2025-03-15")),
            ("TSCSC/2024/APT/0892", "TS/CSC/M/09211", "Amina Usman Bello", "Ministry of Education", "Education Officer I", "GL 09", "2024-11-01", "ACTIVE", generate_document_hash("TS/CSC/M/09211", "Amina Usman Bello", "Ministry of Education", "GL 09", "2024-11-01"))
        ]
        cursor.executemany('''
            INSERT INTO registry (cssn, file_no, full_name, mda, cadre, grade_level, date_issued, status, doc_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', seed_records)
        conn.commit()
        
    conn.close()

def save_appointment(cssn, file_no, full_name, mda, cadre, grade_level, date_issued, status, doc_hash):
    """Saves a new appointment record permanently to SQLite."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    cursor.execute('''
        INSERT OR REPLACE INTO registry (cssn, file_no, full_name, mda, cadre, grade_level, date_issued, status, doc_hash)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (cssn.strip().upper(), file_no.strip().upper(), full_name.strip(), mda.strip(), cadre.strip(), grade_level.strip(), str(date_issued), status, doc_hash))
    conn.commit()
    conn.close()

def get_appointment_by_cssn(cssn):
    """Retrieves an appointment record from SQLite by CSSN."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM registry WHERE UPPER(cssn) = UPPER(?)", conn, params=(cssn.strip(),))
    conn.close()
    return df

def get_all_appointments():
    """Retrieves all registered records from SQLite."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT * FROM registry ORDER BY date_issued DESC", conn)
    conn.close()
    return df

def log_audit(search_query, verdict, details):
    """Logs verification attempts to SQLite."""
    conn = sqlite3.connect(DB_FILE)
    cursor = conn.cursor()
    timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    cursor.execute('''
        INSERT INTO audit_logs (timestamp, search_query, verdict, details)
        VALUES (?, ?, ?, ?)
    ''', (timestamp, search_query, verdict, details))
    conn.commit()
    conn.close()

def get_all_audit_logs():
    """Retrieves all verification audit logs."""
    conn = sqlite3.connect(DB_FILE)
    df = pd.read_sql_query("SELECT timestamp, search_query, verdict, details FROM audit_logs ORDER BY id DESC", conn)
    conn.close()
    return df

# Initialize Database on Run
init_db()

# -----------------------------------------------------------------------------
# CRYPTOGRAPHIC UTILITIES
# -----------------------------------------------------------------------------
def generate_document_hash(file_no, full_name, mda, grade_level, date_issued):
    """Computes a SHA-256 cryptographic signature for letter contents."""
    payload = f"{file_no.strip().upper()}|{full_name.strip().upper()}|{mda.strip().upper()}|{str(grade_level).strip()}|{str(date_issued).strip()}"
    return hashlib.sha256(payload.encode('utf-8')).hexdigest()

def create_qr_code(data_dict):
    """Generates an in-memory QR code image containing JSON payload."""
    json_payload = json.dumps(data_dict)
    qr = qrcode.QRCode(version=1, box_size=5, border=2)
    qr.add_data(json_payload)
    qr.make(fit=True)
    img = qr.make_image(fill_color="#1B5E20", back_color="white")
    
    buf = BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

# -----------------------------------------------------------------------------
# APPLICATION TABS
# -----------------------------------------------------------------------------
tab1, tab2, tab3 = st.tabs([
    "🔍 Real-Time Document Verification", 
    "✍️ CSC Letter Issuance (Admin)", 
    "📋 Master Registry & Audit Logs"
])

# -----------------------------------------------------------------------------
# TAB 1: REAL-TIME VERIFICATION ENGINE
# -----------------------------------------------------------------------------
with tab1:
    st.subheader("Verify Appointment Letter Authenticity")
    st.caption("Cross-examine presented appointment letters against the Taraba State CSC Persistent Database.")
    
    col_mode1, col_mode2 = st.columns([1, 2])
    
    with col_mode1:
        verification_method = st.radio(
            "Verification Input Mode",
            ["Serial Number (CSSN) Lookup", "Manual Feature Hash Comparison"]
        )
    
    with col_mode2:
        if verification_method == "Serial Number (CSSN) Lookup":
            search_cssn = st.text_input("Enter Civil Service Serial Number (CSSN)", placeholder="e.g. TSCSC/2025/APT/0104").strip()
            verify_btn = st.button("🔎 Audit Document Authenticity", type="primary", use_container_width=True)
            
            if verify_btn and search_cssn:
                matched_record = get_appointment_by_cssn(search_cssn)
                
                if not matched_record.empty:
                    rec = matched_record.iloc[0]
                    st.success("🟢 AUTHENTIC APPOINTMENT LETTER VERIFIED")
                    
                    st.markdown("### Official Record Details")
                    res_col1, res_col2 = st.columns(2)
                    with res_col1:
                        st.write(f"**Full Name:** {rec['full_name']}")
                        st.write(f"**Staff File Number:** {rec['file_no']}")
                        st.write(f"**MDA Assigned:** {rec['mda']}")
                    with res_col2:
                        st.write(f"**Cadre/Post:** {rec['cadre']}")
                        st.write(f"**Grade Level:** {rec['grade_level']}")
                        st.write(f"**Date of Issue:** {rec['date_issued']}")
                        st.write(f"**Record Status:** `{rec['status']}`")
                        
                    st.info(f"**Cryptographic Document Hash (SHA-256):** `{rec['doc_hash']}`")
                    
                    log_audit(search_cssn, "🟢 VERIFIED", f"Match found for {rec['full_name']} ({rec['file_no']})")
                    
                else:
                    st.error("🔴 FAKE LETTER DETECTED / RECORD NOT FOUND")
                    st.warning("⚠️ No appointment record matching this Serial Number exists in the Taraba State CSC Database. This document is unauthorized or fraudulent.")
                    
                    log_audit(search_cssn, "🔴 FAKE / NOT FOUND", "Unrecognized Serial Number searched.")

        else:
            st.markdown("#### Input Letter Attributes for Tamper Audit")
            v_cssn = st.text_input("Serial Number (CSSN)", value="TSCSC/2025/APT/0104").strip()
            v_file_no = st.text_input("File Number", value="TS/CSC/P/18204").strip()
            v_name = st.text_input("Full Name", value="Danladi Musa Ibrahim").strip()
            v_mda = st.text_input("MDA", value="Ministry of Finance, Budget & Economic Planning").strip()
            v_gl = st.selectbox("Grade Level", ["GL 07", "GL 08", "GL 09", "GL 10", "GL 12", "GL 13", "GL 14"])
            v_date = st.date_input("Date Issued", datetime.date(2025, 3, 15))
            
            if st.button("🔐 Run Hash Tamper Audit", type="primary"):
                computed_hash = generate_document_hash(v_file_no, v_name, v_mda, v_gl, str(v_date))
                
                matched_record = get_appointment_by_cssn(v_cssn)
                
                if matched_record.empty:
                    st.error("🔴 FAKE APPOINTMENT LETTER: Serial Number does not exist in state records.")
                    log_audit(v_cssn, "🔴 FAKE / NOT FOUND", "Manual tamper audit with invalid CSSN.")
                else:
                    official_hash = matched_record.iloc[0]['doc_hash']
                    if computed_hash == official_hash:
                        st.success("🟢 DOCUMENT UNTAMPERED: All details match official records perfectly.")
                        log_audit(v_cssn, "🟢 VERIFIED", "Tamper hash check passed.")
                    else:
                        st.error("🚨 FORGED / TAMPERED LETTER DETECTED!")
                        st.write("The Serial Number exists, but **the details on this document have been altered post-issuance**.")
                        st.write(f"**Expected Hash:** `{official_hash}`")
                        st.write(f"**Computed Hash:** `{computed_hash}`")
                        log_audit(v_cssn, "🚨 TAMPERED", "Document details differ from database hash.")

# -----------------------------------------------------------------------------
# TAB 2: CSC ADMIN LETTER ISSUANCE
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Generate Official Civil Service Appointment Letter")
    st.caption("Authorized CSC Officers only. Permanently registers letters to SQLite with embedded security markers.")
    
    with st.form("issue_letter_form"):
        col_a, col_b = st.columns(2)
        
        with col_a:
            in_file_no = st.text_input("Staff File Number", placeholder="e.g. TS/CSC/P/20491")
            in_full_name = st.text_input("Candidate Full Name", placeholder="e.g. James Ezekiel Taraba")
            in_mda = st.selectbox("Assign MDA", [
                "Ministry of Agriculture & Natural Resources",
                "Ministry of Education",
                "Ministry of Health",
                "Ministry of Works & Transport",
                "Ministry of Finance, Budget & Economic Planning",
                "Taraba State Board of Internal Revenue"
            ])
            
        with col_b:
            in_cadre = st.text_input("Cadre / Designation", placeholder="e.g. Senior Accountant")
            in_gl = st.selectbox("Grade Level Allocated", ["GL 07", "GL 08", "GL 09", "GL 10", "GL 12", "GL 13", "GL 14"])
            in_date = st.date_input("Date of Appointment", datetime.date.today())
            
        submit_issue = st.form_submit_button("📜 Register & Generate Verifiable Letter")
        
    if submit_issue:
        if not in_file_no or not in_full_name:
            st.error("Please fill in all required fields (File Number and Candidate Name).")
        else:
            year = in_date.year
            rand_seq = datetime.datetime.now().strftime("%S%f")[:4]
            generated_cssn = f"TSCSC/{year}/APT/{rand_seq}"
            
            doc_hash = generate_document_hash(in_file_no, in_full_name, in_mda, in_gl, str(in_date))
            
            # Save Permanently to SQLite
            save_appointment(
                generated_cssn, in_file_no, in_full_name, 
                in_mda, in_cadre, in_gl, in_date, "ACTIVE", doc_hash
            )
            
            st.success(f"✅ Appointment Record Registered Permanently! Serial No: **{generated_cssn}**")
            
            # Generate Security QR Code
            qr_payload = {
                "CSSN": generated_cssn,
                "File_No": in_file_no.upper().strip(),
                "Name": in_full_name.strip(),
                "Hash": doc_hash
            }
            qr_bytes = create_qr_code(qr_payload)
            
            st.markdown("---")
            st.markdown("### 📄 Generated Document Preview")
            
            preview_col1, preview_col2 = st.columns([3, 1])
            
            with preview_col1:
                st.markdown(f"""
                **CIVIL SERVICE COMMISSION, TARABA STATE**  
                **Serial No:** `{generated_cssn}`  
                **Date:** {in_date.strftime('%B %d, %Y')}  
                
                **OFFER OF APPOINTMENT**  
                
                To: **{in_full_name.upper()}** ({in_file_no.upper()})  
                
                I am directed to inform you that the Civil Service Commission, Taraba State, has approved your appointment as **{in_cadre}** on **{in_gl}** in the **{in_mda}**.  
                
                *This letter is cryptographically signed and permanently saved in the state database.*
                """)
            
            with preview_col2:
                st.image(qr_bytes, caption="Verification QR Code", width=150)
                st.caption(f"Hash: `{doc_hash[:10]}...`")

# -----------------------------------------------------------------------------
# TAB 3: REGISTRY DATABASE & AUDIT TRAIL
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Master Appointment Registry (SQLite Database)")
    
    registry_df = get_all_appointments()
    st.dataframe(
        registry_df,
        use_container_width=True,
        hide_index=True
    )
    
    # Download Registry as CSV
    csv_bytes = registry_df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Master Registry CSV",
        data=csv_bytes,
        file_name="taraba_csc_appointment_registry.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    st.subheader("Verification Audit Logs")
    
    audit_df = get_all_audit_logs()
    if audit_df.empty:
        st.info("No verification attempts logged yet.")
    else:
        st.dataframe(
            audit_df,
            use_container_width=True,
            hide_index=True
        )
