---
name: wiki-graph
description: Generate wiki/documentation sites from code knowledge graphs. Transforms AST-derived graph data (entities, edges, observations) into interconnected wiki pages with cross-references, breadcrumbs, backlinks, and quality signals. Supports Markdown, HTML, D2 diagrams, JSON, Gibber, and mdBook output.
trigger: When the user asks to generate documentation from a codebase graph, create a code wiki, build API docs from a knowledge graph, or produce navigable documentation from code-graph MCP data.
---

# Wiki Graph Skill

Generate structured, cross-referenced documentation from a code knowledge graph. A "wiki graph" is a documentation site where **pages are entities** and **links are relations** -- a code wiki that writes itself from the AST.

---

## 1. What Is a Wiki Graph

A wiki graph is a documentation artifact produced by traversing a code knowledge graph (nodes = code entities, edges = relationships like `imports`, `calls`, `extends`, `contains`) and emitting one page per entity with hyperlinks corresponding to edges.

**Input:** A code-graph database with entity types (`code_file`, `code_class`, `code_function`, `code_module`, `codebase`) and edge types (`contains`, `imports`, `extends`, `calls`), plus observations (docstrings, signatures, metadata).

**Output:** A set of interconnected documents (Markdown, HTML, etc.) with:
- One page per entity (or per significant entity, filtered by type)
- Hyperlinks between pages following graph edges
- Index pages, breadcrumbs, backlinks
- Embedded dependency diagrams (D2)
- Quality signals (missing docs, orphans, circular deps)

### Conceptual Model

```
Code Knowledge Graph              Wiki Graph
==================              ==========
Entity (code_class)       -->   Page (ClassName.md)
Edge (calls)              -->   Link ("Calls: [FuncB](func_b.md)")
Observation (docstring)   -->   Page section ("## Description")
Containment (file->class) -->   Breadcrumb ("src/models.rs > User")
Reverse edge (called-by)  -->   Backlink section ("## Called By")
```

### Data Flow Pipeline

```
1. Extract    graph from code-graph MCP (get_graph, get_entity, get_dependencies)
2. Resolve    entity metadata (observations, source locations, signatures)
3. Slugify    entity names to filesystem-safe page paths
4. Template   each entity through its page-type template
5. Cross-link replace entity name references with hyperlinks
6. Index      generate index pages, ToC, navigation
7. Emit       write to output format (md, html, json, d2, gibber, mdbook)
```

---

## 2. Page Types and Templates

### 2.1 Module Page

Represents a file or module (e.g., `src/models.rs`).

**Template (Markdown):**

```markdown
# Module: {{ module.display_name }}

**File:** `{{ module.file_path }}`
**Language:** {{ module.language }}

## Imports
{% for imp in module.imports %}
- [{{ imp.display_name }}]({{ imp.slug }}.md)
{% endfor %}

## Exports
{% for exp in module.exports %}
- [{{ exp.display_name }}]({{ exp.slug }}.md) ({{ exp.entity_type }})
{% endfor %}

## Defines

### Classes
{% for cls in module.classes %}
- [{{ cls.display_name }}]({{ cls.slug }}.md)
{% endfor %}

### Functions
{% for func in module.functions %}
- [{{ func.display_name }}]({{ func.slug }}.md)
{% endfor %}

## Imported By
{% for dep in module.imported_by %}
- [{{ dep.display_name }}]({{ dep.slug }}.md)
{% endfor %}

## Dependency Diagram
```d2
{{ module.d2_diagram }}
```
```

**Data extraction:**

```
get_graph(codebase_id, entity_types="code_file", file_filter="src/*")
  -> for each file node:
       get_dependencies(entity_id, direction="outgoing")  -> imports
       get_dependencies(entity_id, direction="incoming")  -> imported_by
       get_graph(codebase_id, file_filter=<this_file>)    -> contained entities
```

### 2.2 Class Page

```markdown
# Class: {{ class.display_name }}

**Defined in:** [{{ class.module }}]({{ class.module_slug }}.md)
**Language:** {{ class.language }}

## Inheritance
{% if class.extends %}
**Extends:** [{{ class.extends.display_name }}]({{ class.extends.slug }}.md)
{% endif %}
{% if class.extended_by %}
**Extended by:**
{% for sub in class.extended_by %}
- [{{ sub.display_name }}]({{ sub.slug }}.md)
{% endfor %}
{% endif %}

## Description
{{ class.docstring | default("*No documentation.*") }}

## Properties
| Name | Type | Description |
|------|------|-------------|
{% for prop in class.properties %}
| `{{ prop.name }}` | `{{ prop.type_annotation }}` | {{ prop.description }} |
{% endfor %}

## Methods
{% for method in class.methods %}
### `{{ method.name }}({{ method.params_short }})`
**Signature:** `{{ method.full_signature }}`
**Returns:** `{{ method.return_type }}`
{{ method.docstring }}
{% endfor %}

## Used By
{% for user in class.used_by %}
- [{{ user.display_name }}]({{ user.slug }}.md) ({{ user.relation }})
{% endfor %}

## Backlinks
{% for link in class.backlinks %}
- [{{ link.display_name }}]({{ link.slug }}.md)
{% endfor %}
```

**Data extraction:**

```
get_entity(entity_id)                              -> name, observations (docstring)
get_dependencies(entity_id, direction="outgoing")  -> extends edges
get_dependencies(entity_id, direction="incoming")  -> extended_by, called_by, imported_by
get_graph(codebase_id, file_filter=<file>)         -> methods as contained functions
```

### 2.3 Function Page

```markdown
# Function: {{ func.display_name }}

**Defined in:** [{{ func.module }}]({{ func.module_slug }}.md)
{% if func.class %}
**Class:** [{{ func.class }}]({{ func.class_slug }}.md)
{% endif %}

## Signature
```{{ func.language }}
{{ func.full_signature }}
```

## Parameters
| Name | Type | Default | Description |
|------|------|---------|-------------|
{% for param in func.parameters %}
| `{{ param.name }}` | `{{ param.type_annotation }}` | {{ param.default }} | {{ param.description }} |
{% endfor %}

## Returns
`{{ func.return_type }}` -- {{ func.return_description }}

## Description
{{ func.docstring | default("*No documentation.*") }}

## Calls (outgoing)
{% for callee in func.calls %}
- [{{ callee.display_name }}]({{ callee.slug }}.md)
{% endfor %}

## Called By (incoming)
{% for caller in func.called_by %}
- [{{ caller.display_name }}]({{ caller.slug }}.md)
{% endfor %}
```

### 2.4 Interface / Trait Page

```markdown
# Trait: {{ trait.display_name }}

**Defined in:** [{{ trait.module }}]({{ trait.module_slug }}.md)

## Required Methods
{% for method in trait.required_methods %}
### `{{ method.name }}({{ method.params_short }})`
{{ method.docstring }}
{% endfor %}

## Provided Methods
{% for method in trait.provided_methods %}
### `{{ method.name }}({{ method.params_short }})` *(default impl)*
{{ method.docstring }}
{% endfor %}

## Implementors
{% for impl in trait.implementors %}
- [{{ impl.display_name }}]({{ impl.slug }}.md)
{% endfor %}
```

### 2.5 Package / Crate Page

```markdown
# Crate: {{ crate.name }}

**Version:** {{ crate.version }}
**Root module:** [{{ crate.root_module }}]({{ crate.root_slug }}.md)

## Submodules
{% for mod in crate.submodules %}
- [{{ mod.display_name }}]({{ mod.slug }}.md) -- {{ mod.summary }}
{% endfor %}

## Dependencies (external)
{% for dep in crate.external_deps %}
- `{{ dep.name }}` {{ dep.version }}
{% endfor %}

## Dependents (who uses this crate)
{% for dep in crate.dependents %}
- [{{ dep.display_name }}]({{ dep.slug }}.md)
{% endfor %}
```

### 2.6 Index Page

```markdown
# {{ codebase.name }} -- Code Wiki

Generated: {{ timestamp }}
Source: `{{ codebase.root_path }}`

## Summary
| Entity Type | Count |
|-------------|-------|
| Modules     | {{ counts.modules }} |
| Classes     | {{ counts.classes }} |
| Functions   | {{ counts.functions }} |
| Traits      | {{ counts.traits }} |

## Modules
{% for mod in modules %}
- [{{ mod.display_name }}]({{ mod.slug }}.md) -- {{ mod.summary }}
{% endfor %}

## Quality Signals
- Missing docstrings: {{ quality.missing_docs }} entities
- Orphan entities: {{ quality.orphans }} (no incoming edges)
- High fan-out: {{ quality.high_fanout }} functions (>10 outgoing calls)
- Circular dependencies: {{ quality.circular_deps }} cycles detected
```

