"""
parse_mm.py: Parse the Monster Manual PDF into grouped .md files per creature family.

Run this once. It creates a monsters/ subfolder with one .md file per creature family,
plus an index.json mapping clean names to filenames for use by filter_monsters.py.

How it groups monsters:
  - Each new family starts when a section contains a "Habitat" line
    (matched loosely to handle font garbling like "Habitaü")
  - Everything until the next "Habitat:" section (variants, stat blocks, subsections)
    is kept together in one file
  - Clean names are extracted from the lore text to work around heading font garbling

Usage:
    python parse_mm.py mm_2024.pdf
    python parse_mm.py mm_2024.pdf --out monsters
"""

import argparse
import json
import re
import sys
from pathlib import Path
from docling.document_converter import DocumentConverter
from docling.datamodel.base_models import InputFormat
from docling.datamodel.pipeline_options import PdfPipelineOptions
from docling.document_converter import PdfFormatOption


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert PDF to Markdown using Docling, with local cache."""
    md_path = Path(pdf_path).with_suffix(".md")

    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")
        print(f"  ✅ Using cached: {md_path.name} ({len(markdown):,} characters)")
        return markdown

    print(f"  🤖 Processing with Docling: {Path(pdf_path).name}  (this may take ~30 minutes for a full MM)")
    pipeline_options = PdfPipelineOptions()
    pipeline_options.do_ocr = False  # PDFs are text-based, no OCR needed
    converter = DocumentConverter(
        format_options={InputFormat.PDF: PdfFormatOption(pipeline_options=pipeline_options)}
    )
    markdown = converter.convert(pdf_path).document.export_to_markdown()
    md_path.write_text(markdown, encoding="utf-8")
    print(f"  💾 Cached at: {md_path.name} ({len(markdown):,} characters)")
    return markdown


def slugify(name: str) -> str:
    name = name.lower().strip()
    name = re.sub(r"[^\w\s-]", "", name)
    name = re.sub(r"[\s-]+", "_", name)
    return name.strip("_")


def is_habitat_section(body: str) -> bool:
    """
    Detect the 'Habitat' marker loosely — the MM's stylized font sometimes
    renders it as 'Habitaü', 'Habitât', etc.
    """
    return bool(re.search(r"Habit\w{1,3}[\s:]", body))


CREATURE_VERBS = (
    r"are|is|dwell|lurk|haunt|roam|soar|gather|serve|stand|guard|seek|rule|"
    r"range|prowl|hunt|stalk|patrol|dream|possess|use|make|prefer|live|feed|"
    r"attack|worship|wander|appear|embody|manifest|exist|inhabit|create|form|"
    r"build|collect|control|command|lead|fight|protect|defend|thrive|have|"
    r"claim|occupy|operate|manipulate|terrorize|plague|stalk|bend|hoard|"
    r"transform|dominate|consume|devour|rise|emerge|descend|ascend"
)

STOPWORDS = {
    "they", "it", "these", "those", "many", "some", "most", "all", "few",
    "each", "their", "its", "this", "that", "such", "other", "others", "who",
    "which", "what", "where", "when", "how", "both", "more", "less", "much",
    "often", "always", "never", "sometimes", "usually", "typically", "beyond",
    "behind", "while", "though", "although"
}


def char_similarity(a: str, b: str) -> float:
    """Score how many characters two strings share (case-insensitive)."""
    sa, sb = set(a.lower()), set(b.lower())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / max(len(sa), len(sb))


def normalize_candidate(candidate: str) -> str:
    """Title-case a candidate name and naively singularize trailing -s."""
    words = []
    for w in candidate.lower().split():
        if w.endswith("s") and not w.endswith("ss") and len(w) > 3:
            w = w[:-1]
        words.append(w.capitalize())
    return " ".join(words)


def extract_clean_name(heading: str, body: str) -> str:
    """
    Extract a clean monster name from the lore body text to work around
    the font garbling that affects H2 headings in the D&D MM PDF.

    Finds all noun phrases followed by a creature verb in the lore text,
    then picks the one most similar to the heading (by character overlap).
    This handles cases like "While all yugoloths are fiendish, arcanaloths bend..."
    where a genus term appears before the actual monster name.
    """
    habitat_match = re.search(r"Habit\w{1,3}[\s:].*?\n", body)
    lore_text = body[habitat_match.end():].strip() if habitat_match else body

    matches = re.findall(
        rf"([a-zA-Z][a-zA-Z]+(?:\s[a-zA-Z][a-zA-Z]+){{0,2}})\s+(?:{CREATURE_VERBS})\b",
        lore_text,
    )

    candidates = []
    for candidate in matches:
        words = candidate.lower().split()
        if all(w not in STOPWORDS for w in words) and len(candidate) > 2:
            normalized = normalize_candidate(candidate)
            score = char_similarity(heading, normalized)
            candidates.append((score, normalized))

    if candidates:
        candidates.sort(key=lambda x: -x[0])
        return candidates[0][1]

    # Fallback: clean up the (garbled) heading
    clean = re.sub(r"\\[_\-\s]", "", heading)
    return re.sub(r"\s+", " ", clean).strip()


def split_into_families(markdown: str) -> list[dict]:
    """
    Split Markdown into creature families grouped by the Habitat anchor.
    A new family starts whenever a section's content contains a Habitat line.
    """
    pattern = r"^(## .+)$"
    parts = re.split(pattern, markdown, flags=re.MULTILINE)

    sections: list[tuple[str, str]] = []
    for i in range(1, len(parts) - 1, 2):
        sections.append((parts[i].strip(), parts[i + 1].strip()))

    families: list[dict] = []
    current: dict | None = None

    for heading, body in sections:
        if is_habitat_section(body):
            if current:
                families.append(current)
            heading_text = heading.lstrip("#").strip()
            clean_name = extract_clean_name(heading_text, body)
            current = {
                "heading": heading_text,
                "clean_name": clean_name,
                "content": f"{heading}\n\n{body}",
            }
        else:
            if current is None:
                continue
            current["content"] += f"\n\n{heading}\n\n{body}"

    if current:
        families.append(current)

    return families


def parse_monster_manual(pdf_path: str, output_dir: str) -> None:
    print("\n📖 Monster Manual Parser")
    print("=" * 50)

    print("\n🔄 Loading Monster Manual:")
    markdown = pdf_to_markdown(pdf_path)

    h2_count = len(re.findall(r"^## .+$", markdown, re.MULTILINE))
    print(f"  📊 Found {h2_count} H2 headings")

    print("\n✂️  Grouping by creature family (Habitat anchor)...")
    families = split_into_families(markdown)

    if not families:
        print("❌ Could not find any creature families.")
        print("   Check that the cached .md file contains 'Habitat' lines.")
        sys.exit(1)

    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    index: dict[str, str] = {}
    name_collisions: dict[str, int] = {}

    print(f"💾 Writing {len(families)} family files to '{output_dir}/'...")
    for family in families:
        base_slug = slugify(family["clean_name"]) or slugify(family["heading"])

        if base_slug in name_collisions:
            name_collisions[base_slug] += 1
            slug = f"{base_slug}_{name_collisions[base_slug]}"
        else:
            name_collisions[base_slug] = 0
            slug = base_slug

        filename = f"{slug}.md"
        (out_path / filename).write_text(family["content"], encoding="utf-8")

        index[family["clean_name"].lower()] = filename
        if family["heading"].lower() != family["clean_name"].lower():
            index[slugify(family["heading"])] = filename

    (out_path / "index.json").write_text(
        json.dumps(index, indent=2, ensure_ascii=False), encoding="utf-8"
    )

    examples = [f["clean_name"] for f in families[:5]]
    print(f"\n✅ Done!")
    print(f"   {len(families)} family files written to '{output_dir}/'")
    print(f"   Index saved to '{output_dir}/index.json'")
    print(f"   Examples: {', '.join(examples)}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Parse Monster Manual PDF into grouped .md files per creature family.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("pdf",   help="Path to the Monster Manual PDF")
    parser.add_argument("--out", default="monsters", metavar="DIR", help="Output folder for monster .md files")
    args = parser.parse_args()

    parse_monster_manual(args.pdf, args.out)
