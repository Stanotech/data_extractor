import os

import pytest

from pdf_extractor.extractor import PDFExtractor

DOCS_DIR = "docs"

test_cases = [
    (
        "CBZ TOUCH MANUAL REGISTRATION FORM filled.pdf",
        {
            "customer_name": "Laura Pulsen",
            "branch_name": "London Mansion House",
            "account_number": "GM1948218",
        },
    ),
    (
        "MORTGAGE APPLICATION FORM_filled.pdf",
        {
            "customer_name": "Tim James",
            "branch_name": "Tottenham Court, London",
            "account_number": "76543234",
        },
    ),
    (
        "FNOL-form-MOTOR-v10 filled2.pdf",
        {"customer_name": "Emma Munteri", "branch_name": None, "account_number": None},
    ),
    (
        "M-PIN CBZ TOUCH_filled.pdf",
        {
            "customer_name": "William Burkley",
            "branch_name": "Manchester city",
            "account_number": "7654345",
        },
    ),
    (
        "FNOL-form-MOTOR-v10_filled.pdf",
        {
            "customer_name": "Penelope Tulley",
            "branch_name": None,
            "account_number": None,
        },
    ),
    (
        "notice-of-loss-form_novt2019_axa-xl_filled.pdf",
        {
            "customer_name": "Jennifer Fauler",
            "branch_name": None,
            "account_number": None,
        },
    ),
    (
        "FUNDS RECALL FORM_filled.pdf",
        {
            "customer_name": "Garry Gordon",
            "branch_name": "Bristol River Side",
            "account_number": "TI81729731",
        },
    ),
    (
        "Personal Loan Application Form_filled.pdf",
        {
            "customer_name": "Jon Smith",
            "branch_name": "Southwark",
            "account_number": "93934950",
        },
    ),
    (
        "INTERNET BANKING REGISTRATION FORM1_filled.pdf",
        {
            "customer_name": "Josie Jordan",
            "branch_name": "342",
            "account_number": "34333233233332",
        },
    ),
    (
        "PROOF OF PAYMENT REQUISITION FORM_filled.pdf",
        {
            "customer_name": "Laura Lauren",
            "branch_name": "Oxford st, London",
            "account_number": "5468912",
        },
    ),
    (
        "INTERNET PASSWORD RESET APPLICATION FORM_filled.pdf",
        {
            "customer_name": "Taylor Red",
            "branch_name": "London Battersea",
            "account_number": "55544443222",
        },
    ),
    (
        "property-loss-form_filled.pdf",
        {"customer_name": None, "branch_name": None, "account_number": None},
    ),
]


@pytest.mark.parametrize("filename, expected", test_cases)
def test_pdf_extractor_integration(filename: str, expected: dict) -> None:
    pdf_path = os.path.join(DOCS_DIR, filename)
    extractor = PDFExtractor(pdf_path)
    result = extractor.extract()

    assert result["customer_name"] == expected["customer_name"]
    assert result["branch_name"] == expected["branch_name"]
    assert result["account_number"] == expected["account_number"]
