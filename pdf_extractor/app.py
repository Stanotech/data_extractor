import streamlit as st
from extractor import extract_pdf_data
from database import init_db, save_data

init_db()

st.title("PDF Data Extractor")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    with open("temp.pdf", "wb") as f:
        f.write(uploaded_file.read())

    data = extract_pdf_data("temp.pdf")
    save_data(data)

    st.subheader("Extracted Data")
    st.json(data)