### 2.7 Dependency Graph Page

```markdown
# Dependency Graph

## Module Dependencies
```d2
{% for edge in module_edges %}
{{ edge.source }}.style.fill: "#e8f4fd"
{{ edge.source }} -> {{ edge.target }}: {{ edge.label }}
{% endfor %}
```

## Class Inheritance
```d2
direction: down
{% for edge in inheritance_edges %}
{{ edge.child }} -> {{ edge.parent }}: extends
{% endfor %}
```
```

### 2.8 Changelog Page (Diff Between Two Graph Snapshots)

```markdown
# Changelog: {{ old_timestamp }} -> {{ new_timestamp }}

## Added Entities
{% for e in added %}
- **{{ e.entity_type }}** [{{ e.display_name }}]({{ e.slug }}.md)
{% endfor %}

## Removed Entities
{% for e in removed %}
- **{{ e.entity_type }}** {{ e.display_name }}
{% endfor %}

## Modified Entities
{% for e in modified %}
- [{{ e.display_name }}]({{ e.slug }}.md): {{ e.change_description }}
{% endfor %}

## New Edges
{% for e in new_edges %}
- {{ e.source }} --{{ e.type }}--> {{ e.target }}
{% endfor %}

## Removed Edges
{% for e in removed_edges %}
- ~~{{ e.source }} --{{ e.type }}--> {{ e.target }}~~
{% endfor %}
```

---

## 3. Cross-Referencing and Linking

### 3.1 Entity Name to Page Slug Mapping

Every entity gets a deterministic, filesystem-safe slug:

```rust
/// Convert an entity display name to a filesystem-safe slug.
/// Handles namespaces by preserving hierarchy with double underscores.
///
/// Examples:
///   "UserService"         -> "userservice"
///   "src/models.rs"       -> "src__models_rs"
///   "MyClass::my_method"  -> "myclass__my_method"
///   "std::io::Read"       -> "std__io__read"
fn slugify(entity_name: &str, entity_type: &str) -> String {
    let prefix = match entity_type {
        "code_file" | "code_module" => "mod",
        "code_class" => "cls",
        "code_function" => "fn",
        "codebase" => "crate",
        _ => "ent",
    };

    let slug_body: String = entity_name
        .chars()
        .map(|c| match c {
            '/' | '\\' => '_',
            ':' => '_',
            '.' => '_',
            ' ' => '_',
            c if c.is_alphanumeric() || c == '_' => c.to_ascii_lowercase(),
            _ => '_',
        })
        .collect();

    // Collapse repeated underscores, trim edges
    let collapsed = slug_body
        .split('_')
        .filter(|s| !s.is_empty())
        .collect::<Vec<_>>()
        .join("_");

    format!("{prefix}_{collapsed}")
}
```

**Slug registry** (prevents collisions):

```rust
use std::collections::HashMap;

struct SlugRegistry {
    slugs: HashMap<String, String>,          // entity_id -> slug
    reverse: HashMap<String, String>,        // slug -> entity_id
}

impl SlugRegistry {
    fn new() -> Self {
        Self { slugs: HashMap::new(), reverse: HashMap::new() }
    }

    fn register(&mut self, entity_id: &str, display_name: &str, entity_type: &str) -> String {
        if let Some(slug) = self.slugs.get(entity_id) {
            return slug.clone();
        }

        let mut slug = slugify(display_name, entity_type);
        let base = slug.clone();
        let mut counter = 1;

        // Handle collisions by appending a counter
        while self.reverse.contains_key(&slug) {
            slug = format!("{base}_{counter}");
            counter += 1;
        }

        self.slugs.insert(entity_id.to_string(), slug.clone());
        self.reverse.insert(slug.clone(), entity_id.to_string());
        slug
    }

    fn get_slug(&self, entity_id: &str) -> Option<&str> {
        self.slugs.get(entity_id).map(|s| s.as_str())
    }

    fn get_entity_id(&self, slug: &str) -> Option<&str> {
        self.reverse.get(slug).map(|s| s.as_str())
    }
}
```

### 3.2 Auto-Linking Entity Names in Text

Scan observation text (docstrings, descriptions) and replace recognized entity names with hyperlinks:

```rust
use regex::Regex;

/// Build a regex that matches any known entity name.
/// Sort names by length descending so longer names match first
/// (prevents "User" matching inside "UserService").
fn build_autolink_regex(entity_names: &[&str]) -> Regex {
    let mut sorted: Vec<&&str> = entity_names.iter().collect();
    sorted.sort_by(|a, b| b.len().cmp(&a.len()));

    let alternatives: Vec<String> = sorted
        .iter()
        .map(|name| regex::escape(name))
        .collect();

    // Word-boundary anchored
    let pattern = format!(r"\b({})\b", alternatives.join("|"));
    Regex::new(&pattern).expect("valid regex")
}

/// Replace entity name occurrences with markdown links.
/// Skip replacements inside existing links or code blocks.
fn autolink_text(
    text: &str,
    regex: &Regex,
    slug_map: &HashMap<String, String>,  // display_name -> slug
) -> String {
    // Simple approach: skip if already inside []() or backticks
    regex.replace_all(text, |caps: &regex::Captures| {
        let name = &caps[0];
        if let Some(slug) = slug_map.get(name) {
            format!("[{name}]({slug}.md)")
        } else {
            name.to_string()
        }
    }).to_string()
}
```

### 3.3 Backlink Generation

Every page includes a "What Links Here" section. Build this from the edge set:

```rust
use std::collections::{HashMap, HashSet};

/// Backlink index: for each entity_id, which other entity_ids link TO it.
struct BacklinkIndex {
    /// entity_id -> set of (source_entity_id, edge_type)
    links: HashMap<String, HashSet<(String, String)>>,
}

impl BacklinkIndex {
    fn new() -> Self {
        Self { links: HashMap::new() }
    }

    fn add_edge(&mut self, source_id: &str, target_id: &str, edge_type: &str) {
        self.links
            .entry(target_id.to_string())
            .or_default()
            .insert((source_id.to_string(), edge_type.to_string()));
    }

    fn get_backlinks(&self, entity_id: &str) -> Vec<(&str, &str)> {
        self.links
            .get(entity_id)
            .map(|set| {
                set.iter()
                    .map(|(src, edge)| (src.as_str(), edge.as_str()))
                    .collect()
            })
            .unwrap_or_default()
    }
}
```

### 3.4 Breadcrumb Navigation

Generate hierarchical breadcrumbs from containment edges (`contains`):

```rust
/// Build the containment path for an entity.
/// Returns: ["crate::my_crate", "src/models.rs", "UserService", "get_name"]
fn build_breadcrumb(
    entity_id: &str,
    containment: &HashMap<String, String>,  // child_id -> parent_id
    display_names: &HashMap<String, String>,
    slug_registry: &SlugRegistry,
) -> Vec<(String, String)> {
    let mut crumbs = Vec::new();
    let mut current = entity_id.to_string();

    loop {
        let name = display_names.get(&current).cloned().unwrap_or_default();
        let slug = slug_registry.get_slug(&current).unwrap_or("").to_string();
        crumbs.push((name, slug));

        match containment.get(&current) {
            Some(parent) => current = parent.clone(),
            None => break,
        }
    }

    crumbs.reverse();
    crumbs
}

/// Render breadcrumbs as markdown.
fn render_breadcrumb(crumbs: &[(String, String)]) -> String {
    crumbs
        .iter()
        .map(|(name, slug)| {
            if slug.is_empty() {
                name.clone()
            } else {
                format!("[{name}]({slug}.md)")
            }
        })
        .collect::<Vec<_>>()
        .join(" > ")
}
```

### 3.5 Namespace-Aware Linking

Handle entities with the same display name in different modules:

```rust
/// Resolve an ambiguous entity name to the correct slug.
/// Uses the current page's module context to prefer local entities.
fn resolve_entity_link(
    name: &str,
    current_module: &str,
    name_index: &HashMap<String, Vec<(String, String)>>,  // name -> [(entity_id, module)]
    slug_registry: &SlugRegistry,
) -> Option<String> {
    let candidates = name_index.get(name)?;

    if candidates.len() == 1 {
        return slug_registry.get_slug(&candidates[0].0).map(|s| s.to_string());
    }

    // Prefer entity in the same module
    if let Some((id, _)) = candidates.iter().find(|(_, m)| m == current_module) {
        return slug_registry.get_slug(id).map(|s| s.to_string());
    }

    // Fallback: use the first match but qualify the link text
    let (id, module) = &candidates[0];
    slug_registry.get_slug(id).map(|slug| {
        format!("{slug}") // caller should display as "module::name"
    })
}
```

