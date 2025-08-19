import io
import os
import sys
import importlib
import pytest
import streamlit as st
from unittest import mock

import pdf_extractor.app as app


@pytest.fixture(autouse=True)
def mock_init_db(monkeypatch: mock.Mock) -> None:
    monkeypatch.setattr(app, "init_db", lambda: None)


def test_app_without_file(monkeypatch: mock.Mock) -> None:
    """Sprawdza czy aplikacja wyświetla tytuł i uploader bez pliku."""
    with (
        mock.patch.object(st, "title") as mock_title,
        mock.patch.object(st, "file_uploader", return_value=None) as mock_uploader,
    ):
        import importlib

        importlib.reload(app)

        mock_title.assert_called_with("PDF Data Extractor")
        mock_uploader.assert_called_once()


def test_app_with_file() -> None:
    """Sprawdza logikę działania aplikacji przy wgranym pliku, bez realnego PDF."""
    fake_pdf_data = {
        "customer_name": "John",
        "branch_name": "Main",
        "account_number": "123",
    }

    with (
        mock.patch.object(st, "title"),
        mock.patch.object(st, "file_uploader", return_value=io.BytesIO(b"fake-pdf")),
        mock.patch.object(st, "subheader") as mock_subheader,
        mock.patch.object(st, "json") as mock_json,
        mock.patch("pdf_extractor.extractor.PDFExtractor") as MockExtractor,
        mock.patch("pdf_extractor.database.save_data") as mock_save,
        mock.patch("pdf_extractor.database.init_db"),
    ):
        instance = MockExtractor.return_value
        instance.extract.return_value = fake_pdf_data

        sys.modules.pop("pdf_extractor.app", None)
        importlib.import_module("pdf_extractor.app")

        MockExtractor.assert_called_once_with("temp.pdf")
        instance.extract.assert_called_once()
        mock_save.assert_called_once_with(fake_pdf_data)
        mock_subheader.assert_called_once_with("Extracted Data")
        mock_json.assert_called_once_with(fake_pdf_data)

    if os.path.exists("temp.pdf"):
        os.remove("temp.pdf")
