"""
Fetch a party program from a webpage and save it as a PDF.

Usage:
    uv run python scripts/fetch_program_pdf.py \\
        --url https://pvbl.nl/partijprogramma/ \\
        --output data/programs/amsterdam-2026/pvbl.pdf \\
        --party "Partij voor Betaalbaar Leven (PVBL)"

The script fetches the page, extracts readable text while preserving heading
hierarchy, and renders a clean PDF using fpdf2 with Arial Unicode fonts.
"""

import argparse
import re
import sys
from pathlib import Path

import requests
from bs4 import BeautifulSoup, NavigableString, Tag
from fpdf import FPDF
from fpdf.enums import XPos, YPos

FONT_DIR = "/System/Library/Fonts/Supplemental"

# Tags that map to heading levels 1–6
HEADING_TAGS = {"h1", "h2", "h3", "h4", "h5", "h6"}

# Tags whose text content we want to skip entirely
SKIP_TAGS = {"script", "style", "nav", "header", "footer", "noscript", "form", "iframe"}

# Inline tags — their text is folded into the parent block
INLINE_TAGS = {"a", "span", "strong", "em", "b", "i", "u", "small", "mark", "abbr", "cite"}


# ---------------------------------------------------------------------------
# Scraping
# ---------------------------------------------------------------------------

def _clean(text: str) -> str:
    """Collapse whitespace and strip."""
    return re.sub(r"\s+", " ", text).strip()


def _extract_blocks(element: Tag) -> list[dict]:
    """
    Recursively walk the DOM and return a flat list of blocks:
        {"type": "h1"|"h2"|...|"h6"|"p"|"li", "text": str}
    Skips navigation, scripts, and empty nodes.
    """
    blocks: list[dict] = []

    for child in element.children:
        if isinstance(child, NavigableString):
            continue

        tag = child.name
        if not tag:
            continue
        if tag in SKIP_TAGS:
            continue

        if tag in HEADING_TAGS:
            text = _clean(child.get_text())
            if text:
                blocks.append({"type": tag, "text": text})

        elif tag == "p":
            text = _clean(child.get_text())
            if text:
                blocks.append({"type": "p", "text": text})

        elif tag in ("ul", "ol"):
            for li in child.find_all("li", recursive=False):
                text = _clean(li.get_text())
                if text:
                    blocks.append({"type": "li", "text": text})

        elif tag in ("section", "article", "main", "div", "aside"):
            blocks.extend(_extract_blocks(child))

        elif tag in INLINE_TAGS:
            # Top-level inline element — treat as paragraph
            text = _clean(child.get_text())
            if text:
                blocks.append({"type": "p", "text": text})

    return blocks


def _deduplicate(blocks: list[dict]) -> list[dict]:
    """Remove consecutive duplicate blocks (e.g. repeated headings from sticky navs)."""
    seen: list[str] = []
    result: list[dict] = []
    for b in blocks:
        if b["text"] not in seen:
            result.append(b)
            seen.append(b["text"])
            if len(seen) > 20:
                seen.pop(0)
    return result


def scrape_program(url: str) -> list[dict]:
    """Fetch a URL and return extracted content blocks."""
    headers = {"User-Agent": "Mozilla/5.0 (compatible; VibeCheck/1.0; +https://verkiezingen.app)"}
    resp = requests.get(url, headers=headers, timeout=20)
    resp.raise_for_status()

    soup = BeautifulSoup(resp.text, "html.parser")

    # Try to find a <main> or <article> element; fall back to <body>
    root = soup.find("main") or soup.find("article") or soup.find("body")
    if not root:
        raise ValueError("Could not find page body")

    blocks = _extract_blocks(root)
    blocks = _deduplicate(blocks)

    # Strip blocks that are clearly nav-noise (very short or ALL CAPS menu items)
    blocks = [b for b in blocks if len(b["text"]) > 3]

    return blocks


# ---------------------------------------------------------------------------
# PDF rendering
# ---------------------------------------------------------------------------