---

## 4. Content Generation Strategies

### 4.1 From AST Observations

Extract structured content from entity observations stored in the graph:

```rust
#[derive(Debug, Clone)]
struct EntityContent {
    display_name: String,
    entity_type: String,
    docstring: Option<String>,
    signature: Option<String>,
    parameters: Vec<Parameter>,
    return_type: Option<String>,
    source_location: Option<SourceLocation>,
}

#[derive(Debug, Clone)]
struct Parameter {
    name: String,
    type_annotation: Option<String>,
    default_value: Option<String>,
    description: Option<String>,
}

#[derive(Debug, Clone)]
struct SourceLocation {
    file_path: String,
    line_start: usize,
    line_end: usize,
}

/// Parse observations from entity metadata into structured content.
fn extract_content(entity: &serde_json::Value) -> EntityContent {
    let observations = entity["observations"]
        .as_array()
        .cloned()
        .unwrap_or_default();

    let docstring = observations.iter()
        .find(|o| {
            let text = o.as_str().unwrap_or("");
            text.starts_with("\"\"\"") || text.starts_with("///") || text.starts_with("/**")
        })
        .and_then(|o| o.as_str())
        .map(|s| strip_doc_markers(s));

    let signature = observations.iter()
        .find(|o| {
            let text = o.as_str().unwrap_or("");
            text.contains("fn ") || text.contains("def ") || text.contains("function ")
        })
        .and_then(|o| o.as_str())
        .map(|s| s.to_string());

    EntityContent {
        display_name: entity["display_name"].as_str().unwrap_or("").to_string(),
        entity_type: entity["entity_type"].as_str().unwrap_or("").to_string(),
        docstring,
        signature,
        parameters: Vec::new(), // parsed from signature
        return_type: None,      // parsed from signature
        source_location: None,
    }
}

fn strip_doc_markers(doc: &str) -> String {
    doc.lines()
        .map(|line| {
            line.trim()
                .trim_start_matches("///")
                .trim_start_matches("/**")
                .trim_start_matches("**/")
                .trim_start_matches("* ")
                .trim_start_matches("*")
                .trim_start_matches("\"\"\"")
                .trim_start_matches("#")
        })
        .collect::<Vec<_>>()
        .join("\n")
        .trim()
        .to_string()
}
```

### 4.2 From Graph Topology

Generate content by analyzing the shape of the graph:

```rust
/// Analyze topology to generate summary content.
struct TopologyAnalyzer {
    edges: Vec<(String, String, String)>,  // (source, target, edge_type)
}

impl TopologyAnalyzer {
    /// Build inheritance tree for a class.
    fn inheritance_chain(&self, class_id: &str) -> Vec<String> {
        let mut chain = vec![class_id.to_string()];
        let mut current = class_id.to_string();

        loop {
            let parent = self.edges.iter()
                .find(|(src, _, etype)| src == &current && etype == "extends")
                .map(|(_, tgt, _)| tgt.clone());

            match parent {
                Some(p) => {
                    if chain.contains(&p) { break; } // cycle guard
                    chain.push(p.clone());
                    current = p;
                }
                None => break,
            }
        }

        chain
    }

    /// Find the full call chain from a function (BFS, bounded depth).
    fn call_chain(&self, func_id: &str, max_depth: usize) -> Vec<(String, usize)> {
        let mut visited = std::collections::HashSet::new();
        let mut queue = std::collections::VecDeque::new();
        let mut result = Vec::new();

        queue.push_back((func_id.to_string(), 0usize));
        visited.insert(func_id.to_string());

        while let Some((current, depth)) = queue.pop_front() {
            if depth > 0 {
                result.push((current.clone(), depth));
            }
            if depth >= max_depth { continue; }

            for (src, tgt, etype) in &self.edges {
                if src == &current && etype == "calls" && !visited.contains(tgt) {
                    visited.insert(tgt.clone());
                    queue.push_back((tgt.clone(), depth + 1));
                }
            }
        }

        result
    }

    /// Fan-out: how many things does this entity call/import.
    fn fan_out(&self, entity_id: &str) -> usize {
        self.edges.iter()
            .filter(|(src, _, etype)| src == entity_id && (etype == "calls" || etype == "imports"))
            .count()
    }

    /// Fan-in: how many things call/import this entity.
    fn fan_in(&self, entity_id: &str) -> usize {
        self.edges.iter()
            .filter(|(_, tgt, etype)| tgt == entity_id && (etype == "calls" || etype == "imports"))
            .count()
    }

    /// Detect circular dependencies using Tarjan's SCC algorithm.
    fn find_cycles(&self) -> Vec<Vec<String>> {
        // Collect unique nodes
        let mut nodes = std::collections::HashSet::new();
        for (src, tgt, _) in &self.edges {
            nodes.insert(src.clone());
            nodes.insert(tgt.clone());
        }

        // Tarjan's SCC
        let mut index_counter = 0u64;
        let mut stack = Vec::new();
        let mut on_stack = std::collections::HashSet::new();
        let mut indices = std::collections::HashMap::new();
        let mut lowlinks = std::collections::HashMap::new();
        let mut sccs: Vec<Vec<String>> = Vec::new();

        fn strongconnect(
            v: &str,
            edges: &[(String, String, String)],
            index_counter: &mut u64,
            stack: &mut Vec<String>,
            on_stack: &mut std::collections::HashSet<String>,
            indices: &mut std::collections::HashMap<String, u64>,
            lowlinks: &mut std::collections::HashMap<String, u64>,
            sccs: &mut Vec<Vec<String>>,
        ) {
            indices.insert(v.to_string(), *index_counter);
            lowlinks.insert(v.to_string(), *index_counter);
            *index_counter += 1;
            stack.push(v.to_string());
            on_stack.insert(v.to_string());

            for (src, tgt, _) in edges {
                if src != v { continue; }
                if !indices.contains_key(tgt) {
                    strongconnect(tgt, edges, index_counter, stack, on_stack,
                                  indices, lowlinks, sccs);
                    let tgt_ll = lowlinks[tgt];
                    let v_ll = lowlinks.get_mut(v).unwrap();
                    *v_ll = (*v_ll).min(tgt_ll);
                } else if on_stack.contains(tgt) {
                    let tgt_idx = indices[tgt];
                    let v_ll = lowlinks.get_mut(v).unwrap();
                    *v_ll = (*v_ll).min(tgt_idx);
                }
            }

            if lowlinks[v] == indices[v] {
                let mut scc = Vec::new();
                loop {
                    let w = stack.pop().unwrap();
                    on_stack.remove(&w);
                    scc.push(w.clone());
                    if w == v { break; }
                }
                if scc.len() > 1 {
                    sccs.push(scc);
                }
            }
        }

        for node in &nodes {
            if !indices.contains_key(node) {
                strongconnect(
                    node, &self.edges, &mut index_counter, &mut stack,
                    &mut on_stack, &mut indices, &mut lowlinks, &mut sccs,
                );
            }
        }

        sccs
    }

    /// Dependency fan: for a module, which other modules does it touch (and how many edges).
    fn dependency_fan(&self, module_id: &str, containment: &HashMap<String, String>) -> HashMap<String, usize> {
        let mut fan: HashMap<String, usize> = HashMap::new();

        // Find all entities contained in this module
        let children: Vec<&str> = containment.iter()
            .filter(|(_, parent)| parent.as_str() == module_id)
            .map(|(child, _)| child.as_str())
            .collect();

        for (src, tgt, _) in &self.edges {
            if children.contains(&src.as_str()) {
                // Find the module that contains the target
                if let Some(target_module) = containment.get(tgt) {
                    if target_module != module_id {
                        *fan.entry(target_module.clone()).or_insert(0) += 1;
                    }
                }
            }
        }

        fan
    }
}
```

### 4.3 From Vector Similarity

If embeddings are available, show related entities:

```rust
/// Find the N most similar entities by embedding cosine distance.
fn find_related_entities(
    entity_embedding: &[f32],
    all_embeddings: &HashMap<String, Vec<f32>>,  // entity_id -> embedding
    top_n: usize,
    exclude_id: &str,
) -> Vec<(String, f32)> {
    let mut scores: Vec<(String, f32)> = all_embeddings
        .iter()
        .filter(|(id, _)| id.as_str() != exclude_id)
        .map(|(id, emb)| {
            let sim = cosine_similarity(entity_embedding, emb);
            (id.clone(), sim)
        })
        .collect();

    scores.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
    scores.truncate(top_n);
    scores
}

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if norm_a == 0.0 || norm_b == 0.0 { return 0.0; }
    dot / (norm_a * norm_b)
}
```

