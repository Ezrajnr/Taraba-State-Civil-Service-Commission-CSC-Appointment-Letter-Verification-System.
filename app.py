import streamlit as st
import pandas as pd
import qrcode
import io
from datetime import datetime
from sqlalchemy import create_engine, text

# --- DATABASE ENGINE SETUP ---
# Adjust connection string to match your database credentials
# Example: "postgresql://user:password@localhost:5432/csc_db" or "mysql+pymysql://user:password@localhost/csc_db"
DATABASE_URL = "sqlite:///csc_verification.db"  # Replace with your DB URL
engine = create_engine(DATABASE_URL)

# --- DATABASE CRUD HELPER FUNCTIONS ---
def add_record(file_no, full_name, cadre, grade_level, mda, doa, qr_code_id):
    query = text("""
        INSERT INTO csc_registry (file_no, full_name, cadre, grade_level, mda, doa, qr_code_id)
        VALUES (:file_no, :full_name, :cadre, :grade_level, :mda, :doa, :qr_code_id);
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "file_no": file_no.upper(),
            "full_name": full_name,
            "cadre": cadre,
            "grade_level": grade_level,
            "mda": mda,
            "doa": doa,
            "qr_code_id": qr_code_id.upper()
        })

def update_record(record_id, file_no, full_name, cadre, grade_level, mda, doa, qr_code_id):
    query = text("""
        UPDATE csc_registry 
        SET file_no = :file_no, full_name = :full_name, cadre = :cadre, 
            grade_level = :grade_level, mda = :mda, doa = :doa, qr_code_id = :qr_code_id
        WHERE id = :id;
    """)
    with engine.begin() as conn:
        conn.execute(query, {
            "file_no": file_no.upper(),
            "full_name": full_name,
            "cadre": cadre,
            "grade_level": grade_level,
            "mda": mda,
            "doa": doa,
            "qr_code_id": qr_code_id.upper(),
            "id": record_id
        })

def delete_record(record_id):
    query = text("DELETE FROM csc_registry WHERE id = :id;")
    with engine.begin() as conn:
        conn.execute(query, {"id": record_id})

def generate_qr_code(payload_text):
    qr = qrcode.QRCode(
        version=1,
        error_correction=qrcode.constants.ERROR_CORRECT_H,
        box_size=10,
        border=2,
    )
    qr.add_data(payload_text)
    qr.make(fit=True)
    img = qr.make_image(fill_color="black", back_color="white")
    
    img_bytes = io.BytesIO()
    img.save(img_bytes, format='PNG')
    return img_bytes.getvalue()

# --- PAGE CONFIGURATION ---
st.set_page_config(
    page_title="Taraba State CSC - Appointment Registry",
    page_icon="📜",
    layout="wide"
)

st.title("📜 Taraba State Civil Service Commission")
st.caption("Official Appointment Letter Verification & Registry Portal")

# Main Navigation Tabs
tab1, tab2 = st.tabs(["➕ Add New Record", "📋 View & Manage Records"])

# ==============================================================================
# TAB 1: ADD RECORD & GENERATE QR CODE
# ==============================================================================
with tab1:
    st.subheader("Register New Appointment Letter")
    
    # Form container ONLY for input fields & submission
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
                    # 1. Save record to DB
                    add_record(file_no, full_name, cadre, grade_level, mda, doa, qr_code_id)
                    st.success(f"Successfully registered appointment for {full_name} ({file_no})!")
                    
                    # 2. Build QR payload & generate image bytes
                    qr_payload = f"TARABA STATE CSC VERIFICATION\nFile No: {file_no.upper()}\nSecurity ID: {qr_code_id.upper()}\nName: {full_name}"
                    qr_img_bytes = generate_qr_code(qr_payload)
                    
                    # 3. Store in session_state to display outside the form
                    st.session_state["last_registered_qr"] = {
                        "bytes": qr_img_bytes,
                        "file_no": file_no.upper(),
                        "filename": f"CSC_QR_{file_no.replace('/', '_')}.png"
                    }
                except Exception as e:
                    st.error("Failed to register record. Check if File Number or QR ID already exists.")
                    st.code(str(e))

    # DOWNLOAD & CLEAR SECTION (Outside st.form to avoid runtime error)
    if "last_registered_qr" in st.session_state and st.session_state["last_registered_qr"]:
        qr_data = st.session_state["last_registered_qr"]
        st.divider()
        st.subheader("Generated Official Security QR Code")
        qr_col1, qr_col2 = st.columns([1, 2])
        
        with qr_col1:
            st.image(qr_data["bytes"], caption=f"QR Code for {qr_data['file_no']}", width=200)
        
        with qr_col2:
            st.markdown("### Print Ready Badge")
            st.write("Download this QR code PNG and attach/print it onto the official physical appointment letter.")
            
            btn_col1, btn_col2 = st.columns([1, 1])
            with btn_col1:
                st.download_button(
                    label="📥 Download QR Code PNG",
                    data=qr_data["bytes"],
                    file_name=qr_data["filename"],
                    mime="image/png",
                    type="primary",
                    use_container_width=True
                )
            
            with btn_col2:
                if st.button("🔄 Clear & Register Another", type="secondary", use_container_width=True):
                    del st.session_state["last_registered_qr"]
                    st.rerun()

# ==============================================================================
# TAB 2: VIEW, EXPORT, EDIT & DELETE RECORDS
# ==============================================================================
with tab2:
    st.subheader("CSC Master Registry Management")
    try:
        df_records = pd.read_sql("SELECT * FROM csc_registry ORDER BY id DESC;", engine)
        
        if not df_records.empty:
            # Metrics & Export Bar
            col_info, col_export = st.columns([2, 1])
            with col_info:
                st.metric("Total Registered Letters", len(df_records))
            with col_export:
                csv_data = df_records.to_csv(index=False).encode('utf-8')
                st.download_button(
                    label="📥 Export Master Registry (CSV)",
                    data=csv_data,
                    file_name=f"Taraba_CSC_Registry_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv",
                    mime="text/csv",
                    type="primary",
                    use_container_width=True
                )
            
            st.divider()

            # Admin Operations Expander
            with st.expander("🛠️ Admin Management Tools (Edit / Delete Record)", expanded=False):
                record_options = {
                    f"{row['file_no']} | {row['full_name']}": row 
                    for _, row in df_records.iterrows()
                }
                
                selected_label = st.selectbox(
                    "Select Record to Modify or Delete:", 
                    options=list(record_options.keys())
                )
                
                selected_row = record_options[selected_label]
                record_id = selected_row['id']

                action_tab1, action_tab2 = st.tabs(["✏️ Edit Record", "🗑️ Delete Record"])

                # EDIT SUB-TAB
                with action_tab1:
                    with st.form(f"edit_form_{record_id}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            edit_file_no = st.text_input("File Number", value=selected_row['file_no'])
                            edit_full_name = st.text_input("Full Name", value=selected_row['full_name'])
                            edit_cadre = st.text_input("Cadre / Post", value=selected_row['cadre'])
                            
                            gl_options = [f"GL {i:02d}" for i in range(1, 18)]
                            current_gl_idx = gl_options.index(selected_row['grade_level']) if selected_row['grade_level'] in gl_options else 0
                            edit_grade_level = st.selectbox("Grade Level", gl_options, index=current_gl_idx)

                        with col2:
                            edit_mda = st.text_input("MDA", value=selected_row['mda'])
                            edit_doa = st.date_input("Date of Effective Appointment", value=pd.to_datetime(selected_row['doa']))
                            edit_qr_id = st.text_input("Generated Security/QR ID", value=selected_row['qr_code_id'])

                        update_btn = st.form_submit_button("💾 Save Changes", type="primary")

                        if update_btn:
                            try:
                                update_record(
                                    record_id, edit_file_no, edit_full_name, 
                                    edit_cadre, edit_grade_level, edit_mda, 
                                    edit_doa, edit_qr_id
                                )
                                st.success(f"Record {edit_file_no} updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Failed to update record: {e}")

                # DELETE SUB-TAB
                with action_tab2:
                    st.warning(f"⚠️ Are you sure you want to permanently delete **{selected_row['full_name']}** ({selected_row['file_no']})?")
                    st.caption("This action is permanent and will purge the record from the verification database.")
                    
                    confirm_delete = st.button("Confirm Permanent Deletion", type="primary", key=f"del_{record_id}")
                    if confirm_delete:
                        try:
                            delete_record(record_id)
                            st.success(f"Record {selected_row['file_no']} permanently deleted.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Failed to delete record: {e}")

            st.divider()
            
            # Master Data Table
            st.dataframe(df_records, use_container_width=True)

        else:
            st.info("No appointment records found in the database.")
            
    except Exception as e:
        st.error(f"Error fetching records from database: {e}")
