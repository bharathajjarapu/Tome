"""Text extraction. AnyDoc handles the binary formats; text formats need no parser."""

import logging
from pathlib import Path

import anydoc

log = logging.getLogger(__name__)

# Anything shorter is an empty extraction, not a document. Scanned PDFs land here.
MIN_CHARS = 20

# Already Markdown or close enough. AnyDoc rejects them, so decode instead.
TEXT_SUFFIXES = {".md", ".markdown", ".txt"}


class ParseError(Exception):
    """Raised when a file yields no usable text."""


def parse(data: bytes, filename: str) -> str:
    """Return the file's text as Markdown."""
    suffix = Path(filename).suffix.lower()
    if suffix in TEXT_SUFFIXES:
        text = data.decode("utf-8", errors="replace")
    else:
        text = _anydoc(data, filename, suffix)
    if len(text.strip()) < MIN_CHARS:
        raise ParseError(f"{filename}: no text found")
    log.info("parsed %s (%d chars)", filename, len(text))
    return text


def _anydoc(data: bytes, filename: str, suffix: str) -> str:
    # ocr="reject" keeps the call local: a scanned PDF raises rather than going to a hosted service.
    # ponytail: that is the Docling fallback's slot, wire it here when OCR is needed.
    try:
        return anydoc.to_markdown_bytes(data, anydoc.format_from_extension(suffix), ocr="reject")
    except anydoc.ConvertError as exc:
        raise ParseError(f"{filename}: {exc}") from exc