### 4.4 From Git History

Enrich pages with authorship and change frequency:

```rust
use std::process::Command;

#[derive(Debug, Clone)]
struct GitInfo {
    last_modified: String,
    last_author: String,
    commit_count: usize,
    change_frequency: f64,  // commits per week
}

fn get_git_info(file_path: &str, repo_root: &str) -> Option<GitInfo> {
    let log_output = Command::new("git")
        .args(["log", "--format=%H|%an|%aI", "--follow", "--", file_path])
        .current_dir(repo_root)
        .output()
        .ok()?;

    let log_str = String::from_utf8_lossy(&log_output.stdout);
    let lines: Vec<&str> = log_str.lines().collect();

    if lines.is_empty() { return None; }

    let first_parts: Vec<&str> = lines[0].split('|').collect();
    let last_modified = first_parts.get(2)?.to_string();
    let last_author = first_parts.get(1)?.to_string();
    let commit_count = lines.len();

    // Approximate change frequency
    let oldest_parts: Vec<&str> = lines.last()?.split('|').collect();
    let _oldest_date = oldest_parts.get(2)?;
    // Simplified: assume linear distribution
    let change_frequency = commit_count as f64 / 52.0; // rough per-week

    Some(GitInfo {
        last_modified,
        last_author,
        commit_count,
        change_frequency,
    })
}
```

### 4.5 Summary Generation

Generate a one-line summary for a module based on its contents:

```rust
/// Generate a summary string for a module based on its contained entities.
fn generate_module_summary(
    module_name: &str,
    classes: &[&str],
    functions: &[&str],
    imports: &[&str],
) -> String {
    if classes.is_empty() && functions.is_empty() {
        return format!("{module_name}: empty module");
    }

    let mut parts = Vec::new();

    if !classes.is_empty() {
        if classes.len() <= 3 {
            parts.push(format!("defines {}", classes.join(", ")));
        } else {
            parts.push(format!("defines {} classes", classes.len()));
        }
    }

    if !functions.is_empty() {
        if functions.len() <= 3 {
            parts.push(format!("provides {}", functions.join(", ")));
        } else {
            parts.push(format!("{} functions", functions.len()));
        }
    }

    if !imports.is_empty() {
        parts.push(format!("depends on {} modules", imports.len()));
    }

    format!("{module_name}: {}", parts.join("; "))
}
```

---

## 5. Output Formats

### 5.1 Markdown (GitHub-Flavored)

The primary output format. Each page is a `.md` file in a flat or hierarchical directory.

```rust
use std::path::PathBuf;
use std::fs;

struct MarkdownEmitter {
    output_dir: PathBuf,
}

impl MarkdownEmitter {
    fn new(output_dir: PathBuf) -> Self {
        fs::create_dir_all(&output_dir).expect("create output dir");
        Self { output_dir }
    }

    fn emit_page(&self, slug: &str, content: &str) {
        let path = self.output_dir.join(format!("{slug}.md"));
        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent).expect("create parent dir");
        }
        fs::write(&path, content).expect("write page");
    }

    fn emit_index(&self, index_content: &str) {
        let path = self.output_dir.join("index.md");
        fs::write(&path, index_content).expect("write index");
    }
}
```

### 5.2 HTML (Static Site)

Wrap markdown in an HTML shell with navigation:

```rust
struct HtmlEmitter {
    output_dir: PathBuf,
    nav_html: String,
}

impl HtmlEmitter {
    fn wrap_page(&self, title: &str, body_html: &str, breadcrumb_html: &str) -> String {
        format!(r#"<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <title>{title}</title>
  <link rel="stylesheet" href="style.css">
</head>
<body>
  <nav class="sidebar">{nav}</nav>
  <main>
    <div class="breadcrumb">{breadcrumb_html}</div>
    <article>{body_html}</article>
  </main>
  <script src="search.js"></script>
</body>
</html>"#,
            nav = self.nav_html,
        )
    }

    fn emit_page(&self, slug: &str, title: &str, markdown: &str, breadcrumb: &str) {
        // Convert markdown to HTML using pulldown-cmark
        let body_html = markdown_to_html(markdown);
        let full_html = self.wrap_page(title, &body_html, breadcrumb);

        let path = self.output_dir.join(format!("{slug}.html"));
        fs::write(&path, full_html).expect("write html page");
    }

    fn emit_css(&self) {
        let css = r#"
body { font-family: -apple-system, sans-serif; margin: 0; display: flex; }
nav.sidebar { width: 260px; padding: 1rem; background: #f5f5f5; height: 100vh;
              overflow-y: auto; position: fixed; }
main { margin-left: 280px; padding: 2rem; max-width: 900px; }
.breadcrumb { color: #666; margin-bottom: 1rem; }
.breadcrumb a { color: #0366d6; text-decoration: none; }
table { border-collapse: collapse; width: 100%; }
th, td { border: 1px solid #ddd; padding: 8px; text-align: left; }
th { background: #f5f5f5; }
code { background: #f0f0f0; padding: 2px 6px; border-radius: 3px; }
pre code { display: block; padding: 1rem; overflow-x: auto; }
a { color: #0366d6; }
"#;
        fs::write(self.output_dir.join("style.css"), css).expect("write css");
    }
}

/// Convert markdown to HTML using pulldown-cmark.
/// Cargo.toml: pulldown-cmark = "0.10"
fn markdown_to_html(markdown: &str) -> String {
    use pulldown_cmark::{Parser, Options, html};

    let mut options = Options::empty();
    options.insert(Options::ENABLE_TABLES);
    options.insert(Options::ENABLE_STRIKETHROUGH);

    let parser = Parser::new_ext(markdown, options);
    let mut html_output = String::new();
    html::push_html(&mut html_output, parser);
    html_output
}
```

### 5.3 D2 Diagrams

Generate D2 diagram code for dependency visualization:

```rust
struct D2Generator;

impl D2Generator {
    /// Generate a module dependency diagram.
    fn module_deps(modules: &[(String, Vec<String>)]) -> String {
        let mut d2 = String::from("direction: right\n\n");

        for (module, deps) in modules {
            let safe_name = module.replace('/', "_").replace('.', "_");
            d2.push_str(&format!("{safe_name}: {module}\n"));
            d2.push_str(&format!("{safe_name}.style.fill: \"#e8f4fd\"\n"));
        }

        d2.push('\n');

        for (module, deps) in modules {
            let src = module.replace('/', "_").replace('.', "_");
            for dep in deps {
                let tgt = dep.replace('/', "_").replace('.', "_");
                d2.push_str(&format!("{src} -> {tgt}\n"));
            }
        }

        d2
    }

    /// Generate a class inheritance diagram.
    fn inheritance_tree(edges: &[(String, String)]) -> String {
        let mut d2 = String::from("direction: down\n\n");

        for (child, parent) in edges {
            d2.push_str(&format!("{child} -> {parent}: extends {{\n"));
            d2.push_str("  style.stroke-dash: 3\n");
            d2.push_str("}\n");
        }

        d2
    }

    /// Generate a call graph diagram for a function.
    fn call_graph(center: &str, calls: &[(String, usize)]) -> String {
        let mut d2 = String::from("direction: right\n\n");

        let safe_center = center.replace("::", "__");
        d2.push_str(&format!("{safe_center}: {center}\n"));
        d2.push_str(&format!("{safe_center}.style.fill: \"#ffd700\"\n\n"));

        for (callee, depth) in calls {
            let safe_callee = callee.replace("::", "__");
            let opacity = 1.0 - (*depth as f64 * 0.2).min(0.8);
            d2.push_str(&format!("{safe_callee}: {callee}\n"));
            d2.push_str(&format!("{safe_callee}.style.opacity: {opacity:.1}\n"));

            if *depth == 1 {
                d2.push_str(&format!("{safe_center} -> {safe_callee}\n"));
            }
        }

        // Add deeper edges
        // (Would need the full edge set for precise deep linking)

        d2
    }

    /// Generate a circular dependency diagram.
    fn circular_deps(cycles: &[Vec<String>]) -> String {
        let mut d2 = String::from("direction: right\n\n");

        for (i, cycle) in cycles.iter().enumerate() {
            d2.push_str(&format!("cycle_{i}: \"Cycle {i}\" {{\n"));
            for j in 0..cycle.len() {
                let from = &cycle[j].replace("::", "__");
                let to = &cycle[(j + 1) % cycle.len()].replace("::", "__");
                d2.push_str(&format!("  {from} -> {to}\n"));
            }
            for node in cycle {
                let safe = node.replace("::", "__");
                d2.push_str(&format!("  {safe}.style.fill: \"#ff6b6b\"\n"));
            }
            d2.push_str("}\n\n");
        }

        d2
    }
}
```