class ProgramPDF(FPDF):
    def __init__(self, party_name: str, source_url: str):
        super().__init__()
        self._party_name = party_name
        self._source_url = source_url
        self.add_font("Arial", "", f"{FONT_DIR}/Arial.ttf")
        self.add_font("Arial", "B", f"{FONT_DIR}/Arial Bold.ttf")
        self.add_font("Arial", "I", f"{FONT_DIR}/Arial Italic.ttf")
        self.set_auto_page_break(auto=True, margin=20)

    def header(self):
        self.set_font("Arial", "I", 9)
        self.set_text_color(140, 140, 140)
        self.cell(
            0, 8, self._party_name, align="L",
            new_x=XPos.LMARGIN, new_y=YPos.NEXT,
        )

    def footer(self):
        self.set_y(-12)
        self.set_font("Arial", "", 8)
        self.set_text_color(150, 150, 150)
        self.cell(0, 8, f"Pagina {self.page_no()}", align="C")

    def _ensure_left(self):
        self.set_x(self.l_margin)

    def render_title_page(self):
        self.add_page()
        self.ln(20)
        self.set_font("Arial", "B", 24)
        self.set_text_color(0, 70, 140)
        self._ensure_left()
        self.multi_cell(self.epw, 12, self._party_name, align="C")
        self.ln(6)
        self.set_font("Arial", "", 14)
        self.set_text_color(60, 60, 60)
        self._ensure_left()
        self.multi_cell(self.epw, 8, "Verkiezingsprogramma 2026", align="C")
        self.ln(10)
        # Rule
        y = self.get_y()
        self.set_draw_color(0, 70, 140)
        self.set_line_width(0.6)
        self.line(self.l_margin + 30, y, self.w - self.r_margin - 30, y)
        self.ln(10)
        self.set_font("Arial", "I", 10)
        self.set_text_color(120, 120, 120)
        self._ensure_left()
        self.multi_cell(self.epw, 6, f"Bron: {self._source_url}", align="C")

    def render_blocks(self, blocks: list[dict]):
        self.add_page()

        # Mapping heading level → (font size, color, top spacing, bottom spacing)
        heading_style: dict[str, tuple] = {
            "h1": (18, (0, 70, 140),  6, 3),
            "h2": (15, (0, 70, 140),  5, 2),
            "h3": (13, (30, 90, 160), 4, 2),
            "h4": (12, (50, 100, 160), 3, 1),
            "h5": (11, (70, 110, 160), 2, 1),
            "h6": (10, (90, 120, 160), 2, 1),
        }

        for block in blocks:
            btype = block["type"]
            text  = block["text"]
            self._ensure_left()

            if btype in heading_style:
                size, color, top, bot = heading_style[btype]
                self.ln(top)
                self.set_font("Arial", "B", size)
                self.set_text_color(*color)
                self.multi_cell(self.epw, size * 0.6, text)
                self.ln(bot)

            elif btype == "li":
                self.set_font("Arial", "", 11)
                self.set_text_color(30, 30, 30)
                # Indent + bullet
                self.set_x(self.l_margin + 5)
                self.multi_cell(self.epw - 5, 6, f"\u2022  {text}", align="J")
                self.ln(1)

            else:  # p
                self.set_font("Arial", "", 11)
                self.set_text_color(30, 30, 30)
                self.multi_cell(self.epw, 6, text, align="J")
                self.ln(3)


def build_pdf(blocks: list[dict], output_path: Path, party_name: str, source_url: str):
    pdf = ProgramPDF(party_name=party_name, source_url=source_url)
    pdf.render_title_page()
    pdf.render_blocks(blocks)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(output_path))


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="Scrape a party program webpage and save it as a PDF."
    )
    parser.add_argument("--url",    required=True, help="URL of the program page")
    parser.add_argument("--output", required=True, help="Output PDF path (e.g. data/programs/amsterdam-2026/pvbl.pdf)")
    parser.add_argument("--party",  default="",    help="Party name for the title page and header")
    args = parser.parse_args()

    url    = args.url
    output = Path(args.output)
    party  = args.party or output.stem.upper()

    print(f"Fetching {url} ...")
    try:
        blocks = scrape_program(url)
    except Exception as exc:
        print(f"ERROR: could not fetch/parse page: {exc}", file=sys.stderr)
        sys.exit(1)

    print(f"Extracted {len(blocks)} content blocks.")

    print(f"Rendering PDF -> {output} ...")
    build_pdf(blocks, output, party_name=party, source_url=url)
    print("Done.")


if __name__ == "__main__":
    main()
