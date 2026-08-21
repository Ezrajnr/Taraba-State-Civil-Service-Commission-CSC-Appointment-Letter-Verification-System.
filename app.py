import streamlit as st
import pandas as pd
import hashlib
import json
import datetime
import qrcode
from io import BytesIO
from PIL import Image

# -----------------------------------------------------------------------------
# PAGE CONFIGURATION
# -----------------------------------------------------------------------------
st.set_page_config(
    page_title="Taraba State CSC - Appointment Verification",
    page_icon="📜",
    layout="wide"
)

# Custom Styling for Official State Branding
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
# DATABASE INITIALIZATION (SESSION STATE)
# -----------------------------------------------------------------------------
if 'csc_registry' not in st.session_state:
    # Seed with sample official appointments
    seed_records = [
        {
            "CSSN": "TSCSC/2025/APT/0104",
            "File_No": "TS/CSC/P/18204",
            "Full_Name": "Danladi Musa Ibrahim",
            "MDA": "Ministry of Finance, Budget & Economic Planning",
            "Cadre": "Administrative Officer II",
            "Grade_Level": "GL 08",
            "Date_Issued": "2025-03-15",
            "Status": "ACTIVE",
            "Doc_Hash": generate_document_hash("TS/CSC/P/18204", "Danladi Musa Ibrahim", "Ministry of Finance, Budget & Economic Planning", "GL 08", "2025-03-15")
        },
        {
            "CSSN": "TSCSC/2024/APT/0892",
            "File_No": "TS/CSC/M/09211",
            "Full_Name": "Amina Usman Bello",
            "MDA": "Ministry of Education",
            "Cadre": "Education Officer I",
            "Grade_Level": "GL 09",
            "Date_Issued": "2024-11-01",
            "Status": "ACTIVE",
            "Doc_Hash": generate_document_hash("TS/CSC/M/09211", "Amina Usman Bello", "Ministry of Education", "GL 09", "2024-11-01")
        }
    ]
    st.session_state.csc_registry = pd.DataFrame(seed_records)

if 'verification_audit_log' not in st.session_state:
    st.session_state.verification_audit_log = pd.DataFrame(columns=[
        "Timestamp", "Search_Query", "Verdict", "Details"
    ])

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
    st.caption("Cross-examine presented appointment letters against the Taraba State CSC Master Registry.")
    
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
                registry = st.session_state.csc_registry
                matched_record = registry[registry['CSSN'].str.upper() == search_cssn.upper()]
                
                timestamp = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                if not matched_record.empty:
                    rec = matched_record.iloc[0]
                    st.success("🟢 AUTHENTIC APPOINTMENT LETTER VERIFIED")
                    
                    st.markdown("### Official Record Details")
                    res_col1, res_col2 = st.columns(2)
                    with res_col1:
                        st.write(f"**Full Name:** {rec['Full_Name']}")
                        st.write(f"**Staff File Number:** {rec['File_No']}")
                        st.write(f"**MDA Assigned:** {rec['MDA']}")
                    with res_col2:
                        st.write(f"**Cadre/Post:** {rec['Cadre']}")
                        st.write(f"**Grade Level:** {rec['Grade_Level']}")
                        st.write(f"**Date of Issue:** {rec['Date_Issued']}")
                        st.write(f"**Record Status:** `{rec['Status']}`")
                        
                    st.info(f"**Cryptographic Document Hash (SHA-256):** `{rec['Doc_Hash']}`")
                    
                    # Log Audit
                    new_log = pd.DataFrame([{
                        "Timestamp": timestamp,
                        "Search_Query": search_cssn,
                        "Verdict": "🟢 VERIFIED",
                        "Details": f"Match found for {rec['Full_Name']} ({rec['File_No']})"
                    }])
                    st.session_state.verification_audit_log = pd.concat([new_log, st.session_state.verification_audit_log], ignore_index=True)
                    
                else:
                    st.error("🔴 FAKE LETTER DETECTED / RECORD NOT FOUND")
                    st.warning("⚠️ No appointment record matching this Serial Number exists in the Taraba State CSC Registry. This document is unauthorized or fraudulent.")
                    
                    # Log Audit
                    new_log = pd.DataFrame([{
                        "Timestamp": timestamp,
                        "Search_Query": search_cssn,
                        "Verdict": "🔴 FAKE / NOT FOUND",
                        "Details": "Unrecognized Serial Number searched."
                    }])
                    st.session_state.verification_audit_log = pd.concat([new_log, st.session_state.verification_audit_log], ignore_index=True)

        else:
            st.markdown("#### Input Letter Attributes for Tamper Audit")
            v_cssn = st.text_input("Serial Number (CSSN)", value="TSCSC/2025/APT/0104")
            v_file_no = st.text_input("File Number", value="TS/CSC/P/18204")
            v_name = st.text_input("Full Name", value="Danladi Musa Ibrahim")
            v_mda = st.text_input("MDA", value="Ministry of Finance, Budget & Economic Planning")
            v_gl = st.selectbox("Grade Level", ["GL 07", "GL 08", "GL 09", "GL 10", "GL 12", "GL 13", "GL 14"])
            v_date = st.date_input("Date Issued", datetime.date(2025, 3, 15))
            
            if st.button("🔐 Run Hash Tamper Audit", type="primary"):
                computed_hash = generate_document_hash(v_file_no, v_name, v_mda, v_gl, str(v_date))
                
                registry = st.session_state.csc_registry
                matched_record = registry[registry['CSSN'].str.upper() == v_cssn.strip().upper()]
                
                if matched_record.empty:
                    st.error("🔴 FAKE APPOINTMENT LETTER: Serial Number does not exist in state records.")
                else:
                    official_hash = matched_record.iloc[0]['Doc_Hash']
                    if computed_hash == official_hash:
                        st.success("🟢 DOCUMENT UNTAMPERED: All details match official records perfectly.")
                    else:
                        st.error("🚨 FORGED / TAMPERED LETTER DETECTED!")
                        st.write("The Serial Number exists, but **the details on this document (Grade Level, Name, or MDA) have been altered post-issuance**.")
                        st.write(f"**Expected Hash:** `{official_hash}`")
                        st.write(f"**Computed Hash:** `{computed_hash}`")

