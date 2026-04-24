# Document Indexing — Comprehensive Skill Reference

Use this skill when the user asks about: building a code search engine, indexing source files, tree-sitter parsing for indexing, incremental indexing, full-text search in Rust, hybrid search (FTS + vector), or any pipeline that transforms raw source files into searchable structured data.

---

## 1. What Is Document Indexing

Document indexing is the pipeline that transforms raw source files into searchable, queryable structured data. The pipeline stages are:

```
Raw Files --> Discovery --> Filtering --> Parsing --> Entity Extraction
    --> Chunking --> Embedding --> Storage --> Search
```

**Goal**: given a query (text or semantic), return the most relevant code entities (functions, types, modules) with their source locations, ranked by relevance.

**Core data model**:

```rust
use std::collections::HashMap;
use std::path::PathBuf;

/// A single indexable unit extracted from source code.
#[derive(Debug, Clone)]
pub struct CodeEntity {
    /// Unique key: "file_path::entity_name" or similar
    pub key: String,
    /// The kind of entity
    pub kind: EntityKind,
    /// Human-readable name (function name, class name, etc.)
    pub name: String,
    /// Full file path
    pub file_path: PathBuf,
    /// 1-based start line
    pub start_line: usize,
    /// 1-based end line
    pub end_line: usize,
    /// The raw source text of this entity
    pub source_text: String,
    /// Language
    pub language: Language,
    /// Optional: signature, docstring, decorators, etc.
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone, PartialEq)]
pub enum EntityKind {
    Function,
    Method,
    Class,
    Struct,
    Enum,
    Trait,
    Interface,
    Import,
    Module,
    TypeAlias,
    Constant,
}

#[derive(Debug, Clone, PartialEq)]
pub enum Language {
    Rust,
    Python,
    JavaScript,
    TypeScript,
    Go,
    Unknown,
}
```

---

## 2. The Indexing Pipeline — Full Architecture

### Pipeline struct

```rust
use std::path::Path;
use std::time::Instant;

pub struct IndexingPipeline {
    pub discovery: FileDiscovery,
    pub parser: TreeSitterParser,
    pub chunker: Chunker,
    pub embedder: Embedder,
    pub fts: FtsIndex,
    pub vector_store: VectorStore,
    pub graph: KnowledgeGraph,
    pub state: IndexState,
}

pub struct IndexStats {
    pub files_discovered: usize,
    pub files_skipped: usize,
    pub files_parsed: usize,
    pub files_failed: usize,
    pub entities_extracted: usize,
    pub chunks_created: usize,
    pub embeddings_generated: usize,
    pub elapsed: std::time::Duration,
}

impl IndexingPipeline {
    /// Run full or incremental indexing on a directory.
    pub fn index(&mut self, root: &Path, force: bool) -> Result<IndexStats, IndexError> {
        let start = Instant::now();
        let mut stats = IndexStats::default();

        // Stage 1: Discovery
        let files = self.discovery.walk(root)?;
        stats.files_discovered = files.len();

        // Stage 2: Filter to changed files (unless force rebuild)
        let files_to_index = if force {
            // Force: remove all existing data for this root, reindex everything
            self.state.clear_root(root)?;
            files
        } else {
            self.filter_changed(&files)?
        };

        // Stage 2b: Detect deleted files
        let deleted = self.state.find_deleted(&files)?;
        for path in &deleted {
            self.remove_file(path)?;
        }

        // Stage 3-6: Parse, extract, chunk, embed, store
        for file_path in &files_to_index {
            match self.index_single_file(file_path) {
                Ok(file_stats) => {
                    stats.entities_extracted += file_stats.entities;
                    stats.chunks_created += file_stats.chunks;
                    stats.files_parsed += 1;
                }
                Err(e) => {
                    eprintln!("Warning: failed to index {}: {}", file_path.display(), e);
                    stats.files_failed += 1;
                    // Continue — never let one bad file stop the pipeline
                }
            }
        }

        stats.files_skipped = stats.files_discovered - files_to_index.len();
        stats.elapsed = start.elapsed();
        Ok(stats)
    }

    fn index_single_file(&mut self, path: &Path) -> Result<FileIndexResult, IndexError> {
        // Remove old entities for this file (stale entity cleanup)
        self.remove_file(path)?;

        // Read source
        let source = std::fs::read_to_string(path)?;
        let lang = Language::detect(path);

        // Parse with tree-sitter
        let entities = self.parser.extract_entities(path, &source, &lang)?;

        // Chunk each entity
        let mut all_chunks = Vec::new();
        for entity in &entities {
            let chunks = self.chunker.chunk(entity);
            all_chunks.extend(chunks);
        }

        // Batch embed
        let texts: Vec<&str> = all_chunks.iter().map(|c| c.text.as_str()).collect();
        let embeddings = self.embedder.embed_batch(&texts)?;

        // Store in FTS
        for chunk in &all_chunks {
            self.fts.insert(chunk)?;
        }

        // Store in vector store
        for (chunk, embedding) in all_chunks.iter().zip(embeddings.iter()) {
            self.vector_store.insert(&chunk.key, embedding, &chunk.metadata)?;
        }

        // Store entities in knowledge graph
        for entity in &entities {
            self.graph.add_entity(entity)?;
        }

        // Update index state
        let hash = blake3::hash(source.as_bytes());
        self.state.mark_indexed(path, hash, entities.len())?;

        Ok(FileIndexResult {
            entities: entities.len(),
            chunks: all_chunks.len(),
        })
    }

    fn remove_file(&mut self, path: &Path) -> Result<(), IndexError> {
        self.fts.remove_by_file(path)?;
        self.vector_store.remove_by_file(path)?;
        self.graph.remove_by_file(path)?;
        self.state.remove(path)?;
        Ok(())
    }

    fn filter_changed(&self, files: &[PathBuf]) -> Result<Vec<PathBuf>, IndexError> {
        let mut changed = Vec::new();
        for file in files {
            let source = std::fs::read(file)?;
            let current_hash = blake3::hash(&source);
            match self.state.get_hash(file)? {
                Some(stored_hash) if stored_hash == current_hash => {
                    // Unchanged — skip
                }
                _ => {
                    changed.push(file.clone());
                }
            }
        }
        Ok(changed)
    }
}
```

---

## 3. File Discovery Patterns in Rust

### Using the `ignore` crate (recommended — same engine as ripgrep)

```toml
# Cargo.toml
[dependencies]
ignore = "0.4"
walkdir = "2"
rayon = "1.10"
```

```rust
use ignore::WalkBuilder;
use std::path::{Path, PathBuf};

pub struct FileDiscovery {
    /// File extensions to include (e.g., ["rs", "py", "ts", "js", "go"])
    pub extensions: Vec<String>,
    /// Max file size in bytes (skip files larger than this)
    pub max_file_size: u64,
    /// Additional ignore patterns beyond .gitignore
    pub ignore_patterns: Vec<String>,
}

impl FileDiscovery {
    pub fn new() -> Self {
        Self {
            extensions: vec![
                "rs", "py", "ts", "tsx", "js", "jsx", "go", "java",
                "c", "cpp", "h", "hpp", "rb", "php", "swift", "kt",
            ]
            .into_iter()
            .map(String::from)
            .collect(),
            max_file_size: 1_000_000, // 1 MB
            ignore_patterns: vec![
                "node_modules".into(),
                "target".into(),
                "vendor".into(),
                ".git".into(),
                "dist".into(),
                "build".into(),
                "__pycache__".into(),
                "*.min.js".into(),
                "*.bundle.js".into(),
                "*.generated.*".into(),
                "package-lock.json".into(),
                "yarn.lock".into(),
                "Cargo.lock".into(),
            ],
        }
    }

    /// Walk a directory, respecting .gitignore and custom ignore rules.
    /// Uses the `ignore` crate (same engine as ripgrep).
    pub fn walk(&self, root: &Path) -> Result<Vec<PathBuf>, std::io::Error> {
        let mut builder = WalkBuilder::new(root);
        builder
            .hidden(true)           // skip hidden files
            .git_ignore(true)       // respect .gitignore
            .git_global(true)       // respect global gitignore
            .git_exclude(true)      // respect .git/info/exclude
            .parents(true)          // check parent directories for .gitignore
            .max_filesize(Some(self.max_file_size));

        // Add custom ignore patterns via an override
        let mut overrides = ignore::overrides::OverrideBuilder::new(root);
        for pattern in &self.ignore_patterns {
            // Prefix with ! to ignore (negate) these patterns
            overrides.add(&format!("!{}", pattern)).ok();
        }
        if let Ok(built) = overrides.build() {
            builder.overrides(built);
        }

        let mut files = Vec::new();
        for entry in builder.build() {
            let entry = entry.map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
            let path = entry.path();

            if !path.is_file() {
                continue;
            }

            // Extension filter
            if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                if self.extensions.contains(&ext.to_lowercase()) {
                    // Binary detection: read first 8KB, check for null bytes
                    if !self.is_binary(path) {
                        files.push(path.to_path_buf());
                    }
                }
            }
        }

        Ok(files)
    }

    /// Parallel file walking with rayon (for very large repos).
    pub fn walk_parallel(&self, root: &Path) -> Vec<PathBuf> {
        use std::sync::Mutex;

        let files = Mutex::new(Vec::new());
        let mut builder = WalkBuilder::new(root);
        builder
            .hidden(true)
            .git_ignore(true)
            .max_filesize(Some(self.max_file_size))
            .threads(num_cpus::get());

        builder.build_parallel().run(|| {
            let files = &files;
            let extensions = &self.extensions;
            Box::new(move |entry| {
                if let Ok(entry) = entry {
                    let path = entry.path();
                    if path.is_file() {
                        if let Some(ext) = path.extension().and_then(|e| e.to_str()) {
                            if extensions.contains(&ext.to_lowercase()) {
                                files.lock().unwrap().push(path.to_path_buf());
                            }
                        }
                    }
                }
                ignore::WalkState::Continue
            })
        });

        files.into_inner().unwrap()
    }

    /// Detect binary files by checking for null bytes in the first 8KB.
    fn is_binary(&self, path: &Path) -> bool {
        use std::io::Read;
        let mut file = match std::fs::File::open(path) {
            Ok(f) => f,
            Err(_) => return true,
        };
        let mut buf = [0u8; 8192];
        let n = match file.read(&mut buf) {
            Ok(n) => n,
            Err(_) => return true,
        };
        buf[..n].contains(&0)
    }
}
```

