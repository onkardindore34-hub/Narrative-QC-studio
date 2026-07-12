import streamlit as st
import spacy
import dateparser
import re
import os
import sys
from datetime import datetime
from docx import Document
from pypdf import PdfReader

# Automatic bypass for Streamlit Cloud Python 3.14 bug
try:
    nlp = spacy.load("en_core_web_sm")
 Chin except OSError:
    os.system(f"{sys.executable} -m spacy download en_core_web_sm")
    nlp = spacy.load("en_core_web_sm")
