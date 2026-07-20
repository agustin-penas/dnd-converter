"""
test_headings.py: Quick inspection of MM PDF text structure using pdfplumber.
No model downloads needed. Use this to check heading levels before running Docling.

Usage:
    python test_headings.py mm_2024.pdf 13 23
"""

import sys
import re
import pdfplumber
from pathlib import Path


def inspect_pages(pdf_path: str, start_page: int = 1, end_page: int = 10) -> None:
    print(f"\n🔬 Inspecting pages {start_page}–{end_page} of '{Path(pdf_path).name}'")
    print("=" * 60)

    full_text = ""
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages[start_page - 1 : end_page]
        for i, page in enumerate(pages, start=start_page):
            text = page.extract_text()
            if text:
                full_text += f"\n\n--- PAGE {i} ---\n\n" + text

    # Save raw text
    out_file = Path(pdf_path).stem + f"_pages_{start_page}_{end_page}_raw.txt"
    Path(out_file).write_text(full_text, encoding="utf-8")
    print(f"💾 Raw text saved to: {out_file}")
    print(f"   {len(full_text):,} characters extracted\n")
    print("─" * 60)
    print("PREVIEW (first 3000 characters):")
    print("─" * 60)
    print(full_text[:3000])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_headings.py mm_2024.pdf [start_page] [end_page]")
        sys.exit(1)

    pdf = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    inspect_pages(pdf, start, end)