### Using walkdir for simple traversal (no .gitignore support)

```rust
use walkdir::WalkDir;

fn walk_simple(root: &Path) -> Vec<PathBuf> {
    WalkDir::new(root)
        .into_iter()
        .filter_map(|e| e.ok())
        .filter(|e| e.file_type().is_file())
        .filter(|e| {
            e.path()
                .extension()
                .and_then(|ext| ext.to_str())
                .map(|ext| matches!(ext, "rs" | "py" | "ts" | "js" | "go"))
                .unwrap_or(false)
        })
        .map(|e| e.into_path())
        .collect()
}
```

### Glob pattern matching

```rust
use glob::glob;

fn find_rust_files(root: &str) -> Vec<PathBuf> {
    let pattern = format!("{}/**/*.rs", root);
    glob(&pattern)
        .expect("Invalid glob pattern")
        .filter_map(|entry| entry.ok())
        .collect()
}
```

---

## 4. Tree-Sitter Integration for Indexing

### Cargo.toml dependencies

```toml
[dependencies]
tree-sitter = "0.24"
tree-sitter-rust = "0.23"
tree-sitter-python = "0.23"
tree-sitter-javascript = "0.23"
tree-sitter-typescript = "0.23"
tree-sitter-go = "0.23"
```

### Language detection and parser creation

```rust
use std::path::Path;
use tree_sitter::{Language, Parser, Query, QueryCursor, Node, Tree};

impl crate::Language {
    pub fn detect(path: &Path) -> Self {
        match path.extension().and_then(|e| e.to_str()) {
            Some("rs") => Self::Rust,
            Some("py") => Self::Python,
            Some("js" | "jsx") => Self::JavaScript,
            Some("ts" | "tsx") => Self::TypeScript,
            Some("go") => Self::Go,
            _ => Self::Unknown,
        }
    }

    pub fn tree_sitter_language(&self) -> Option<Language> {
        match self {
            Self::Rust => Some(tree_sitter_rust::LANGUAGE.into()),
            Self::Python => Some(tree_sitter_python::LANGUAGE.into()),
            Self::JavaScript => Some(tree_sitter_javascript::LANGUAGE.into()),
            Self::TypeScript => Some(tree_sitter_typescript::language_typescript().into()),
            Self::Go => Some(tree_sitter_go::LANGUAGE.into()),
            Self::Unknown => None,
        }
    }
}
```

### Tree-sitter parser and entity extraction

```rust
pub struct TreeSitterParser {
    parsers: HashMap<crate::Language, Parser>,
}

impl TreeSitterParser {
    pub fn new() -> Self {
        let mut parsers = HashMap::new();

        for lang in &[
            crate::Language::Rust,
            crate::Language::Python,
            crate::Language::JavaScript,
            crate::Language::TypeScript,
            crate::Language::Go,
        ] {
            if let Some(ts_lang) = lang.tree_sitter_language() {
                let mut parser = Parser::new();
                parser.set_language(&ts_lang).expect("Language version mismatch");
                parsers.insert(lang.clone(), parser);
            }
        }

        Self { parsers }
    }

    pub fn extract_entities(
        &mut self,
        file_path: &Path,
        source: &str,
        lang: &crate::Language,
    ) -> Result<Vec<CodeEntity>, IndexError> {
        let parser = self.parsers.get_mut(lang)
            .ok_or(IndexError::UnsupportedLanguage)?;

        let tree = parser.parse(source, None)
            .ok_or(IndexError::ParseFailed)?;

        let query_source = Self::query_for_language(lang);
        let ts_lang = lang.tree_sitter_language().unwrap();
        let query = Query::new(&ts_lang, &query_source)
            .map_err(|e| IndexError::QueryError(e.to_string()))?;

        let mut cursor = QueryCursor::new();
        let matches = cursor.matches(&query, tree.root_node(), source.as_bytes());

        let mut entities = Vec::new();
        for m in matches {
            if let Some(entity) = Self::match_to_entity(file_path, source, lang, &query, &m) {
                entities.push(entity);
            }
        }

        Ok(entities)
    }

    /// S-expression queries per language. Each query captures:
    ///   @entity — the full node (for source text + line range)
    ///   @name   — the name node (for the entity name)
    fn query_for_language(lang: &crate::Language) -> String {
        match lang {
            crate::Language::Rust => r#"
                (function_item name: (identifier) @name) @entity
                (struct_item name: (type_identifier) @name) @entity
                (enum_item name: (type_identifier) @name) @entity
                (impl_item type: (type_identifier) @name) @entity
                (trait_item name: (type_identifier) @name) @entity
                (use_declaration argument: (_) @name) @entity
                (mod_item name: (identifier) @name) @entity
                (type_item name: (type_identifier) @name) @entity
                (const_item name: (identifier) @name) @entity
                (static_item name: (identifier) @name) @entity
            "#.into(),

            crate::Language::Python => r#"
                (function_definition name: (identifier) @name) @entity
                (class_definition name: (identifier) @name) @entity
                (import_statement) @entity @name
                (import_from_statement module_name: (dotted_name) @name) @entity
                (decorated_definition definition: (function_definition name: (identifier) @name)) @entity
                (decorated_definition definition: (class_definition name: (identifier) @name)) @entity
            "#.into(),

            crate::Language::JavaScript | crate::Language::TypeScript => r#"
                (function_declaration name: (identifier) @name) @entity
                (class_declaration name: (identifier) @name) @entity
                (import_statement source: (string) @name) @entity
                (arrow_function) @entity
                (lexical_declaration
                    (variable_declarator name: (identifier) @name)) @entity
                (export_statement
                    declaration: (function_declaration name: (identifier) @name)) @entity
                (export_statement
                    declaration: (class_declaration name: (identifier) @name)) @entity
                (interface_declaration name: (type_identifier) @name) @entity
                (type_alias_declaration name: (type_identifier) @name) @entity
            "#.into(),

            crate::Language::Go => r#"
                (function_declaration name: (identifier) @name) @entity
                (method_declaration name: (field_identifier) @name) @entity
                (type_declaration (type_spec name: (type_identifier) @name)) @entity
                (import_declaration) @entity @name
            "#.into(),

            _ => String::new(),
        }
    }

    fn match_to_entity(
        file_path: &Path,
        source: &str,
        lang: &crate::Language,
        query: &Query,
        m: &tree_sitter::QueryMatch,
    ) -> Option<CodeEntity> {
        let mut entity_node = None;
        let mut name_text = None;

        for capture in m.captures {
            let capture_name = &query.capture_names()[capture.index as usize];
            match capture_name.as_str() {
                "entity" => entity_node = Some(capture.node),
                "name" => {
                    name_text = Some(
                        source[capture.node.byte_range()].to_string()
                    );
                }
                _ => {}
            }
        }

        let node = entity_node?;
        let name = name_text.unwrap_or_else(|| "<anonymous>".into());
        let source_text = source[node.byte_range()].to_string();
        let start_line = node.start_position().row + 1;
        let end_line = node.end_position().row + 1;
        let kind = Self::classify_node(node, lang);

        let key = format!("{}::{}::{}", file_path.display(), name, start_line);

        let mut metadata = HashMap::new();

        // Extract additional metadata based on language
        Self::extract_metadata(&node, source, lang, &mut metadata);

        Some(CodeEntity {
            key,
            kind,
            name,
            file_path: file_path.to_path_buf(),
            start_line,
            end_line,
            source_text,
            language: lang.clone(),
            metadata,
        })
    }

    fn classify_node(node: Node, lang: &crate::Language) -> EntityKind {
        let kind_str = node.kind();
        match (lang, kind_str) {
            // Rust
            (crate::Language::Rust, "function_item") => EntityKind::Function,
            (crate::Language::Rust, "struct_item") => EntityKind::Struct,
            (crate::Language::Rust, "enum_item") => EntityKind::Enum,
            (crate::Language::Rust, "impl_item") => EntityKind::Class,
            (crate::Language::Rust, "trait_item") => EntityKind::Trait,
            (crate::Language::Rust, "use_declaration") => EntityKind::Import,
            (crate::Language::Rust, "mod_item") => EntityKind::Module,
            (crate::Language::Rust, "type_item") => EntityKind::TypeAlias,
            (crate::Language::Rust, "const_item" | "static_item") => EntityKind::Constant,

            // Python
            (crate::Language::Python, "function_definition") => EntityKind::Function,
            (crate::Language::Python, "class_definition") => EntityKind::Class,
            (crate::Language::Python, "import_statement" | "import_from_statement") => EntityKind::Import,
            (crate::Language::Python, "decorated_definition") => EntityKind::Function, // refined later

            // JS/TS
            (crate::Language::JavaScript | crate::Language::TypeScript, "function_declaration") => EntityKind::Function,
            (crate::Language::JavaScript | crate::Language::TypeScript, "class_declaration") => EntityKind::Class,
            (crate::Language::JavaScript | crate::Language::TypeScript, "import_statement") => EntityKind::Import,
            (crate::Language::JavaScript | crate::Language::TypeScript, "arrow_function") => EntityKind::Function,
            (crate::Language::JavaScript | crate::Language::TypeScript, "interface_declaration") => EntityKind::Interface,
            (crate::Language::JavaScript | crate::Language::TypeScript, "type_alias_declaration") => EntityKind::TypeAlias,

            // Go
            (crate::Language::Go, "function_declaration") => EntityKind::Function,
            (crate::Language::Go, "method_declaration") => EntityKind::Method,
            (crate::Language::Go, "type_declaration") => EntityKind::Struct,
            (crate::Language::Go, "import_declaration") => EntityKind::Import,

            _ => EntityKind::Function, // fallback
        }
    }

    /// Extract extra metadata: docstrings, parameters, return types, decorators.
    fn extract_metadata(
        node: &Node,
        source: &str,
        lang: &crate::Language,
        metadata: &mut HashMap<String, String>,
    ) {
        match lang {
            crate::Language::Python => {
                // Docstring: first child expression_statement containing a string
                if let Some(body) = node.child_by_field_name("body") {
                    if let Some(first_stmt) = body.named_child(0) {
                        if first_stmt.kind() == "expression_statement" {
                            if let Some(string_node) = first_stmt.named_child(0) {
                                if string_node.kind() == "string" {
                                    let doc = source[string_node.byte_range()].to_string();
                                    metadata.insert("docstring".into(), doc);
                                }
                            }
                        }
                    }
                }
                // Parameters
                if let Some(params) = node.child_by_field_name("parameters") {
                    let params_text = source[params.byte_range()].to_string();
                    metadata.insert("parameters".into(), params_text);
                }
                // Return type annotation
                if let Some(ret) = node.child_by_field_name("return_type") {
                    metadata.insert("return_type".into(), source[ret.byte_range()].to_string());
                }
            }
            crate::Language::Rust => {
                // Parameters
                if let Some(params) = node.child_by_field_name("parameters") {
                    metadata.insert("parameters".into(), source[params.byte_range()].to_string());
                }
                // Return type
                if let Some(ret) = node.child_by_field_name("return_type") {
                    metadata.insert("return_type".into(), source[ret.byte_range()].to_string());
                }
                // Visibility (pub, pub(crate), etc.)
                for i in 0..node.child_count() {
                    if let Some(child) = node.child(i) {
                        if child.kind() == "visibility_modifier" {
                            metadata.insert("visibility".into(), source[child.byte_range()].to_string());
                        }
                    }
                }
            }
            crate::Language::TypeScript | crate::Language::JavaScript => {
                if let Some(params) = node.child_by_field_name("parameters") {
                    metadata.insert("parameters".into(), source[params.byte_range()].to_string());
                }
                if let Some(ret) = node.child_by_field_name("return_type") {
                    metadata.insert("return_type".into(), source[ret.byte_range()].to_string());
                }
            }
            crate::Language::Go => {
                if let Some(params) = node.child_by_field_name("parameters") {
                    metadata.insert("parameters".into(), source[params.byte_range()].to_string());
                }
                if let Some(result) = node.child_by_field_name("result") {
                    metadata.insert("return_type".into(), source[result.byte_range()].to_string());
                }
            }
            _ => {}
        }
    }
}
```