### 5.4 JSON (Structured)

Machine-readable output for programmatic consumption:

```rust
use serde::{Serialize, Deserialize};

#[derive(Serialize)]
struct WikiJson {
    metadata: WikiMetadata,
    pages: Vec<PageJson>,
    edges: Vec<EdgeJson>,
    quality: QualityReport,
}

#[derive(Serialize)]
struct WikiMetadata {
    codebase: String,
    generated_at: String,
    entity_count: usize,
    page_count: usize,
}

#[derive(Serialize)]
struct PageJson {
    entity_id: String,
    slug: String,
    entity_type: String,
    display_name: String,
    module_path: Option<String>,
    docstring: Option<String>,
    signature: Option<String>,
    outgoing: Vec<String>,   // slugs
    incoming: Vec<String>,   // slugs
    breadcrumb: Vec<String>, // slug path
}

#[derive(Serialize)]
struct EdgeJson {
    source_slug: String,
    target_slug: String,
    edge_type: String,
}

#[derive(Serialize)]
struct QualityReport {
    missing_docs: Vec<String>,
    orphans: Vec<String>,
    high_fanout: Vec<(String, usize)>,
    cycles: Vec<Vec<String>>,
}

fn emit_json(wiki: &WikiJson, output_path: &std::path::Path) {
    let json = serde_json::to_string_pretty(wiki).expect("serialize");
    std::fs::write(output_path, json).expect("write json");
}
```

### 5.5 Gibber (Compact, for AI Consumption)

Emit wiki data in Gibber format for minimal token usage:

```
(wiki-graph
  :codebase "my_project"
  :generated "2026-04-10T00:00:00Z"
  :entities [
    (entity :id "cls_user_service" :type cls :name "UserService"
      :in "mod_src_services"
      :doc "Handles user CRUD operations"
      :extends ["cls_base_service"]
      :methods [
        (fn :name "get_user" :params [(p :n "id" :t "u64")] :ret "Option<User>")
        (fn :name "create_user" :params [(p :n "input" :t "CreateUserInput")] :ret "Result<User>")
      ]
      :calls ["fn_db_query" "fn_validate_input"]
      :called-by ["fn_handle_request" "fn_test_user_service"]
    )
    ; ... more entities
  ]
  :quality (quality
    :missing-docs ["fn_helper_123" "cls_internal_cache"]
    :orphans ["fn_unused_legacy"]
    :high-fanout [("fn_init" 15)]
    :cycles [["mod_a" "mod_b" "mod_c"]]
  )
)
```

### 5.6 mdBook Format

Generate an mdBook-compatible structure:

```rust
struct MdBookEmitter {
    output_dir: PathBuf,
}

impl MdBookEmitter {
    fn emit(&self, wiki: &WikiData) {
        let src_dir = self.output_dir.join("src");
        fs::create_dir_all(&src_dir).expect("create src dir");

        // Generate SUMMARY.md (mdBook's table of contents)
        let summary = self.generate_summary(wiki);
        fs::write(src_dir.join("SUMMARY.md"), summary).expect("write summary");

        // Generate book.toml
        let book_toml = format!(
r#"[book]
title = "{} Documentation"
authors = ["Generated by wiki-graph"]
language = "en"

[output.html]
default-theme = "light"
git-repository-url = ""
"#,
            wiki.codebase_name
        );
        fs::write(self.output_dir.join("book.toml"), book_toml).expect("write book.toml");

        // Emit each page into src/
        for page in &wiki.pages {
            let page_path = src_dir.join(format!("{}.md", page.slug));
            fs::write(&page_path, &page.content).expect("write page");
        }
    }

    fn generate_summary(&self, wiki: &WikiData) -> String {
        let mut summary = String::from("# Summary\n\n");
        summary.push_str("- [Index](index.md)\n");
        summary.push_str("- [Dependency Graph](deps.md)\n\n");

        summary.push_str("# Modules\n\n");
        for page in wiki.pages.iter().filter(|p| p.entity_type == "code_file") {
            summary.push_str(&format!(
                "- [{}]({}.md)\n",
                page.display_name, page.slug
            ));
        }

        summary.push_str("\n# Classes\n\n");
        for page in wiki.pages.iter().filter(|p| p.entity_type == "code_class") {
            summary.push_str(&format!(
                "  - [{}]({}.md)\n",
                page.display_name, page.slug
            ));
        }

        summary.push_str("\n# Quality\n\n");
        summary.push_str("- [Quality Report](quality.md)\n");

        summary
    }
}
```

---

## 6. Incremental Wiki Updates

### 6.1 Only Regenerate Changed Pages

Track which entities have changed since the last generation:

```rust
use std::collections::HashSet;

#[derive(Serialize, Deserialize)]
struct WikiManifest {
    generated_at: String,
    /// entity_id -> content hash
    page_hashes: HashMap<String, String>,
    /// entity_id -> slug
    slug_map: HashMap<String, String>,
}

impl WikiManifest {
    fn load(path: &std::path::Path) -> Option<Self> {
        let data = fs::read_to_string(path).ok()?;
        serde_json::from_str(&data).ok()
    }

    fn save(&self, path: &std::path::Path) {
        let data = serde_json::to_string_pretty(self).expect("serialize manifest");
        fs::write(path, data).expect("write manifest");
    }
}

/// Determine which pages need regeneration.
fn diff_entities(
    old_manifest: &WikiManifest,
    current_entities: &HashMap<String, String>,  // entity_id -> content_hash
) -> IncrementalPlan {
    let old_ids: HashSet<&str> = old_manifest.page_hashes.keys().map(|s| s.as_str()).collect();
    let new_ids: HashSet<&str> = current_entities.keys().map(|s| s.as_str()).collect();

    let added: Vec<String> = new_ids.difference(&old_ids)
        .map(|s| s.to_string())
        .collect();

    let removed: Vec<String> = old_ids.difference(&new_ids)
        .map(|s| s.to_string())
        .collect();

    let modified: Vec<String> = old_ids.intersection(&new_ids)
        .filter(|id| {
            old_manifest.page_hashes.get(**id) != current_entities.get(**id)
        })
        .map(|s| s.to_string())
        .collect();

    IncrementalPlan { added, removed, modified }
}

struct IncrementalPlan {
    added: Vec<String>,
    removed: Vec<String>,
    modified: Vec<String>,
}

impl IncrementalPlan {
    fn needs_regeneration(&self) -> HashSet<String> {
        let mut set: HashSet<String> = HashSet::new();
        set.extend(self.added.iter().cloned());
        set.extend(self.modified.iter().cloned());
        set
    }

    fn stale_pages(&self) -> &[String] {
        &self.removed
    }
}
```

### 6.2 Detect and Clean Stale Pages

```rust
fn clean_stale_pages(
    plan: &IncrementalPlan,
    old_manifest: &WikiManifest,
    output_dir: &std::path::Path,
) {
    for entity_id in plan.stale_pages() {
        if let Some(slug) = old_manifest.slug_map.get(entity_id) {
            let md_path = output_dir.join(format!("{slug}.md"));
            let html_path = output_dir.join(format!("{slug}.html"));

            if md_path.exists() {
                fs::remove_file(&md_path).ok();
            }
            if html_path.exists() {
                fs::remove_file(&html_path).ok();
            }

            eprintln!("Removed stale page: {slug} (entity {entity_id} no longer exists)");
        }
    }
}
```

### 6.3 Diff Two Wiki Snapshots

```rust
/// Compare two wiki manifests and produce a human-readable changelog.
fn generate_changelog(
    old: &WikiManifest,
    new: &WikiManifest,
    display_names: &HashMap<String, String>,
) -> String {
    let plan = diff_entities(old, &new.page_hashes
        .iter()
        .map(|(k, v)| (k.clone(), v.clone()))
        .collect());

    let mut changelog = format!(
        "# Changelog: {} -> {}\n\n",
        old.generated_at, new.generated_at
    );

    if !plan.added.is_empty() {
        changelog.push_str("## Added\n");
        for id in &plan.added {
            let name = display_names.get(id).map(|s| s.as_str()).unwrap_or(id);
            let slug = new.slug_map.get(id).map(|s| s.as_str()).unwrap_or("");
            changelog.push_str(&format!("- [{name}]({slug}.md)\n"));
        }
        changelog.push('\n');
    }

    if !plan.removed.is_empty() {
        changelog.push_str("## Removed\n");
        for id in &plan.removed {
            let name = display_names.get(id).map(|s| s.as_str()).unwrap_or(id);
            changelog.push_str(&format!("- ~~{name}~~\n"));
        }
        changelog.push('\n');
    }

    if !plan.modified.is_empty() {
        changelog.push_str("## Modified\n");
        for id in &plan.modified {
            let name = display_names.get(id).map(|s| s.as_str()).unwrap_or(id);
            let slug = new.slug_map.get(id).map(|s| s.as_str()).unwrap_or("");
            changelog.push_str(&format!("- [{name}]({slug}.md)\n"));
        }
        changelog.push('\n');
    }

    changelog
}
```

