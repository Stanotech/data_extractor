import logging
import streamlit as st
from pdf_extractor.database import init_db, save_data
from pdf_extractor.extractor import PDFExtractor

# Konfiguracja loggera
logging.basicConfig(level=logging.INFO)

# Inicjalizacja bazy danych
try:
    init_db()
    logging.info("Database initialized successfully")
except Exception:
    logging.exception("Failed to initialize database")
    st.error("Could not initialize the database.")
    st.stop()

st.title("PDF Data Extractor")

uploaded_file = st.file_uploader("Upload a PDF file", type=["pdf"])

if uploaded_file is not None:
    try:
        # Zapis tymczasowego pliku
        with open("temp.pdf", "wb") as f:
            f.write(uploaded_file.read())
        logging.info("Uploaded file saved as temp.pdf")

        # Ekstrakcja danych z PDF
        extractor = PDFExtractor("temp.pdf")
        data = extractor.extract()
        logging.info("Data extracted from PDF successfully")

        # Zapis danych do bazy
        save_data(data)
        logging.info("Data saved to database successfully")

        # Prezentacja danych
        st.subheader("Extracted Data")
        st.json(data)

    except Exception:
        logging.exception("Error while processing PDF")
        st.error("Could not process the PDF file.")
        st.stop()