---

## 5. Incremental Indexing

### Index state tracking

```rust
use std::collections::HashMap;
use std::path::{Path, PathBuf};
use serde::{Serialize, Deserialize};

/// Tracks the state of every indexed file for incremental updates.
#[derive(Debug, Serialize, Deserialize)]
pub struct IndexState {
    /// Map from canonical file path to its index metadata
    pub files: HashMap<PathBuf, FileIndexMeta>,
    /// Path to the state file on disk
    #[serde(skip)]
    pub state_path: PathBuf,
}

#[derive(Debug, Serialize, Deserialize, Clone)]
pub struct FileIndexMeta {
    /// blake3 hash of file content at last index time
    pub content_hash: String,
    /// Last modified time (Unix seconds) — used as a fast pre-check
    pub mtime: u64,
    /// Number of entities extracted last time
    pub entity_count: usize,
    /// When this file was last indexed (Unix seconds)
    pub indexed_at: u64,
}

impl IndexState {
    /// Load from disk, or create empty.
    pub fn load(state_path: &Path) -> Self {
        if state_path.exists() {
            let data = std::fs::read_to_string(state_path).unwrap_or_default();
            serde_json::from_str(&data).unwrap_or_else(|_| Self {
                files: HashMap::new(),
                state_path: state_path.to_path_buf(),
            })
        } else {
            Self {
                files: HashMap::new(),
                state_path: state_path.to_path_buf(),
            }
        }
    }

    /// Persist to disk.
    pub fn save(&self) -> Result<(), std::io::Error> {
        let data = serde_json::to_string_pretty(&self)?;
        std::fs::write(&self.state_path, data)
    }

    /// Check if a file needs reindexing.
    /// Fast path: compare mtime first (cheap). If mtime changed, compare hash (accurate).
    pub fn needs_reindex(&self, path: &Path, source: &[u8]) -> bool {
        match self.files.get(path) {
            None => true, // New file
            Some(meta) => {
                // Fast path: check mtime
                if let Ok(fs_meta) = std::fs::metadata(path) {
                    if let Ok(modified) = fs_meta.modified() {
                        let mtime = modified
                            .duration_since(std::time::UNIX_EPOCH)
                            .unwrap_or_default()
                            .as_secs();
                        if mtime == meta.mtime {
                            return false; // mtime unchanged — skip
                        }
                    }
                }
                // Slow path: content hash
                let current_hash = blake3::hash(source).to_hex().to_string();
                current_hash != meta.content_hash
            }
        }
    }

    /// Record that a file has been indexed.
    pub fn mark_indexed(
        &mut self,
        path: &Path,
        hash: blake3::Hash,
        entity_count: usize,
    ) -> Result<(), IndexError> {
        let mtime = std::fs::metadata(path)
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_secs())
            .unwrap_or(0);

        self.files.insert(path.to_path_buf(), FileIndexMeta {
            content_hash: hash.to_hex().to_string(),
            mtime,
            entity_count,
            indexed_at: std::time::SystemTime::now()
                .duration_since(std::time::UNIX_EPOCH)
                .unwrap_or_default()
                .as_secs(),
        });

        self.save().map_err(|e| IndexError::IoError(e))
    }

    /// Find files that were previously indexed but no longer exist on disk.
    pub fn find_deleted(&self, current_files: &[PathBuf]) -> Result<Vec<PathBuf>, IndexError> {
        let current_set: std::collections::HashSet<&PathBuf> = current_files.iter().collect();
        Ok(self.files.keys()
            .filter(|p| !current_set.contains(p))
            .cloned()
            .collect())
    }

    /// Remove a file from the state.
    pub fn remove(&mut self, path: &Path) -> Result<(), IndexError> {
        self.files.remove(path);
        self.save().map_err(|e| IndexError::IoError(e))
    }

    /// Clear all state for a given root directory (for force rebuild).
    pub fn clear_root(&mut self, root: &Path) -> Result<(), IndexError> {
        self.files.retain(|path, _| !path.starts_with(root));
        self.save().map_err(|e| IndexError::IoError(e))
    }

    /// Get hash for a file if it exists.
    pub fn get_hash(&self, path: &Path) -> Result<Option<blake3::Hash>, IndexError> {
        match self.files.get(path) {
            Some(meta) => {
                // Parse the stored hex hash back
                let bytes = hex::decode(&meta.content_hash)
                    .map_err(|e| IndexError::Other(e.to_string()))?;
                let hash = blake3::Hash::from_bytes(
                    bytes.try_into()
                        .map_err(|_| IndexError::Other("Invalid hash length".into()))?
                );
                Ok(Some(hash))
            }
            None => Ok(None),
        }
    }
}
```

### Alternative: SQLite-backed index state