---

## 7. Quality Signals

### 7.1 Full Quality Analysis

```rust
#[derive(Debug, Serialize)]
struct QualityAnalysis {
    missing_docs: Vec<QualityIssue>,
    orphan_entities: Vec<QualityIssue>,
    high_fanout: Vec<QualityIssue>,
    circular_deps: Vec<Vec<String>>,
    untested_entities: Vec<QualityIssue>,
    total_entities: usize,
    documented_ratio: f64,
    tested_ratio: f64,
}

#[derive(Debug, Serialize)]
struct QualityIssue {
    entity_id: String,
    display_name: String,
    slug: String,
    detail: String,
}

fn analyze_quality(
    entities: &[EntityData],
    edges: &[(String, String, String)],
    topology: &TopologyAnalyzer,
    slug_registry: &SlugRegistry,
) -> QualityAnalysis {
    let mut missing_docs = Vec::new();
    let mut orphans = Vec::new();
    let mut high_fanout = Vec::new();
    let mut untested = Vec::new();

    let total = entities.len();
    let mut documented = 0usize;
    let mut tested = 0usize;

    for entity in entities {
        let slug = slug_registry.get_slug(&entity.id).unwrap_or("").to_string();

        // Missing docstrings
        if entity.docstring.is_none()
            && (entity.entity_type == "code_class" || entity.entity_type == "code_function")
        {
            missing_docs.push(QualityIssue {
                entity_id: entity.id.clone(),
                display_name: entity.display_name.clone(),
                slug: slug.clone(),
                detail: "No docstring found".to_string(),
            });
        } else if entity.docstring.is_some() {
            documented += 1;
        }

        // Orphan entities (no incoming edges)
        let fan_in = topology.fan_in(&entity.id);
        if fan_in == 0
            && entity.entity_type != "code_file"
            && entity.entity_type != "codebase"
        {
            orphans.push(QualityIssue {
                entity_id: entity.id.clone(),
                display_name: entity.display_name.clone(),
                slug: slug.clone(),
                detail: "No incoming edges (not referenced by anything)".to_string(),
            });
        }

        // High fan-out
        let fo = topology.fan_out(&entity.id);
        if fo > 10 {
            high_fanout.push(QualityIssue {
                entity_id: entity.id.clone(),
                display_name: entity.display_name.clone(),
                slug: slug.clone(),
                detail: format!("Fan-out of {fo} (calls/imports > 10)"),
            });
        }

        // Test coverage: check if any test entity calls this entity
        let has_test = edges.iter().any(|(src, tgt, etype)| {
            tgt == &entity.id
                && etype == "calls"
                && (src.contains("test") || src.contains("spec"))
        });
        if has_test {
            tested += 1;
        } else if entity.entity_type == "code_function" || entity.entity_type == "code_class" {
            untested.push(QualityIssue {
                entity_id: entity.id.clone(),
                display_name: entity.display_name.clone(),
                slug: slug.clone(),
                detail: "No test entity calls this".to_string(),
            });
        }
    }

    let cycles = topology.find_cycles();

    QualityAnalysis {
        missing_docs,
        orphan_entities: orphans,
        high_fanout,
        circular_deps: cycles,
        untested_entities: untested,
        total_entities: total,
        documented_ratio: if total > 0 { documented as f64 / total as f64 } else { 0.0 },
        tested_ratio: if total > 0 { tested as f64 / total as f64 } else { 0.0 },
    }
}
```

### 7.2 Quality Report Page

```markdown
# Quality Report

Generated: {{ timestamp }}

## Summary
| Metric | Value |
|--------|-------|
| Total entities | {{ quality.total_entities }} |
| Documented | {{ (quality.documented_ratio * 100) | round }}% |
| Tested | {{ (quality.tested_ratio * 100) | round }}% |
| Orphans | {{ quality.orphan_entities | length }} |
| High fan-out | {{ quality.high_fanout | length }} |
| Circular deps | {{ quality.circular_deps | length }} cycles |

## Missing Documentation
{% for issue in quality.missing_docs %}
- [{{ issue.display_name }}]({{ issue.slug }}.md) -- {{ issue.detail }}
{% endfor %}

## Orphan Entities
{% for issue in quality.orphan_entities %}
- [{{ issue.display_name }}]({{ issue.slug }}.md) -- {{ issue.detail }}
{% endfor %}

## High Fan-Out Functions
{% for issue in quality.high_fanout %}
- [{{ issue.display_name }}]({{ issue.slug }}.md) -- {{ issue.detail }}
{% endfor %}

## Circular Dependencies
{% for cycle in quality.circular_deps %}
### Cycle {{ loop.index }}
```d2
{% for i in range(cycle | length) %}
{{ cycle[i] }} -> {{ cycle[(i + 1) % cycle | length] }}
{% endfor %}
```
{% endfor %}

## Untested Entities
{% for issue in quality.untested_entities %}
- [{{ issue.display_name }}]({{ issue.slug }}.md) -- {{ issue.detail }}
{% endfor %}
```

---

## 8. Rust Implementation Patterns

### 8.1 Cargo.toml

```toml
[package]
name = "wiki-graph"
version = "0.1.0"
edition = "2021"

[dependencies]
# Template engine
tera = "1"
# Alternatively: handlebars = "5"

# Markdown to HTML
pulldown-cmark = "0.10"

# Serialization
serde = { version = "1", features = ["derive"] }
serde_json = "1"
serde_yaml = "0.9"

# Parallel generation
rayon = "1"

# Regex for auto-linking
regex = "1"

# CLI
clap = { version = "4", features = ["derive"] }

# Error handling
anyhow = "1"
thiserror = "2"

# Hashing for content change detection
sha2 = "0.10"

# Date/time
chrono = "0.4"
```

### 8.2 Project Structure

```
wiki-graph/
  src/
    main.rs              # CLI entry point
    lib.rs               # pub mod declarations
    errors.rs            # WikiError type
    models.rs            # EntityData, EdgeData, WikiData, etc.
    graph/
      mod.rs             # Graph loading and traversal
      topology.rs        # TopologyAnalyzer (cycles, chains, fan-out)
      backlinks.rs       # BacklinkIndex
    slugs.rs             # SlugRegistry, slugify()
    content/
      mod.rs             # Content extraction pipeline
      ast.rs             # From observations/AST
      git.rs             # From git history
      summary.rs         # Module summary generation
      similarity.rs      # Vector similarity (optional)
    templates/
      mod.rs             # Template loading and rendering
      pages.rs           # Page type enum + render dispatch
    linking/
      mod.rs             # Cross-reference engine
      autolink.rs        # Auto-linking entity names in text
      breadcrumb.rs      # Breadcrumb generation
      namespace.rs       # Namespace-aware resolution
    output/
      mod.rs             # Output trait + format dispatch
      markdown.rs        # MarkdownEmitter
      html.rs            # HtmlEmitter
      d2.rs              # D2Generator
      json.rs            # JSON output
      gibber.rs          # Gibber output
      mdbook.rs          # mdBook output
    incremental.rs       # WikiManifest, diff, stale detection
    quality.rs           # QualityAnalysis
  templates/             # Tera template files
    module.md.tera
    class.md.tera
    function.md.tera
    trait.md.tera
    index.md.tera
    quality.md.tera
    deps.md.tera
    changelog.md.tera
  tests/
    integration.rs
```

### 8.3 Template Engine (Tera)

