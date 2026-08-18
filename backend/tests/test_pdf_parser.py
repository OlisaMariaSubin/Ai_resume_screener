from app.services.pdf_parser import extract_text_from_pdf
from tests.conftest import make_empty_pdf_bytes, make_pdf_bytes


def test_valid_pdf_extracts_text():
    pdf_bytes = make_pdf_bytes(["John Doe", "Python developer with FastAPI experience"])
    result = extract_text_from_pdf(pdf_bytes)
    assert result["success"] is True
    assert "John Doe" in result["text"]
    assert "FastAPI" in result["text"]


def test_empty_pdf_returns_error():
    pdf_bytes = make_empty_pdf_bytes()
    result = extract_text_from_pdf(pdf_bytes)
    assert result["success"] is False
    assert "no extractable text" in result["error"].lower()


def test_malformed_pdf_returns_error():
    result = extract_text_from_pdf(b"not a real pdf at all")
    assert result["success"] is False
    assert "error" in result