```rust
use rusqlite::Connection;

pub struct SqliteIndexState {
    conn: Connection,
}

impl SqliteIndexState {
    pub fn new(db_path: &Path) -> Result<Self, rusqlite::Error> {
        let conn = Connection::open(db_path)?;
        conn.execute_batch("
            CREATE TABLE IF NOT EXISTS index_state (
                file_path TEXT PRIMARY KEY,
                content_hash TEXT NOT NULL,
                mtime INTEGER NOT NULL,
                entity_count INTEGER NOT NULL,
                indexed_at INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_state_mtime ON index_state(mtime);
        ")?;
        Ok(Self { conn })
    }

    pub fn needs_reindex(&self, path: &Path, content_hash: &str) -> Result<bool, rusqlite::Error> {
        let result: Option<String> = self.conn.query_row(
            "SELECT content_hash FROM index_state WHERE file_path = ?1",
            [path.to_string_lossy().as_ref()],
            |row| row.get(0),
        ).optional()?;

        Ok(match result {
            None => true,
            Some(stored) => stored != content_hash,
        })
    }

    pub fn mark_indexed(
        &self,
        path: &Path,
        content_hash: &str,
        entity_count: usize,
    ) -> Result<(), rusqlite::Error> {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_secs();
        let mtime = std::fs::metadata(path)
            .and_then(|m| m.modified())
            .ok()
            .and_then(|t| t.duration_since(std::time::UNIX_EPOCH).ok())
            .map(|d| d.as_secs())
            .unwrap_or(0);

        self.conn.execute(
            "INSERT OR REPLACE INTO index_state (file_path, content_hash, mtime, entity_count, indexed_at)
             VALUES (?1, ?2, ?3, ?4, ?5)",
            rusqlite::params![
                path.to_string_lossy().as_ref(),
                content_hash,
                mtime as i64,
                entity_count as i64,
                now as i64,
            ],
        )?;
        Ok(())
    }

    pub fn remove(&self, path: &Path) -> Result<(), rusqlite::Error> {
        self.conn.execute(
            "DELETE FROM index_state WHERE file_path = ?1",
            [path.to_string_lossy().as_ref()],
        )?;
        Ok(())
    }

    pub fn get_stats(&self) -> Result<IndexStatusReport, rusqlite::Error> {
        let total: i64 = self.conn.query_row(
            "SELECT COUNT(*) FROM index_state", [], |r| r.get(0)
        )?;
        let total_entities: i64 = self.conn.query_row(
            "SELECT COALESCE(SUM(entity_count), 0) FROM index_state", [], |r| r.get(0)
        )?;
        let oldest: Option<i64> = self.conn.query_row(
            "SELECT MIN(indexed_at) FROM index_state", [], |r| r.get(0)
        ).optional()?.flatten();
        let newest: Option<i64> = self.conn.query_row(
            "SELECT MAX(indexed_at) FROM index_state", [], |r| r.get(0)
        ).optional()?.flatten();

        Ok(IndexStatusReport {
            total_files: total as usize,
            total_entities: total_entities as usize,
            oldest_index: oldest.map(|t| t as u64),
            newest_index: newest.map(|t| t as u64),
        })
    }
}

pub struct IndexStatusReport {
    pub total_files: usize,
    pub total_entities: usize,
    pub oldest_index: Option<u64>,
    pub newest_index: Option<u64>,
}
```

---

## 6. Chunking

```rust
/// A chunk is the atomic unit stored in FTS and vector indices.
#[derive(Debug, Clone)]
pub struct Chunk {
    /// Unique key (inherited from entity key + chunk index)
    pub key: String,
    /// The text content
    pub text: String,
    /// Metadata for filtering and enrichment
    pub metadata: ChunkMetadata,
}

#[derive(Debug, Clone)]
pub struct ChunkMetadata {
    pub file_path: String,
    pub entity_name: String,
    pub entity_kind: String,
    pub language: String,
    pub start_line: usize,
    pub end_line: usize,
}

pub struct Chunker {
    /// Max tokens per chunk (approximate — uses char count / 4)
    pub max_chunk_tokens: usize,
    /// Overlap between chunks in tokens
    pub overlap_tokens: usize,
}

impl Chunker {
    pub fn new(max_chunk_tokens: usize, overlap_tokens: usize) -> Self {
        Self { max_chunk_tokens, overlap_tokens }
    }

    /// Chunk a code entity. Small entities become a single chunk.
    /// Large entities are split on line boundaries with overlap.
    pub fn chunk(&self, entity: &CodeEntity) -> Vec<Chunk> {
        let approx_tokens = entity.source_text.len() / 4;

        if approx_tokens <= self.max_chunk_tokens {
            // Fits in one chunk
            return vec![Chunk {
                key: format!("{}#0", entity.key),
                text: self.build_chunk_text(entity, &entity.source_text),
                metadata: ChunkMetadata {
                    file_path: entity.file_path.to_string_lossy().into(),
                    entity_name: entity.name.clone(),
                    entity_kind: format!("{:?}", entity.kind),
                    language: format!("{:?}", entity.language),
                    start_line: entity.start_line,
                    end_line: entity.end_line,
                },
            }];
        }

        // Split into overlapping chunks on line boundaries
        let lines: Vec<&str> = entity.source_text.lines().collect();
        let max_chars = self.max_chunk_tokens * 4;
        let overlap_chars = self.overlap_tokens * 4;
        let mut chunks = Vec::new();
        let mut start_idx = 0;
        let mut chunk_index = 0;

        while start_idx < lines.len() {
            let mut end_idx = start_idx;
            let mut char_count = 0;

            // Accumulate lines until we hit the max
            while end_idx < lines.len() && char_count + lines[end_idx].len() < max_chars {
                char_count += lines[end_idx].len() + 1; // +1 for newline
                end_idx += 1;
            }

            if end_idx == start_idx {
                end_idx = start_idx + 1; // Always include at least one line
            }

            let chunk_text: String = lines[start_idx..end_idx].join("\n");
            chunks.push(Chunk {
                key: format!("{}#{}", entity.key, chunk_index),
                text: self.build_chunk_text(entity, &chunk_text),
                metadata: ChunkMetadata {
                    file_path: entity.file_path.to_string_lossy().into(),
                    entity_name: entity.name.clone(),
                    entity_kind: format!("{:?}", entity.kind),
                    language: format!("{:?}", entity.language),
                    start_line: entity.start_line + start_idx,
                    end_line: entity.start_line + end_idx - 1,
                },
            });

            // Advance, leaving overlap
            let overlap_lines = self.count_lines_for_chars(&lines[start_idx..end_idx], overlap_chars);
            start_idx = end_idx.saturating_sub(overlap_lines);
            if start_idx <= chunk_index { // prevent infinite loop
                start_idx = end_idx;
            }
            chunk_index += 1;
        }

        chunks
    }

    /// Prefix chunk text with contextual header for better embedding quality.
    fn build_chunk_text(&self, entity: &CodeEntity, body: &str) -> String {
        format!(
            "{:?} {:?} `{}` in {} (lines {}-{}):\n{}",
            entity.language,
            entity.kind,
            entity.name,
            entity.file_path.display(),
            entity.start_line,
            entity.end_line,
            body,
        )
    }

    fn count_lines_for_chars(&self, lines: &[&str], target_chars: usize) -> usize {
        let mut count = 0;
        let mut chars = 0;
        for line in lines.iter().rev() {
            chars += line.len() + 1;
            count += 1;
            if chars >= target_chars {
                break;
            }
        }
        count
    }
}
```

---

## 7. Full-Text Search (FTS)

### SQLite FTS5

```toml
[dependencies]
rusqlite = { version = "0.32", features = ["bundled", "fts5"] }
```

