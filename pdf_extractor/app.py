import streamlit as st
from database import init_db, save_data

from pdf_extractor.extractor import PDFExtractor

init_db()

st.title("PDF Data Extractor")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.read())

    extractor = PDFExtractor("temp.pdf")
    data = extractor.extract()
    save_data(data)

    st.subheader("Extracted Data")
    st.json(data)
