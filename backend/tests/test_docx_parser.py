from app.services.docx_parser import extract_text_from_docx
from tests.conftest import make_docx_bytes, make_empty_docx_bytes


def test_valid_docx_extracts_paragraphs():
    docx_bytes = make_docx_bytes(["Jane Smith", "Experienced with Python and React"])
    result = extract_text_from_docx(docx_bytes)
    assert result["success"] is True
    assert "Jane Smith" in result["text"]
    assert "React" in result["text"]


def test_docx_extracts_table_text():
    docx_bytes = make_docx_bytes(
        ["Skills Summary"],
        table_rows=[["Skill", "Level"], ["Python", "Expert"], ["Docker", "Intermediate"]],
    )
    result = extract_text_from_docx(docx_bytes)
    assert result["success"] is True
    assert "Python" in result["text"]
    assert "Docker" in result["text"]


def test_empty_docx_returns_error():
    docx_bytes = make_empty_docx_bytes()
    result = extract_text_from_docx(docx_bytes)
    assert result["success"] is False
    assert "no extractable text" in result["error"].lower()


def test_malformed_docx_returns_error():
    result = extract_text_from_docx(b"not a real docx")
    assert result["success"] is False