```rust
use rusqlite::{Connection, params};
use std::path::Path;

pub struct FtsIndex {
    conn: Connection,
}

impl FtsIndex {
    pub fn new(db_path: &Path) -> Result<Self, rusqlite::Error> {
        let conn = Connection::open(db_path)?;

        conn.execute_batch("
            -- Main FTS5 virtual table with porter stemmer tokenizer
            CREATE VIRTUAL TABLE IF NOT EXISTS fts_chunks USING fts5(
                key,
                content,
                entity_name,
                entity_kind,
                file_path,
                language,
                start_line UNINDEXED,
                end_line UNINDEXED,
                tokenize = 'porter unicode61'
            );

            -- Metadata table for non-FTS queries
            CREATE TABLE IF NOT EXISTS chunk_meta (
                key TEXT PRIMARY KEY,
                file_path TEXT NOT NULL,
                entity_name TEXT NOT NULL,
                entity_kind TEXT NOT NULL,
                language TEXT NOT NULL,
                start_line INTEGER NOT NULL,
                end_line INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_chunk_file ON chunk_meta(file_path);
        ")?;

        Ok(Self { conn })
    }

    /// Insert a chunk into FTS and metadata tables.
    pub fn insert(&self, chunk: &Chunk) -> Result<(), rusqlite::Error> {
        self.conn.execute(
            "INSERT OR REPLACE INTO fts_chunks(key, content, entity_name, entity_kind, file_path, language, start_line, end_line)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7, ?8)",
            params![
                chunk.key,
                chunk.text,
                chunk.metadata.entity_name,
                chunk.metadata.entity_kind,
                chunk.metadata.file_path,
                chunk.metadata.language,
                chunk.metadata.start_line as i64,
                chunk.metadata.end_line as i64,
            ],
        )?;

        self.conn.execute(
            "INSERT OR REPLACE INTO chunk_meta(key, file_path, entity_name, entity_kind, language, start_line, end_line)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6, ?7)",
            params![
                chunk.key,
                chunk.metadata.file_path,
                chunk.metadata.entity_name,
                chunk.metadata.entity_kind,
                chunk.metadata.language,
                chunk.metadata.start_line as i64,
                chunk.metadata.end_line as i64,
            ],
        )?;
        Ok(())
    }

    /// Remove all chunks belonging to a file.
    pub fn remove_by_file(&self, path: &Path) -> Result<(), rusqlite::Error> {
        let path_str = path.to_string_lossy();

        // Get keys to remove from FTS
        let keys: Vec<String> = {
            let mut stmt = self.conn.prepare(
                "SELECT key FROM chunk_meta WHERE file_path = ?1"
            )?;
            stmt.query_map([path_str.as_ref()], |row| row.get(0))?
                .filter_map(|r| r.ok())
                .collect()
        };

        for key in &keys {
            self.conn.execute(
                "DELETE FROM fts_chunks WHERE key = ?1",
                [key],
            )?;
        }

        self.conn.execute(
            "DELETE FROM chunk_meta WHERE file_path = ?1",
            [path_str.as_ref()],
        )?;

        Ok(())
    }

    /// Search with BM25 ranking. Returns results sorted by relevance.
    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<FtsResult>, rusqlite::Error> {
        // FTS5 MATCH query with BM25 ranking
        // bm25() returns negative values where more negative = better match
        // We negate and normalize to 0-1 range
        let mut stmt = self.conn.prepare(
            "SELECT
                key,
                entity_name,
                entity_kind,
                file_path,
                language,
                start_line,
                end_line,
                snippet(fts_chunks, 1, '>>>', '<<<', '...', 64) as snippet,
                -bm25(fts_chunks) as score
             FROM fts_chunks
             WHERE fts_chunks MATCH ?1
             ORDER BY score DESC
             LIMIT ?2"
        )?;

        let results = stmt.query_map(params![query, limit as i64], |row| {
            Ok(FtsResult {
                key: row.get(0)?,
                entity_name: row.get(1)?,
                entity_kind: row.get(2)?,
                file_path: row.get(3)?,
                language: row.get(4)?,
                start_line: row.get::<_, i64>(5)? as usize,
                end_line: row.get::<_, i64>(6)? as usize,
                snippet: row.get(7)?,
                score: row.get(8)?,
            })
        })?.filter_map(|r| r.ok()).collect::<Vec<_>>();

        // Normalize scores to 0-1 range
        let max_score = results.iter().map(|r| r.score).fold(0.0_f64, f64::max);
        Ok(results.into_iter().map(|mut r| {
            r.score = if max_score > 0.0 { r.score / max_score } else { 0.0 };
            r
        }).collect())
    }

    /// Advanced FTS5 query syntax examples:
    /// - Boolean: "foo AND bar", "foo OR bar", "foo NOT bar"
    /// - Phrase: "\"exact phrase\""
    /// - Prefix: "pref*"
    /// - Column filter: "entity_name:Parser"
    /// - NEAR: "NEAR(foo bar, 5)"
    pub fn search_advanced(&self, fts5_query: &str, limit: usize) -> Result<Vec<FtsResult>, rusqlite::Error> {
        self.search(fts5_query, limit)
    }
}

#[derive(Debug, Clone)]
pub struct FtsResult {
    pub key: String,
    pub entity_name: String,
    pub entity_kind: String,
    pub file_path: String,
    pub language: String,
    pub start_line: usize,
    pub end_line: usize,
    pub snippet: String,
    pub score: f64, // 0.0 to 1.0 (normalized BM25)
}
```

### Tantivy alternative (Rust-native full-text search)

```toml
[dependencies]
tantivy = "0.22"
```

```rust
use tantivy::schema::*;
use tantivy::{Index, IndexWriter, ReloadPolicy};
use tantivy::collector::TopDocs;
use tantivy::query::QueryParser;
use std::path::Path;

pub struct TantivyFts {
    index: Index,
    schema: Schema,
    // Field handles
    key_field: Field,
    content_field: Field,
    entity_name_field: Field,
    entity_kind_field: Field,
    file_path_field: Field,
    language_field: Field,
    start_line_field: Field,
    end_line_field: Field,
}

impl TantivyFts {
    pub fn new(index_dir: &Path) -> Result<Self, tantivy::TantivyError> {
        let mut schema_builder = Schema::builder();

        let key_field = schema_builder.add_text_field("key", STRING | STORED);
        let content_field = schema_builder.add_text_field("content", TEXT | STORED);
        let entity_name_field = schema_builder.add_text_field("entity_name", TEXT | STORED);
        let entity_kind_field = schema_builder.add_text_field("entity_kind", STRING | STORED);
        let file_path_field = schema_builder.add_text_field("file_path", STRING | STORED);
        let language_field = schema_builder.add_text_field("language", STRING | STORED);
        let start_line_field = schema_builder.add_u64_field("start_line", STORED);
        let end_line_field = schema_builder.add_u64_field("end_line", STORED);

        let schema = schema_builder.build();

        std::fs::create_dir_all(index_dir)?;
        let index = Index::create_in_dir(index_dir, schema.clone())?;

        Ok(Self {
            index,
            schema,
            key_field,
            content_field,
            entity_name_field,
            entity_kind_field,
            file_path_field,
            language_field,
            start_line_field,
            end_line_field,
        })
    }

    pub fn insert_batch(&self, chunks: &[Chunk]) -> Result<(), tantivy::TantivyError> {
        let mut writer: IndexWriter = self.index.writer(50_000_000)?; // 50MB heap

        for chunk in chunks {
            let mut doc = TantivyDocument::new();
            doc.add_text(self.key_field, &chunk.key);
            doc.add_text(self.content_field, &chunk.text);
            doc.add_text(self.entity_name_field, &chunk.metadata.entity_name);
            doc.add_text(self.entity_kind_field, &chunk.metadata.entity_kind);
            doc.add_text(self.file_path_field, &chunk.metadata.file_path);
            doc.add_text(self.language_field, &chunk.metadata.language);
            doc.add_u64(self.start_line_field, chunk.metadata.start_line as u64);
            doc.add_u64(self.end_line_field, chunk.metadata.end_line as u64);
            writer.add_document(doc)?;
        }

        writer.commit()?;
        Ok(())
    }

    pub fn search(&self, query_str: &str, limit: usize) -> Result<Vec<FtsResult>, tantivy::TantivyError> {
        let reader = self.index
            .reader_builder()
            .reload_policy(ReloadPolicy::OnCommitWithDelay)
            .try_into()?;

        let searcher = reader.searcher();
        let query_parser = QueryParser::for_index(
            &self.index,
            vec![self.content_field, self.entity_name_field],
        );
        let query = query_parser.parse_query(query_str)?;
        let top_docs = searcher.search(&query, &TopDocs::with_limit(limit))?;

        let max_score = top_docs.first().map(|(s, _)| *s).unwrap_or(1.0);
        let mut results = Vec::new();

        for (score, doc_addr) in top_docs {
            let doc: TantivyDocument = searcher.doc(doc_addr)?;
            let normalized_score = if max_score > 0.0 { score / max_score } else { 0.0 };

            results.push(FtsResult {
                key: Self::get_text(&doc, self.key_field),
                entity_name: Self::get_text(&doc, self.entity_name_field),
                entity_kind: Self::get_text(&doc, self.entity_kind_field),
                file_path: Self::get_text(&doc, self.file_path_field),
                language: Self::get_text(&doc, self.language_field),
                start_line: Self::get_u64(&doc, self.start_line_field) as usize,
                end_line: Self::get_u64(&doc, self.end_line_field) as usize,
                snippet: Self::get_text(&doc, self.content_field)
                    .chars().take(200).collect(),
                score: normalized_score as f64,
            });
        }

        Ok(results)
    }

    fn get_text(doc: &TantivyDocument, field: Field) -> String {
        doc.get_first(field)
            .and_then(|v| v.as_str())
            .unwrap_or("")
            .to_string()
    }

    fn get_u64(doc: &TantivyDocument, field: Field) -> u64 {
        doc.get_first(field)
            .and_then(|v| v.as_u64())
            .unwrap_or(0)
    }

    pub fn remove_by_key(&self, key: &str) -> Result<(), tantivy::TantivyError> {
        let mut writer: IndexWriter = self.index.writer(50_000_000)?;
        let term = tantivy::Term::from_field_text(self.key_field, key);
        writer.delete_term(term);
        writer.commit()?;
        Ok(())
    }
}
```

### FTS5 vs Tantivy comparison

| Feature | SQLite FTS5 | Tantivy |
|---------|------------|---------|
| Setup complexity | Minimal (bundled with rusqlite) | Moderate (separate index directory) |
| Query syntax | FTS5 syntax (MATCH, NEAR, column:) | Lucene-like (AND, OR, field:, phrase) |
| Ranking | BM25 (built-in) | BM25 + TF-IDF + custom scorers |
| Highlighting | snippet() function | Built-in snippet generator |
| Performance (small) | Excellent | Excellent |
| Performance (large, >100K docs) | Good | Superior |
| Concurrent reads | Good (WAL mode) | Excellent (lock-free readers) |
| Incremental updates | Straightforward (INSERT/DELETE) | Segment-based merge |
| Binary size | Small (linked with SQLite) | Larger (~3MB) |
| Recommendation | Best for embedded tools, small-medium codebases | Best for large codebases, high-throughput search |

