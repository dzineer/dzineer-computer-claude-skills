---
name: structural-probe
description: High-density codebase investigation using code-graph MCP tools. Builds semantic maps without token overflow by using Inventory -> Targeted Extraction -> Verification stages.
---

## Core Logic: The 3-Stage Probe

Instead of calling heavy "summary" tools that return massive strings, follow this multi-stage approach to build a semantic map efficiently:

### Stage A: Inventory
Use `list_codebases` and `get_graph` (with entity_types filter) to identify entry points and boundaries.
- Filter by `entity_types: "code_class,code_function"` to avoid file-level noise
- Use `file_filter` glob to scope to the area of interest
- **Goal:** Get a list of entity IDs and names, NOT full source code

### Stage B: Targeted Extraction
Once an area of interest is identified, use `get_entity` or `get_dependencies` on specific symbols.
- Use `get_dependencies` with `direction: "outgoing"` to see what a class/function depends on
- Use `get_dependencies` with `direction: "incoming"` to see what depends on it
- Use `get_call_chain` with `depth: 2` to trace execution flow
- **Goal:** Understand the dependency web around a specific entity

### Stage C: Verification
If a `get_module_summary` or `get_porting_summary` is needed, ALWAYS post-process the output:
- Pipe through `python3 -c` or `jq` to extract only the fields needed
- Never let raw 100KB+ JSON hit the context window
- **Goal:** Extract exactly what you need, nothing more

## Usage Patterns

### "What does this module depend on?"
```
1. get_module_summary(codebase_id=8, module_path="src/agents")
2. Extract only `internal_dependencies` and `external_dependencies` via jq
3. For each internal dep, get_entity to check if it's been ported
```

### "What's the porting order for this directory?"
```
1. get_graph(codebase_id=8, entity_types="code_file", file_filter="src/vault/*")
2. For each file, get_dependencies(direction="outgoing")
3. Build adjacency list, topological sort -> leaf-first order
```

### "Is this entity safe to port now?"
```
1. get_dependencies(entity_id, direction="outgoing")
2. Check: are all outgoing deps either (a) external crates or (b) already ported?
3. If yes -> safe to port. If no -> list blockers.
```

## Rules
- NEVER call `get_porting_summary` without a post-processing pipeline
- NEVER call `get_module_summary` on `src/` (too broad) -- always scope to a subdirectory
- Prefer `get_entity` + `get_dependencies` over summaries when investigating a single class or function
- Use `search_code` for keyword-based discovery, but note it uses FTS5 (no special characters in queries)
- Cache entity IDs in your working context so you don't re-query them

## MCP Tools Reference
- `list_codebases` - Get codebase IDs
- `get_file_structure(codebase_id)` - All files (use with post-processing)
- `get_graph(codebase_id, entity_types, file_filter, limit)` - Filtered graph
- `get_entity(entity_id)` - Single entity details
- `get_entities_batch(entity_ids)` - Multiple entities at once
- `get_dependencies(entity_id, direction)` - Edges for an entity
- `get_call_chain(entity_id, depth, direction)` - Multi-hop trace
- `get_module_summary(codebase_id, module_path)` - Module overview
- `search_code(query, codebase_id)` - FTS5 keyword search
