"""
parse_mm.py: Parse the Monster Manual PDF into grouped .md files per creature family.

Run this once. It creates a monsters/ subfolder with one .md file per creature family,
grouping all variants together:
  - goblin.md          ← Goblin + Goblin Boss + Goblin Shaman
  - orc.md             ← Orc + Orc War Chief + Orc Eye of Gruumsh
  - dragon_red.md      ← Red Dragon Wyrmling + Young + Adult + Ancient Red Dragon

How it works:
  - H1 headings  → chapter/section markers, ignored
  - H2 headings  → creature family → one file per family
  - H3+ headings → variants/stat blocks, kept inside the family file

Usage:
    python parse_mm.py mm_2024.pdf
    python parse_mm.py mm_2024.pdf --out monsters
"""

import argparse
import re
import sys
from pathlib import Path
from docling.document_converter import DocumentConverter


# Words that indicate a heading is a chapter/section, not a monster entry.
# These H2s will be skipped rather than written as monster files.
SECTION_KEYWORDS = {
    "introduction", "appendix", "chapter", "contents", "index",
    "foreword", "preface", "credits", "monsters", "creatures",
    "table", "list", "using this book", "reading a stat block",
}


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to Markdown using Docling, with local cache."""
    md_path = Path(pdf_path).with_suffix(".md")

    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")
        print(f"  ✅ Using cached: {md_path.name} ({len(markdown):,} characters)")
        return markdown

    print(f"  🤖 Processing with Docling: {Path(pdf_path).name}  (first time — may take ~30 minutes for a full MM)")
    converter = DocumentConverter()
    markdown = converter.convert(pdf_path).document.export_to_markdown()
    md_path.write_text(markdown, encoding="utf-8")
    print(f"  💾 Cached at: {md_path.name} ({len(markdown):,} characters)")
    return markdown


def slugify(name: str) -> str:
    """Convert a creature family name to a safe filename."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name.strip("_")


def is_section_heading(name: str) -> bool:
    """Return True if this heading looks like a chapter/section rather than a monster."""
    lower = name.lower().strip()
    return any(kw in lower for kw in SECTION_KEYWORDS)


def split_into_families(markdown: str) -> dict[str, str]:
    """
    Split Markdown into creature families grouped by H2 heading.

    Structure assumed (standard D&D MM layout after Docling):
      # Chapter heading        ← H1, ignored
      ## Goblin                ← H2, start of family group
      Intro text about goblins
      ### Goblin               ← H3, individual stat block (variant)
      ### Goblin Boss          ← H3, another variant in same family
      ## Orc                   ← H2, next family
      ...

    Everything between two H2 headings (including all H3+ variants) is
    kept together in one family file.
    """
    # Split on H2 boundaries only
    pattern = r"^(## .+)$"
    parts = re.split(pattern, markdown, flags=re.MULTILINE)

    families: dict[str, str] = {}

    # parts: [preamble, "## Goblin", goblin_content, "## Orc", orc_content, ...]
    for i in range(1, len(parts) - 1, 2):
        heading_line = parts[i].strip()          # "## Goblin"
        body = parts[i + 1].strip()              # everything until next H2

        name = heading_line.lstrip("#").strip()  # "Goblin"

        if is_section_heading(name) or not body:
            continue

        full_entry = f"{heading_line}\n\n{body}"
        families[name] = full_entry

    return families


def detect_heading_level(markdown: str) -> str:
    """
    Inspect the Markdown to determine what heading level Docling used for monster entries.
    Returns a brief summary to help diagnose unexpected structures.
    """
    h1 = len(re.findall(r"^# .+$", markdown, re.MULTILINE))
    h2 = len(re.findall(r"^## .+$", markdown, re.MULTILINE))
    h3 = len(re.findall(r"^### .+$", markdown, re.MULTILINE))
    return f"H1: {h1}, H2: {h2}, H3: {h3}"


def parse_monster_manual(pdf_path: str, output_dir: str) -> None:
    print("\n📖 Monster Manual Parser")
    print("=" * 50)

    print("\n🔄 Loading Monster Manual:")
    markdown = pdf_to_markdown(pdf_path)

    heading_summary = detect_heading_level(markdown)
    print(f"  📊 Heading structure detected — {heading_summary}")

    print("\n✂️  Grouping monsters by creature family...")
    families = split_into_families(markdown)

    if not families:
        print("❌ Could not find creature family entries.")
        print(f"   Heading structure: {heading_summary}")
        print("   Try opening the cached .md file and check the heading levels used.")
        sys.exit(1)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"💾 Writing {len(families)} family files to '{output_dir}/'...")
    for name, content in families.items():
        filepath = out_path / f"{slugify(name)}.md"
        filepath.write_text(content, encoding="utf-8")

    examples = list(families.keys())[:3]
    print(f"\n✅ Done! {len(families)} files written to '{output_dir}/'")
    print(f"   Examples: {', '.join(slugify(n) + '.md' for n in examples)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse Monster Manual PDF into grouped .md files per creature family.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pdf",   help="Path to the Monster Manual PDF")
    parser.add_argument("--out", default="monsters", metavar="DIR", help="Output folder for monster .md files")
    args = parser.parse_args()

    parse_monster_manual(args.pdf, args.out)