---

## 8. Embedding

```toml
[dependencies]
fastembed = "4"
```

```rust
use fastembed::{TextEmbedding, EmbeddingModel, InitOptions};

pub struct Embedder {
    model: TextEmbedding,
    dimension: usize,
}

impl Embedder {
    /// Initialize the embedder. Downloads model on first use.
    pub fn new() -> Result<Self, Box<dyn std::error::Error>> {
        let model = TextEmbedding::try_new(InitOptions {
            model_name: EmbeddingModel::AllMiniLML6V2, // 384 dimensions, fast
            show_download_progress: true,
            ..Default::default()
        })?;

        Ok(Self {
            model,
            dimension: 384,
        })
    }

    /// Embed a single text.
    pub fn embed(&self, text: &str) -> Result<Vec<f32>, Box<dyn std::error::Error>> {
        let results = self.model.embed(vec![text], None)?;
        Ok(results.into_iter().next().unwrap())
    }

    /// Batch embed multiple texts (much faster than one at a time).
    pub fn embed_batch(&self, texts: &[&str]) -> Result<Vec<Vec<f32>>, Box<dyn std::error::Error>> {
        let owned: Vec<String> = texts.iter().map(|t| t.to_string()).collect();
        let results = self.model.embed(owned, None)?;
        Ok(results)
    }

    pub fn dimension(&self) -> usize {
        self.dimension
    }
}
```

---

## 9. Vector Store

```rust
use std::collections::HashMap;
use std::path::Path;
use serde::{Serialize, Deserialize};

/// Simple in-memory vector store with persistence.
/// For production, consider qdrant, milvus, or lancedb.
pub struct VectorStore {
    entries: Vec<VectorEntry>,
    dimension: usize,
    persist_path: PathBuf,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct VectorEntry {
    pub key: String,
    pub embedding: Vec<f32>,
    pub file_path: String,
    pub metadata: HashMap<String, String>,
}

#[derive(Debug, Clone)]
pub struct VectorResult {
    pub key: String,
    pub score: f64, // cosine similarity, 0-1
    pub file_path: String,
    pub metadata: HashMap<String, String>,
}

impl VectorStore {
    pub fn new(dimension: usize, persist_path: &Path) -> Self {
        let entries = if persist_path.exists() {
            let data = std::fs::read(persist_path).unwrap_or_default();
            bincode::deserialize(&data).unwrap_or_default()
        } else {
            Vec::new()
        };

        Self {
            entries,
            dimension,
            persist_path: persist_path.to_path_buf(),
        }
    }

    pub fn insert(
        &mut self,
        key: &str,
        embedding: &[f32],
        metadata: &ChunkMetadata,
    ) -> Result<(), IndexError> {
        // Remove existing entry with same key
        self.entries.retain(|e| e.key != key);

        let mut meta_map = HashMap::new();
        meta_map.insert("entity_name".into(), metadata.entity_name.clone());
        meta_map.insert("entity_kind".into(), metadata.entity_kind.clone());
        meta_map.insert("language".into(), metadata.language.clone());
        meta_map.insert("start_line".into(), metadata.start_line.to_string());
        meta_map.insert("end_line".into(), metadata.end_line.to_string());

        self.entries.push(VectorEntry {
            key: key.to_string(),
            embedding: embedding.to_vec(),
            file_path: metadata.file_path.clone(),
            metadata: meta_map,
        });

        Ok(())
    }

    /// Cosine similarity search.
    pub fn search(&self, query_embedding: &[f32], limit: usize) -> Vec<VectorResult> {
        let mut scored: Vec<(f64, &VectorEntry)> = self.entries.iter()
            .map(|entry| {
                let score = cosine_similarity(query_embedding, &entry.embedding);
                (score, entry)
            })
            .collect();

        scored.sort_by(|a, b| b.0.partial_cmp(&a.0).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(limit);

        scored.into_iter().map(|(score, entry)| VectorResult {
            key: entry.key.clone(),
            score,
            file_path: entry.file_path.clone(),
            metadata: entry.metadata.clone(),
        }).collect()
    }

    pub fn remove_by_file(&mut self, path: &Path) -> Result<(), IndexError> {
        let path_str = path.to_string_lossy().to_string();
        self.entries.retain(|e| e.file_path != path_str);
        Ok(())
    }

    pub fn persist(&self) -> Result<(), std::io::Error> {
        let data = bincode::serialize(&self.entries)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        std::fs::write(&self.persist_path, data)
    }

    pub fn len(&self) -> usize {
        self.entries.len()
    }
}

/// Cosine similarity between two vectors.
fn cosine_similarity(a: &[f32], b: &[f32]) -> f64 {
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 {
        return 0.0;
    }
    (dot / (norm_a * norm_b)) as f64
}
```

---

## 10. Hybrid Search

```rust
use std::collections::HashMap;

/// Merged search result combining FTS and vector scores.
#[derive(Debug, Clone)]
pub struct SearchResult {
    pub key: String,
    pub entity_name: String,
    pub entity_kind: String,
    pub file_path: String,
    pub language: String,
    pub start_line: usize,
    pub end_line: usize,
    pub snippet: String,
    pub fts_score: f64,
    pub vector_score: f64,
    pub combined_score: f64,
}

pub struct HybridSearcher {
    pub fts: FtsIndex,
    pub vector_store: VectorStore,
    pub embedder: Embedder,
    /// Weight for FTS score (0.0-1.0). Vector weight = 1.0 - fts_weight.
    pub fts_weight: f64,
}

impl HybridSearcher {
    pub fn search(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>, IndexError> {
        // Run both searches in parallel (conceptually — use rayon for actual parallelism)
        let fts_results = self.fts.search(query, limit * 2)?;
        let query_embedding = self.embedder.embed(query)?;
        let vector_results = self.vector_store.search(&query_embedding, limit * 2);

        // Merge by key using weighted scoring
        self.merge_weighted(fts_results, vector_results, limit)
    }

    pub fn search_text_only(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>, IndexError> {
        let results = self.fts.search(query, limit)?;
        Ok(results.into_iter().map(|r| SearchResult {
            key: r.key,
            entity_name: r.entity_name,
            entity_kind: r.entity_kind,
            file_path: r.file_path,
            language: r.language,
            start_line: r.start_line,
            end_line: r.end_line,
            snippet: r.snippet,
            fts_score: r.score,
            vector_score: 0.0,
            combined_score: r.score,
        }).collect())
    }

    pub fn search_vector_only(&self, query: &str, limit: usize) -> Result<Vec<SearchResult>, IndexError> {
        let query_embedding = self.embedder.embed(query)?;
        let results = self.vector_store.search(&query_embedding, limit);
        Ok(results.into_iter().map(|r| SearchResult {
            key: r.key.clone(),
            entity_name: r.metadata.get("entity_name").cloned().unwrap_or_default(),
            entity_kind: r.metadata.get("entity_kind").cloned().unwrap_or_default(),
            file_path: r.file_path,
            language: r.metadata.get("language").cloned().unwrap_or_default(),
            start_line: r.metadata.get("start_line").and_then(|s| s.parse().ok()).unwrap_or(0),
            end_line: r.metadata.get("end_line").and_then(|s| s.parse().ok()).unwrap_or(0),
            snippet: String::new(),
            fts_score: 0.0,
            vector_score: r.score,
            combined_score: r.score,
        }).collect())
    }

    /// Weighted merge: combined = fts_weight * fts_score + (1 - fts_weight) * vector_score
    fn merge_weighted(
        &self,
        fts_results: Vec<FtsResult>,
        vector_results: Vec<VectorResult>,
        limit: usize,
    ) -> Result<Vec<SearchResult>, IndexError> {
        let mut merged: HashMap<String, SearchResult> = HashMap::new();

        // Add FTS results
        for r in fts_results {
            merged.insert(r.key.clone(), SearchResult {
                key: r.key,
                entity_name: r.entity_name,
                entity_kind: r.entity_kind,
                file_path: r.file_path,
                language: r.language,
                start_line: r.start_line,
                end_line: r.end_line,
                snippet: r.snippet,
                fts_score: r.score,
                vector_score: 0.0,
                combined_score: 0.0,
            });
        }

        // Merge vector results
        for r in vector_results {
            if let Some(existing) = merged.get_mut(&r.key) {
                existing.vector_score = r.score;
            } else {
                merged.insert(r.key.clone(), SearchResult {
                    key: r.key.clone(),
                    entity_name: r.metadata.get("entity_name").cloned().unwrap_or_default(),
                    entity_kind: r.metadata.get("entity_kind").cloned().unwrap_or_default(),
                    file_path: r.file_path,
                    language: r.metadata.get("language").cloned().unwrap_or_default(),
                    start_line: r.metadata.get("start_line").and_then(|s| s.parse().ok()).unwrap_or(0),
                    end_line: r.metadata.get("end_line").and_then(|s| s.parse().ok()).unwrap_or(0),
                    snippet: String::new(),
                    fts_score: 0.0,
                    vector_score: r.score,
                    combined_score: 0.0,
                });
            }
        }

        // Calculate combined scores
        let vector_weight = 1.0 - self.fts_weight;
        let mut results: Vec<SearchResult> = merged.into_values().map(|mut r| {
            r.combined_score = self.fts_weight * r.fts_score + vector_weight * r.vector_score;
            r
        }).collect();

        results.sort_by(|a, b| b.combined_score.partial_cmp(&a.combined_score).unwrap());
        results.truncate(limit);
        Ok(results)
    }
}

/// Reciprocal Rank Fusion — alternative to weighted scoring.
/// Combines rankings from multiple result lists without needing normalized scores.
///
/// RRF score for a document = sum over lists: 1 / (k + rank_in_list)
/// where k is a constant (typically 60) that controls how much weight
/// lower-ranked results get.
pub fn reciprocal_rank_fusion(
    result_lists: &[Vec<String>], // Each list is keys in ranked order
    k: f64,
) -> Vec<(String, f64)> {
    let mut scores: HashMap<String, f64> = HashMap::new();

    for list in result_lists {
        for (rank, key) in list.iter().enumerate() {
            *scores.entry(key.clone()).or_insert(0.0) += 1.0 / (k + rank as f64 + 1.0);
        }
    }

    let mut sorted: Vec<(String, f64)> = scores.into_iter().collect();
    sorted.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    sorted
}
```

