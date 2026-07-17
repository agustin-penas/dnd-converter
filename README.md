# 🎲 dnd-converter

> Convert any tabletop RPG adventure PDF into ready-to-play **D&D 5e 2024** encounters.

Given a PDF from any RPG system (Pathfinder, Call of Cthulhu, WFRP, OSR, etc.), this tool extracts all combat encounters and converts them to D&D 5e 2024 stat blocks — including CR, XP, difficulty rating, and suggested tactics — using AI.

**See an example of the output:** [`examples/output_sample.md`](examples/output_sample.md)

---

## How it works

```
Your adventure PDF
       │
       ▼
  Docling (IBM)          ← Converts PDF to clean, structured Markdown
       │
       ▼
  Gemini Flash           ← Reads the adventure + optional rules/monster context
       │
       ▼
  Markdown output        ← Stat blocks, CR, XP, difficulty, tactics
```

- **[Docling](https://github.com/DS4SD/docling)** (IBM open-source) is used instead of basic PDF readers because it preserves tables, headings, and lists — critical for accurate stat block extraction and for the model to understand the source material.
- PDFs of rulebooks (DMG, Monster Manual) are processed **once** and cached locally as Markdown, so you don't wait on every run.
- The adventure PDF is always sent **in full** to the model — no arbitrary character truncation.

---

## Requirements

- Python **3.10 or higher**
- A **Gemini API key** (free tier available: 1,500 requests/day)

---

## Installation

### 1. Clone the repository

```bash
git clone https://github.com/tu-usuario/dnd-converter.git
cd dnd-converter
```

### 2. Create a virtual environment

**macOS / Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

**Windows:**
```cmd
python -m venv venv
venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> ⚠️ Docling downloads AI models (~1–2 GB) on first use. This only happens once.

### 4. Get a Gemini API key (free)

1. Go to [aistudio.google.com](https://aistudio.google.com)
2. Sign in with your Google account
3. Click **"Get API Key"** → **"Create API key"**
4. Copy the key

### 5. Add your API key to the script

Open `converter.py` and replace the placeholder on line 8:

```python
API_KEY = "paste-your-api-key-here"
```

---

## Usage

### Basic (adventure only)

```bash
python converter.py my_adventure.pdf
```

### With D&D 5e reference material (recommended)

```bash
python converter.py my_adventure.pdf \
  --reglas dmg_2024.pdf \
  --monstruos mm_2024.pdf
```

### Full options

```bash
python converter.py my_adventure.pdf \
  --reglas dmg_2024.pdf \
  --monstruos mm_2024.pdf \
  --nivel 8 \
  --jugadores 5
```

| Argument | Description | Default |
|---|---|---|
| `aventura` | Path to the adventure PDF to convert *(required)* | — |
| `--reglas` | Path to the DMG / SRD PDF for combat rules context | None |
| `--monstruos` | Path to the Monster Manual PDF for stat block reference | None |
| `--nivel` | Average party level | `5` |
| `--jugadores` | Number of players in the party | `4` |

### Output

A `.md` file is created in the same folder as your adventure PDF:

```
my_adventure.pdf  →  my_adventure_dnd5e_2024.md
```

Open it in **VS Code** (`Ctrl+Shift+V` / `Cmd+Shift+V`) to preview the formatted tables and stat blocks.

---

## Getting D&D 5e Reference PDFs

> ⚠️ You must legally own any PDFs you use with this tool.

| Document | Where to get it |
|---|---|
| **SRD 5.2** (free, CC license) | [dnd.wizards.com/resources/systems-reference-document](https://dnd.wizards.com/resources/systems-reference-document) — includes ~400 monsters and combat rules |
| **DMG 2024** | D&D Beyond or DriveThruRPG (purchase required) |
| **Monster Manual 2024** | D&D Beyond or DriveThruRPG (purchase required) |

The **SRD 5.2 is free** and covers most use cases — it's a great starting point.

---

## PDF Caching

Rulebook and monster manual PDFs are processed by Docling once and cached as `.md` files next to the originals:

```
dmg_2024.pdf     →  dmg_2024.md      ← generated once, reused forever
mm_2024.pdf      →  mm_2024.md       ← generated once, reused forever
my_adventure.pdf →  my_adventure.md  ← cached per adventure
```

On subsequent runs, the cached `.md` is loaded instantly. To force a re-process, delete the `.md` file.

---

## Supported source systems

The tool works with any RPG adventure PDF, including:

- Pathfinder 1e / 2e
- Call of Cthulhu
- Warhammer Fantasy Roleplay (WFRP)
- OSR systems (Basic D&D, OSRIC, Old-School Essentials)
- Shadowrun
- Any other system with combat encounters

---

## Example output

See [`examples/output_sample.md`](examples/output_sample.md) for a sample of what the converted output looks like.

---

## Contributing

Contributions are welcome! Some ideas for improvement:

- [ ] Smart chunking for very long adventure PDFs
- [ ] JSON output for VTT import (Foundry VTT format)
- [ ] Web UI with Gradio
- [ ] Support for plain text input (no PDF required)
- [ ] Auto-detect source RPG system and tailor conversion

To contribute, fork the repo, create a branch, and open a pull request.

---

## License

MIT — see [LICENSE](LICENSE).

---

## Disclaimer

This tool uses AI to convert content between game systems. Always review the output before using it at the table — stat blocks should be verified against official D&D 5e 2024 sources. This tool does not include, distribute, or reproduce any copyrighted game content.
