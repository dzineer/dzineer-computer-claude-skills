#!/usr/bin/env bash
# safe-unwind.sh — deterministic gates for the safe-unwind-restore skill.
#
# Subcommands (run from inside the git repo):
#   backup  <first_bad_commit> <backup_dir>
#       Enumerate every file changed in <first_bad_commit>^..HEAD, copy each
#       (current worktree version) into <backup_dir>/files preserving paths,
#       sha256-verify every copy against its source, write INDEX.md +
#       checksums.txt. Exits non-zero unless every file matches (0 missing,
#       0 mismatch). NOTHING in the repo is modified.
#
#   verify-revert <pristine_commit>
#       Assert `git diff <pristine> HEAD -- .` is empty (tree identical to
#       pristine). Exits non-zero if not, printing the offending paths.
#
#   verify-restore <pre_revert_commit> <backup_dir> [glob_exclude ...]
#       Assert every file under <backup_dir>/files that exists in the worktree
#       sha256-matches its backup, AND the source diff vs <pre_revert_commit>
#       is empty EXCLUDING the given globs (pass generated files like
#       '*/Cargo.lock' or a bundle dir — they are regenerated from source).
#
# Design: fail LOUD on a real problem, never fail spuriously. Every gate
# prints a machine-checkable summary line the caller shows the user as proof.
# No hardcoded repo/layout paths — the repo is the current directory.

set -euo pipefail

die() { echo "SAFE-UNWIND FAIL: $*" >&2; exit 1; }
have() { command -v "$1" >/dev/null 2>&1 || die "missing tool: $1"; }

sha() { sha256sum "$1" | awk '{print $1}'; }

require_repo() {
  git rev-parse --is-inside-work-tree >/dev/null 2>&1 || die "not inside a git repo"
}

cmd_backup() {
  local first_bad="${1:-}" backup="${2:-}"
  [ -n "$first_bad" ] && [ -n "$backup" ] || die "usage: backup <first_bad_commit> <backup_dir>"
  require_repo; have sha256sum
  git cat-file -e "${first_bad}^" 2>/dev/null || die "no parent for $first_bad (is it the first commit?)"

  local files_dir="$backup/files"
  rm -rf "$backup"; mkdir -p "$files_dir"
  git diff --name-only "${first_bad}^..HEAD" > "$backup/filelist.txt"
  local expected copied=0 missing=0 mismatch=0 ok=0
  expected=$(wc -l < "$backup/filelist.txt" | tr -d ' ')
  : > "$backup/checksums.txt"
  {
    echo "# safe-unwind backup INDEX"
    echo "# range ${first_bad}^..HEAD  expected=$expected"
    echo "| repo path | sha256(repo) | sha256(backup) | result |"
    echo "|---|---|---|---|"
  } > "$backup/INDEX.md"

  local f src dst
  while IFS= read -r f; do
    [ -n "$f" ] || continue
    if [ ! -f "$f" ]; then
      echo "MISSING IN WORKTREE: $f" >&2; missing=$((missing+1)); continue
    fi
    mkdir -p "$files_dir/$(dirname "$f")"
    cp -p "$f" "$files_dir/$f"; copied=$((copied+1))
    src=$(sha "$f"); dst=$(sha "$files_dir/$f")
    if [ "$src" = "$dst" ]; then ok=$((ok+1)); local r=MATCH; else mismatch=$((mismatch+1)); local r=MISMATCH; echo "MISMATCH: $f" >&2; fi
    printf '%s  %s\n' "$src" "$f" >> "$backup/checksums.txt"
    printf '| `%s` | %s | %s | %s |\n' "$f" "$src" "$dst" "$r" >> "$backup/INDEX.md"
  done < "$backup/filelist.txt"

  echo "==== BACKUP PROOF ===="
  echo "expected=$expected copied=$copied MATCH=$ok mismatch=$mismatch missing=$missing"
  echo "backup_dir=$backup"
  [ "$mismatch" -eq 0 ] && [ "$missing" -eq 0 ] && [ "$copied" -eq "$expected" ] \
    || die "backup incomplete — DO NOT proceed to revert"
  echo "BACKUP OK — safe to proceed"
}

cmd_verify_revert() {
  local pristine="${1:-}"
  [ -n "$pristine" ] || die "usage: verify-revert <pristine_commit>"
  require_repo
  local n; n=$(git diff "$pristine" HEAD -- . | wc -l | tr -d ' ')
  echo "==== REVERT PROOF ===="
  echo "git diff $pristine HEAD -- .  =>  $n lines"
  if [ "$n" -ne 0 ]; then
    echo "offending paths:"; git diff --name-only "$pristine" HEAD -- . | sed 's/^/  /'
    die "tree not identical to pristine — revert incomplete"
  fi
  echo "REVERT OK — tree identical to $pristine"
}

cmd_verify_restore() {
  local pre_revert="${1:-}" backup="${2:-}"; shift 2 || true
  [ -n "$pre_revert" ] && [ -n "$backup" ] || die "usage: verify-restore <pre_revert_commit> <backup_dir> [exclude_glob ...]"
  require_repo; have sha256sum
  local files_dir="$backup/files"
  [ -d "$files_dir" ] || die "backup files dir not found: $files_dir"

  # 1) every backed-up file present in the worktree must match its backup
  local mm=0 ok=0 f rel
  while IFS= read -r f; do
    rel="${f#$files_dir/}"
    [ -f "$rel" ] || continue          # a file intentionally not restored is fine
    if [ "$(sha "$rel")" = "$(sha "$f")" ]; then ok=$((ok+1)); else echo "MISMATCH: $rel" >&2; mm=$((mm+1)); fi
  done < <(find "$files_dir" -type f)

  # 2) source diff vs pre-revert, excluding generated globs passed by caller
  local ex=() g
  for g in "$@"; do ex+=(":(exclude)$g"); done
  local n; n=$(git diff "$pre_revert" HEAD -- . "${ex[@]}" | wc -l | tr -d ' ')

  echo "==== RESTORE PROOF ===="
  echo "sha256 vs backup: MATCH=$ok mismatch=$mm"
  echo "source diff vs $pre_revert (excluding: ${*:-none}) => $n lines"
  [ "$mm" -eq 0 ] || die "restored files differ from backup"
  [ "$n" -eq 0 ] || { git diff --name-only "$pre_revert" HEAD -- . "${ex[@]}" | sed 's/^/  /'; die "restored source not byte-identical to pre-revert"; }
  echo "RESTORE OK — source byte-identical to $pre_revert (generated files excluded, rebuild to regenerate)"
}

main() {
  local sub="${1:-}"; shift || true
  case "$sub" in
    backup)         cmd_backup "$@";;
    verify-revert)  cmd_verify_revert "$@";;
    verify-restore) cmd_verify_restore "$@";;
    *) cat >&2 <<EOF
safe-unwind.sh — gates for the safe-unwind-restore skill (run inside the repo)
  backup         <first_bad_commit> <backup_dir>
  verify-revert  <pristine_commit>
  verify-restore <pre_revert_commit> <backup_dir> [exclude_glob ...]
EOF
       exit 2;;
  esac
}
main "$@"