---

## 11. Index Management Commands (CLI)

```rust
use clap::{Parser, Subcommand};
use std::path::PathBuf;

#[derive(Parser)]
#[command(name = "codeindex")]
pub struct Cli {
    #[command(subcommand)]
    pub command: Command,
}

#[derive(Subcommand)]
pub enum Command {
    /// Index a directory (incremental by default)
    Index {
        /// Directory to index
        dir: PathBuf,
        /// Force full rebuild (ignore cached state)
        #[arg(long)]
        force: bool,
        /// Show current index status without indexing
        #[arg(long)]
        status: bool,
        /// Remove a specific file from the index
        #[arg(long)]
        remove: Option<PathBuf>,
    },
    /// Incremental reindex (alias for `index <dir>`)
    Reindex {
        dir: PathBuf,
    },
    /// Search the index
    Search {
        /// Search query
        query: String,
        /// Max results
        #[arg(short, long, default_value = "10")]
        limit: usize,
        /// Text search only (no vector search)
        #[arg(long)]
        text_only: bool,
        /// Vector search only (no text search)
        #[arg(long)]
        vector_only: bool,
        /// Filter by language
        #[arg(long)]
        language: Option<String>,
        /// Filter by entity kind
        #[arg(long)]
        kind: Option<String>,
    },
}

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let cli = Cli::parse();

    match cli.command {
        Command::Index { dir, force, status, remove } => {
            if status {
                return show_status(&dir);
            }
            if let Some(path) = remove {
                return remove_file(&dir, &path);
            }

            let mut pipeline = IndexingPipeline::new(&dir)?;
            let stats = pipeline.index(&dir, force)?;
            println!("Indexing complete:");
            println!("  Files discovered: {}", stats.files_discovered);
            println!("  Files indexed:    {}", stats.files_parsed);
            println!("  Files skipped:    {}", stats.files_skipped);
            println!("  Files failed:     {}", stats.files_failed);
            println!("  Entities:         {}", stats.entities_extracted);
            println!("  Chunks:           {}", stats.chunks_created);
            println!("  Time:             {:.2}s", stats.elapsed.as_secs_f64());
        }
        Command::Reindex { dir } => {
            let mut pipeline = IndexingPipeline::new(&dir)?;
            let stats = pipeline.index(&dir, false)?;
            println!("Reindex complete: {} files, {} entities in {:.2}s",
                stats.files_parsed, stats.entities_extracted, stats.elapsed.as_secs_f64());
        }
        Command::Search { query, limit, text_only, vector_only, language, kind } => {
            let searcher = HybridSearcher::load(&std::env::current_dir()?)?;
            let results = if text_only {
                searcher.search_text_only(&query, limit)?
            } else if vector_only {
                searcher.search_vector_only(&query, limit)?
            } else {
                searcher.search(&query, limit)?
            };

            // Apply post-filters
            let results: Vec<_> = results.into_iter()
                .filter(|r| language.as_ref().map_or(true, |l| r.language.eq_ignore_ascii_case(l)))
                .filter(|r| kind.as_ref().map_or(true, |k| r.entity_kind.eq_ignore_ascii_case(k)))
                .collect();

            for (i, r) in results.iter().enumerate() {
                println!("{}. [{}] {} ({})", i + 1, r.entity_kind, r.entity_name, r.file_path);
                println!("   Lines {}-{} | FTS: {:.3} | Vec: {:.3} | Combined: {:.3}",
                    r.start_line, r.end_line, r.fts_score, r.vector_score, r.combined_score);
                if !r.snippet.is_empty() {
                    println!("   {}", r.snippet.replace('\n', "\n   "));
                }
                println!();
            }

            if results.is_empty() {
                println!("No results found for: {}", query);
            }
        }
    }

    Ok(())
}

fn show_status(dir: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let state = IndexState::load(&dir.join(".codeindex/state.json"));
    println!("Index status for: {}", dir.display());
    println!("  Total files indexed: {}", state.files.len());

    let total_entities: usize = state.files.values().map(|m| m.entity_count).sum();
    println!("  Total entities:      {}", total_entities);

    // Find stale files
    let mut stale = 0;
    for (path, meta) in &state.files {
        if !path.exists() {
            stale += 1;
            continue;
        }
        if let Ok(fs_meta) = std::fs::metadata(path) {
            if let Ok(modified) = fs_meta.modified() {
                let mtime = modified.duration_since(std::time::UNIX_EPOCH)
                    .unwrap_or_default().as_secs();
                if mtime != meta.mtime {
                    stale += 1;
                }
            }
        }
    }
    println!("  Stale files:         {}", stale);

    // Languages breakdown
    let mut langs: HashMap<String, usize> = HashMap::new();
    for path in state.files.keys() {
        let lang = crate::Language::detect(path);
        *langs.entry(format!("{:?}", lang)).or_insert(0) += 1;
    }
    println!("  Languages:");
    for (lang, count) in &langs {
        println!("    {}: {}", lang, count);
    }

    Ok(())
}

fn remove_file(dir: &Path, file: &Path) -> Result<(), Box<dyn std::error::Error>> {
    let mut pipeline = IndexingPipeline::new(dir)?;
    pipeline.remove_file(file)?;
    println!("Removed {} from index", file.display());
    Ok(())
}
```

---

## 12. Performance Patterns

### Parallel file parsing with rayon

```rust
use rayon::prelude::*;
use std::sync::Mutex;

impl IndexingPipeline {
    /// Index files in parallel using rayon for parsing + entity extraction.
    /// Embedding and storage are batched sequentially (they need mutable access).
    pub fn index_parallel(&mut self, root: &Path, force: bool) -> Result<IndexStats, IndexError> {
        let start = Instant::now();
        let files = self.discovery.walk(root)?;

        let files_to_index = if force {
            self.state.clear_root(root)?;
            files.clone()
        } else {
            self.filter_changed(&files)?
        };

        // Phase 1: Parse all files in parallel (read-only, thread-safe)
        let parse_results: Vec<_> = files_to_index.par_iter()
            .map(|path| {
                let source = match std::fs::read_to_string(path) {
                    Ok(s) => s,
                    Err(e) => return Err((path.clone(), e.to_string())),
                };
                let lang = Language::detect(path);

                // Each thread gets its own parser (Parser is not Send)
                let mut parser = TreeSitterParser::new();
                match parser.extract_entities(path, &source, &lang) {
                    Ok(entities) => Ok((path.clone(), source, entities)),
                    Err(e) => Err((path.clone(), e.to_string())),
                }
            })
            .collect();

        // Phase 2: Chunk all entities
        let mut all_chunks: Vec<Chunk> = Vec::new();
        let mut all_entities: Vec<CodeEntity> = Vec::new();
        let mut files_parsed = 0;
        let mut files_failed = 0;

        for result in parse_results {
            match result {
                Ok((path, source, entities)) => {
                    for entity in &entities {
                        let chunks = self.chunker.chunk(entity);
                        all_chunks.extend(chunks);
                    }
                    all_entities.extend(entities);
                    files_parsed += 1;

                    // Update state
                    let hash = blake3::hash(source.as_bytes());
                    self.state.mark_indexed(&path, hash, all_entities.len())?;
                }
                Err((path, err)) => {
                    eprintln!("Failed to parse {}: {}", path.display(), err);
                    files_failed += 1;
                }
            }
        }

        // Phase 3: Batch embed (GPU/CPU intensive — do in one batch)
        let batch_size = 256;
        let mut embedding_idx = 0;
        for batch_start in (0..all_chunks.len()).step_by(batch_size) {
            let batch_end = (batch_start + batch_size).min(all_chunks.len());
            let texts: Vec<&str> = all_chunks[batch_start..batch_end]
                .iter()
                .map(|c| c.text.as_str())
                .collect();

            let embeddings = self.embedder.embed_batch(&texts)?;

            for (chunk, embedding) in all_chunks[batch_start..batch_end].iter().zip(embeddings.iter()) {
                self.fts.insert(chunk)?;
                self.vector_store.insert(&chunk.key, embedding, &chunk.metadata)?;
            }
        }

        // Phase 4: Store entities in graph
        for entity in &all_entities {
            self.graph.add_entity(entity)?;
        }

        self.vector_store.persist()?;

        Ok(IndexStats {
            files_discovered: files.len(),
            files_skipped: files.len() - files_to_index.len(),
            files_parsed,
            files_failed,
            entities_extracted: all_entities.len(),
            chunks_created: all_chunks.len(),
            embeddings_generated: all_chunks.len(),
            elapsed: start.elapsed(),
        })
    }
}
```

