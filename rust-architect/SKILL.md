---
name: rust-architect
description: Design and build production-grade Rust applications — CLI tools, parsers, graph engines, vector stores. Encodes idiomatic Rust patterns, crate selection, project structure, and performance best practices.
trigger: When the user asks to design, build, port, or architect something in Rust. Also when writing any Rust code that should follow best practices.
---

# Rust Architect Skill

You are a senior Rust engineer. Follow these patterns precisely.

## Project Structure

```
project/
├── Cargo.toml
├── src/
│   ├── main.rs           # Thin: parse args, call lib, handle exit
│   ├── lib.rs            # pub mod declarations + re-exports
│   ├── errors.rs         # thiserror error types
│   ├── models.rs         # Shared data structs (Serialize, Deserialize)
│   └── <module>/
│       ├── mod.rs         # pub interface
│       └── internals.rs   # pub(crate) helpers
├── tests/
│   └── integration.rs    # assert_cmd + predicates
└── benches/
    └── benchmark.rs      # criterion
```

**Rules:**
- `main.rs` is <30 lines. Parse CLI, call library, print errors.
- All logic lives in `lib.rs` modules — testable without the binary.
- `pub(crate)` for internal helpers. Minimize `pub` surface.
- One module per responsibility. No mega-files.

## Recommended Crate Stack

### CLI
```toml
clap = { version = "4", features = ["derive"] }
```

Pattern — derive API with subcommands:
```rust
use clap::{Parser, Subcommand};

#[derive(Parser)]
#[command(name = "tool", version, about)]
struct Cli {
    #[arg(long, global = true)]
    json: bool,
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Index source files
    Index {
        #[arg(value_name = "PATH")]
        path: std::path::PathBuf,
    },
    /// Search the graph
    Search {
        query: String,
        #[arg(long, default_value_t = 20)]
        limit: usize,
    },
}
```

### Error Handling
```toml
anyhow = "1"      # main.rs and command handlers
thiserror = "2"    # library error types
```

Pattern:
```rust
// errors.rs
use thiserror::Error;

#[derive(Error, Debug)]
pub enum AppError {
    #[error("parse failed: {path}: {source}")]
    Parse { path: String, source: tree_sitter::LanguageError },
    #[error("graph: {0}")]
    Graph(String),
    #[error(transparent)]
    Io(#[from] std::io::Error),
}

// main.rs
fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();
    run(cli).context("command failed")
}
```

### Serialization
```toml
serde = { version = "1", features = ["derive"] }
serde_json = "1"
```

### Tree-sitter (AST parsing)
```toml
tree-sitter = "0.24"
tree-sitter-python = "0.23"
tree-sitter-javascript = "0.23"
tree-sitter-typescript = "0.23"
tree-sitter-rust = "0.23"
tree-sitter-go = "0.23"
```

Pattern — parser + query:
```rust
use tree_sitter::{Parser, Language, Query, QueryCursor};

fn parse_file(source: &[u8], language: Language) -> anyhow::Result<tree_sitter::Tree> {
    let mut parser = Parser::new();
    parser.set_language(&language)?;
    parser.parse(source, None)
        .ok_or_else(|| anyhow::anyhow!("parse failed"))
}

// Use S-expression queries for structured extraction:
fn find_functions(source: &[u8], tree: &tree_sitter::Tree, language: Language) -> Vec<String> {
    let query = Query::new(&language, "(function_definition name: (identifier) @name)").unwrap();
    let mut cursor = QueryCursor::new();
    cursor.matches(&query, tree.root_node(), source)
        .flat_map(|m| m.captures.iter())
        .map(|c| c.node.utf8_text(source).unwrap_or("").to_string())
        .collect()
}
```

**Prefer tree-sitter queries over manual AST walking** — they're declarative, faster, and less code.

### Graph Storage

**Option A — petgraph (in-memory) + serde_json (persistence):**
```toml
petgraph = { version = "0.6", features = ["serde-1"] }
```

Good for: graphs <100K nodes, simple persistence, fast traversal.

```rust
use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::Bfs;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
struct KnowledgeGraph {
    graph: DiGraph<Entity, Relation>,
}

// BFS neighbor traversal
fn neighbors(graph: &DiGraph<Entity, Relation>, start: NodeIndex, depth: usize) -> Vec<NodeIndex> {
    let mut bfs = Bfs::new(&graph, start);
    let mut result = Vec::new();
    let mut current_depth = 0;
    // ... traverse
    result
}
```

**Option B — rusqlite (SQLite, persistent):**
```toml
rusqlite = { version = "0.31", features = ["bundled"] }
```

Good for: large graphs, complex queries, persistence, FTS5 text search.

