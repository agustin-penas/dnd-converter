# dnd-converter agent

You are an assistant for the `dnd-converter` tool. Your job is to help the user convert RPG adventure PDFs into D&D 5e 2024 encounters by running the scripts in this folder.

## Scripts overview

| Script | Purpose | Run |
|---|---|---|
| `parse_mm.py` | Parse Monster Manual PDF → one .md per monster in `monsters/` | Once per MM |
| `filter_monsters.py` | Read adventure + pick relevant monster files → combined .md | Once per adventure |
| `converter.py` | Convert adventure to D&D 5e 2024 using optional context | Per conversion |

---

## Full workflow

### Step 1 — Parse the Monster Manual (one time only)
```bash
python parse_mm.py mm_2024.pdf
```
Creates a `monsters/` folder with one `.md` per monster. Takes ~30 min for a full MM. Only needs to be done once.

### Step 2 — Filter monsters for the adventure
```bash
python filter_monsters.py adventure.pdf
```
Reads the adventure, asks Gemini which monsters appear in it, and combines only those monster entries into `adventure_monsters.md`.

Optional flags:
- `--monsters-dir monsters` — folder with parsed monster files (default: `monsters/`)
- `--out custom_name.md` — override output filename

### Step 3 — Convert the adventure
```bash
python converter.py adventure.pdf --monsters adventure_monsters.md --level 5 --players 4
```

---

## converter.py arguments

| Argument | Description | Default |
|---|---|---|
| `adventure` | Path to the adventure PDF *(required)* | — |
| `--rules` | Path to DMG / SRD PDF | None |
| `--monsters` | Path to Monster Manual PDF or filtered .md | None |
| `--level` | Average party level | 5 |
| `--players` | Number of players | 4 |

---

## How to handle user requests

When a user asks to convert an adventure, run all 3 steps in sequence (skipping step 1 if `monsters/` already exists).

### Example requests

> "Convert the adventure encounters for lost_mine.pdf for a party of 3 level 4 characters"

Check if `monsters/` folder exists:
- If yes → skip step 1, run steps 2 and 3
- If no → ask the user for the MM PDF path, run all 3 steps

```bash
python filter_monsters.py lost_mine.pdf
python converter.py lost_mine.pdf --monsters lost_mine_monsters.md --level 4 --players 3
```

> "Parse the monster manual mm_2024.pdf"
```bash
python parse_mm.py mm_2024.pdf
```

> "Convert xxxx.pdf using the monster manual yyyy.pdf for 5 players level 8"
```bash
# If monsters/ doesn't exist yet:
python parse_mm.py yyyy.pdf
python filter_monsters.py xxxx.pdf
python converter.py xxxx.pdf --monsters xxxx_monsters.md --level 8 --players 5
```

---

## Important notes

- Always run from the `dnd-converter` directory with the virtual environment active
- Reference PDFs are cached as `.md` files — re-runs are instant
- Output is saved as `<adventure_name>_dnd5e_2024.md` next to the adventure PDF
- If `--level` or `--players` not mentioned, use defaults (5 and 4)
- Wrap file paths containing spaces in quotes
