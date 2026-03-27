---
name: ascii-banner
description: >
  Generate ASCII art banners from text. Use when the user asks for ASCII art,
  text banners, terminal art, figlet-style text, or decorative text headers.
user-invocable: true
---

# ASCII Banner Generator

Generate ASCII art banners from text input with multiple font styles and optional borders.

## When to Use

- User asks for "ASCII art", "banner", "figlet", "text art", or "terminal art"
- User wants decorative text headers for READMEs, scripts, or terminal output
- User asks to "make text big" or "stylize text" in ASCII

## How It Works

Run the bundled Python script. Zero external dependencies.

### Commands

**Basic banner:**
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "Hello World"
```

**Choose a font (block, slim, shadow, dos, mini, script, banner, digital):**
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "Hello" --font shadow
```

**Add a border:**
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "Deploy v2.0" --border
```

**Custom border character:**
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "ALERT" --border --border-char "#"
```

**List available fonts:**
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py --list-fonts
```

**Save to file:**
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "My App" --output banner.txt
```

## Examples

**User:** "Make me an ASCII banner that says DZINEER"
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "DZINEER" --font block
```

**User:** "Generate a bordered banner for my deploy script header"
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "DEPLOY" --font shadow --border
```

**User:** "ASCII art saying Hello in a slim style"
```bash
python3 ~/.claude/skills/ascii-banner/scripts/banner.py "Hello" --font slim
```

## Important Notes

- All fonts are built-in — no pip installs, no pyfiglet, no external deps
- Only ASCII characters A-Z, 0-9, space, and common punctuation are supported
- Lowercase input is auto-uppercased for block/shadow/dos fonts
- The script uses only Python standard library
- Output is plain text safe for terminals, scripts, READMEs, and code comments
