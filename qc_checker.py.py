import streamlit as st
import spacy
import dateparser
import re
import difflib
from datetime import datetime
from docx import Document
from pypdf import PdfReader

nlp = spacy.load("en_core_web_sm")

# Master dictionary
MED_ABBS = {
    "HTN": "Hypertension", 
    "DM": "Diabetes Mellitus", 
    "T2DM": "Type 2 Diabetes Mellitus",
    "COPD": "Chronic Obstructive Pulmonary Disease",
    "CKD": "Chronic Kidney Disease", 
    "CHF": "Congestive Heart Failure", 
    "CAD": "Coronary Artery Disease",
    "MI": "Myocardial Infarction", 
    "CVA": "Cerebrovascular Accident", 
    "TIA": "Transient Ischemic Attack",
    "PE": "Pulmonary Embolism", 
    "DVT": "Deep Vein Thrombosis", 
    "GERD": "Gastroesophageal Reflux Disease",
    "RA": "Rheumatoid Arthritis", 
    "OA": "Osteoarthritis", 
    "UTI": "Urinary Tract Infection",
    "URI": "Upper Respiratory Infection", 
    "BID": "twice a day", 
    "TID": "three times a day", 
    "QD": "once a day", 
    "QID": "four times a day", 
    "PRN": "as needed", 
    "PO": "by mouth", 
    "IV": "intravenous", 
    "IM": "intramuscular", 
    "SC": "subcutaneous", 
    "CBC": "Complete Blood Count", 
    "WBC": "White Blood Cell count", 
    "RBC": "Red Blood Cell count", 
    "HGB": "Hemoglobin", 
    "HCT": "Hematocrit", 
    "PLT": "Platelets", 
    "ALT": "Alanine Pharmacotransferase", 
    "AST": "Aspartate Aminotransferase", 
    "BUN": "Blood Urea Nitrogen", 
    "SCR": "Serum Creatinine", 
    "ADR": "Adverse Drug Reaction", 
    "AE": "Adverse Event", 
    "SAE": "Serious Adverse Event", 
    "BP": "Blood Pressure", 
    "HR": "Heart Rate", 
    "ICU": "Intensive Care Unit", 
    "ED": "Emergency Department"
}

LAB_UNITS = {
    "HGB": "g/dL", 
    "WBC": "x10^3/uL", 
    "RBC": "x10^6/uL", 
    "PLT": "x10^3/uL",
    "ALT": "U/L", 
    "AST": "U/L", 
    "BUN": "mg/dL", 
    "SCR": "mg/dL"
}

SPELL_FIX = {
    "recieved": "received",
    "received": "received",
    "informatoin": "information",
    "phyisician": "physician",
    "hospial": "hospital",
    "medicatoin": "medication"
}

VERBS = {
    "is": "was", "are": "were", "am": "was", 
    "shows": "showed", "indicates": "indicated",
    "presents": "presented", "complains": "complained", 
    "returns": "returned", "feels": "felt",
    "has": "had", "have": "had", "goes": "went", "comes": "came"
}

def clean_and_tense(text, term):
    text = re.sub(r'\bPatient\b', term, text)
    text = re.sub(r'\bpatient\b', term.lower(), text)
    words = text.split(" ")
    out = []
    for w in words:
        base = re.sub(r'[^\w]', '', w)
        low = base.lower()
        if low in SPELL_FIX:
            fixed_word = SPELL_FIX[low]
            if w and w[0].isupper():
                fixed_word = fixed_word.capitalize()
            w = w.replace(base, fixed_word)
            base = fixed_word
            low = base.lower()
        if low in VERBS:
            rep = VERBS[low]
            if w and w[0].isupper():
                rep = rep.capitalize()
            w = w.replace(base, rep)
        out.append(w)
    return " ".join(out)

