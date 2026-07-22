"""
dnd-converter: Convert any RPG adventure PDF into D&D 5e 2024 encounters.

Uploads PDFs directly to the Gemini File API — no local text extraction needed.
Reference files (Monster Manual, DMG) are cached for 48 hours so they only
need to be uploaded once.

Usage:
    python converter.py adventure.pdf
    python converter.py adventure.pdf --rules dmg_2024.pdf --monsters mm_2024.pdf
    python converter.py adventure.pdf --monsters mm_2024.pdf --level 8 --players 5
"""

import argparse
import json
import os
import sys
import time
from pathlib import Path

import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# ── Configuration ──────────────────────────────────────────────────────────────
API_KEY = os.getenv("GEMINI_API_KEY")
if not API_KEY:
    print("❌ GEMINI_API_KEY not set. Copy .env.example to .env and add your key.")
    sys.exit(1)

MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
UPLOAD_CACHE_FILE = Path(".upload_cache.json")
# ───────────────────────────────────────────────────────────────────────────────

genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)


def load_cache() -> dict:
    if UPLOAD_CACHE_FILE.exists():
        return json.loads(UPLOAD_CACHE_FILE.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: dict) -> None:
    UPLOAD_CACHE_FILE.write_text(json.dumps(cache, indent=2), encoding="utf-8")


def upload_pdf(pdf_path: str) -> genai.protos.File:
    """
    Upload a PDF to the Gemini File API.
    Caches the file name and upload timestamp locally.
    Files expire on Gemini after 48h — re-upload happens automatically.
    """
    cache = load_cache()
    abs_path = str(Path(pdf_path).resolve())
    name = Path(pdf_path).name

    if abs_path in cache:
        cached = cache[abs_path]
        age_hours = (time.time() - cached.get("uploaded_at", 0)) / 3600
        remaining = 48 - age_hours

        if remaining > 0:
            # File should still be alive — verify with a quick API check
            try:
                file = genai.get_file(cached["name"])
                if file.state.name == "ACTIVE":
                    print(f"  ✅ Using cached upload: {name} ({remaining:.0f}h remaining)")
                    return file
            except Exception:
                pass  # File gone on Gemini's side, re-upload
        else:
            print(f"  🔄 Cache expired for {name}, re-uploading...")

    # Upload the file
    print(f"  📤 Uploading {name} to Gemini... ", end="", flush=True)
    file = genai.upload_file(pdf_path, mime_type="application/pdf")

    # Wait for Gemini to finish processing
    while file.state.name == "PROCESSING":
        print(".", end="", flush=True)
        time.sleep(2)
        file = genai.get_file(file.name)

    print(" done!")

    if file.state.name != "ACTIVE":
        print(f"❌ Upload failed. File state: {file.state.name}")
        sys.exit(1)

    # Save to cache with upload timestamp
    cache[abs_path] = {"name": file.name, "uri": file.uri, "uploaded_at": time.time()}
    save_cache(cache)
    return file


def build_prompt(level: int, players: int) -> str:
    return f"""You are an expert Dungeon Master. The attached PDFs contain:
1. (If provided) D&D 5e 2024 reference material: Monster Manual and/or DMG
2. A tabletop RPG adventure to convert

Using the reference material for accurate stat blocks, convert every combat encounter
in the adventure to D&D 5e 2024 format.

The party consists of {players} characters at level {level}.

For each combat encounter produce:
1. Encounter name and a 2-3 line tactical description of the scene
2. Full stat block for each creature (Markdown tables, D&D 5e 2024 format)
3. Individual CR and total XP for the encounter
4. Difficulty rating for {players} players at level {level}
5. Suggested tactics for the monsters
"""


def convert_adventure(
    pdf_adventure: str,
    pdf_rules: str | None,
    pdf_monsters: str | None,
    level: int,
    players: int,
) -> None:
    print(f"\n🎲 dnd-converter — Level {level}, {players} players | model: {MODEL}")
    print("=" * 55)

    content_parts = []

    # Upload reference files (cached 48h — only re-uploaded when expired)
    if pdf_monsters:
        print("\n👹 Monster Manual:")
        content_parts.append(upload_pdf(pdf_monsters))

    if pdf_rules:
        print("\n📚 Rules reference:")
        content_parts.append(upload_pdf(pdf_rules))

    # Upload adventure (fresh each time)
    print("\n📖 Adventure:")
    content_parts.append(upload_pdf(pdf_adventure))

    # Add the conversion prompt
    content_parts.append(build_prompt(level, players))

    print(f"\n🤖 Converting with {MODEL}...")
    response = model.generate_content(content_parts)

    output_path = Path(pdf_adventure).with_name(Path(pdf_adventure).stem + "_dnd5e_2024.md")
    output_path.write_text("# D&D 5e 2024 Encounters\n\n" + response.text, encoding="utf-8")
    print(f"\n✅ Done! Output saved to: {output_path}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Convert any RPG adventure PDF into D&D 5e 2024 encounters.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument("adventure",    help="Path to the adventure PDF")
    parser.add_argument("--rules",      default=None, metavar="PDF", help="Path to DMG / SRD PDF")
    parser.add_argument("--monsters",   default=None, metavar="PDF", help="Path to Monster Manual PDF")
    parser.add_argument("--level",      type=int, default=5,  metavar="N", help="Average party level")
    parser.add_argument("--players",    type=int, default=4,  metavar="N", help="Number of players")
    args = parser.parse_args()

    convert_adventure(args.adventure, args.rules, args.monsters, args.level, args.players)
