#!/usr/bin/env python3
"""
File Checksum Calculator
Computes cryptographic checksums for files and directories.
No external dependencies — uses only Python standard library.
"""

import argparse
import hashlib
import os
import sys
import fnmatch


ALGORITHMS = {
    "md5": hashlib.md5,
    "sha1": hashlib.sha1,
    "sha256": hashlib.sha256,
    "sha512": hashlib.sha512,
}

CHUNK_SIZE = 8192


def compute_checksum(file_path, algorithm="sha256"):
    """Compute checksum of a single file."""
    hasher = ALGORITHMS[algorithm]()
    with open(file_path, "rb") as f:
        while True:
            chunk = f.read(CHUNK_SIZE)
            if not chunk:
                break
            hasher.update(chunk)
    return hasher.hexdigest()


def collect_files(path, glob_pattern=None, include_hidden=True):
    """Collect files from a path (file or directory)."""
    if os.path.isfile(path):
        return [path]

    files = []
    for root, dirs, filenames in os.walk(path):
        if not include_hidden:
            dirs[:] = [d for d in dirs if not d.startswith(".")]
            filenames = [f for f in filenames if not f.startswith(".")]

        for filename in sorted(filenames):
            if glob_pattern and not fnmatch.fnmatch(filename, glob_pattern):
                continue
            files.append(os.path.join(root, filename))

    return sorted(files)


def generate_checksums(path, algorithms, glob_pattern=None, include_hidden=True):
    """Generate checksums for all files at path."""
    files = collect_files(path, glob_pattern, include_hidden)
    results = []

    for file_path in files:
        try:
            rel_path = os.path.relpath(file_path)
            for algo in algorithms:
                checksum = compute_checksum(file_path, algo)
                results.append((algo, checksum, rel_path))
        except (PermissionError, OSError) as e:
            print(f"SKIP    {file_path}  ({e})", file=sys.stderr)

    return results


def format_results(results):
    """Format results as lines."""
    lines = []
    for algo, checksum, path in results:
        lines.append(f"{algo}  {checksum}  {path}")
    return lines


def load_manifest(manifest_path):
    """Load a previously saved manifest file."""
    entries = {}
    with open(manifest_path, "r") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            parts = line.split("  ", 2)
            if len(parts) == 3:
                algo, checksum, path = parts
                entries[path] = (algo, checksum)
    return entries


def verify_against_manifest(path, manifest_path, glob_pattern=None, include_hidden=True):
    """Verify current files against a saved manifest."""
    manifest = load_manifest(manifest_path)
    current_files = collect_files(path, glob_pattern, include_hidden)
    current_rel = {os.path.relpath(f) for f in current_files}
    manifest_paths = set(manifest.keys())

    output = []
    changed = 0
    ok = 0

    for rel_path in sorted(current_rel | manifest_paths):
        if rel_path in current_rel and rel_path not in manifest_paths:
            output.append(f"NEW     {rel_path}")
            changed += 1
        elif rel_path not in current_rel and rel_path in manifest_paths:
            output.append(f"MISSING {rel_path}")
            changed += 1
        else:
            algo, expected = manifest[rel_path]
            actual = compute_checksum(
                os.path.join(os.path.dirname(path) if os.path.isfile(path) else path, rel_path),
                algo,
            )
            if actual == expected:
                output.append(f"OK      {rel_path}")
                ok += 1
            else:
                output.append(f"CHANGED {rel_path}")
                changed += 1

    output.append("")
    output.append(f"Total: {ok + changed} files, {ok} unchanged, {changed} changed/new/missing")
    return output


def verify_single(file_path, expected_hash, algorithms):
    """Verify a single file against an expected hash."""
    for algo in algorithms:
        actual = compute_checksum(file_path, algo)
        if actual.lower() == expected_hash.lower():
            print(f"MATCH   {algo}  {actual}  {file_path}")
            return True

    # No match — show what we computed
    print(f"NO MATCH for {file_path}")
    print(f"Expected: {expected_hash}")
    for algo in ALGORITHMS:
        actual = compute_checksum(file_path, algo)
        if actual.lower() == expected_hash.lower():
            print(f"MATCH on {algo}: {actual}")
            return True
        print(f"  {algo}: {actual}")
    return False


def main():
    parser = argparse.ArgumentParser(
        description="Calculate checksums of files and directories"
    )
    parser.add_argument("path", help="File or directory to checksum")
    parser.add_argument(
        "--algorithm", "-a",
        nargs="+",
        default=["sha256"],
        choices=list(ALGORITHMS.keys()),
        help="Hash algorithm(s) to use (default: sha256)",
    )
    parser.add_argument(
        "--glob", "-g",
        default=None,
        help="Glob pattern to filter files (e.g., '*.py')",
    )
    parser.add_argument(
        "--output", "-o",
        default=None,
        help="Save results to a manifest file",
    )
    parser.add_argument(
        "--verify", "-v",
        default=None,
        metavar="MANIFEST",
        help="Verify files against a saved manifest",
    )
    parser.add_argument(
        "--expect", "-e",
        default=None,
        help="Verify a single file matches this hash value",
    )
    parser.add_argument(
        "--no-hidden",
        action="store_true",
        help="Exclude hidden files and directories",
    )

    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"Error: '{args.path}' does not exist", file=sys.stderr)
        sys.exit(1)

    include_hidden = not args.no_hidden

    # Mode: verify single file against expected hash
    if args.expect:
        success = verify_single(args.path, args.expect, list(ALGORITHMS.keys()))
        sys.exit(0 if success else 1)

    # Mode: verify against manifest
    if args.verify:
        if not os.path.exists(args.verify):
            print(f"Error: Manifest '{args.verify}' does not exist", file=sys.stderr)
            sys.exit(1)
        lines = verify_against_manifest(args.path, args.verify, args.glob, include_hidden)
        for line in lines:
            print(line)
        sys.exit(0)

    # Mode: generate checksums
    results = generate_checksums(args.path, args.algorithm, args.glob, include_hidden)
    lines = format_results(results)

    for line in lines:
        print(line)

    if args.output:
        with open(args.output, "w") as f:
            f.write(f"# Checksum manifest generated by file-checksum skill\n")
            f.write(f"# Path: {os.path.abspath(args.path)}\n")
            for line in lines:
                f.write(line + "\n")
        print(f"\nManifest saved to: {args.output}", file=sys.stderr)

    # Summary to stderr
    print(f"\n{len(results)} checksum(s) computed", file=sys.stderr)


if __name__ == "__main__":
    main()
