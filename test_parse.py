"""
test_parse.py: Quick test to see how Docling parses a few pages of the Monster Manual.

Usage:
    python test_parse.py mm_2024.pdf          # parse first 10 pages
    python test_parse.py mm_2024.pdf 20 35    # parse pages 20-35
"""

import sys
from pathlib import Path

from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption


def test_pages(pdf_path: str, start_page: int = 1, end_page: int = 10) -> None:
    print(f"\n🔬 Testing Docling on pages {start_page}–{end_page} of '{Path(pdf_path).name}'")
    print("=" * 60)

    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False        # MM is text-based, no OCR needed
    pipeline_options.do_table_structure = True

    converter = DocumentConverter(
        format_options={
            InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)
        }
    )

    print("⏳ Processing...")
    result = converter.convert(pdf_path, page_range=(start_page, end_page))
    markdown = result.document.export_to_markdown()

    # Save output
    out_file = Path(pdf_path).stem + f"_pages_{start_page}_{end_page}.md"
    Path(out_file).write_text(markdown, encoding="utf-8")

    # Print preview
    print(f"✅ Done — {len(markdown):,} characters extracted")
    print(f"💾 Saved to: {out_file}")
    print(f"\n{'─'*60}")
    print("PREVIEW (first 3000 characters):")
    print('─'*60)
    print(markdown[:3000])


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_parse.py mm_2024.pdf [start_page] [end_page]")
        sys.exit(1)

    pdf = sys.argv[1]
    start = int(sys.argv[2]) if len(sys.argv) > 2 else 1
    end = int(sys.argv[3]) if len(sys.argv) > 3 else 10

    test_pages(pdf, start, end)