# -----------------------------------------------------------------------------
# TAB 2: CSC ADMIN LETTER ISSUANCE
# -----------------------------------------------------------------------------
with tab2:
    st.subheader("Generate Official Civil Service Appointment Letter")
    st.caption("Authorized CSC Officers only. Generates letters with embedded QR codes and security hashes.")
    
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
            # Generate Unique CSSN and Hash
            year = in_date.year
            rand_seq = datetime.datetime.now().strftime("%S%f")[:4]
            generated_cssn = f"TSCSC/{year}/APT/{rand_seq}"
            
            doc_hash = generate_document_hash(in_file_no, in_full_name, in_mda, in_gl, str(in_date))
            
            # Store in session database
            new_record = {
                "CSSN": generated_cssn,
                "File_No": in_file_no.upper(),
                "Full_Name": in_full_name,
                "MDA": in_mda,
                "Cadre": in_cadre,
                "Grade_Level": in_gl,
                "Date_Issued": str(in_date),
                "Status": "ACTIVE",
                "Doc_Hash": doc_hash
            }
            
            st.session_state.csc_registry = pd.concat([
                pd.DataFrame([new_record]), 
                st.session_state.csc_registry
            ], ignore_index=True)
            
            st.success(f"✅ Appointment Record Registered Successfully! Serial No: **{generated_cssn}**")
            
            # Generate Security QR Code
            qr_payload = {
                "CSSN": generated_cssn,
                "File_No": in_file_no.upper(),
                "Name": in_full_name,
                "Hash": doc_hash
            }
            qr_bytes = create_qr_code(qr_payload)
            
            # Display Generated Document Preview
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
                
                *This letter is cryptographically signed and registered with the state verification engine.*
                """)
            
            with preview_col2:
                st.image(qr_bytes, caption="Verification QR Code", width=150)
                st.caption(f"Hash: `{doc_hash[:10]}...`")

# -----------------------------------------------------------------------------
# TAB 3: REGISTRY DATABASE & AUDIT TRAIL
# -----------------------------------------------------------------------------
with tab3:
    st.subheader("Master Appointment Registry")
    
    st.dataframe(
        st.session_state.csc_registry,
        use_container_width=True,
        hide_index=True
    )
    
    # Download Registry as CSV
    csv_bytes = st.session_state.csc_registry.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="📥 Export Master Registry CSV",
        data=csv_bytes,
        file_name="taraba_csc_appointment_registry.csv",
        mime="text/csv"
    )
    
    st.markdown("---")
    st.subheader("Verification Audit Trail")
    st.caption("Logs of all lookups and fake letter detection alerts.")
    
    if st.session_state.verification_audit_log.empty:
        st.info("No verification requests logged yet.")
    else:
        st.dataframe(
            st.session_state.verification_audit_log,
            use_container_width=True,
            hide_index=True
        )
