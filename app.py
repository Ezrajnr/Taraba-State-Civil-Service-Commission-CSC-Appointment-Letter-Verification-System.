import streamlit as st
import pandas as pd
import urllib.parse
from datetime import datetime
from sqlalchemy import create_engine, text

# ==========================================
# 1. PAGE CONFIGURATION & STYLING
# ==========================================
st.set_page_config(
    page_title="Taraba State CSC - Appointment Verification System",
    page_icon="📜",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Custom CSS Styling
st.markdown(
    """
    <style>
    .main-header {
        text-align: center;
        padding: 10px 0;
        border-bottom: 2px solid #006699;
        margin-bottom: 20px;
    }
    .verified-badge {
        background-color: #d4edda;
        color: #155724;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #c3e6cb;
        margin: 15px 0;
    }
    .unverified-badge {
        background-color: #f8d7da;
        color: #721c24;
        padding: 15px;
        border-radius: 8px;
        border: 1px solid #f5c6cb;
        margin: 15px 0;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

# ==========================================
# 2. DATABASE CONNECTION & INITIALIZATION
# ==========================================
@st.cache_resource
def get_db_engine():
    """
    Safely builds SQLAlchemy engine using structured secrets
    and encodes special characters in passwords.
    """
    try:
        if "postgres" in st.secrets and "user" in st.secrets["postgres"]:
            pg = st.secrets["postgres"]
            user = pg["user"]
            # Encodes special characters (@, #, !, %, etc.) in password
            password = urllib.parse.quote_plus(pg["password"])
            host = pg["host"]
            port = pg["port"]
            dbname = pg["dbname"]
            db_url = f"postgresql://{user}:{password}@{host}:{port}/{dbname}"
        else:
            db_url = st.secrets["postgres"]["url"]

        return create_engine(db_url, pool_pre_ping=True, pool_size=5, max_overflow=10)
    except Exception as e:
        st.error("Configuration Error: Failed to parse secrets for database connection.")
        st.code(str(e), language="bash")
        st.stop()

engine = get_db_engine()

def init_db():
    """Initializes tables in Supabase PostgreSQL if they do not exist."""
    create_registry_table = """
    CREATE TABLE IF NOT EXISTS csc_registry (
        id SERIAL PRIMARY KEY,
        file_number VARCHAR(100) UNIQUE NOT NULL,
        full_name VARCHAR(255) NOT NULL,
        cadre VARCHAR(150) NOT NULL,
        grade_level VARCHAR(50) NOT NULL,
        mda VARCHAR(255) NOT NULL,
        date_of_appointment DATE NOT NULL,
        qr_code_id VARCHAR(100) UNIQUE NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    create_audit_table = """
    CREATE TABLE IF NOT EXISTS csc_audit_logs (
        id SERIAL PRIMARY KEY,
        search_query VARCHAR(255) NOT NULL,
        search_status VARCHAR(50) NOT NULL,
        timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """
    
    try:
        with engine.begin() as conn:
            conn.execute(text(create_registry_table))
            conn.execute(text(create_audit_table))
    except Exception as e:
        st.error("Database Initialization Error: Unable to connect or execute setup.")
        st.code(str(e), language="bash")
        st.stop()

# Run DB Initialization
init_db()

# ==========================================
# 3. HELPER FUNCTIONS
# ==========================================
import io
import qrcode

def generate_qr_code(data_string: str) -> bytes:
    """
    Generates a PNG QR code image as bytes in memory.
    """
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=4,
    )
    qr.add_data(data_string)
    qr.make(fit=True)
    
    img = qr.make_image(fill_color="black", back_color="white")
    
    # Save image to in-memory byte buffer
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()
def log_audit_search(query: str, status: str):
    """Logs verification lookup attempts for security audit trailing."""
    try:
        with engine.begin() as conn:
            conn.execute(
                text("INSERT INTO csc_audit_logs (search_query, search_status) VALUES (:q, :s)"),
                {"q": query.strip().upper(), "s": status}
            )
    except Exception as e:
        st.warning(f"Audit log warning: {e}")

def verify_appointment(search_key: str):
    """Searches the CSC registry by File Number or QR Code ID."""
    query_text = """
    SELECT file_number, full_name, cadre, grade_level, mda, date_of_appointment, qr_code_id, created_at
    FROM csc_registry
    WHERE UPPER(file_number) = :key OR UPPER(qr_code_id) = :key
    LIMIT 1;
    """
    with engine.connect() as conn:
        result = conn.execute(text(query_text), {"key": search_key.strip().upper()}).fetchone()
        return result

def add_record(file_number, full_name, cadre, grade_level, mda, date_of_appointment, qr_code_id):
    """Adds a new appointment record to the registry."""
    insert_text = """
    INSERT INTO csc_registry (file_number, full_name, cadre, grade_level, mda, date_of_appointment, qr_code_id)
    VALUES (:file_num, :name, :cadre, :gl, :mda, :doa, :qr_id);
    """
    with engine.begin() as conn:
        conn.execute(
            text(insert_text),
            {
                "file_num": file_number.strip().upper(),
                "name": full_name.strip().title(),
                "cadre": cadre.strip(),
                "gl": grade_level.strip(),
                "mda": mda.strip(),
                "doa": date_of_appointment,
                "qr_id": qr_code_id.strip().upper()
            }
        )

# ==========================================
# 4. USER INTERFACE (SIDEBAR & NAVIGATION)
# ==========================================
st.sidebar.image("https://upload.wikimedia.org/wikipedia/commons/a/a8/Coat_of_arms_of_Nigeria.svg", width=100)
st.sidebar.title("Taraba State CSC")
st.sidebar.markdown("**Appointment Letter Verification System**")

page = st.sidebar.radio("Navigation", ["🔍 Public Verification Portal", "🔐 Admin Dashboard"])

# ==========================================
# 5. PUBLIC VERIFICATION PORTAL
# ==========================================
if page == "🔍 Public Verification Portal":
    st.markdown("<div class='main-header'><h2>TARABA STATE CIVIL SERVICE COMMISSION</h2><p>Official Verification Portal for CSC Appointment Letters</p></div>", unsafe_allow_html=True)
    
    st.info("💡 Enter the **CSC Reference / File Number** or scan the **QR Code ID** printed on the appointment letter to verify its authenticity.")

    col1, col2 = st.columns([3, 1])
    with col1:
        search_input = st.text_input("Enter Reference Number / File No / QR ID:", placeholder="e.g. TSB/CSC/2024/001 or QR-100234")
    with col2:
        st.write("")
        st.write("")
        verify_btn = st.button("Verify Letter", type="primary", use_container_width=True)

    if verify_btn or search_input:
        if not search_input.strip():
            st.warning("Please enter a valid reference number or QR code ID.")
        else:
            record = verify_appointment(search_input)
            
            if record:
                log_audit_search(search_input, "VERIFIED_AUTHENTIC")
                st.markdown(
                    f"""
                    <div class='verified-badge'>
                        <h3>✅ OFFICIAL RECORD VERIFIED</h3>
                        <p>This appointment letter is authentic and registered in the Taraba State Civil Service Commission Database.</p>
                    </div>
                    """,
                    unsafe_allow_html=True
                )
                
                # Display Verification Details
                res_col1, res_col2 = st.columns(2)
                with res_col1:
                    st.markdown(f"**Full Name:** {record.full_name}")
                    st.markdown(f"**File Number:** {record.file_number}")
                    st.markdown(f"**Cadre/Post:** {record.cadre}")
                    st.markdown(f"**Grade Level:** {record.grade_level}")
                
                with res_col2:
                    st.markdown(f"**Ministry / MDA:** {record.mda}")
                    st.markdown(f"**Date of Appointment:** {record.date_of_appointment.strftime('%B %d, %Y')}")
                    st.markdown(f"**System Security ID:** `{record.qr_code_id}`")
                    st.markdown(f"**Verification Timestamp:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S WAT')}")
                    
            # ==========================================
# 6. ADMIN DASHBOARD WITH FORM LOGIN
# ==========================================
elif page == "🔐 Admin Dashboard":
    st.markdown("<div class='main-header'><h2>CSC Admin Registry Management</h2></div>", unsafe_allow_html=True)
    
    SECRET_ADMIN_PASS = st.secrets.get("admin", {}).get("password", "TarabaCSC2026!")

    # Check session state for login
    if not st.session_state["admin_logged_in"]:
        col1, col2, col3 = st.columns([1, 2, 1])
        with col2:
            st.subheader("Administrator Login")
            with st.form("admin_login_form"):
                password_input = st.text_input("Enter Admin Password", type="password")
                login_button = st.form_submit_button("Sign In to Portal", type="primary", use_container_width=True)
                
                if login_button:
                    if password_input == SECRET_ADMIN_PASS:
                        st.session_state["admin_logged_in"] = True
                        st.success("Authentication Successful!")
                        st.rerun()
                    else:
                        st.error("Invalid Administrative Password.")
    else:
        # Show logged in status and logout button in sidebar
        st.sidebar.success("Status: Authenticated Admin")
        if st.sidebar.button("Logout of Admin Session", type="secondary"):
            st.session_state["admin_logged_in"] = False
            st.rerun()

        # -------------------------------------------------------------
        # TABS MUST BE CREATED INSIDE THIS 'ELSE' BLOCK (AUTHENTICATED)
        # -------------------------------------------------------------
        tab1, tab2, tab3 = st.tabs(["➕ Add New Record", "📋 View All Records", "📊 Audit Log Trail"])
        
        # TAB 1: ADD RECORD & GENERATE QR CODE
        with tab1:
            st.subheader("Register New Appointment Letter")
            with st.form("add_record_form", clear_on_submit=False):
                col1, col2 = st.columns(2)
                with col1:
                    file_no = st.text_input("File Number *", placeholder="TSB/CSC/2026/045")
                    full_name = st.text_input("Full Name *", placeholder="e.g. John Danjuma Bako")
                    cadre = st.text_input("Cadre / Post *", placeholder="Administrative Officer II")
                    grade_level = st.selectbox("Grade Level *", [f"GL {i:02d}" for i in range(1, 18)])
                
                with col2:
                    mda = st.text_input("Ministry / Department / Agency *", placeholder="Ministry of Finance, Budget & Economic Planning")
                    doa = st.date_input("Date of Effective Appointment")
                    qr_code_id = st.text_input("Generated Security/QR ID *", placeholder="QR-2026-9901")
                
                submitted = st.form_submit_button("Save Record & Generate QR Code", type="primary")
                
                if submitted:
                    if not (file_no and full_name and cadre and mda and qr_code_id):
                        st.error("Please fill in all required fields marked with *")
                    else:
                        try:
                            # 1. Save to Supabase DB
                            add_record(file_no, full_name, cadre, grade_level, mda, doa, qr_code_id)
                            st.success(f"Successfully registered appointment for {full_name} ({file_no})!")
                            
                            # 2. Build verification data payload for QR code
                            qr_payload = f"TARABA STATE CSC VERIFICATION\nFile No: {file_no.upper()}\nSecurity ID: {qr_code_id.upper()}\nName: {full_name}"
                            
                            # 3. Generate PNG QR bytes
                            qr_img_bytes = generate_qr_code(qr_payload)
                            
                            # 4. Display and Download UI
                            st.divider()
                            st.subheader("Generated Official Security QR Code")
                            qr_col1, qr_col2 = st.columns([1, 2])
                            
                            with qr_col1:
                                st.image(qr_img_bytes, caption=f"QR Code for {file_no.upper()}", width=200)
                            
                            with qr_col2:
                                st.markdown("### Print Ready Badge")
                                st.write("Download this QR code PNG and attach/print it onto the official physical appointment letter.")
                                
                                st.download_button(
                                    label="📥 Download QR Code PNG",
                                    data=qr_img_bytes,
                                    file_name=f"CSC_QR_{file_no.replace('/', '_')}.png",
                                    mime="image/png",
                                    type="primary"
                                )
                        except Exception as e:
                            st.error("Failed to register record. Check if File Number or QR ID already exists.")
                            st.code(str(e))
                            
        # TAB 2: VIEW RECORDS
        with tab2:
            st.subheader("CSC Master Registry")
            try:
                df_records = pd.read_sql("SELECT * FROM csc_registry ORDER BY id DESC;", engine)
                st.dataframe(df_records, use_container_width=True)
                st.caption(f"Total Registered Letters: {len(df_records)}")
            except Exception as e:
                st.error(f"Error fetching records: {e}")
                
        # TAB 3: AUDIT TRAIL
        with tab3:
            st.subheader("System Verification Audit Logs")
            try:
                df_audit = pd.read_sql("SELECT * FROM csc_audit_logs ORDER BY id DESC LIMIT 100;", engine)
                st.dataframe(df_audit, use_container_width=True)
            except Exception as e:
                st.error(f"Error fetching audit logs: {e}")
        with col2:
            mda = st.text_input("Ministry / Department / Agency *", placeholder="Ministry of Finance, Budget & Economic Planning")
            doa = st.date_input("Date of Effective Appointment")
            qr_code_id = st.text_input("Generated Security/QR ID *", placeholder="QR-2026-9901")
        
        submitted = st.form_submit_button("Save Record & Generate QR Code", type="primary")
        
        if submitted:
            if not (file_no and full_name and cadre and mda and qr_code_id):
                st.error("Please fill in all required fields marked with *")
            else:
                try:
                    # 1. Save to Supabase DB
                    add_record(file_no, full_name, cadre, grade_level, mda, doa, qr_code_id)
                    st.success(f"Successfully registered appointment for {full_name} ({file_no})!")
                    
                    # 2. Build verification data payload for QR code
                    qr_payload = f"TARABA STATE CSC VERIFICATION\nFile No: {file_no.upper()}\nSecurity ID: {qr_code_id.upper()}\nName: {full_name}"
                    
                    # 3. Generate PNG QR bytes
                    qr_img_bytes = generate_qr_code(qr_payload)
                    
                    # 4. Display and Download UI
                    st.divider()
                    st.subheader("Generated Official Security QR Code")
                    qr_col1, qr_col2 = st.columns([1, 2])
                    
                    with qr_col1:
                        st.image(qr_img_bytes, caption=f"QR Code for {file_no.upper()}", width=200)
                    
                    with qr_col2:
                        st.markdown("### Print Ready Badge")
                        st.write("Download this QR code PNG and attach/print it onto the official physical appointment letter.")
                        
                        st.download_button(
                            label="📥 Download QR Code PNG",
                            data=qr_img_bytes,
                            file_name=f"CSC_QR_{file_no.replace('/', '_')}.png",
                            mime="image/png",
                            type="primary"
                        )
                except Exception as e:
                    st.error("Failed to register record. Check if File Number or QR ID already exists.")
                    st.code(str(e))
                            
        # TAB 2: VIEW RECORDS
        with tab2:
            st.subheader("CSC Master Registry")
            try:
                df_records = pd.read_sql("SELECT * FROM csc_registry ORDER BY id DESC;", engine)
                st.dataframe(df_records, use_container_width=True)
                st.caption(f"Total Registered Letters: {len(df_records)}")
            except Exception as e:
                st.error(f"Error fetching records: {e}")
                
        # TAB 3: AUDIT TRAIL
        with tab3:
            st.subheader("System Verification Audit Logs")
            try:
                df_audit = pd.read_sql("SELECT * FROM csc_audit_logs ORDER BY id DESC LIMIT 100;", engine)
                st.dataframe(df_audit, use_container_width=True)
            except Exception as e:
                st.error(f"Error fetching audit logs: {e}")
