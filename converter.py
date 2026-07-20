"""
dnd-converter: Convert any RPG adventure PDF into D&D 5e 2024 encounters.

Uses Docling for high-quality PDF-to-Markdown extraction and Gemini Flash
for the system conversion. Reference PDFs (rulebooks, monster manuals) are
cached as Markdown on first use so they don't need to be reprocessed.

Usage:
    python converter.py adventure.pdf
    python converter.py adventure.pdf --rules dmg_2024.pdf --monsters mm_2024.pdf
    python converter.py adventure.pdf --level 8 --players 5
"""

import argparse
import os
import sys
import google.generativeai as genai
from docling.document_converter import DocumentConverter
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
# Set GEMINI_API_KEY and optionally GEMINI_MODEL in a .env file
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("❌ GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")

# Safe character limit for the full prompt (Gemini Flash supports ~1M tokens).
# The adventure text is always kept intact; reference context is trimmed if needed.
MAX_CHARS = 700_000
# ───────────────────────────────────────────────────────────────────────────────

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)


def pdf_to_markdown(pdf_path: str) -> str:
    """Convert a PDF to Markdown using Docling, caching the result alongside the source file."""
    md_path = Path(pdf_path).with_suffix(".md")

    if md_path.exists():
        markdown = md_path.read_text(encoding="utf-8")
        print(f"  ✅ Using cached: {md_path.name} ({len(markdown):,} characters)")
        return markdown

    print(f"  🤖 Processing with Docling: {Path(pdf_path).name}  (first time — may take a few minutes)")
    converter = DocumentConverter()
    markdown = converter.convert(pdf_path).document.export_to_markdown()
    md_path.write_text(markdown, encoding="utf-8")
    print(f"  💾 Cached at: {md_path.name} ({len(markdown):,} characters)")
    return markdown


def build_prompt(adventure_text: str, reference_context: str, level: int, players: int) -> str:
    return f"""You are an expert Dungeon Master. Use the reference documents provided to convert
this adventure into D&D 5e 2024 format.

The party consists of {players} characters at level {level}.

For every combat encounter found in the adventure, generate:
1. Encounter name and a 2–3 line tactical description of the scene
2. Full stat block for each creature (Markdown tables, D&D 5e 2024 format)
3. Individual CR and total XP for the encounter
4. Difficulty rating for the party ({players} players, level {level})
5. Suggested tactics for the monsters

{reference_context}

# ADVENTURE TO CONVERT
{adventure_text}
"""


def convert_adventure(
    pdf_adventure: str,
    pdf_rules: str | None,
    pdf_monsters: str | None,
    level: int,
    players: int,
) -> None:
    print(f"\n🎲 dnd-converter — Level {level}, {players} players | model: {MODEL}")
    print("=" * 50)

    reference_context = ""

    if pdf_rules:
        reference_context += f"\n\n# D&D 5e 2024 COMBAT RULES\n{pdf_to_markdown(pdf_rules)}"

    if pdf_monsters:
        reference_context += f"\n\n# MONSTER MANUAL\n{pdf_to_markdown(pdf_monsters)}"

    adventure_text = pdf_to_markdown(pdf_adventure)

    # Trim reference context if total prompt exceeds the safe limit.
    # The adventure text is never trimmed.
    total_chars = len(reference_context) + len(adventure_text)
    print(f"\n📊 Total context: {total_chars:,} characters")

    if total_chars > MAX_CHARS:
        print("⚠️  Context exceeds safe limit — trimming reference material...")
        available = MAX_CHARS - len(adventure_text)
        if available < 0:
            print("❌ The adventure alone exceeds the limit. Split the PDF into smaller parts.")
            sys.exit(1)
        reference_context = reference_context[:available]

    print("\n🤖 Converting with Gemini Flash...")
    prompt = build_prompt(adventure_text, reference_context, level, players)
    response = model.generate_content(prompt)

    output_path = Path(pdf_adventure).with_name(Path(pdf_adventure).stem + "_dnd5e_2024.md")
    output_path.write_text("# D&D 5e 2024 Encounters\n\n" + response.text, encoding="utf-8")
    print(f"\n✅ Done! Output saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert any RPG adventure PDF into D&D 5e 2024 encounters.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("adventure",      help="Path to the adventure PDF")
    parser.add_argument("--rules",      default=None, metavar="PDF", help="Path to DMG / SRD PDF (combat rules context)")
    parser.add_argument("--monsters",   default=None, metavar="PDF", help="Path to Monster Manual PDF")
    parser.add_argument("--level",       type=int, default=5,  metavar="N", help="Average party level")
    parser.add_argument("--players",   type=int, default=4,  metavar="N", help="Number of players in the party")
    args = parser.parse_args()

    convert_adventure(args.adventure, args.rules, args.monsters, args.level, args.players)

