import pytest

from tome.core.config import settings
from tome.ingestion.parse import TEXT_SUFFIXES, ParseError, parse


def minipdf(text: str) -> bytes:
    """A one-page PDF with a single line of extractable text."""
    stream = f"BT /F1 24 Tf 72 700 Td ({text}) Tj ET".encode()
    objs = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Contents 4 0 R "
        b"/Resources << /Font << /F1 5 0 R >> >> >>",
        b"<< /Length %d >>\nstream\n" % len(stream) + stream + b"\nendstream",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
    ]
    out = bytearray(b"%PDF-1.4\n")
    offsets = []
    for number, body in enumerate(objs, 1):
        offsets.append(len(out))
        out += b"%d 0 obj\n" % number + body + b"\nendobj\n"
    xref = len(out)
    out += b"xref\n0 %d\n0000000000 65535 f \n" % (len(objs) + 1)
    for offset in offsets:
        out += b"%010d 00000 n \n" % offset
    out += b"trailer\n<< /Size %d /Root 1 0 R >>\nstartxref\n%d\n%%%%EOF\n" % (len(objs) + 1, xref)
    return bytes(out)


def test_pdf_text_is_extracted() -> None:
    assert "ninety days" in parse(minipdf("The retention window is ninety days."), "policy.pdf")


def test_spreadsheet_becomes_a_markdown_table() -> None:
    text = parse(b"name,role\nada,engineering\nlin,design\n", "team.csv")
    assert "| name | role |" in text


def test_markdown_is_passed_through() -> None:
    assert parse(b"# Title\n\nSome body text here.", "notes.md").startswith("# Title")


def test_corrupt_file_raises_with_the_filename() -> None:
    with pytest.raises(ParseError, match="broken.pdf"):
        parse(b"%PDF-1.4 not really a pdf", "broken.pdf")


def test_empty_extraction_raises() -> None:
    with pytest.raises(ParseError, match="no text found"):
        parse(b"  ", "blank.txt")


def test_every_extension_the_parser_reads_is_accepted() -> None:
    """A file the parser handles must not be rejected at the door."""
    assert TEXT_SUFFIXES <= settings.allowed_extensions
