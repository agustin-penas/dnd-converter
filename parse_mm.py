"""
parse_mm.py: Parse the Monster Manual PDF into individual .md files per monster.

Run this once. It creates a monsters/ subfolder with one .md file per monster entry,
named after the monster (e.g., goblin.md, orc_war_chief.md).

Usage:
    python parse_mm.py mm_2024.pdf
    python parse_mm.py mm_2024.pdf --out monsters
"""

import argparse
import re
import sys
from pathlib import Path
from docling.document_converter import DocumentConverter


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to Markdown using Docling, with local cache."""
    md_path = Path(pdf_path).with_suffix(".md")

    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")
        print(f"  ✅ Using cached: {md_path.name} ({len(markdown):,} characters)")
        return markdown

    print(f"  🤖 Processing with Docling: {Path(pdf_path).name}  (first time — may take several minutes)")
    converter = DocumentConverter()
    markdown = converter.convert(pdf_path).document.export_to_markdown()
    md_path.write_text(markdown, encoding="utf-8")
    print(f"  💾 Cached at: {md_path.name} ({len(markdown):,} characters)")
    return markdown


def slugify(name: str) -> str:
    """Convert a monster name to a safe filename."""
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name


def split_by_monster(markdown: str) -> dict[str, str]:
    """
    Split the Monster Manual Markdown into per-monster sections.

    Looks for H2 headings (## Monster Name) as entry boundaries,
    which is the standard structure in the D&D 5e Monster Manual.
    Falls back to H3 if no H2 entries are found.
    """
    # Try H2 first, fall back to H3
    for heading_level in (2, 3):
        pattern = rf"^({'#' * heading_level}) (.+)$"
        entries = re.split(pattern, markdown, flags=re.MULTILINE)

        if len(entries) > 3:
            monsters = {}
            # entries: [pre-content, level, name, content, level, name, content, ...]
            for i in range(1, len(entries) - 2, 3):
                hashes = entries[i]
                name = entries[i + 1].strip()
                content = entries[i + 2].strip()
                if name and content:
                    full_entry = f"{'#' * len(hashes)} {name}\n\n{content}"
                    monsters[name] = full_entry
            if monsters:
                return monsters

    return {}


def parse_monster_manual(pdf_path: str, output_dir: str) -> None:
    print(f"\n📖 Monster Manual Parser")
    print("=" * 50)

    print("\n🔄 Loading Monster Manual:")
    markdown = pdf_to_markdown(pdf_path)

    print("\n✂️  Splitting into individual monster entries...")
    monsters = split_by_monster(markdown)

    if not monsters:
        print("❌ Could not find monster entries. The PDF structure may be non-standard.")
        print("   Try opening the cached .md file and checking the heading structure.")
        sys.exit(1)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    print(f"💾 Writing {len(monsters)} monsters to '{output_dir}/'...\n")
    for name, content in monsters.items():
        filename = out_path / f"{slugify(name)}.md"
        filename.write_text(content, encoding="utf-8")

    print(f"✅ Done! {len(monsters)} monster files written to '{output_dir}/'")
    print(f"   Example: {out_path / (slugify(next(iter(monsters))) + '.md')}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse Monster Manual PDF into individual .md files per monster.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pdf",   help="Path to the Monster Manual PDF")
    parser.add_argument("--out", default="monsters", metavar="DIR", help="Output folder for monster .md files")
    args = parser.parse_args()

    parse_monster_manual(args.pdf, args.out)