```rust
use tera::{Tera, Context};
use std::path::Path;

struct WikiTemplateEngine {
    tera: Tera,
}

impl WikiTemplateEngine {
    fn new(template_dir: &Path) -> anyhow::Result<Self> {
        let glob = format!("{}/**/*.tera", template_dir.display());
        let tera = Tera::new(&glob)?;
        Ok(Self { tera })
    }

    /// Load templates from embedded strings (no filesystem dependency).
    fn with_embedded() -> anyhow::Result<Self> {
        let mut tera = Tera::default();

        tera.add_raw_templates(vec![
            ("module.md.tera", include_str!("../templates/module.md.tera")),
            ("class.md.tera", include_str!("../templates/class.md.tera")),
            ("function.md.tera", include_str!("../templates/function.md.tera")),
            ("trait.md.tera", include_str!("../templates/trait.md.tera")),
            ("index.md.tera", include_str!("../templates/index.md.tera")),
            ("quality.md.tera", include_str!("../templates/quality.md.tera")),
            ("deps.md.tera", include_str!("../templates/deps.md.tera")),
            ("changelog.md.tera", include_str!("../templates/changelog.md.tera")),
        ])?;

        Ok(Self { tera })
    }

    fn render_page(&self, page: &PageData) -> anyhow::Result<String> {
        let template_name = match page.entity_type.as_str() {
            "code_file" | "code_module" => "module.md.tera",
            "code_class" => "class.md.tera",
            "code_function" => "function.md.tera",
            // Add more as needed
            _ => "module.md.tera",
        };

        let mut ctx = Context::new();
        ctx.insert("page", page);
        ctx.insert("breadcrumb", &page.breadcrumb_md);
        ctx.insert("backlinks", &page.backlinks);

        Ok(self.tera.render(template_name, &ctx)?)
    }
}
```

### 8.4 Parallel Page Generation with Rayon

```rust
use rayon::prelude::*;
use std::sync::Mutex;

struct WikiGenerator {
    templates: WikiTemplateEngine,
    slug_registry: SlugRegistry,
    backlink_index: BacklinkIndex,
    output_dir: PathBuf,
}

impl WikiGenerator {
    /// Generate all pages in parallel.
    fn generate_all(&self, pages: &[PageData]) -> anyhow::Result<WikiManifest> {
        let errors: Mutex<Vec<(String, String)>> = Mutex::new(Vec::new());
        let hashes: Mutex<HashMap<String, String>> = Mutex::new(HashMap::new());
        let slugs: Mutex<HashMap<String, String>> = Mutex::new(HashMap::new());

        pages.par_iter().for_each(|page| {
            match self.generate_page(page) {
                Ok((content_hash, slug)) => {
                    let mut h = hashes.lock().unwrap();
                    h.insert(page.entity_id.clone(), content_hash);
                    let mut s = slugs.lock().unwrap();
                    s.insert(page.entity_id.clone(), slug);
                }
                Err(e) => {
                    let mut errs = errors.lock().unwrap();
                    errs.push((page.entity_id.clone(), e.to_string()));
                }
            }
        });

        let errs = errors.into_inner().unwrap();
        if !errs.is_empty() {
            eprintln!("Errors generating {} pages:", errs.len());
            for (id, err) in &errs {
                eprintln!("  {id}: {err}");
            }
        }

        Ok(WikiManifest {
            generated_at: chrono::Utc::now().to_rfc3339(),
            page_hashes: hashes.into_inner().unwrap(),
            slug_map: slugs.into_inner().unwrap(),
        })
    }

    fn generate_page(&self, page: &PageData) -> anyhow::Result<(String, String)> {
        let content = self.templates.render_page(page)?;

        // Auto-link entity names in the rendered content
        // (Skip this in code blocks to avoid mangling)
        let linked = self.autolink_content(&content, &page.module_path);

        // Compute content hash for incremental builds
        let hash = content_hash(&linked);

        // Write to disk
        let slug = self.slug_registry.get_slug(&page.entity_id)
            .unwrap_or("unknown")
            .to_string();
        let path = self.output_dir.join(format!("{slug}.md"));

        if let Some(parent) = path.parent() {
            std::fs::create_dir_all(parent)?;
        }
        std::fs::write(&path, &linked)?;

        Ok((hash, slug))
    }

    fn autolink_content(&self, content: &str, current_module: &str) -> String {
        // Implementation delegates to linking::autolink module
        content.to_string() // placeholder
    }
}

fn content_hash(content: &str) -> String {
    use sha2::{Sha256, Digest};
    let mut hasher = Sha256::new();
    hasher.update(content.as_bytes());
    format!("{:x}", hasher.finalize())
}
```

### 8.5 Main Entry Point

```rust
use clap::{Parser, Subcommand, ValueEnum};

#[derive(Parser)]
#[command(name = "wiki-graph", version, about = "Generate documentation from code knowledge graphs")]
struct Cli {
    #[command(subcommand)]
    command: Commands,
}

#[derive(Subcommand)]
enum Commands {
    /// Generate wiki from a code-graph database
    Generate {
        /// Path to code-graph database or MCP endpoint
        #[arg(long)]
        graph: String,

        /// Codebase ID
        #[arg(long)]
        codebase_id: usize,

        /// Output directory
        #[arg(long, short, default_value = "wiki")]
        output: PathBuf,

        /// Output format
        #[arg(long, short, default_value = "markdown")]
        format: OutputFormat,

        /// Only regenerate changed pages
        #[arg(long)]
        incremental: bool,

        /// Include quality report
        #[arg(long)]
        quality: bool,

        /// Include D2 diagrams
        #[arg(long)]
        diagrams: bool,

        /// Entity types to include (comma-separated)
        #[arg(long, default_value = "code_file,code_class,code_function")]
        entity_types: String,

        /// File glob filter
        #[arg(long)]
        file_filter: Option<String>,
    },

    /// Diff two wiki snapshots
    Diff {
        /// Path to old manifest
        #[arg(long)]
        old: PathBuf,

        /// Path to new manifest
        #[arg(long)]
        new: PathBuf,

        /// Output changelog path
        #[arg(long, short, default_value = "CHANGELOG.md")]
        output: PathBuf,
    },

    /// Show quality report for a generated wiki
    Quality {
        /// Path to wiki manifest
        #[arg(long)]
        manifest: PathBuf,
    },
}

#[derive(ValueEnum, Clone)]
enum OutputFormat {
    Markdown,
    Html,
    Json,
    Gibber,
    Mdbook,
}

fn main() -> anyhow::Result<()> {
    let cli = Cli::parse();

    match cli.command {
        Commands::Generate {
            graph, codebase_id, output, format,
            incremental, quality, diagrams, entity_types, file_filter,
        } => {
            // 1. Load graph data
            // 2. Build slug registry
            // 3. Build backlink index
            // 4. Build page data for each entity
            // 5. If incremental, load old manifest and compute diff
            // 6. Generate pages (parallel)
            // 7. If quality, run analysis and emit report page
            // 8. If diagrams, generate D2 pages
            // 9. Generate index page
            // 10. Save manifest

            eprintln!("Generated wiki at {}", output.display());
            Ok(())
        }
        Commands::Diff { old, new, output } => {
            let old_manifest = WikiManifest::load(&old)
                .ok_or_else(|| anyhow::anyhow!("Cannot load old manifest"))?;
            let new_manifest = WikiManifest::load(&new)
                .ok_or_else(|| anyhow::anyhow!("Cannot load new manifest"))?;
            let changelog = generate_changelog(&old_manifest, &new_manifest, &HashMap::new());
            std::fs::write(&output, changelog)?;
            eprintln!("Changelog written to {}", output.display());
            Ok(())
        }
        Commands::Quality { manifest } => {
            // Load manifest, run quality analysis, print report
            Ok(())
        }
    }
}
```

### 8.6 Loading from code-graph MCP

When using the code-graph MCP server (as opposed to a local database), the data extraction looks like:

