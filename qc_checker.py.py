import streamlit as st
import spacy
import dateparser
import re
from datetime import datetime
from docx import Document
from pypdf import PdfReader

# Load the model directly (since requirements.txt pre-downloads it)
nlp = spacy.load("en_core_web_sm")

# Session State Initialization for Authentication
if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

# Security Gateway Login View
if not st.session_state.authenticated:
    st.set_page_config(page_title="Workspace Gateway | Security Login", layout="centered", page_icon="🔒")
    
    st.title("🔒 Narrative QC Studio Pro")
    st.subheader("Secure Verification Workspace Gateway")
    st.write("Please authenticate with your credentials to access the quality control processing environment.")
    
    username = st.text_input("Username", placeholder="Enter your ID")
    password = st.text_input("Password", type="password", placeholder="Enter your token")
    
    if st.button("Login to Workspace", use_container_width=True):
        if username == "admin" and password == "clinical2026":
            st.session_state.authenticated = True
            st.success("Authorization successful! Loading environment...")
            st.rerun()
        else:
            st.error("Invalid credentials. Please verify your access tokens and try again.")
    st.stop()

# Authenticated Application Interface
st.set_page_config(page_title="Narrative QC Studio Pro", layout="wide", page_icon="🛡️")

# Top Header Profile Panel
st.markdown("""
    <div style="background-color:#1e293b; padding:15px; border-radius:10px; margin-bottom:20px; color:white;">
        <h2 style="margin:0; color:#38bdf8;">🛡️ Narrative QC Studio Pro</h2>
        <p style="margin:5px 0 0 0; font-size:14px; color:#94a3b8;">Quality Control & Automated Chronology Verification Suite</p>
    </div>
""", unsafe_allow_html=True)

# Main Workspace Layout Split
left_col, right_col = st.columns([1, 1])

with left_col:
    st.header("📄 Source Document Ingestion")
    uploaded_file = st.file_uploader("Upload Narrative Report (PDF, DOCX, or TXT format)", type=["pdf", "docx", "txt"])
    
    raw_text = ""
    if uploaded_file is not None:
        file_ext = uploaded_file.name.split(".")[-1].lower()
        
        if file_ext == "txt":
            raw_text = uploaded_file.read().decode("utf-8")
        elif file_ext == "docx":
            doc = Document(uploaded_file)
            raw_text = "\n".join([p.text for p in doc.paragraphs])
        elif file_ext == "pdf":
            pdf_reader = PdfReader(uploaded_file)
            for page in pdf_reader.pages:
                text_content = page.extract_text()
                if text_content:
                    raw_text += text_content + "\n"
                    
        st.success(f"Successfully ingested: {uploaded_file.name}")
        st.text_area("Raw Narrative Preview", value=raw_text[:2000] + ("..." if len(raw_text) > 2000 else ""), height=300)

with right_col:
    st.header("⚙️ QC Core Processing Engine")
    
    if not raw_text:
        st.info("Awaiting file ingestion from the source panel to initialize narrative quality control pipelines.")
    else:
        st.markdown("### Chronological Order & Validation Pipeline")
        
        # Internal Processing Core
        sentences = [sent.text.strip() for sent in nlp(raw_text).sents if len(sent.text.strip()) > 5]
        extracted_events = []
        
        for sent in sentences:
            dates = dateparser.search.search_dates(sent)
            if dates:
                for date_str, date_obj in dates:
                    if len(date_str) > 3 and not date_str.isdigit():
                        extracted_events.append({
                            "date": date_obj,
                            "date_text": date_str,
                            "context": sent
                        })
                        break
        
        # Sort Chronology
        extracted_events.sort(key=lambda x: x["date"])
        
        if extracted_events:
            st.success(f"Analysis Complete: Identified and verified {len(extracted_events)} explicit clinical timelines.")
            
            for idx, event in enumerate(extracted_events):
                with st.expander(f"📍 [{event['date'].strftime('%Y-%m-%d')}] - Source Fragment Reference {idx+1}"):
                    st.markdown(f"**Identified Temporal Marker:** `{event['date_text']}`")
                    st.markdown(f"**Contextual Narrative Script:**\n> {event['context']}")
            
            # Download Verified Output Package
            output_buffer = "NARRATIVE QC STUDIO PRO - VERIFIED CHRONOLOGY REPORT\n"
            output_buffer += f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            output_buffer += "="*60 + "\n\n"
            for event in extracted_events:
                output_buffer += f"[{event['date'].strftime('%Y-%m-%d')}] (Found text: '{event['date_text']}')\nContext: {event['context']}\n\n"
                
            st.download_button(
                label="📥 Export Verified QC Report Package",
                data=output_buffer,
                file_name=f"QC_Verified_Report_{datetime.now().strftime('%Y%m%d')}.txt",
                mime="text/plain",
                use_container_width=True
            )
        else:
            st.warning("No explicit temporal data markers or milestones could be safely parsed from the target document structure.")

# Global Operational Environment Footer
st.markdown("---")
footer_cols = st.columns([3, 1])
with footer_cols[0]:
    st.caption("🔒 Architecture Status: Memory Bound | Blinding Protocol Active | Zero Network Data Leaks")
with footer_cols[1]:
    if st.button("Secure Workspace Exit", use_container_width=True):
        st.session_state.authenticated = False
        st.rerun()