### Progress reporting with indicatif

```rust
use indicatif::{ProgressBar, ProgressStyle, MultiProgress};

fn index_with_progress(pipeline: &mut IndexingPipeline, root: &Path, force: bool) -> Result<IndexStats, IndexError> {
    let multi = MultiProgress::new();

    // Discovery progress (spinner)
    let discover_pb = multi.add(ProgressBar::new_spinner());
    discover_pb.set_style(ProgressStyle::default_spinner()
        .template("{spinner:.green} [{elapsed}] {msg}")
        .unwrap());
    discover_pb.set_message("Discovering files...");

    let files = pipeline.discovery.walk(root)?;
    discover_pb.finish_with_message(format!("Found {} files", files.len()));

    let files_to_index = if force {
        pipeline.state.clear_root(root)?;
        files.clone()
    } else {
        let changed = pipeline.filter_changed(&files)?;
        if changed.is_empty() {
            println!("Index is up to date. No changes detected.");
            return Ok(IndexStats::default());
        }
        changed
    };

    // Parsing progress bar
    let parse_pb = multi.add(ProgressBar::new(files_to_index.len() as u64));
    parse_pb.set_style(ProgressStyle::default_bar()
        .template("{spinner:.green} [{elapsed}] [{bar:40.cyan/blue}] {pos}/{len} {msg}")
        .unwrap()
        .progress_chars("=>-"));
    parse_pb.set_message("Parsing files...");

    let mut all_entities = Vec::new();
    let mut all_chunks = Vec::new();

    for file in &files_to_index {
        match pipeline.index_single_file(file) {
            Ok(result) => {
                all_entities.extend_from_slice(&[]); // entities already stored
            }
            Err(e) => {
                parse_pb.println(format!("  Warning: {}: {}", file.display(), e));
            }
        }
        parse_pb.inc(1);
    }
    parse_pb.finish_with_message("Parsing complete");

    // Embedding progress bar
    let embed_pb = multi.add(ProgressBar::new(all_chunks.len() as u64));
    embed_pb.set_style(ProgressStyle::default_bar()
        .template("{spinner:.green} [{elapsed}] [{bar:40.yellow/red}] {pos}/{len} Embedding...")
        .unwrap());

    // ... batch embedding with progress updates ...
    embed_pb.finish_with_message("Embedding complete");

    Ok(IndexStats::default()) // fill in real stats
}
```

### Lazy embedding pattern

```rust
pub struct LazyEmbedder {
    inner: Option<Embedder>,
}

impl LazyEmbedder {
    pub fn new() -> Self {
        Self { inner: None }
    }

    /// Only initialize (download model) when first embed is requested.
    fn ensure_initialized(&mut self) -> Result<&Embedder, Box<dyn std::error::Error>> {
        if self.inner.is_none() {
            eprintln!("Initializing embedding model (first use)...");
            self.inner = Some(Embedder::new()?);
        }
        Ok(self.inner.as_ref().unwrap())
    }

    pub fn embed(&mut self, text: &str) -> Result<Vec<f32>, Box<dyn std::error::Error>> {
        self.ensure_initialized()?.embed(text)
    }

    pub fn embed_batch(&mut self, texts: &[&str]) -> Result<Vec<Vec<f32>>, Box<dyn std::error::Error>> {
        self.ensure_initialized()?.embed_batch(texts)
    }
}
```

---

## 13. Error Handling

```rust
use thiserror::Error;

#[derive(Error, Debug)]
pub enum IndexError {
    #[error("IO error: {0}")]
    IoError(#[from] std::io::Error),

    #[error("Parse error: failed to parse {0}")]
    ParseFailed,

    #[error("Unsupported language")]
    UnsupportedLanguage,

    #[error("Query error: {0}")]
    QueryError(String),

    #[error("Embedding error: {0}")]
    EmbeddingError(String),

    #[error("Database error: {0}")]
    DatabaseError(#[from] rusqlite::Error),

    #[error("Serialization error: {0}")]
    SerializationError(String),

    #[error("{0}")]
    Other(String),
}

/// Result type alias for indexing operations.
pub type IndexResult<T> = Result<T, IndexError>;
```

---

## 14. Complete Cargo.toml

```toml
[package]
name = "codeindex"
version = "0.1.0"
edition = "2021"

[dependencies]
# CLI
clap = { version = "4", features = ["derive"] }

# File discovery
ignore = "0.4"
walkdir = "2"
glob = "0.3"
num_cpus = "1"

# Parsing
tree-sitter = "0.24"
tree-sitter-rust = "0.23"
tree-sitter-python = "0.23"
tree-sitter-javascript = "0.23"
tree-sitter-typescript = "0.23"
tree-sitter-go = "0.23"

# Hashing
blake3 = "1"
hex = "0.4"

# Full-text search
rusqlite = { version = "0.32", features = ["bundled", "fts5"] }
# Alternative: tantivy = "0.22"

# Embeddings
fastembed = "4"

# Vector store persistence
bincode = "1"

# Parallelism
rayon = "1.10"

# Progress
indicatif = "0.17"

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"

# Error handling
thiserror = "2"
```

---

## 15. Architecture Summary

```
codeindex/
  src/
    main.rs           -- CLI entry point (clap)
    lib.rs            -- re-exports
    discovery.rs      -- FileDiscovery (ignore crate walker)
    parser.rs         -- TreeSitterParser + Language detection
    entity.rs         -- CodeEntity, EntityKind, Language enums
    chunker.rs        -- Chunker (split entities into indexable units)
    embedder.rs       -- Embedder (fastembed wrapper)
    fts.rs            -- FtsIndex (SQLite FTS5)
    vector_store.rs   -- VectorStore (in-memory + persistence)
    hybrid_search.rs  -- HybridSearcher (merge FTS + vector)
    state.rs          -- IndexState (change detection, mtime/hash tracking)
    pipeline.rs       -- IndexingPipeline (orchestrator)
    error.rs          -- IndexError enum
  .codeindex/         -- runtime data directory (created per-project)
    state.json        -- index state manifest
    fts.db            -- SQLite FTS5 database
    vectors.bin       -- persisted vector store
```

### Data flow

```
1. FileDiscovery.walk(root)
      |
      v
2. IndexState.filter_changed(files)
      |
      v
3. TreeSitterParser.extract_entities(file, source, lang)
      |
      v
4. Chunker.chunk(entity) -> Vec<Chunk>
      |
      v
5. Embedder.embed_batch(chunk_texts) -> Vec<Vec<f32>>
      |
      +---> FtsIndex.insert(chunk)           [SQLite FTS5]
      +---> VectorStore.insert(key, embedding) [cosine search]
      +---> KnowledgeGraph.add_entity(entity)  [relationships]
      |
      v
6. IndexState.mark_indexed(path, hash)
      |
      v
7. HybridSearcher.search(query)
      +---> FTS: BM25 ranked results
      +---> Vector: cosine similarity results
      +---> Merge: weighted or RRF fusion
      +---> Enrich: add graph context
      |
      v
8. Vec<SearchResult> (ranked, deduplicated, enriched)
```

### Key design decisions

1. **blake3 over SHA-256** for content hashing: 3-5x faster, SIMD-accelerated, sufficient for change detection (not crypto).

2. **Two-phase change detection**: check mtime first (free syscall), only compute blake3 hash if mtime differs. This makes incremental indexing O(1) per unchanged file.

3. **Stale entity removal before re-insertion**: when a file changes, delete ALL old entities for that file, then re-parse and re-insert. This is simpler and more correct than diffing ASTs.

4. **Batch embedding**: embedding models are optimized for batch inference. Embedding 256 chunks at once is 10-50x faster than embedding them one at a time.

5. **FTS5 with porter stemmer**: the `porter unicode61` tokenizer handles stemming ("searching" matches "search") and Unicode normalization. BM25 is the gold standard for keyword relevance.

6. **Hybrid search with weighted merge**: FTS catches exact keyword matches that vector search misses; vector search catches semantic similarity that keyword search misses. Default weight: 0.4 FTS + 0.6 vector.

7. **RRF as alternative to weighted merge**: Reciprocal Rank Fusion does not require score normalization and is more robust when score distributions differ wildly between FTS and vector search. Use k=60 (standard constant).

8. **Skip-and-continue error handling**: a single unparseable file must never stop the entire indexing pipeline. Log the error, skip the file, continue.

9. **Lazy embedding initialization**: the embedding model download (~30MB for MiniLM) should only happen when search is first used, not on every index operation (some users may only need the graph, not search).

10. **ignore crate over walkdir**: the `ignore` crate is the exact same engine used by ripgrep. It handles `.gitignore`, `.ignore`, global gitignore, and nested ignore files correctly. It also supports parallel walking via `build_parallel()`.
