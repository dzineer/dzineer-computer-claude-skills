---
name: git-up
description: Create branch (if needed), commit, push, create PR, wait for checks, and merge to main
disable-model-invocation: false
---

Perform a full git-up workflow. Follow these steps IN ORDER:

## 1. Check current state
- Run `git status` to see what's changed
- Run `git branch --show-current` to get the current branch name
- Run `git log --oneline -5` to see recent commit style

## 2. Branch
- If already on a feature branch (not `main`/`master`), stay on it
- If on `main`/`master`, ask the user for a branch name, then create and switch to it:
  ```
  git checkout -b <branch-name>
  ```
- If the branch already exists remotely, just check it out

## 3. Stage and Commit
- Review all changes with `git diff` and `git diff --staged`
- Stage relevant files (prefer specific files over `git add -A` to avoid secrets)
- Write a concise commit message summarizing the changes (1-2 sentences, focus on "why")
- **NEVER add Co-Authored-By lines** — user explicitly forbids this
- Commit using a HEREDOC:
  ```
  git commit -m "$(cat <<'EOF'
  Your commit message here
  EOF
  )"
  ```

## 4. Push
- Push the branch to origin with tracking:
  ```
  git push -u origin <branch-name>
  ```

## 5. Create PR
- Use `gh pr create` with a clear title and body:
  ```
  gh pr create --title "Short title" --body "$(cat <<'EOF'
  ## Summary
  - bullet points

  ## Test plan
  - [ ] verification steps
  EOF
  )"
  ```
- If a PR already exists for this branch, skip creation and show the existing PR URL

## 6. Wait for checks
- Run `gh pr checks <pr-number> --watch` to wait for CI checks to complete
- If no checks are configured, proceed immediately
- If checks fail, report the failure to the user and STOP — do not merge

## 7. Merge
- Merge the PR into main:
  ```
  gh pr merge <pr-number> --merge --delete-branch
  ```
- After merge, switch back to main and pull:
  ```
  git checkout main && git pull origin main
  ```

## 8. Report
- Show the user the merged PR URL and confirm success

## Important
- If ANY step fails, stop and report the error — don't continue blindly
- Never force push
- Never skip hooks (no --no-verify)
- Ask the user before proceeding if anything looks unexpected
