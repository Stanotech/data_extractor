import os
import logging
import streamlit as st
from pdf_extractor.database import init_db, save_data, DB_NAME
from pdf_extractor.extractor import PDFExtractor

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

if not os.path.exists(DB_NAME):
    try:
        init_db()
        logger.info("Database initialized successfully")
    except Exception:
        logger.exception("Failed to initialize database")
        st.error("Could not initialize the database.")
        st.stop()
else:
    logger.info("Database already exists, skipping initialization")

st.title("PDF Data Extractor")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    try:
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.read())
        logger.info("Uploaded file saved as temp.pdf")

        extractor = PDFExtractor("temp.pdf")
        data = extractor.extract()
        logger.info("Data extracted from PDF successfully")

        save_data(data)
        logger.info("Data saved to database successfully")

        st.subheader("Extracted Data")
        st.json(data)

    except Exception:
        logger.exception("Error while processing PDF")
        st.error("Could not process the PDF file.")
        st.stop()
