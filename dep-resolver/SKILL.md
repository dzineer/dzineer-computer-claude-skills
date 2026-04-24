---
name: dep-resolver
description: Analyzes the TS codebase to determine the optimal porting order (Leaf-to-Root).
---

## Core Logic
1. **Scan**: Analyze imports in the target TS file.
2. **Graph Check**: Identify which dependencies are "Internal" (part of Jarvis) vs "External" (npm).
3. **Status Check**: Verify if the Internal dependencies have already been ported to the Rust workspace.
4. **Output**: Return a "Portability Score." If dependencies are missing, list them as "Required Prerequisites."

## Usage
"Run dep-resolver on `src/agent/orchestrator.ts` and tell me if I can port it yet."
