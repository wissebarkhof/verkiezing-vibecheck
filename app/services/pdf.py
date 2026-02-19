import logging
import re
from pathlib import Path

from pypdf import PdfReader

logger = logging.getLogger(__name__)


def clean_text(text: str) -> str:
    """Clean up PDF extraction artifacts.

    Handles PDFs where each word ends up on its own line (common with
    justified/multi-column layouts extracted by pypdf).
    """
    lines = text.splitlines()
    cleaned_lines = []
    i = 0
    while i < len(lines):
        line = lines[i].strip()
        if not line:
            # Blank line = paragraph break — preserve one
            if cleaned_lines and cleaned_lines[-1] != "":
                cleaned_lines.append("")
            i += 1
            continue

        # Detect "word-per-line" pattern: if a line is a single word (or short fragment)
        # and the next line is also a single word, merge them into a sentence
        words = [line]
        while i + 1 < len(lines):
            next_line = lines[i + 1].strip()
            if not next_line:
                break
            # Merge if next line looks like a continuation (not a new sentence/header)
            next_words = next_line.split()
            current_words = lines[i].strip().split()
            # If either current or next line is very short (≤3 words), likely word-per-line
            if len(current_words) <= 3 or len(next_words) <= 3:
                # But don't merge if current line ends with sentence punctuation
                if not re.search(r"[.!?]\s*$", lines[i].strip()):
                    words.append(next_line)
                    i += 1
                    continue
            break
        merged = " ".join(words)
        # Collapse internal multiple spaces
        merged = re.sub(r" {2,}", " ", merged)
        cleaned_lines.append(merged)
        i += 1

    text = "\n".join(cleaned_lines)
    # Fix hyphenated line breaks: "wor-\nden" → "worden"
    text = re.sub(r"-\n(\w)", r"\1", text)
    # Collapse 3+ newlines to double newline
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def extract_text_from_pdf(pdf_path: Path) -> str:
    """Extract and clean all text from a PDF file."""
    reader = PdfReader(pdf_path)
    pages = []
    for page in reader.pages:
        text = page.extract_text(extraction_mode="layout")
        if text and text.strip():
            pages.append(text)
    raw = "\n\n".join(pages)
    return clean_text(raw)


def extract_pages_from_pdf(pdf_path: Path) -> list[tuple[int, str]]:
    """Extract and clean text per page, returning (1-based page number, text) pairs."""
    reader = PdfReader(pdf_path)
    pages = []
    for i, page in enumerate(reader.pages, start=1):
        text = page.extract_text(extraction_mode="layout")
        if text and text.strip():
            cleaned = clean_text(text)
            if cleaned:
                pages.append((i, cleaned))
    return pages


def chunk_text(
    text: str,
    chunk_size: int = 1500,
    overlap: int = 200,
) -> list[str]:
    """Split text into overlapping chunks by character count.

    Tries to break at paragraph boundaries. Targets ~500 tokens
    (roughly 1500 characters for Dutch text).
    """
    return [c["content"] for c in chunk_pages([(0, text)], chunk_size, overlap)]


def chunk_pages(
    pages: list[tuple[int, str]],
    chunk_size: int = 1500,
    overlap: int = 200,
) -> list[dict]:
    """Split page-aware text into overlapping chunks, tracking page numbers.

    Returns list of {"content": str, "page_start": int, "page_end": int}.
    page_start/page_end are 1-based PDF page numbers (0 if unknown).
    """
    # Flatten pages into (page_num, paragraph) pairs
    para_list: list[tuple[int, str]] = []
    for page_num, page_text in pages:
        for para in page_text.split("\n\n"):
            para = para.strip()
            if para:
                para_list.append((page_num, para))

    if not para_list:
        return []

    chunks = []
    current_text = ""
    current_page_start = para_list[0][0]
    current_page_end = para_list[0][0]

    for page_num, para in para_list:
        if current_text and len(current_text) + len(para) + 2 > chunk_size:
            chunks.append({
                "content": current_text.strip(),
                "page_start": current_page_start,
                "page_end": current_page_end,
            })
            # Overlap: carry tail of current chunk forward
            if overlap > 0 and len(current_text) > overlap:
                current_text = current_text[-overlap:] + "\n\n" + para
            else:
                current_text = para
            # New chunk starts at the page of the first fresh paragraph
            current_page_start = page_num
            current_page_end = page_num
        else:
            if current_text:
                current_text += "\n\n" + para
            else:
                current_text = para
            current_page_end = page_num

    if current_text.strip():
        chunks.append({
            "content": current_text.strip(),
            "page_start": current_page_start,
            "page_end": current_page_end,
        })

    return chunks