```rust
use rusqlite::Connection;

fn create_tables(conn: &Connection) -> rusqlite::Result<()> {
    conn.execute_batch("
        CREATE TABLE IF NOT EXISTS entities (
            id INTEGER PRIMARY KEY,
            name TEXT UNIQUE NOT NULL,
            entity_type TEXT NOT NULL,
            metadata TEXT DEFAULT '{}'
        );
        CREATE TABLE IF NOT EXISTS edges (
            id INTEGER PRIMARY KEY,
            source_id INTEGER NOT NULL REFERENCES entities(id),
            target_id INTEGER NOT NULL REFERENCES entities(id),
            relation_type TEXT NOT NULL,
            weight REAL DEFAULT 1.0,
            UNIQUE(source_id, target_id, relation_type)
        );
        CREATE VIRTUAL TABLE IF NOT EXISTS entities_fts USING fts5(name, entity_type, content=entities);
    ")
}
```

### Vector Search (local, no network)

**Option A — usearch (lightweight ANN):**
```toml
usearch = "2"
```

```rust
use usearch::{Index, MetricKind, ScalarKind};

let index = Index::new(&IndexOptions {
    dimensions: 384,
    metric: MetricKind::Cos,
    quantization: ScalarKind::F32,
    ..Default::default()
})?;
index.reserve(10000)?;
index.add(key, &embedding)?;
let results = index.search(&query_vec, 10)?;
```

**Option B — lancedb (full vector DB):**
```toml
lancedb = "0.23"
```

Good for: larger datasets, built-in persistence, metadata filtering.

### Embeddings (local)

**fastembed (zero-config, model auto-download):**
```toml
fastembed = "5"
```

```rust
use fastembed::{TextEmbedding, EmbeddingModel, InitOptions};

let model = TextEmbedding::try_new(InitOptions {
    model_name: EmbeddingModel::AllMiniLML6V2,
    show_download_progress: true,
    ..Default::default()
})?;

let embeddings = model.embed(vec!["fn parse_file()"], None)?;
```

### Output
```toml
colored = "2"
comfy-table = "7"
indicatif = "0.17"
```

### Testing
```toml
[dev-dependencies]
assert_cmd = "2"
predicates = "3"
tempfile = "3"
```

## Rust Idioms — Always Follow These

### Ownership
- Function params: `&str` not `String`, `&[T]` not `Vec<T>`, `&Path` not `PathBuf`
- Return owned types when the caller needs ownership
- Use `Cow<str>` when you might or might not allocate
- Clone only when you genuinely need a second owner. Never clone to satisfy the borrow checker without understanding why.

### Error Handling
- `?` operator for propagation. Never `match Ok/Err` when `?` works.
- `thiserror` for library errors with `#[from]` for auto-conversion
- `anyhow` + `.context()` in application/CLI code
- `.expect("reason")` only for invariants that truly cannot fail. Never bare `.unwrap()` in library code.

### Iterators
- Chain `.iter().filter().map().collect()` — no intermediate allocations
- Never collect then re-iterate. Chain the whole pipeline.
- Use `.for_each()` or `for x in iter` at the terminal step
- `Vec::with_capacity(n)` when the size is known

### Types
- Newtype pattern for domain IDs: `struct EntityId(u32);`
- Enums for fixed variant sets. Trait objects only when variants are open-ended.
- Builder pattern for structs with >3 optional fields
- `#[non_exhaustive]` on public enums

### Performance
- `&str` over `String` in function signatures
- `HashMap::entry()` API instead of get-then-insert
- Pre-allocate with `Vec::with_capacity`, `String::with_capacity`
- Avoid `format!()` in hot paths — use `write!()` to a buffer
- Profile before optimizing. Use `cargo flamegraph`.

### Modules
- `pub(crate)` for internal helpers
- Re-export key types from `lib.rs`
- One responsibility per module
- Keep `pub` surface minimal

### Testing
- `#[cfg(test)] mod tests { use super::*; }` in every module
- Integration tests in `tests/` with `assert_cmd`
- Use `tempfile::TempDir` for filesystem tests
- Test error cases, not just happy paths

## Async vs Sync Decision

**Use sync** for:
- File I/O on local disk
- Tree-sitter parsing (single-threaded C library)
- SQLite access (rusqlite is sync)
- CLI tools that do sequential work

**Use async (tokio)** only for:
- Network I/O (HTTP clients, gRPC)
- Concurrent server handlers
- When a dependency requires it

**For CPU-bound parallelism** use `rayon`:
```toml
rayon = "1.10"
```
```rust
use rayon::prelude::*;
files.par_iter().map(|f| parse_file(f)).collect::<Vec<_>>();
```

## Design Checklist

Before writing code, verify:

1. [ ] Project structure follows thin-main / fat-lib pattern
2. [ ] Error types defined with thiserror, used with anyhow in main
3. [ ] All function params borrow unless ownership transfer is needed
4. [ ] No unnecessary cloning
5. [ ] Enums used for known variant sets
6. [ ] pub(crate) used for internal APIs
7. [ ] Tests exist for each module
8. [ ] No unwrap() in library code (expect with reason is OK for true invariants)
9. [ ] Iterator chains preferred over manual loops
10. [ ] Sync unless async is required by a dependency