def apply_blinding(text):
    text = re.sub(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', '[REDACTED EMAIL]', text)
    text = re.sub(r'\b(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}\b|\b\d{10}\b', '[REDACTED PHONE]', text)
    doc = nlp(text)
    for ent in reversed(doc.ents):
        if ent.label_ in ["PERSON", "ORG", "GPE", "LOC"]:
            label_map = {"PERSON": "[REDACTED NAME]", "ORG": "[REDACTED INSTITUTION]", "GPE": "[REDACTED LOCATION]", "LOC": "[REDACTED LOCATION]"}
            text = text[:ent.start_char] + label_map[ent.label_] + text[ent.end_char:]
    return text

def apply_qc(text, term, custom_dates, custom_abbs, all_found_abbs, blind_mode):
    if not text:
        return ""
    txt = clean_and_tense(text, term)
    for abb in all_found_abbs:
        if abb in custom_abbs and custom_abbs[abb].strip():
            long_form = custom_abbs[abb].strip()
            txt = re.sub(r'\b' + abb + r'\b', f"{long_form} ({abb})", txt, flags=re.IGNORECASE)
        elif abb in MED_ABBS:
            long_form = MED_ABBS[abb]
            txt = re.sub(r'\b' + abb + r'\b', f"{long_form} ({abb})", txt, flags=re.IGNORECASE)
    for lab in LAB_UNITS:
        unit = LAB_UNITS[lab]
        pat = r'(\b' + lab + r'\b.*?)\b(\d+(?:\.\d+)?)\b'
        matches = re.findall(pat, txt, flags=re.IGNORECASE)
        for m in matches:
            seg = m[0] + m[1]
            if unit not in seg:
                txt = txt.replace(seg, f"{seg} {unit}")
    date_pattern = r'\b\d{1,2}/\d{1,2}/\d{2,4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{1,2},? \d{4}\b'
    doc = nlp(txt)
    sents = [s.text.strip() for s in doc.sents]
    dated = []
    undated = []
    for s in sents:
        manual_match = False
        for k, v in custom_dates.items():
            if k in s and v:
                s = s.replace(k, v)
                p_date = dateparser.parse(v) or datetime.now()
                dated.append({"date": p_date, "text": s})
                manual_match = True
                break
        if manual_match:
            continue
        match = re.search(date_pattern, s)
        if match:
            raw_date_str = match.group(0)
            p_date = dateparser.parse(raw_date_str, settings={'DATE_ORDER': 'MDY'})
            if p_date:
                f_date = p_date.strftime("%d-%b-%Y")
                s = s.replace(raw_date_str, f_date)
                dated.append({"date": p_date, "text": s})
                continue
        undated.append(s)
    dated.sort(key=lambda x: x["date"])
    final_sents = [item["text"] for item in dated] + undated
    compiled = " ".join(final_sents)
    if blind_mode == "Blinded":
        compiled = apply_blinding(compiled)
    return compiled

def parse_file(uploaded_file):
    name = uploaded_file.name.lower()
    if name.endswith('.txt'):
        return uploaded_file.read().decode("utf-8")
    elif name.endswith('.docx'):
        doc = Document(uploaded_file)
        return "\n".join([p.text for p in doc.paragraphs])
    elif name.endswith('.pdf'):
        reader = PdfReader(uploaded_file)
        return "\n".join([page.extract_text() for page in reader.pages if page.extract_text()])
    return ""

# --- SECURITY INTERFACE GATE ---
st.set_page_config(page_title="Narrative Studio Pro", layout="wide", initial_sidebar_state="collapsed")

if "auth" not in st.session_state:
    st.session_state.auth = False

if not st.session_state.auth:
    st.markdown("<h2 style='text-align: center;'>🔒 Clinical Workspace Gateway</h2>", unsafe_allow_html=True)
    with st.container(border=True):
        u = st.text_input("Username:")
        p = st.text_input("Password:", type="password")
        if st.button("Authenticate Workspace", use_container_width=True):
            if u == "admin" and p == "clinical2026":
                st.session_state.auth = True
                st.rerun()
            else:
                st.error("Invalid credentials.")
    st.stop()

# --- MAIN APPLICATION WORKSPACE ---
st.success("Hi Onkar! Welcome to Narrative QC Checker developed by Onkar.")
st.title("🛡️ Narrative QC Studio Pro")
st.markdown("---")

# STEP 1: CONSOLIDATED PARSING INFRASTRUCTURE
st.subheader("Step 1: Input Narrative Content")
src = st.radio("Choose Input Method:", ["Manual Text Entry", "Upload Document File (TXT, DOCX, PDF)"], horizontal=True)

raw_input = ""
if src == "Manual Text Entry":
    raw_input = st.text_area("Paste text script or draft below:", height=150)
else:
    f = st.file_uploader("Drop document here:", type=["txt", "docx", "pdf"])
    if f:
        raw_input = parse_file(f)
        st.info(f"Loaded successfully: {f.name}")
        with st.expander("Show Parsed Content Raw Text"):
            st.write(raw_input)

custom_dates = {}
custom_abbs = {}
chosen_term = "Patient"

if raw_input:
    st.markdown("---")
    st.subheader("Step 2: Resolve Uncertainties & Configuration Panel")
    
    col_cfg1, col_cfg2 = st.columns(2)
    with col_cfg1:
        chosen_term = st.selectbox("Trial Standard Term:", ["Patient", "Subject", "Participant"])
    with col_cfg2:
        blind_mode = st.radio("Privacy Blinding:", ["Unblinded", "Blinded"], horizontal=True)
        
    st.markdown(" ")
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("🔍 **Partial Dates Processing**")
        partial_pattern = r'\b\d{1,2}/\d{4}\b|\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{4}\b'
        partials = re.findall(partial_pattern, raw_input)
        if partials:
            for p in set(partials):
                custom_dates[p] = st.text_input(f"Define full date for '{p}':", placeholder="e.g. 15-Dec-2024", key=p)
        else:
            st.caption("No partial items detected.")
            
    with c2:
        st.markdown("📖 **Dynamic Acronym Matrix**")
        all_capital_words = re.findall(r'\b[A-Z]{2,5}\b', raw_input)
        unique_abbs = sorted(list(set(all_capital_words)))
        if unique_abbs:
            with st.container(height=180, border=True):
                for a in unique_abbs:
                    default_val = MED_ABBS[a] if a in MED_ABBS else ""
                    custom_abbs[a] = st.text_input(f"Define '{a}':", value=default_val, key=a)
        else:
            st.caption("No abbreviations detected.")

    st.markdown("---")
    st.subheader("Step 3: Final Clean Output & Interactive Verification Report")
    
    final_txt = apply_qc(raw_input, chosen_term, custom_dates, custom_abbs, unique_abbs, blind_mode)
    
    st.markdown("**Validated Clean Narrative:**")
    st.text_area("Final Clean Narrative Output Window:", value=final_txt, height=180)
    
    st.markdown(" ")
    st.markdown("**Side-by-Side Validation Logs:**")
    rep_col1, rep_col2 = st.columns(2)
    with rep_col1:
        st.error("📋 Original Raw Text Log")
        st.text_area("Raw log:", value=raw_input, height=180, disabled=True, label_visibility="collapsed")
    with rep_col2:
        st.success("✅ Cleaned Narrative Block Log")
        st.text_area("Cleaned log:", value=final_txt, height=180, disabled=True, label_visibility="collapsed")