import os
import sys

# Hard-enforced automatic environment installation patch
try:
    import streamlit as st
    import dateparser
    from docx import Document
except ImportError:
    os.system(f"{sys.executable} -m pip install streamlit dateparser python-docx")
    import streamlit as st
    import dateparser
    from docx import Document

try:
    import spacy
    from pypdf import PdfReader
except ImportError:
    os.system(f"{sys.executable} -m pip install spacy pypdf")
    import spacy
    from pypdf import PdfReader

# Dynamic language model download execution
try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    import spacy.cli
    spacy.cli.download("en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
    
import re
from datetime import datetime
