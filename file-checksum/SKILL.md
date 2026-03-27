---
name: file-checksum
description: >
  Calculate checksums (MD5, SHA1, SHA256, SHA512) of files and directories.
  Use when the user asks to verify file integrity, compute hashes, compare
  checksums, detect file changes, or generate a checksum manifest.
user-invocable: true
---

# File Checksum Calculator

Calculate cryptographic checksums of files for integrity verification, change detection, and comparison.

## When to Use

- User asks to "checksum", "hash", or "verify integrity" of files
- User wants to compare files across locations or detect changes
- User needs a checksum manifest for a directory
- User asks to verify a downloaded file against a known hash

## How It Works

Run the bundled Python script to compute checksums. The script supports individual files, directories (recursive), glob patterns, and multiple algorithms.

### Commands

**Single file:**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <file_path>
```

**Directory (recursive):**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <directory_path>
```

**Specific algorithm (md5, sha1, sha256, sha512):**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <path> --algorithm sha512
```

**Multiple algorithms at once:**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <path> --algorithm md5 sha256
```

**Glob pattern:**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <directory> --glob "*.py"
```

**Save manifest to file:**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <path> --output checksums.txt
```

**Compare against a previous manifest:**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <path> --verify checksums.txt
```

**Verify a single file against a known hash:**
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py <file> --expect <hash_value>
```

## Examples

**User:** "Checksum all the Python files in my project"
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py . --glob "*.py"
```

**User:** "Generate SHA256 checksums for everything in src/ and save a manifest"
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py src/ --algorithm sha256 --output src_checksums.txt
```

**User:** "Verify this download matches sha256 abc123..."
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py downloaded_file.zip --expect abc123...
```

**User:** "Check if any files changed since last time"
```bash
python3 ~/.claude/skills/file-checksum/scripts/checksum.py . --verify checksums.txt
```

## Output Format

Default output is one line per file:
```
sha256  a1b2c3d4...  path/to/file.py
```

Manifest files use the same format for easy diffing.

Verification output shows:
```
OK      path/to/unchanged_file.py
CHANGED path/to/modified_file.py
NEW     path/to/new_file.py
MISSING path/to/deleted_file.py
```

## Important Notes

- Default algorithm is **SHA256** (best balance of speed and security)
- Binary files are handled correctly (read in binary mode)
- Symlinks are followed by default
- Hidden files (dotfiles) are included unless `--no-hidden` is passed
- The script requires only Python 3 standard library (no pip installs needed)
- Large files are read in 8KB chunks to avoid memory issues