```rust
/// Pseudocode for extracting wiki data from code-graph MCP responses.
/// In practice, you would call these via MCP tool invocations.
///
/// Step 1: Get all entities
///   get_graph(codebase_id=N, entity_types="code_file,code_class,code_function", limit=2000)
///   -> { nodes: [...], edges: [...] }
///
/// Step 2: For each entity that needs detail, call get_entity(entity_id)
///   -> { entity_type, display_name, observations, metadata }
///
/// Step 3: For dependency data, call get_dependencies(entity_id, direction="both")
///   -> { edges: [...], connected_entities: [...] }
///
/// Step 4: For call chains, call get_call_chain(entity_id, depth=2)
///   -> { chain: [...] }
///
/// Step 5: For file structure, call get_file_structure(codebase_id)
///   -> { files: [...] }
///
/// These responses map directly to the EntityData / EdgeData structs.

#[derive(Debug, Clone, Serialize, Deserialize)]
struct GraphResponse {
    nodes: Vec<NodeData>,
    edges: Vec<EdgeData>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct NodeData {
    entity_id: String,
    entity_type: String,
    display_name: String,
    #[serde(default)]
    observations: Vec<String>,
    #[serde(default)]
    metadata: serde_json::Value,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
struct EdgeData {
    source: String,
    target: String,
    edge_type: String,
}

/// Convert MCP graph response into wiki-ready data.
fn graph_response_to_wiki_data(
    response: &GraphResponse,
    codebase_name: &str,
) -> WikiData {
    let slug_registry = {
        let mut reg = SlugRegistry::new();
        for node in &response.nodes {
            reg.register(&node.entity_id, &node.display_name, &node.entity_type);
        }
        reg
    };

    let backlink_index = {
        let mut idx = BacklinkIndex::new();
        for edge in &response.edges {
            idx.add_edge(&edge.source, &edge.target, &edge.edge_type);
        }
        idx
    };

    let containment: HashMap<String, String> = response.edges.iter()
        .filter(|e| e.edge_type == "contains")
        .map(|e| (e.target.clone(), e.source.clone()))
        .collect();

    let display_names: HashMap<String, String> = response.nodes.iter()
        .map(|n| (n.entity_id.clone(), n.display_name.clone()))
        .collect();

    let pages: Vec<PageData> = response.nodes.iter().map(|node| {
        let slug = slug_registry.get_slug(&node.entity_id).unwrap_or("").to_string();
        let content = extract_content_from_node(node);
        let breadcrumb = build_breadcrumb(
            &node.entity_id, &containment, &display_names, &slug_registry
        );
        let breadcrumb_md = render_breadcrumb(&breadcrumb);
        let backlinks = backlink_index.get_backlinks(&node.entity_id);

        let outgoing: Vec<String> = response.edges.iter()
            .filter(|e| e.source == node.entity_id && e.edge_type != "contains")
            .filter_map(|e| slug_registry.get_slug(&e.target).map(|s| s.to_string()))
            .collect();

        let incoming: Vec<String> = response.edges.iter()
            .filter(|e| e.target == node.entity_id && e.edge_type != "contains")
            .filter_map(|e| slug_registry.get_slug(&e.source).map(|s| s.to_string()))
            .collect();

        PageData {
            entity_id: node.entity_id.clone(),
            entity_type: node.entity_type.clone(),
            display_name: node.display_name.clone(),
            slug,
            module_path: containment.get(&node.entity_id).cloned().unwrap_or_default(),
            docstring: content.docstring,
            signature: content.signature,
            breadcrumb_md,
            backlinks: backlinks.iter()
                .map(|(id, etype)| BacklinkEntry {
                    entity_id: id.to_string(),
                    display_name: display_names.get(*id).cloned().unwrap_or_default(),
                    slug: slug_registry.get_slug(id).unwrap_or("").to_string(),
                    edge_type: etype.to_string(),
                })
                .collect(),
            outgoing,
            incoming,
        }
    }).collect();

    WikiData {
        codebase_name: codebase_name.to_string(),
        pages,
    }
}
```

### 8.7 File Generation with PathBuf

```rust
use std::path::{Path, PathBuf};
use std::fs;

/// Safely write a wiki file, creating directories as needed.
fn write_wiki_file(output_dir: &Path, slug: &str, extension: &str, content: &str) -> anyhow::Result<PathBuf> {
    let file_name = format!("{slug}.{extension}");
    let path = output_dir.join(&file_name);

    // Ensure parent directory exists
    if let Some(parent) = path.parent() {
        fs::create_dir_all(parent)?;
    }

    fs::write(&path, content)?;
    Ok(path)
}

/// Write all wiki artifacts to an output directory.
fn write_wiki(
    wiki: &WikiData,
    output_dir: &Path,
    format: &OutputFormat,
    include_quality: bool,
    include_diagrams: bool,
) -> anyhow::Result<Vec<PathBuf>> {
    fs::create_dir_all(output_dir)?;
    let mut written = Vec::new();

    let ext = match format {
        OutputFormat::Markdown | OutputFormat::Mdbook => "md",
        OutputFormat::Html => "html",
        OutputFormat::Json => "json",
        OutputFormat::Gibber => "gibber",
    };

    // Write page files in parallel
    let paths: Vec<PathBuf> = wiki.pages.par_iter()
        .filter_map(|page| {
            write_wiki_file(output_dir, &page.slug, ext, &page.rendered_content).ok()
        })
        .collect();

    written.extend(paths);

    // Write index
    let index_path = write_wiki_file(output_dir, "index", ext, &wiki.index_content)?;
    written.push(index_path);

    // Write quality report
    if include_quality {
        let quality_path = write_wiki_file(output_dir, "quality", ext, &wiki.quality_content)?;
        written.push(quality_path);
    }

    // Write dependency diagram
    if include_diagrams {
        let d2_path = write_wiki_file(output_dir, "deps", "d2", &wiki.deps_d2)?;
        written.push(d2_path);
    }

    Ok(written)
}
```

---

## 9. End-to-End Algorithm

The complete pipeline for generating a wiki from a code knowledge graph:

```
ALGORITHM: GenerateWikiGraph

INPUT:
  graph_source   -- MCP endpoint or database path
  codebase_id    -- numeric ID
  output_dir     -- filesystem path
  format         -- markdown | html | json | gibber | mdbook
  options        -- { incremental, quality, diagrams, entity_types, file_filter }

STEPS:

1. LOAD GRAPH
   response = get_graph(codebase_id, entity_types, file_filter, limit=2000)
   nodes = response.nodes
   edges = response.edges

2. ENRICH ENTITIES (parallel, batched)
   for batch in nodes.chunks(50):
     details = get_entities_batch(batch.entity_ids)
     merge details into nodes (observations, metadata)

3. BUILD INDICES
   slug_registry = new SlugRegistry()
   for node in nodes:
     slug_registry.register(node.id, node.display_name, node.entity_type)

   backlink_index = new BacklinkIndex()
   containment_map = {}
   for edge in edges:
     backlink_index.add_edge(edge.source, edge.target, edge.type)
     if edge.type == "contains":
       containment_map[edge.target] = edge.source

   name_index = group nodes by display_name (for namespace resolution)
   autolink_regex = build from all entity display_names

4. IF INCREMENTAL:
   old_manifest = load WikiManifest from output_dir/.wiki-manifest.json
   current_hashes = compute content hashes for all nodes
   plan = diff_entities(old_manifest, current_hashes)
   nodes_to_generate = plan.needs_regeneration()
   clean_stale_pages(plan, old_manifest, output_dir)

5. BUILD PAGE DATA (parallel)
   pages = nodes_to_generate.par_map(|node| {
     content = extract_content(node)
     breadcrumb = build_breadcrumb(node.id, containment_map, slug_registry)
     backlinks = backlink_index.get_backlinks(node.id)
     outgoing = edges.filter(source == node.id)
     incoming = edges.filter(target == node.id)
     return PageData { ... }
   })

6. RENDER PAGES (parallel)
   templates = WikiTemplateEngine::with_embedded()
   rendered = pages.par_map(|page| {
     raw = templates.render_page(page)
     linked = autolink_text(raw, autolink_regex, slug_map)
     return (page.slug, linked)
   })

7. GENERATE SPECIAL PAGES
   index = render index page (entity counts, module list)
   if options.diagrams:
     deps_d2 = D2Generator::module_deps(module_edges)
     inheritance_d2 = D2Generator::inheritance_tree(extends_edges)
   if options.quality:
     analysis = analyze_quality(entities, edges, topology, slug_registry)
     quality_page = render quality template with analysis

8. EMIT
   write_wiki(rendered_pages, special_pages, output_dir, format)
   if format == mdbook:
     generate SUMMARY.md and book.toml

9. SAVE MANIFEST
   manifest = WikiManifest { generated_at, page_hashes, slug_map }
   manifest.save(output_dir/.wiki-manifest.json)

10. REPORT
    print summary: N pages generated, M stale removed, quality score
```

---

## 10. Using This Skill

### From code-graph MCP Data

```
1. Use structural-probe to get the graph:
   get_graph(codebase_id=N, entity_types="code_file,code_class,code_function")

2. For each entity, build a PageData struct from the response

3. Choose output format and run the pipeline

4. If D2 diagrams are requested, POST to http://localhost:3333/api/render
```

### Quick Generation (No Rust Build Required)

For quick wiki generation without compiling a Rust binary, generate Markdown directly from MCP tool responses:

```
1. get_graph -> iterate nodes
2. For each node: format a markdown page using the templates above
3. Write .md files to output directory
4. Generate index.md with links to all pages
```

### Integration with Existing Skills

- **structural-probe**: Use Stage A (Inventory) to decide which entities to include
- **gibber**: Emit `.gibber` output for compact AI consumption
- **diagram**: Use D2 service for rendering dependency graphs
- **rust-architect**: Follow the project structure and crate patterns when building the Rust binary
