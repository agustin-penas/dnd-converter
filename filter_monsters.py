"""
filter_monsters.py: Select only the monsters needed for an adventure from the parsed Monster Manual.

Reads an adventure PDF (or its cached .md), asks Gemini to identify which monsters appear
in it, then combines the matching monster files from the monsters/ folder into a single
filtered .md file ready to be passed to converter.py via --monsters.

Usage:
    python filter_monsters.py adventure.pdf
    python filter_monsters.py adventure.pdf --monsters-dir monsters
    python filter_monsters.py adventure.pdf --monsters-dir monsters --out filtered_monsters.md
"""

import argparse
import json
import os
import sys
from pathlib import Path

import google.generativeai as genai
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption
from dotenv import load_dotenv

load_dotenv()

API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("❌ GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to Markdown using Docling, with local cache."""
    md_path = Path(pdf_path).with_suffix(".md")

    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")
        print(f"  ✅ Using cached: {md_path.name} ({len(markdown):,} characters)")
        return markdown

    print(f"  🤖 Processing with Docling: {Path(pdf_path).name}  (first time — may take a few minutes)")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # PDFs are text-based, no OCR needed
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    markdown = converter.convert(pdf_path).document.export_to_markdown()
    md_path.write_text(markdown, encoding="utf-8")
    print(f"  💾 Cached at: {md_path.name} ({len(markdown):,} characters)")
    return markdown


def list_available_monsters(monsters_dir: str) -> dict[str, Path]:
    """
    Return a dict of {display_name: file_path} for all .md files in the monsters folder.
    Uses index.json (produced by parse_mm.py) for clean name mapping.
    Falls back to filename-based names if index not found.
    """
    dir_path = Path(monsters_dir)
    if not dir_path.exists():
        print(f"❌ Monsters folder '{monsters_dir}' not found.")
        print("   Run parse_mm.py first: python parse_mm.py mm_2024.pdf")
        sys.exit(1)

    index_path = dir_path / "index.json"
    if index_path.exists():
        index = json.load(index_path.open(encoding="utf-8"))
        # index maps clean_name_lower → filename; invert to {clean_name: Path}
        seen: set[str] = set()
        result: dict[str, Path] = {}
        for name, filename in index.items():
            filepath = dir_path / filename
            if filepath.exists() and filename not in seen:
                result[name] = filepath
                seen.add(filename)
        return result

    # Fallback: derive names from filenames
    files = list(dir_path.glob("*.md"))
    if not files:
        print(f"❌ No .md files found in '{monsters_dir}'.")
        print("   Run parse_mm.py first: python parse_mm.py mm_2024.pdf")
        sys.exit(1)
    return {f.stem.replace("_", " "): f for f in sorted(files)}


def identify_monsters(adventure_text: str, available_monsters: list[str]) -> list[str]:
    """Ask Gemini to identify which monsters from the available list appear in the adventure."""
    available_list = "\n".join(f"- {name}" for name in sorted(available_monsters))

    prompt = f"""You are analyzing a tabletop RPG adventure to identify which monsters appear in it.

Below is a list of available monster entries from the Monster Manual.
Return ONLY the names of monsters that appear or are referenced in the adventure text.

Rules:
- Match by creature type (e.g., "orc raiders" → "orc", "skeletal warriors" → "skeleton")
- Include variants if the base creature is present (e.g., if adventure has "goblin boss", include "goblin" too)
- Be conservative: only include monsters clearly present, not vague references
- Return a valid JSON array of strings using EXACTLY the names from the available list

AVAILABLE MONSTERS:
{available_list}

ADVENTURE TEXT:
{adventure_text[:50000]}

Respond with ONLY a JSON array, no explanation. Example: ["goblin", "orc", "skeleton warrior"]
"""

    response = model.generate_content(prompt)
    raw = response.text.strip()

    # Strip markdown code fences if present
    raw = raw.removeprefix("```json").removeprefix("```").removesuffix("```").strip()

    try:
        monsters = json.loads(raw)
        if isinstance(monsters, list):
            return [m.lower().strip() for m in monsters]
    except json.JSONDecodeError:
        print(f"⚠️  Could not parse Gemini response as JSON: {raw[:200]}")

    return []


def filter_monsters(pdf_adventure: str, monsters_dir: str, output_file: str) -> None:
    print(f"\n🔍 Monster Filter — model: {MODEL}")
    print("=" * 50)

    print("\n📖 Loading adventure:")
    adventure_text = pdf_to_markdown(pdf_adventure)

    print(f"\n📂 Scanning '{monsters_dir}' for available monsters...")
    available = list_available_monsters(monsters_dir)
    print(f"  Found {len(available)} monster entries")

    print("\n🤖 Asking Gemini to identify monsters in the adventure...")
    matched_names = identify_monsters(adventure_text, list(available.keys()))

    if not matched_names:
        print("⚠️  No monsters identified. The output file will be empty.")

    # Match returned names back to file paths (fuzzy: check if returned name is substring)
    matched_files: list[Path] = []
    not_found: list[str] = []

    for name in matched_names:
        if name in available:
            matched_files.append(available[name])
        else:
            # Fuzzy fallback: find any available monster whose name contains the returned name
            fuzzy = [path for avail_name, path in available.items() if name in avail_name or avail_name in name]
            if fuzzy:
                matched_files.extend(fuzzy)
            else:
                not_found.append(name)

    # Deduplicate
    matched_files = list(dict.fromkeys(matched_files))

    print(f"\n✅ Matched {len(matched_files)} monster files:")
    for f in matched_files:
        print(f"   - {f.stem.replace('_', ' ')}")

    if not_found:
        print(f"\n⚠️  {len(not_found)} monsters not found in the library (will rely on Gemini's knowledge):")
        for name in not_found:
            print(f"   - {name}")

    # Combine into a single .md file
    out_path = Path(output_file)
    combined = "\n\n---\n\n".join(f.read_text(encoding="utf-8") for f in matched_files)
    out_path.write_text(combined, encoding="utf-8")

    print(f"\n💾 Filtered monster data saved to: {out_path}")
    print(f"   {len(combined):,} characters — ready to use with converter.py --monsters {out_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Filter Monster Manual entries to only those used in an adventure.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("adventure",          help="Path to the adventure PDF")
    parser.add_argument("--monsters-dir",     default="monsters", metavar="DIR", help="Folder with parsed monster .md files (from parse_mm.py)")
    parser.add_argument("--out",              default=None, metavar="FILE", help="Output .md file (default: <adventure>_monsters.md)")
    args = parser.parse_args()

    output = args.out or str(Path(args.adventure).with_name(Path(args.adventure).stem + "_monsters.md"))
    filter_monsters(args.adventure, args.monsters_dir, output)
