# Knowledge Graphs -- Comprehensive Skill Document

Use this skill when building, querying, or reasoning about knowledge graphs -- whether for code intelligence, semantic search, entity-relationship modeling, or graph-based analytics.

---

## 1. What Is a Knowledge Graph

A knowledge graph is a structured representation of real-world entities and the relationships between them. Formally:

**Definition**: A knowledge graph G = (V, E, L) where:
- V = set of vertices (entities/nodes)
- E = set of edges (relations) where each edge e = (v_source, v_target)
- L = labeling function that assigns types, properties, and labels to both vertices and edges

### 1.1 Triple Stores (Subject-Predicate-Object)

The most fundamental unit is the **triple**:

```
(subject, predicate, object)
```

Examples:
```
(User:42,    "authored",     PR:187)
(PR:187,     "modifies",     File:"src/main.rs")
(File:"src/main.rs", "contains", Function:"parse_config")
(Function:"parse_config", "calls", Function:"validate")
```

A collection of triples forms a graph. Every triple is a directed edge from subject to object, labeled with the predicate.

### 1.2 RDF vs Property Graphs vs Labeled Property Graphs

#### RDF (Resource Description Framework)

- W3C standard
- Everything is a URI or literal
- Triples: `<subject> <predicate> <object> .`
- Queried with SPARQL
- No native property support on edges (use reification or RDF-star)

```turtle
@prefix code: <http://example.org/code/> .
@prefix rel:  <http://example.org/rel/> .

code:parse_config  rel:calls      code:validate .
code:parse_config  rel:returns    code:Config .
code:parse_config  rel:definedIn  code:main_rs .
```

#### Property Graph Model (Neo4j-style)

- Nodes and edges both carry key-value properties
- Edges are first-class with identity, type, direction, and properties
- Queried with Cypher or Gremlin
- More natural for application developers

```
(:Function {name: "parse_config", file: "src/main.rs", line: 42})
  -[:CALLS {count: 3, is_async: false}]->
(:Function {name: "validate", file: "src/config.rs", line: 10})
```

#### Labeled Property Graph (LPG)

Same as property graph but nodes can have **multiple labels**:

```
(:Function:Public:Async {name: "fetch_data"})
```

#### When to Use Which

| Model | Use When |
|-------|----------|
| RDF | Standards compliance, linked data, SPARQL federation, ontology reasoning |
| Property Graph | Application development, code intelligence, flexible schemas |
| Hypergraph | Relations involve 3+ entities (e.g., "User X merged PR Y into Branch Z") |

---

## 2. Data Models

### 2.1 Entity-Relation Model

The simplest mental model. Entities are nodes with typed properties; relations are directed labeled edges.

**Rust representation:**

```rust
use std::collections::HashMap;
use serde::{Serialize, Deserialize};

/// Unique identifier for any entity in the graph
#[derive(Debug, Clone, Hash, Eq, PartialEq, Serialize, Deserialize)]
pub struct EntityId(pub String);

/// An entity (node) in the knowledge graph
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Entity {
    pub id: EntityId,
    pub entity_type: String,       // "function", "class", "module", "file"
    pub label: String,             // human-readable name
    pub properties: HashMap<String, PropertyValue>,
}

/// A relation (edge) in the knowledge graph
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Relation {
    pub source: EntityId,
    pub target: EntityId,
    pub relation_type: String,     // "calls", "imports", "inherits"
    pub properties: HashMap<String, PropertyValue>,
}

/// Flexible property values
#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(untagged)]
pub enum PropertyValue {
    String(String),
    Integer(i64),
    Float(f64),
    Boolean(bool),
    List(Vec<PropertyValue>),
}
```

### 2.2 RDF Triples

```rust
#[derive(Debug, Clone, Serialize, Deserialize)]
pub enum RdfNode {
    Uri(String),          // <http://example.org/func/parse>
    Literal(String),      // "hello"
    TypedLiteral {
        value: String,
        datatype: String, // xsd:integer, xsd:string, etc.
    },
    BlankNode(String),    // _:b0
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Triple {
    pub subject: RdfNode,
    pub predicate: RdfNode,  // always a URI
    pub object: RdfNode,
}

/// A triple store is just a collection of triples with indexes
pub struct TripleStore {
    triples: Vec<Triple>,
    /// Index: subject -> list of triple indices
    spo_index: HashMap<String, Vec<usize>>,
    /// Index: predicate -> list of triple indices
    pos_index: HashMap<String, Vec<usize>>,
    /// Index: object -> list of triple indices
    osp_index: HashMap<String, Vec<usize>>,
}

impl TripleStore {
    pub fn new() -> Self {
        Self {
            triples: Vec::new(),
            spo_index: HashMap::new(),
            pos_index: HashMap::new(),
            osp_index: HashMap::new(),
        }
    }

    pub fn add(&mut self, triple: Triple) {
        let idx = self.triples.len();
        let s_key = triple.subject.key();
        let p_key = triple.predicate.key();
        let o_key = triple.object.key();

        self.spo_index.entry(s_key).or_default().push(idx);
        self.pos_index.entry(p_key).or_default().push(idx);
        self.osp_index.entry(o_key).or_default().push(idx);
        self.triples.push(triple);
    }

    /// Find all triples where subject matches
    pub fn query_by_subject(&self, subject: &str) -> Vec<&Triple> {
        self.spo_index
            .get(subject)
            .map(|indices| indices.iter().map(|&i| &self.triples[i]).collect())
            .unwrap_or_default()
    }

    /// Find all triples matching (subject?, predicate?, object?)
    /// None means "any"
    pub fn query(
        &self,
        subject: Option<&str>,
        predicate: Option<&str>,
        object: Option<&str>,
    ) -> Vec<&Triple> {
        // Use the most selective index
        match (subject, predicate, object) {
            (Some(s), _, _) => self.spo_index.get(s)
                .map(|idxs| idxs.iter()
                    .map(|&i| &self.triples[i])
                    .filter(|t| predicate.map_or(true, |p| t.predicate.key() == p))
                    .filter(|t| object.map_or(true, |o| t.object.key() == o))
                    .collect())
                .unwrap_or_default(),
            (_, Some(p), _) => self.pos_index.get(p)
                .map(|idxs| idxs.iter()
                    .map(|&i| &self.triples[i])
                    .filter(|t| object.map_or(true, |o| t.object.key() == o))
                    .collect())
                .unwrap_or_default(),
            (_, _, Some(o)) => self.osp_index.get(o)
                .map(|idxs| idxs.iter()
                    .map(|&i| &self.triples[i])
                    .collect())
                .unwrap_or_default(),
            _ => self.triples.iter().collect(),
        }
    }
}
```

### 2.3 Property Graph Model (Neo4j-style)

The richest model for application use. Each node and edge has an ID, a type (or multiple labels), and a bag of properties.

```rust
use petgraph::graph::{DiGraph, NodeIndex, EdgeIndex};
use petgraph::Direction;

/// A full property graph built on petgraph
#[derive(Debug, Serialize, Deserialize)]
pub struct PropertyGraph {
    pub graph: DiGraph<Entity, Relation>,
    /// Fast lookup: entity_id -> node index
    id_to_node: HashMap<EntityId, NodeIndex>,
    /// Fast lookup: entity_type -> list of node indices
    type_index: HashMap<String, Vec<NodeIndex>>,
}

impl PropertyGraph {
    pub fn new() -> Self {
        Self {
            graph: DiGraph::new(),
            id_to_node: HashMap::new(),
            type_index: HashMap::new(),
        }
    }

    pub fn add_entity(&mut self, entity: Entity) -> NodeIndex {
        let id = entity.id.clone();
        let entity_type = entity.entity_type.clone();
        let idx = self.graph.add_node(entity);
        self.id_to_node.insert(id, idx);
        self.type_index.entry(entity_type).or_default().push(idx);
        idx
    }

    pub fn add_relation(&mut self, relation: Relation) -> Option<EdgeIndex> {
        let source = self.id_to_node.get(&relation.source)?;
        let target = self.id_to_node.get(&relation.target)?;
        Some(self.graph.add_edge(*source, *target, relation))
    }

    pub fn get_entity(&self, id: &EntityId) -> Option<&Entity> {
        self.id_to_node.get(id).map(|&idx| &self.graph[idx])
    }

    pub fn get_entities_by_type(&self, entity_type: &str) -> Vec<&Entity> {
        self.type_index
            .get(entity_type)
            .map(|indices| indices.iter().map(|&idx| &self.graph[idx]).collect())
            .unwrap_or_default()
    }

    /// Get all outgoing relations from an entity
    pub fn outgoing(&self, id: &EntityId) -> Vec<(&Relation, &Entity)> {
        let Some(&node) = self.id_to_node.get(id) else { return vec![] };
        self.graph
            .edges_directed(node, Direction::Outgoing)
            .map(|edge| {
                let target = &self.graph[edge.target()];
                (edge.weight(), target)
            })
            .collect()
    }

    /// Get all incoming relations to an entity
    pub fn incoming(&self, id: &EntityId) -> Vec<(&Relation, &Entity)> {
        let Some(&node) = self.id_to_node.get(id) else { return vec![] };
        self.graph
            .edges_directed(node, Direction::Incoming)
            .map(|edge| {
                let source = &self.graph[edge.source()];
                (edge.weight(), source)
            })
            .collect()
    }
}
```

### 2.4 Hypergraph Model

A hypergraph allows a single edge to connect more than two nodes. Useful for modeling n-ary relations.

```rust
/// A hyperedge connects an arbitrary set of nodes with roles
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HyperEdge {
    pub id: String,
    pub edge_type: String,
    /// Each participant has a role: e.g., "author", "pr", "branch"
    pub participants: Vec<(String, EntityId)>, // (role, entity_id)
    pub properties: HashMap<String, PropertyValue>,
}

/// Example: "User:alice merged PR:42 into Branch:main at time T"
/// participants: [("actor", User:alice), ("pr", PR:42), ("target", Branch:main)]
/// properties: {"timestamp": "2026-04-10T12:00:00Z"}

pub struct HyperGraph {
    pub entities: HashMap<EntityId, Entity>,
    pub hyperedges: Vec<HyperEdge>,
    /// Index: entity_id -> indices of hyperedges involving that entity
    entity_to_edges: HashMap<EntityId, Vec<usize>>,
}

impl HyperGraph {
    pub fn edges_involving(&self, id: &EntityId) -> Vec<&HyperEdge> {
        self.entity_to_edges
            .get(id)
            .map(|idxs| idxs.iter().map(|&i| &self.hyperedges[i]).collect())
            .unwrap_or_default()
    }
}
```

### 2.5 Model Selection Guide

| Scenario | Recommended Model |
|----------|------------------|
| Code analysis (call graphs, imports) | Property Graph |
| Semantic web / linked data | RDF |
| Simple entity extraction | Entity-Relation |
| Multi-party transactions / events | Hypergraph |
| Build system dependencies | Property Graph or Entity-Relation |
| Ontology-heavy domain (biology, medicine) | RDF + OWL |

---

## 3. Storage Backends

### 3.1 In-Memory

#### petgraph (Rust)

The de facto graph library for Rust. Provides `Graph`, `DiGraph`, `StableGraph`, `GraphMap`.

```rust
// Cargo.toml
// [dependencies]
// petgraph = { version = "0.7", features = ["serde-1"] }
// serde = { version = "1", features = ["derive"] }
// serde_json = "1"

use petgraph::graph::DiGraph;
use petgraph::dot::Dot;

fn demo_petgraph() {
    let mut graph = DiGraph::<&str, &str>::new();
    let main = graph.add_node("main.rs");
    let config = graph.add_node("config.rs");
    let utils = graph.add_node("utils.rs");

    graph.add_edge(main, config, "imports");
    graph.add_edge(main, utils, "imports");
    graph.add_edge(config, utils, "imports");

    // Export to DOT format for Graphviz
    println!("{}", Dot::new(&graph));

    // Node count, edge count
    println!("Nodes: {}, Edges: {}", graph.node_count(), graph.edge_count());
}
```

**StableGraph** -- keeps indices stable across removals (critical for incremental updates):

```rust
use petgraph::stable_graph::StableDiGraph;

let mut g = StableDiGraph::<String, String>::new();
let a = g.add_node("A".into());
let b = g.add_node("B".into());
let c = g.add_node("C".into());
g.add_edge(a, b, "calls".into());
g.add_edge(b, c, "calls".into());

// Remove node B -- indices for A and C remain valid
g.remove_node(b);
assert!(g.contains_node(a)); // still valid
assert!(g.contains_node(c)); // still valid
```

#### networkx (Python)

```python
import networkx as nx

G = nx.DiGraph()

# Add code entities
G.add_node("parse_config", type="function", file="src/main.rs", line=42)
G.add_node("validate", type="function", file="src/config.rs", line=10)
G.add_node("Config", type="struct", file="src/config.rs", line=1)

# Add relations
G.add_edge("parse_config", "validate", relation="calls", count=3)
G.add_edge("parse_config", "Config", relation="returns")

# Query
callees = list(G.successors("parse_config"))  # ["validate", "Config"]
callers = list(G.predecessors("validate"))    # ["parse_config"]

# All functions
functions = [n for n, d in G.nodes(data=True) if d.get("type") == "function"]

# Shortest path
path = nx.shortest_path(G, "parse_config", "validate")

# PageRank
ranks = nx.pagerank(G)
```

### 3.2 JSON-Lines (JSONL)

One JSON object per line. Simple, appendable, streamable, diffable.

**Schema:**

```jsonl
{"type":"entity","id":"fn:parse_config","entity_type":"function","label":"parse_config","properties":{"file":"src/main.rs","line":42,"visibility":"pub"}}
{"type":"entity","id":"fn:validate","entity_type":"function","label":"validate","properties":{"file":"src/config.rs","line":10,"visibility":"pub"}}
{"type":"relation","source":"fn:parse_config","target":"fn:validate","relation_type":"calls","properties":{"count":3}}
```

**Rust reader/writer:**

```rust
use std::io::{BufRead, BufReader, Write, BufWriter};
use std::fs::File;
use serde::{Serialize, Deserialize};

#[derive(Serialize, Deserialize)]
#[serde(tag = "type")]
enum GraphRecord {
    #[serde(rename = "entity")]
    Entity(Entity),
    #[serde(rename = "relation")]
    Relation(Relation),
}

/// Write graph to JSONL
fn write_jsonl(path: &str, entities: &[Entity], relations: &[Relation]) -> std::io::Result<()> {
    let file = File::create(path)?;
    let mut writer = BufWriter::new(file);
    for e in entities {
        let record = GraphRecord::Entity(e.clone());
        serde_json::to_writer(&mut writer, &record)?;
        writer.write_all(b"\n")?;
    }
    for r in relations {
        let record = GraphRecord::Relation(r.clone());
        serde_json::to_writer(&mut writer, &record)?;
        writer.write_all(b"\n")?;
    }
    Ok(())
}

/// Read graph from JSONL
fn read_jsonl(path: &str) -> std::io::Result<(Vec<Entity>, Vec<Relation>)> {
    let file = File::open(path)?;
    let reader = BufReader::new(file);
    let mut entities = Vec::new();
    let mut relations = Vec::new();

    for line in reader.lines() {
        let line = line?;
        if line.trim().is_empty() { continue; }
        match serde_json::from_str::<GraphRecord>(&line) {
            Ok(GraphRecord::Entity(e)) => entities.push(e),
            Ok(GraphRecord::Relation(r)) => relations.push(r),
            Err(err) => eprintln!("Skipping malformed line: {err}"),
        }
    }
    Ok((entities, relations))
}

/// Append a single record (for incremental updates)
fn append_jsonl(path: &str, record: &GraphRecord) -> std::io::Result<()> {
    let mut file = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(path)?;
    serde_json::to_writer(&mut file, record)?;
    file.write_all(b"\n")?;
    Ok(())
}
```

### 3.3 SQLite (Entities + Edges + FTS5)

SQLite is an excellent embedded storage for knowledge graphs. It gives you ACID transactions, full-text search, and SQL querying without a server.

**Schema:**

```sql
-- Core tables
CREATE TABLE entities (
    id          TEXT PRIMARY KEY,
    entity_type TEXT NOT NULL,
    label       TEXT NOT NULL,
    properties  TEXT NOT NULL DEFAULT '{}',  -- JSON blob
    file_path   TEXT,                        -- source file (for code graphs)
    line_start  INTEGER,
    line_end    INTEGER,
    updated_at  TEXT NOT NULL DEFAULT (datetime('now'))
);

CREATE TABLE relations (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id     TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    target_id     TEXT NOT NULL REFERENCES entities(id) ON DELETE CASCADE,
    relation_type TEXT NOT NULL,
    properties    TEXT NOT NULL DEFAULT '{}',
    updated_at    TEXT NOT NULL DEFAULT (datetime('now')),
    UNIQUE(source_id, target_id, relation_type)
);

-- Indexes for fast traversal
CREATE INDEX idx_relations_source ON relations(source_id);
CREATE INDEX idx_relations_target ON relations(target_id);
CREATE INDEX idx_relations_type   ON relations(relation_type);
CREATE INDEX idx_entities_type    ON entities(entity_type);
CREATE INDEX idx_entities_file    ON entities(file_path);

-- Full-text search on entity labels and properties
CREATE VIRTUAL TABLE entities_fts USING fts5(
    label,
    entity_type,
    properties,
    content='entities',
    content_rowid='rowid'
);

-- Triggers to keep FTS in sync
CREATE TRIGGER entities_ai AFTER INSERT ON entities BEGIN
    INSERT INTO entities_fts(rowid, label, entity_type, properties)
    VALUES (new.rowid, new.label, new.entity_type, new.properties);
END;

CREATE TRIGGER entities_ad AFTER DELETE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, label, entity_type, properties)
    VALUES ('delete', old.rowid, old.label, old.entity_type, old.properties);
END;

CREATE TRIGGER entities_au AFTER UPDATE ON entities BEGIN
    INSERT INTO entities_fts(entities_fts, rowid, label, entity_type, properties)
    VALUES ('delete', old.rowid, old.label, old.entity_type, old.properties);
    INSERT INTO entities_fts(rowid, label, entity_type, properties)
    VALUES (new.rowid, new.label, new.entity_type, new.properties);
END;

-- Watermark table for incremental re-indexing
CREATE TABLE file_watermarks (
    file_path    TEXT PRIMARY KEY,
    content_hash TEXT NOT NULL,
    indexed_at   TEXT NOT NULL DEFAULT (datetime('now'))
);
```

**Common queries:**

```sql
-- 1-hop neighbors (outgoing)
SELECT e.* FROM entities e
JOIN relations r ON r.target_id = e.id
WHERE r.source_id = 'fn:parse_config';

-- 1-hop neighbors (incoming)
SELECT e.* FROM entities e
JOIN relations r ON r.source_id = e.id
WHERE r.target_id = 'fn:validate';

-- All callers of a function (transitive, via recursive CTE)
WITH RECURSIVE callers(id, depth) AS (
    SELECT source_id, 1 FROM relations
    WHERE target_id = 'fn:validate' AND relation_type = 'calls'
    UNION ALL
    SELECT r.source_id, c.depth + 1
    FROM relations r JOIN callers c ON r.target_id = c.id
    WHERE r.relation_type = 'calls' AND c.depth < 10
)
SELECT DISTINCT e.*, c.depth FROM entities e
JOIN callers c ON e.id = c.id
ORDER BY c.depth;

-- Full-text search
SELECT * FROM entities WHERE id IN (
    SELECT id FROM entities_fts WHERE entities_fts MATCH 'parse*'
);

-- Most connected entities (highest degree)
SELECT e.id, e.label, e.entity_type,
    (SELECT COUNT(*) FROM relations WHERE source_id = e.id) as out_degree,
    (SELECT COUNT(*) FROM relations WHERE target_id = e.id) as in_degree
FROM entities e
ORDER BY (out_degree + in_degree) DESC
LIMIT 20;

-- All entities in a file
SELECT * FROM entities WHERE file_path = 'src/main.rs'
ORDER BY line_start;

-- Entities by type breakdown
SELECT entity_type, COUNT(*) as cnt
FROM entities GROUP BY entity_type ORDER BY cnt DESC;
```

**Rust with rusqlite:**

```rust
// Cargo.toml
// [dependencies]
// rusqlite = { version = "0.31", features = ["bundled"] }

use rusqlite::{Connection, params};

pub struct SqliteGraphStore {
    conn: Connection,
}

impl SqliteGraphStore {
    pub fn open(path: &str) -> rusqlite::Result<Self> {
        let conn = Connection::open(path)?;
        conn.execute_batch("PRAGMA journal_mode=WAL; PRAGMA foreign_keys=ON;")?;
        // Create tables (run the schema above)
        conn.execute_batch(include_str!("schema.sql"))?;
        Ok(Self { conn })
    }

    pub fn upsert_entity(&self, entity: &Entity) -> rusqlite::Result<()> {
        self.conn.execute(
            "INSERT INTO entities (id, entity_type, label, properties, file_path, line_start)
             VALUES (?1, ?2, ?3, ?4, ?5, ?6)
             ON CONFLICT(id) DO UPDATE SET
                entity_type = excluded.entity_type,
                label = excluded.label,
                properties = excluded.properties,
                file_path = excluded.file_path,
                line_start = excluded.line_start,
                updated_at = datetime('now')",
            params![
                entity.id.0,
                entity.entity_type,
                entity.label,
                serde_json::to_string(&entity.properties).unwrap(),
                entity.properties.get("file").map(|v| format!("{:?}", v)),
                entity.properties.get("line").and_then(|v| match v {
                    PropertyValue::Integer(n) => Some(*n),
                    _ => None,
                }),
            ],
        )?;
        Ok(())
    }

    pub fn upsert_relation(&self, rel: &Relation) -> rusqlite::Result<()> {
        self.conn.execute(
            "INSERT INTO relations (source_id, target_id, relation_type, properties)
             VALUES (?1, ?2, ?3, ?4)
             ON CONFLICT(source_id, target_id, relation_type) DO UPDATE SET
                properties = excluded.properties,
                updated_at = datetime('now')",
            params![
                rel.source.0,
                rel.target.0,
                rel.relation_type,
                serde_json::to_string(&rel.properties).unwrap(),
            ],
        )?;
        Ok(())
    }

    /// Get 1-hop outgoing neighbors
    pub fn outgoing_neighbors(
        &self,
        entity_id: &str,
        relation_type: Option<&str>,
    ) -> rusqlite::Result<Vec<(String, String, String)>> {
        let mut stmt = if let Some(rt) = relation_type {
            let mut s = self.conn.prepare(
                "SELECT e.id, e.label, r.relation_type
                 FROM entities e JOIN relations r ON r.target_id = e.id
                 WHERE r.source_id = ?1 AND r.relation_type = ?2"
            )?;
            let rows = s.query_map(params![entity_id, rt], |row| {
                Ok((row.get(0)?, row.get(1)?, row.get(2)?))
            })?.collect::<Result<Vec<_>, _>>()?;
            return Ok(rows);
        } else {
            self.conn.prepare(
                "SELECT e.id, e.label, r.relation_type
                 FROM entities e JOIN relations r ON r.target_id = e.id
                 WHERE r.source_id = ?1"
            )?
        };
        let rows = stmt.query_map(params![entity_id], |row| {
            Ok((row.get(0)?, row.get(1)?, row.get(2)?))
        })?.collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// Full-text search
    pub fn search(&self, query: &str) -> rusqlite::Result<Vec<Entity>> {
        let mut stmt = self.conn.prepare(
            "SELECT e.id, e.entity_type, e.label, e.properties
             FROM entities e
             WHERE e.id IN (
                 SELECT id FROM entities_fts WHERE entities_fts MATCH ?1
             )
             LIMIT 50"
        )?;
        let rows = stmt.query_map(params![query], |row| {
            let props_str: String = row.get(3)?;
            let properties: HashMap<String, PropertyValue> =
                serde_json::from_str(&props_str).unwrap_or_default();
            Ok(Entity {
                id: EntityId(row.get(0)?),
                entity_type: row.get(1)?,
                label: row.get(2)?,
                properties,
            })
        })?.collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// Transitive closure: all entities reachable from `start` via `relation_type`
    pub fn transitive_closure(
        &self,
        start: &str,
        relation_type: &str,
        max_depth: u32,
    ) -> rusqlite::Result<Vec<(String, u32)>> {
        let mut stmt = self.conn.prepare(&format!(
            "WITH RECURSIVE reachable(id, depth) AS (
                SELECT target_id, 1 FROM relations
                WHERE source_id = ?1 AND relation_type = ?2
                UNION ALL
                SELECT r.target_id, re.depth + 1
                FROM relations r JOIN reachable re ON r.source_id = re.id
                WHERE r.relation_type = ?2 AND re.depth < {max_depth}
            )
            SELECT DISTINCT id, MIN(depth) FROM reachable GROUP BY id"
        ))?;
        let rows = stmt.query_map(params![start, relation_type], |row| {
            Ok((row.get(0)?, row.get(1)?))
        })?.collect::<Result<Vec<_>, _>>()?;
        Ok(rows)
    }

    /// Delete all entities and relations from a specific file
    pub fn invalidate_file(&self, file_path: &str) -> rusqlite::Result<usize> {
        // CASCADE will delete relations automatically
        let count = self.conn.execute(
            "DELETE FROM entities WHERE file_path = ?1",
            params![file_path],
        )?;
        Ok(count)
    }

    /// Batch operations in a transaction
    pub fn batch_upsert(
        &mut self,
        entities: &[Entity],
        relations: &[Relation],
    ) -> rusqlite::Result<()> {
        let tx = self.conn.transaction()?;
        for e in entities {
            tx.execute(
                "INSERT INTO entities (id, entity_type, label, properties)
                 VALUES (?1, ?2, ?3, ?4)
                 ON CONFLICT(id) DO UPDATE SET
                    entity_type = excluded.entity_type,
                    label = excluded.label,
                    properties = excluded.properties,
                    updated_at = datetime('now')",
                params![
                    e.id.0, e.entity_type, e.label,
                    serde_json::to_string(&e.properties).unwrap(),
                ],
            )?;
        }
        for r in relations {
            tx.execute(
                "INSERT INTO relations (source_id, target_id, relation_type, properties)
                 VALUES (?1, ?2, ?3, ?4)
                 ON CONFLICT(source_id, target_id, relation_type) DO UPDATE SET
                    properties = excluded.properties,
                    updated_at = datetime('now')",
                params![
                    r.source.0, r.target.0, r.relation_type,
                    serde_json::to_string(&r.properties).unwrap(),
                ],
            )?;
        }
        tx.commit()?;
        Ok(())
    }
}
```

### 3.4 Embedded Graph Databases

| DB | Language | Notes |
|----|----------|-------|
| **Kuzu** | C++ with Rust/Python bindings | Embedded OLAP graph DB, Cypher support, columnar storage |
| **DuckDB** | C++ with Rust bindings | SQL OLAP DB with graph extension, great for analytics |
| **sled** | Pure Rust | Embedded KV store, build graph on top of key patterns |
| **redb** | Pure Rust | Simpler embedded KV, ACID, good for small graphs |

**sled-based graph storage pattern:**

```rust
use sled::Db;

/// Key schema for graph storage in sled:
/// "e:{id}"                -> serialized Entity
/// "r:{source}:{type}:{target}" -> serialized Relation properties
/// "ri:{target}:{type}:{source}" -> "" (reverse index, value unused)
/// "t:{entity_type}:{id}" -> "" (type index)

pub struct SledGraphStore {
    db: Db,
}

impl SledGraphStore {
    pub fn open(path: &str) -> sled::Result<Self> {
        let db = sled::open(path)?;
        Ok(Self { db })
    }

    pub fn put_entity(&self, entity: &Entity) -> sled::Result<()> {
        let key = format!("e:{}", entity.id.0);
        let val = serde_json::to_vec(entity).unwrap();
        self.db.insert(key.as_bytes(), val)?;

        // Type index
        let type_key = format!("t:{}:{}", entity.entity_type, entity.id.0);
        self.db.insert(type_key.as_bytes(), b"")?;
        Ok(())
    }

    pub fn put_relation(&self, rel: &Relation) -> sled::Result<()> {
        let key = format!("r:{}:{}:{}", rel.source.0, rel.relation_type, rel.target.0);
        let val = serde_json::to_vec(&rel.properties).unwrap();
        self.db.insert(key.as_bytes(), val)?;

        // Reverse index for incoming queries
        let rev_key = format!("ri:{}:{}:{}", rel.target.0, rel.relation_type, rel.source.0);
        self.db.insert(rev_key.as_bytes(), b"")?;
        Ok(())
    }

    /// Scan all outgoing relations from an entity
    pub fn outgoing(&self, entity_id: &str) -> Vec<(String, String)> {
        let prefix = format!("r:{}:", entity_id);
        self.db
            .scan_prefix(prefix.as_bytes())
            .filter_map(|r| r.ok())
            .filter_map(|(key, _val)| {
                let key_str = String::from_utf8(key.to_vec()).ok()?;
                let parts: Vec<&str> = key_str.splitn(4, ':').collect();
                // parts = ["r", source, relation_type, target]
                if parts.len() == 4 {
                    Some((parts[2].to_string(), parts[3].to_string()))
                } else {
                    None
                }
            })
            .collect()
    }

    /// Get all entities of a given type
    pub fn entities_by_type(&self, entity_type: &str) -> Vec<Entity> {
        let prefix = format!("t:{}:", entity_type);
        self.db
            .scan_prefix(prefix.as_bytes())
            .filter_map(|r| r.ok())
            .filter_map(|(key, _)| {
                let key_str = String::from_utf8(key.to_vec()).ok()?;
                let entity_id = key_str.strip_prefix(&format!("t:{}:", entity_type))?;
                let entity_key = format!("e:{}", entity_id);
                let val = self.db.get(entity_key.as_bytes()).ok()??;
                serde_json::from_slice(&val).ok()
            })
            .collect()
    }
}
```

### 3.5 Full Graph Databases

| Database | Query Language | Strengths |
|----------|---------------|-----------|
| **Neo4j** | Cypher | Most mature, rich ecosystem, APOC library |
| **ArangoDB** | AQL | Multi-model (document + graph + key-value) |
| **TigerGraph** | GSQL | Best for massive scale, real-time deep-link analytics |
| **JanusGraph** | Gremlin | Distributed, pluggable backends (Cassandra, HBase) |

**Neo4j Cypher examples for code graphs:**

```cypher
// Create a code entity
CREATE (:Function {name: 'parse_config', file: 'src/main.rs', line: 42, visibility: 'pub'})

// Create a call relationship
MATCH (caller:Function {name: 'main'}), (callee:Function {name: 'parse_config'})
CREATE (caller)-[:CALLS {is_async: false}]->(callee)

// Find all functions called by main (1-hop)
MATCH (f:Function {name: 'main'})-[:CALLS]->(callee:Function)
RETURN callee.name, callee.file

// Find full call chain (variable depth)
MATCH path = (f:Function {name: 'main'})-[:CALLS*1..5]->(callee:Function)
RETURN [n IN nodes(path) | n.name] AS call_chain

// Impact analysis: what is affected if parse_config changes?
MATCH (changed:Function {name: 'parse_config'})<-[:CALLS*1..10]-(affected)
RETURN DISTINCT affected.name, affected.file

// Dead code: functions that are never called
MATCH (f:Function)
WHERE NOT ()-[:CALLS]->(f) AND f.name <> 'main'
RETURN f.name, f.file

// Most called functions
MATCH ()-[c:CALLS]->(f:Function)
RETURN f.name, COUNT(c) AS call_count
ORDER BY call_count DESC LIMIT 10
```

---

## 4. Graph Algorithms

### 4.1 BFS / DFS Traversal

```rust
use petgraph::graph::{DiGraph, NodeIndex};
use petgraph::visit::Bfs;
use petgraph::Direction;
use std::collections::{HashSet, VecDeque};

/// BFS traversal using petgraph's built-in iterator
fn bfs_petgraph(graph: &DiGraph<String, String>, start: NodeIndex) -> Vec<NodeIndex> {
    let mut bfs = Bfs::new(&graph, start);
    let mut visited = Vec::new();
    while let Some(node) = bfs.next(&graph) {
        visited.push(node);
    }
    visited
}

/// Manual BFS with depth tracking (useful for n-hop queries)
fn bfs_with_depth(
    graph: &DiGraph<String, String>,
    start: NodeIndex,
    max_depth: usize,
) -> Vec<(NodeIndex, usize)> {
    let mut visited = HashSet::new();
    let mut queue = VecDeque::new();
    let mut result = Vec::new();

    visited.insert(start);
    queue.push_back((start, 0));

    while let Some((node, depth)) = queue.pop_front() {
        result.push((node, depth));
        if depth >= max_depth {
            continue;
        }
        for neighbor in graph.neighbors_directed(node, Direction::Outgoing) {
            if visited.insert(neighbor) {
                queue.push_back((neighbor, depth + 1));
            }
        }
    }
    result
}

/// DFS with pre/post ordering (useful for cycle detection, topo sort)
fn dfs_with_ordering(
    graph: &DiGraph<String, String>,
    start: NodeIndex,
) -> (Vec<NodeIndex>, Vec<NodeIndex>) {
    let mut visited = HashSet::new();
    let mut pre_order = Vec::new();
    let mut post_order = Vec::new();

    fn visit(
        graph: &DiGraph<String, String>,
        node: NodeIndex,
        visited: &mut HashSet<NodeIndex>,
        pre: &mut Vec<NodeIndex>,
        post: &mut Vec<NodeIndex>,
    ) {
        if !visited.insert(node) { return; }
        pre.push(node);
        for neighbor in graph.neighbors_directed(node, Direction::Outgoing) {
            visit(graph, neighbor, visited, pre, post);
        }
        post.push(node);
    }

    visit(graph, start, &mut visited, &mut pre_order, &mut post_order);
    (pre_order, post_order)
}
```

### 4.2 Shortest Path

```rust
use petgraph::algo::{dijkstra, astar};
use petgraph::graph::{DiGraph, NodeIndex};

/// Dijkstra: shortest paths from a source to all reachable nodes
fn shortest_paths_from(
    graph: &DiGraph<String, f64>,
    source: NodeIndex,
) -> HashMap<NodeIndex, f64> {
    dijkstra(graph, source, None, |edge| *edge.weight())
}

/// A*: shortest path between two specific nodes (faster than Dijkstra for single target)
fn shortest_path_astar(
    graph: &DiGraph<String, f64>,
    source: NodeIndex,
    target: NodeIndex,
) -> Option<(f64, Vec<NodeIndex>)> {
    astar(
        graph,
        source,
        |n| n == target,       // goal check
        |e| *e.weight(),       // edge cost
        |_| 0.0,               // heuristic (0 = Dijkstra)
    )
}

/// Unweighted shortest path (BFS-based) -- for call chain distance
fn shortest_call_chain(
    graph: &DiGraph<String, String>,
    source: NodeIndex,
    target: NodeIndex,
) -> Option<Vec<NodeIndex>> {
    let mut visited = HashSet::new();
    let mut queue = VecDeque::new();
    let mut parent: HashMap<NodeIndex, NodeIndex> = HashMap::new();

    visited.insert(source);
    queue.push_back(source);

    while let Some(node) = queue.pop_front() {
        if node == target {
            // Reconstruct path
            let mut path = vec![target];
            let mut current = target;
            while let Some(&prev) = parent.get(&current) {
                path.push(prev);
                current = prev;
            }
            path.reverse();
            return Some(path);
        }
        for neighbor in graph.neighbors(node) {
            if visited.insert(neighbor) {
                parent.insert(neighbor, node);
                queue.push_back(neighbor);
            }
        }
    }
    None
}
```

### 4.3 PageRank

Identifies the most "important" entities in the graph. Useful for finding core abstractions, critical functions, key modules.

```rust
use petgraph::graph::DiGraph;

/// PageRank implementation for knowledge graphs
fn pagerank(
    graph: &DiGraph<String, String>,
    damping: f64,       // typically 0.85
    iterations: usize,  // typically 20-100
) -> HashMap<NodeIndex, f64> {
    let n = graph.node_count() as f64;
    let mut ranks: HashMap<NodeIndex, f64> = graph
        .node_indices()
        .map(|node| (node, 1.0 / n))
        .collect();

    for _ in 0..iterations {
        let mut new_ranks: HashMap<NodeIndex, f64> = HashMap::new();
        let mut dangling_sum = 0.0;

        // Identify dangling nodes (no outgoing edges)
        for node in graph.node_indices() {
            if graph.neighbors_directed(node, Direction::Outgoing).count() == 0 {
                dangling_sum += ranks[&node];
            }
        }

        for node in graph.node_indices() {
            let mut rank_sum = 0.0;

            // Sum contributions from incoming neighbors
            for source in graph.neighbors_directed(node, Direction::Incoming) {
                let out_degree = graph
                    .neighbors_directed(source, Direction::Outgoing)
                    .count() as f64;
                rank_sum += ranks[&source] / out_degree;
            }

            // Add dangling node contribution (distributed equally)
            let new_rank = (1.0 - damping) / n
                + damping * (rank_sum + dangling_sum / n);
            new_ranks.insert(node, new_rank);
        }
        ranks = new_ranks;
    }
    ranks
}

/// Usage: Find the most important functions in a codebase
fn find_core_functions(graph: &DiGraph<String, String>) -> Vec<(String, f64)> {
    let ranks = pagerank(graph, 0.85, 50);
    let mut ranked: Vec<_> = ranks
        .into_iter()
        .map(|(node, rank)| (graph[node].clone(), rank))
        .collect();
    ranked.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    ranked
}
```

### 4.4 Community Detection

#### Louvain Algorithm

Finds clusters of tightly connected nodes. Useful for identifying modules, subsystems, or logical groupings.

```rust
use std::collections::HashMap;
use petgraph::graph::DiGraph;

/// Simplified Louvain community detection
/// Returns: node -> community_id mapping
fn louvain_communities(
    graph: &DiGraph<String, String>,
) -> HashMap<NodeIndex, usize> {
    let mut communities: HashMap<NodeIndex, usize> = graph
        .node_indices()
        .enumerate()
        .map(|(i, node)| (node, i))
        .collect();

    let total_edges = graph.edge_count() as f64;
    if total_edges == 0.0 { return communities; }

    let mut improved = true;
    while improved {
        improved = false;
        for node in graph.node_indices() {
            let current_community = communities[&node];

            // Count edges to each neighboring community
            let mut community_edges: HashMap<usize, usize> = HashMap::new();
            for neighbor in graph.neighbors_undirected(node) {
                let neighbor_community = communities[&neighbor];
                *community_edges.entry(neighbor_community).or_insert(0) += 1;
            }

            // Find the community with the most connections
            if let Some((&best_community, &best_count)) = community_edges
                .iter()
                .max_by_key(|(_, &count)| count)
            {
                let current_count = community_edges
                    .get(&current_community)
                    .copied()
                    .unwrap_or(0);

                if best_count > current_count && best_community != current_community {
                    communities.insert(node, best_community);
                    improved = true;
                }
            }
        }
    }

    // Compact community IDs to be sequential
    let unique: Vec<usize> = {
        let mut s: Vec<_> = communities.values().copied().collect();
        s.sort(); s.dedup(); s
    };
    let remap: HashMap<usize, usize> = unique
        .into_iter()
        .enumerate()
        .map(|(new, old)| (old, new))
        .collect();

    communities
        .into_iter()
        .map(|(node, comm)| (node, remap[&comm]))
        .collect()
}
```

#### Label Propagation

Faster but less stable than Louvain.

```rust
use rand::seq::SliceRandom;

fn label_propagation(
    graph: &DiGraph<String, String>,
    max_iterations: usize,
) -> HashMap<NodeIndex, usize> {
    let mut labels: HashMap<NodeIndex, usize> = graph
        .node_indices()
        .enumerate()
        .map(|(i, n)| (n, i))
        .collect();

    let mut nodes: Vec<NodeIndex> = graph.node_indices().collect();
    let mut rng = rand::thread_rng();

    for _ in 0..max_iterations {
        let mut changed = false;
        nodes.shuffle(&mut rng);

        for &node in &nodes {
            let mut label_counts: HashMap<usize, usize> = HashMap::new();
            for neighbor in graph.neighbors_undirected(node) {
                *label_counts.entry(labels[&neighbor]).or_insert(0) += 1;
            }
            if let Some((&best_label, _)) = label_counts.iter().max_by_key(|(_, &c)| c) {
                if labels[&node] != best_label {
                    labels.insert(node, best_label);
                    changed = true;
                }
            }
        }
        if !changed { break; }
    }
    labels
}
```

### 4.5 Cycle Detection

Critical for dependency analysis -- cycles in imports or calls indicate potential design issues.

```rust
use petgraph::algo::is_cyclic_directed;
use petgraph::graph::DiGraph;

/// Simple cycle check using petgraph
fn has_cycles(graph: &DiGraph<String, String>) -> bool {
    is_cyclic_directed(graph)
}

/// Find all cycles (returns each cycle as a list of nodes)
fn find_cycles(graph: &DiGraph<String, String>) -> Vec<Vec<NodeIndex>> {
    let mut cycles = Vec::new();
    let mut visited = HashSet::new();
    let mut on_stack = HashSet::new();
    let mut stack = Vec::new();

    for start in graph.node_indices() {
        if visited.contains(&start) { continue; }
        find_cycles_dfs(graph, start, &mut visited, &mut on_stack, &mut stack, &mut cycles);
    }
    cycles
}

fn find_cycles_dfs(
    graph: &DiGraph<String, String>,
    node: NodeIndex,
    visited: &mut HashSet<NodeIndex>,
    on_stack: &mut HashSet<NodeIndex>,
    stack: &mut Vec<NodeIndex>,
    cycles: &mut Vec<Vec<NodeIndex>>,
) {
    visited.insert(node);
    on_stack.insert(node);
    stack.push(node);

    for neighbor in graph.neighbors(node) {
        if !visited.contains(&neighbor) {
            find_cycles_dfs(graph, neighbor, visited, on_stack, stack, cycles);
        } else if on_stack.contains(&neighbor) {
            // Found a cycle -- extract it
            let cycle_start = stack.iter().position(|&n| n == neighbor).unwrap();
            let cycle: Vec<NodeIndex> = stack[cycle_start..].to_vec();
            cycles.push(cycle);
        }
    }

    stack.pop();
    on_stack.remove(&node);
}

/// Find strongly connected components (each SCC with >1 node is a cycle group)
fn find_sccs(graph: &DiGraph<String, String>) -> Vec<Vec<NodeIndex>> {
    petgraph::algo::kosaraju_scc(graph)
        .into_iter()
        .filter(|scc| scc.len() > 1)
        .collect()
}
```

### 4.6 Topological Sort

For dependency ordering -- build order, initialization order, migration order.

```rust
use petgraph::algo::toposort;

/// Topological sort (returns error if graph has cycles)
fn dependency_order(graph: &DiGraph<String, String>) -> Result<Vec<NodeIndex>, ()> {
    toposort(graph, None).map_err(|_cycle| ())
}

/// Topological sort with cycle-breaking (for real-world codebases that have cycles)
fn dependency_order_with_cycle_breaking(
    graph: &mut DiGraph<String, String>,
) -> Vec<NodeIndex> {
    // First, find SCCs
    let sccs = petgraph::algo::kosaraju_scc(&*graph);

    // For each SCC with multiple nodes, remove the edge with lowest weight
    // (or an arbitrary back edge) to break the cycle
    for scc in &sccs {
        if scc.len() <= 1 { continue; }
        let scc_set: HashSet<_> = scc.iter().copied().collect();

        // Find a back edge to remove
        'outer: for &node in scc {
            for edge in graph.edges(node) {
                if scc_set.contains(&edge.target()) {
                    let edge_id = edge.id();
                    graph.remove_edge(edge_id);
                    break 'outer;
                }
            }
        }
    }

    // Now the graph should be DAG-ifiable
    toposort(&*graph, None).unwrap_or_else(|_| graph.node_indices().collect())
}

/// Kahn's algorithm -- also gives you "layers" for parallel execution
fn topological_layers(graph: &DiGraph<String, String>) -> Vec<Vec<NodeIndex>> {
    let mut in_degree: HashMap<NodeIndex, usize> = HashMap::new();
    for node in graph.node_indices() {
        in_degree.insert(node, graph.neighbors_directed(node, Direction::Incoming).count());
    }

    let mut layers = Vec::new();
    let mut remaining: HashSet<NodeIndex> = graph.node_indices().collect();

    while !remaining.is_empty() {
        // Find all nodes with in-degree 0 (within remaining)
        let layer: Vec<NodeIndex> = remaining
            .iter()
            .copied()
            .filter(|&n| in_degree[&n] == 0)
            .collect();

        if layer.is_empty() {
            // Cycle detected -- dump remaining as final layer
            layers.push(remaining.into_iter().collect());
            break;
        }

        // Remove this layer and update in-degrees
        for &node in &layer {
            remaining.remove(&node);
            for neighbor in graph.neighbors_directed(node, Direction::Outgoing) {
                if let Some(deg) = in_degree.get_mut(&neighbor) {
                    *deg = deg.saturating_sub(1);
                }
            }
        }
        layers.push(layer);
    }
    layers
}
```

### 4.7 Subgraph Extraction

Extract a portion of the graph around a point of interest.

```rust
/// Extract the subgraph within N hops of a starting node
fn extract_subgraph(
    graph: &DiGraph<String, String>,
    center: NodeIndex,
    max_hops: usize,
) -> DiGraph<String, String> {
    let nodes_with_depth = bfs_with_depth(graph, center, max_hops);
    let node_set: HashSet<NodeIndex> = nodes_with_depth.iter().map(|(n, _)| *n).collect();

    let mut subgraph = DiGraph::new();
    let mut node_map: HashMap<NodeIndex, NodeIndex> = HashMap::new();

    for &(node, _) in &nodes_with_depth {
        let new_idx = subgraph.add_node(graph[node].clone());
        node_map.insert(node, new_idx);
    }

    for &(node, _) in &nodes_with_depth {
        for edge in graph.edges(node) {
            if node_set.contains(&edge.target()) {
                subgraph.add_edge(
                    node_map[&node],
                    node_map[&edge.target()],
                    edge.weight().clone(),
                );
            }
        }
    }
    subgraph
}

/// Extract subgraph induced by a set of entity types
fn extract_by_types(
    graph: &PropertyGraph,
    entity_types: &[&str],
    relation_types: &[&str],
) -> PropertyGraph {
    let mut sub = PropertyGraph::new();
    let type_set: HashSet<&str> = entity_types.iter().copied().collect();
    let rel_set: HashSet<&str> = relation_types.iter().copied().collect();

    // Add matching entities
    for node in graph.graph.node_indices() {
        let entity = &graph.graph[node];
        if type_set.contains(entity.entity_type.as_str()) {
            sub.add_entity(entity.clone());
        }
    }

    // Add matching relations (only where both endpoints exist)
    for edge in graph.graph.edge_indices() {
        if let Some((s, t)) = graph.graph.edge_endpoints(edge) {
            let rel = &graph.graph[edge];
            if rel_set.contains(rel.relation_type.as_str()) {
                let source = &graph.graph[s];
                let target = &graph.graph[t];
                if type_set.contains(source.entity_type.as_str())
                    && type_set.contains(target.entity_type.as_str())
                {
                    sub.add_relation(rel.clone());
                }
            }
        }
    }
    sub
}
```

### 4.8 Connected Components

```rust
use petgraph::algo::connected_components;

/// Count connected components (treats graph as undirected)
fn count_components(graph: &DiGraph<String, String>) -> usize {
    connected_components(graph)
}

/// Get strongly connected components (for directed graphs)
fn strongly_connected(graph: &DiGraph<String, String>) -> Vec<Vec<NodeIndex>> {
    petgraph::algo::kosaraju_scc(graph)
}

/// Find isolated nodes (no edges at all)
fn isolated_nodes(graph: &DiGraph<String, String>) -> Vec<NodeIndex> {
    graph.node_indices()
        .filter(|&n| {
            graph.neighbors_directed(n, Direction::Outgoing).count() == 0
                && graph.neighbors_directed(n, Direction::Incoming).count() == 0
        })
        .collect()
}
```

---

## 5. Query Patterns

### 5.1 Neighbor Queries (1-hop, n-hop)

```rust
impl PropertyGraph {
    /// 1-hop: direct neighbors
    pub fn neighbors_1hop(
        &self,
        id: &EntityId,
        direction: Direction,
        relation_type: Option<&str>,
    ) -> Vec<(&Entity, &Relation)> {
        let Some(&node) = self.id_to_node.get(id) else { return vec![] };
        self.graph
            .edges_directed(node, direction)
            .filter(|edge| {
                relation_type.map_or(true, |rt| edge.weight().relation_type == rt)
            })
            .map(|edge| {
                let other = match direction {
                    Direction::Outgoing => edge.target(),
                    Direction::Incoming => edge.source(),
                };
                (&self.graph[other], edge.weight())
            })
            .collect()
    }

    /// n-hop: all entities within n edges
    pub fn neighbors_nhop(
        &self,
        id: &EntityId,
        n: usize,
        direction: Direction,
        relation_type: Option<&str>,
    ) -> Vec<(&Entity, usize)> {
        let Some(&start) = self.id_to_node.get(id) else { return vec![] };
        let mut visited = HashSet::new();
        let mut queue = VecDeque::new();
        let mut results = Vec::new();

        visited.insert(start);
        queue.push_back((start, 0));

        while let Some((node, depth)) = queue.pop_front() {
            if depth > 0 {
                results.push((&self.graph[node], depth));
            }
            if depth >= n { continue; }

            for edge in self.graph.edges_directed(node, direction) {
                if let Some(rt) = relation_type {
                    if edge.weight().relation_type != rt { continue; }
                }
                let other = match direction {
                    Direction::Outgoing => edge.target(),
                    Direction::Incoming => edge.source(),
                };
                if visited.insert(other) {
                    queue.push_back((other, depth + 1));
                }
            }
        }
        results
    }
}
```

### 5.2 Path Queries

```rust
impl PropertyGraph {
    /// Find all simple paths between two entities (with max depth limit)
    pub fn all_paths(
        &self,
        from: &EntityId,
        to: &EntityId,
        max_depth: usize,
    ) -> Vec<Vec<EntityId>> {
        let Some(&start) = self.id_to_node.get(from) else { return vec![] };
        let Some(&end) = self.id_to_node.get(to) else { return vec![] };

        let mut all_paths = Vec::new();
        let mut current_path = vec![start];
        let mut visited = HashSet::new();
        visited.insert(start);

        self.dfs_all_paths(start, end, max_depth, &mut visited, &mut current_path, &mut all_paths);
        all_paths
    }

    fn dfs_all_paths(
        &self,
        current: NodeIndex,
        target: NodeIndex,
        max_depth: usize,
        visited: &mut HashSet<NodeIndex>,
        path: &mut Vec<NodeIndex>,
        results: &mut Vec<Vec<EntityId>>,
    ) {
        if current == target {
            let id_path: Vec<EntityId> = path
                .iter()
                .map(|&n| self.graph[n].id.clone())
                .collect();
            results.push(id_path);
            return;
        }
        if path.len() > max_depth { return; }

        for neighbor in self.graph.neighbors(current) {
            if visited.insert(neighbor) {
                path.push(neighbor);
                self.dfs_all_paths(neighbor, target, max_depth, visited, path, results);
                path.pop();
                visited.remove(&neighbor);
            }
        }
    }
}
```

### 5.3 Pattern Matching

```rust
/// A simple pattern: "find all X connected to Y via relation R"
pub struct GraphPattern {
    pub source_type: Option<String>,
    pub relation_type: Option<String>,
    pub target_type: Option<String>,
}

impl PropertyGraph {
    /// Match a pattern across the entire graph
    pub fn match_pattern(&self, pattern: &GraphPattern) -> Vec<(&Entity, &Relation, &Entity)> {
        let mut results = Vec::new();

        for edge in self.graph.edge_indices() {
            let rel = &self.graph[edge];

            // Check relation type
            if let Some(ref rt) = pattern.relation_type {
                if rel.relation_type != *rt { continue; }
            }

            if let Some((src_idx, tgt_idx)) = self.graph.edge_endpoints(edge) {
                let source = &self.graph[src_idx];
                let target = &self.graph[tgt_idx];

                // Check source type
                if let Some(ref st) = pattern.source_type {
                    if source.entity_type != *st { continue; }
                }
                // Check target type
                if let Some(ref tt) = pattern.target_type {
                    if target.entity_type != *tt { continue; }
                }

                results.push((source, rel, target));
            }
        }
        results
    }

    /// Complex pattern: chain of relations
    /// e.g., Function -calls-> Function -returns-> Type
    pub fn match_chain(
        &self,
        start_type: &str,
        chain: &[(String, String)], // (relation_type, target_type)
    ) -> Vec<Vec<EntityId>> {
        let mut results = Vec::new();

        // Start with all entities of the start type
        for &start_node in self.type_index.get(start_type).unwrap_or(&vec![]) {
            let mut paths = vec![vec![start_node]];

            for (rel_type, target_type) in chain {
                let mut new_paths = Vec::new();
                for path in &paths {
                    let current = *path.last().unwrap();
                    for edge in self.graph.edges_directed(current, Direction::Outgoing) {
                        if edge.weight().relation_type != *rel_type { continue; }
                        let target = edge.target();
                        if self.graph[target].entity_type != *target_type { continue; }
                        let mut new_path = path.clone();
                        new_path.push(target);
                        new_paths.push(new_path);
                    }
                }
                paths = new_paths;
            }

            for path in paths {
                results.push(
                    path.iter().map(|&n| self.graph[n].id.clone()).collect()
                );
            }
        }
        results
    }
}
```

### 5.4 Aggregation Queries

```rust
impl PropertyGraph {
    /// Count edges by relation type
    pub fn edge_type_counts(&self) -> HashMap<String, usize> {
        let mut counts = HashMap::new();
        for edge in self.graph.edge_indices() {
            let rel = &self.graph[edge];
            *counts.entry(rel.relation_type.clone()).or_insert(0) += 1;
        }
        counts
    }

    /// Most connected nodes (by total degree)
    pub fn most_connected(&self, top_n: usize) -> Vec<(&Entity, usize)> {
        let mut degrees: Vec<_> = self.graph.node_indices()
            .map(|n| {
                let in_deg = self.graph.neighbors_directed(n, Direction::Incoming).count();
                let out_deg = self.graph.neighbors_directed(n, Direction::Outgoing).count();
                (&self.graph[n], in_deg + out_deg)
            })
            .collect();
        degrees.sort_by(|a, b| b.1.cmp(&a.1));
        degrees.truncate(top_n);
        degrees
    }

    /// Fan-in analysis: entities with the most incoming edges (most depended-on)
    pub fn highest_fan_in(&self, top_n: usize) -> Vec<(&Entity, usize)> {
        let mut fan_ins: Vec<_> = self.graph.node_indices()
            .map(|n| {
                let in_deg = self.graph.neighbors_directed(n, Direction::Incoming).count();
                (&self.graph[n], in_deg)
            })
            .collect();
        fan_ins.sort_by(|a, b| b.1.cmp(&a.1));
        fan_ins.truncate(top_n);
        fan_ins
    }

    /// Fan-out analysis: entities with the most outgoing edges (most dependencies)
    pub fn highest_fan_out(&self, top_n: usize) -> Vec<(&Entity, usize)> {
        let mut fan_outs: Vec<_> = self.graph.node_indices()
            .map(|n| {
                let out_deg = self.graph.neighbors_directed(n, Direction::Outgoing).count();
                (&self.graph[n], out_deg)
            })
            .collect();
        fan_outs.sort_by(|a, b| b.1.cmp(&a.1));
        fan_outs.truncate(top_n);
        fan_outs
    }
}
```

### 5.5 Tree-sitter S-Expression Queries for Code ASTs

Tree-sitter provides S-expression patterns to query ASTs:

```scheme
;; Find all function definitions in Rust
(function_item
  name: (identifier) @func_name
  parameters: (parameters) @params
  return_type: (_)? @return_type
  body: (block) @body)

;; Find all function calls
(call_expression
  function: [
    (identifier) @call_name
    (field_expression
      field: (field_identifier) @method_name)
    (scoped_identifier
      path: (_) @path
      name: (identifier) @scoped_name)
  ]
  arguments: (arguments) @args)

;; Find struct definitions
(struct_item
  name: (type_identifier) @struct_name
  body: (field_declaration_list)? @fields)

;; Find impl blocks
(impl_item
  type: (type_identifier) @impl_type
  trait: (type_identifier)? @trait_name
  body: (declaration_list) @impl_body)

;; Find use/import statements
(use_declaration
  argument: (_) @import_path)

;; Find trait definitions
(trait_item
  name: (type_identifier) @trait_name
  body: (declaration_list) @trait_body)

;; Find all method calls on a specific type (chained)
(call_expression
  function: (field_expression
    value: (_) @receiver
    field: (field_identifier) @method))
```

**Rust code to execute tree-sitter queries:**

```rust
// Cargo.toml
// [dependencies]
// tree-sitter = "0.22"
// tree-sitter-rust = "0.21"

use tree_sitter::{Parser, Query, QueryCursor};

fn extract_functions_from_rust(source: &str) -> Vec<(String, usize, usize)> {
    let mut parser = Parser::new();
    let language = tree_sitter_rust::language();
    parser.set_language(&language).unwrap();

    let tree = parser.parse(source, None).unwrap();
    let root = tree.root_node();

    let query = Query::new(
        &language,
        "(function_item name: (identifier) @func_name) @func_def",
    ).unwrap();

    let mut cursor = QueryCursor::new();
    let matches = cursor.matches(&query, root, source.as_bytes());

    let mut functions = Vec::new();
    for m in matches {
        for capture in m.captures {
            if query.capture_names()[capture.index as usize] == "func_name" {
                let name = &source[capture.node.byte_range()];
                let start = capture.node.start_position().row + 1;
                let end = capture.node.end_position().row + 1;
                functions.push((name.to_string(), start, end));
            }
        }
    }
    functions
}

fn extract_calls_from_rust(source: &str) -> Vec<(String, usize)> {
    let mut parser = Parser::new();
    let language = tree_sitter_rust::language();
    parser.set_language(&language).unwrap();

    let tree = parser.parse(source, None).unwrap();
    let root = tree.root_node();

    let query = Query::new(
        &language,
        "(call_expression function: (identifier) @call_name)",
    ).unwrap();

    let mut cursor = QueryCursor::new();
    let matches = cursor.matches(&query, root, source.as_bytes());

    let mut calls = Vec::new();
    for m in matches {
        for capture in m.captures {
            let name = &source[capture.node.byte_range()];
            let line = capture.node.start_position().row + 1;
            calls.push((name.to_string(), line));
        }
    }
    calls
}
```

---

## 6. Knowledge Graph for Code

### 6.1 Entity Types

| Entity Type | Description | Example ID |
|-------------|-------------|------------|
| `module` | A file or module | `mod:src/main.rs` |
| `class` | Class or struct | `class:Config` |
| `function` | Standalone function | `fn:parse_config` |
| `method` | Method on a class/struct | `method:Config::validate` |
| `variable` | Global or module-level variable | `var:DEFAULT_PORT` |
| `import` | Import/use statement | `import:serde::Deserialize` |
| `type` | Type alias or typedef | `type:Result<T>` |
| `trait` | Trait/interface | `trait:Iterator` |
| `enum` | Enum definition | `enum:Status` |
| `constant` | Constant value | `const:MAX_RETRIES` |
| `macro` | Macro definition | `macro:println` |

### 6.2 Relation Types

| Relation | Source | Target | Meaning |
|----------|--------|--------|---------|
| `defines` | module | function/class/type | Module defines entity |
| `calls` | function | function | Function calls another |
| `imports` | module | module/entity | Module imports from another |
| `inherits` | class | class | Class extends another |
| `implements` | class | trait | Class implements trait |
| `returns` | function | type | Function returns this type |
| `accepts` | function | type | Function parameter type |
| `uses` | function | variable/type | Function references entity |
| `contains` | class/module | function/class | Structural containment |
| `overrides` | method | method | Method overrides parent |
| `depends_on` | module | module | Module depends on another |
| `instantiates` | function | class | Creates instance of class |
| `reads` | function | variable | Reads a variable |
| `writes` | function | variable | Writes to a variable |
| `throws` | function | type | Function can throw/return error |

### 6.3 Extracting from ASTs (tree-sitter)

**Full code graph builder in Rust:**

```rust
use std::collections::HashMap;
use std::path::Path;

/// Build a code knowledge graph from a Rust source file
pub struct CodeGraphBuilder {
    entities: Vec<Entity>,
    relations: Vec<Relation>,
    /// Track which function we are currently inside (for nesting context)
    current_scope: Vec<EntityId>,
}

impl CodeGraphBuilder {
    pub fn new() -> Self {
        Self {
            entities: Vec::new(),
            relations: Vec::new(),
            current_scope: Vec::new(),
        }
    }

    /// Process a single Rust source file
    pub fn process_file(&mut self, file_path: &str, source: &str) {
        let mut parser = Parser::new();
        let language = tree_sitter_rust::language();
        parser.set_language(&language).unwrap();

        let tree = parser.parse(source, None).unwrap();
        let root = tree.root_node();

        // Create module entity
        let mod_id = EntityId(format!("mod:{}", file_path));
        self.entities.push(Entity {
            id: mod_id.clone(),
            entity_type: "module".into(),
            label: file_path.into(),
            properties: HashMap::from([
                ("file".into(), PropertyValue::String(file_path.into())),
            ]),
        });

        self.current_scope.push(mod_id.clone());
        self.visit_node(root, source, file_path);
        self.current_scope.pop();
    }

    fn visit_node(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        match node.kind() {
            "function_item" => self.extract_function(node, source, file_path),
            "struct_item" => self.extract_struct(node, source, file_path),
            "impl_item" => self.extract_impl(node, source, file_path),
            "use_declaration" => self.extract_use(node, source, file_path),
            "trait_item" => self.extract_trait(node, source, file_path),
            "enum_item" => self.extract_enum(node, source, file_path),
            "call_expression" => self.extract_call(node, source, file_path),
            _ => {
                // Recurse into children
                let mut cursor = node.walk();
                for child in node.children(&mut cursor) {
                    self.visit_node(child, source, file_path);
                }
            }
        }
    }

    fn extract_function(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        let name_node = node.child_by_field_name("name");
        let Some(name_node) = name_node else { return };
        let name = &source[name_node.byte_range()];

        let fn_id = EntityId(format!("fn:{}:{}", file_path, name));

        // Check visibility
        let is_pub = node.children(&mut node.walk())
            .any(|c| c.kind() == "visibility_modifier");

        let mut props = HashMap::new();
        props.insert("file".into(), PropertyValue::String(file_path.into()));
        props.insert("line".into(), PropertyValue::Integer(node.start_position().row as i64 + 1));
        props.insert("visibility".into(), PropertyValue::String(
            if is_pub { "pub" } else { "private" }.into()
        ));

        // Extract return type
        if let Some(ret) = node.child_by_field_name("return_type") {
            let ret_text = &source[ret.byte_range()];
            props.insert("return_type".into(), PropertyValue::String(ret_text.into()));

            // Create "returns" relation
            let type_id = EntityId(format!("type:{}", ret_text));
            self.relations.push(Relation {
                source: fn_id.clone(),
                target: type_id,
                relation_type: "returns".into(),
                properties: HashMap::new(),
            });
        }

        // Extract parameter types
        if let Some(params) = node.child_by_field_name("parameters") {
            let params_text = &source[params.byte_range()];
            props.insert("params".into(), PropertyValue::String(params_text.into()));
        }

        self.entities.push(Entity {
            id: fn_id.clone(),
            entity_type: "function".into(),
            label: name.into(),
            properties: props,
        });

        // "defines" relation from current scope
        if let Some(scope) = self.current_scope.last() {
            self.relations.push(Relation {
                source: scope.clone(),
                target: fn_id.clone(),
                relation_type: "defines".into(),
                properties: HashMap::new(),
            });
        }

        // Visit body for calls
        self.current_scope.push(fn_id);
        if let Some(body) = node.child_by_field_name("body") {
            let mut cursor = body.walk();
            for child in body.children(&mut cursor) {
                self.visit_node(child, source, file_path);
            }
        }
        self.current_scope.pop();
    }

    fn extract_struct(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        let name_node = node.child_by_field_name("name");
        let Some(name_node) = name_node else { return };
        let name = &source[name_node.byte_range()];

        let struct_id = EntityId(format!("struct:{}:{}", file_path, name));

        let mut props = HashMap::new();
        props.insert("file".into(), PropertyValue::String(file_path.into()));
        props.insert("line".into(), PropertyValue::Integer(node.start_position().row as i64 + 1));

        // Extract fields
        if let Some(body) = node.child_by_field_name("body") {
            let mut fields = Vec::new();
            let mut cursor = body.walk();
            for child in body.children(&mut cursor) {
                if child.kind() == "field_declaration" {
                    let field_text = &source[child.byte_range()];
                    fields.push(PropertyValue::String(field_text.trim().into()));
                }
            }
            if !fields.is_empty() {
                props.insert("fields".into(), PropertyValue::List(fields));
            }
        }

        self.entities.push(Entity {
            id: struct_id.clone(),
            entity_type: "struct".into(),
            label: name.into(),
            properties: props,
        });

        if let Some(scope) = self.current_scope.last() {
            self.relations.push(Relation {
                source: scope.clone(),
                target: struct_id,
                relation_type: "defines".into(),
                properties: HashMap::new(),
            });
        }
    }

    fn extract_impl(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        let type_node = node.child_by_field_name("type");
        let Some(type_node) = type_node else { return };
        let type_name = &source[type_node.byte_range()];

        let struct_id = EntityId(format!("struct:{}:{}", file_path, type_name));

        // Check if this is a trait impl
        if let Some(trait_node) = node.child_by_field_name("trait") {
            let trait_name = &source[trait_node.byte_range()];
            let trait_id = EntityId(format!("trait:{}", trait_name));

            self.relations.push(Relation {
                source: struct_id.clone(),
                target: trait_id,
                relation_type: "implements".into(),
                properties: HashMap::new(),
            });
        }

        // Visit impl body for methods
        self.current_scope.push(struct_id);
        if let Some(body) = node.child_by_field_name("body") {
            let mut cursor = body.walk();
            for child in body.children(&mut cursor) {
                self.visit_node(child, source, file_path);
            }
        }
        self.current_scope.pop();
    }

    fn extract_use(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        let use_text = &source[node.byte_range()];
        // Strip "use " prefix and ";" suffix
        let path = use_text
            .trim_start_matches("use ")
            .trim_end_matches(';')
            .trim();

        let import_id = EntityId(format!("import:{}:{}", file_path, path));
        self.entities.push(Entity {
            id: import_id.clone(),
            entity_type: "import".into(),
            label: path.into(),
            properties: HashMap::from([
                ("file".into(), PropertyValue::String(file_path.into())),
                ("path".into(), PropertyValue::String(path.into())),
            ]),
        });

        if let Some(scope) = self.current_scope.last() {
            self.relations.push(Relation {
                source: scope.clone(),
                target: import_id,
                relation_type: "imports".into(),
                properties: HashMap::new(),
            });
        }
    }

    fn extract_trait(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        let name_node = node.child_by_field_name("name");
        let Some(name_node) = name_node else { return };
        let name = &source[name_node.byte_range()];

        let trait_id = EntityId(format!("trait:{}:{}", file_path, name));
        self.entities.push(Entity {
            id: trait_id.clone(),
            entity_type: "trait".into(),
            label: name.into(),
            properties: HashMap::from([
                ("file".into(), PropertyValue::String(file_path.into())),
                ("line".into(), PropertyValue::Integer(node.start_position().row as i64 + 1)),
            ]),
        });

        if let Some(scope) = self.current_scope.last() {
            self.relations.push(Relation {
                source: scope.clone(),
                target: trait_id.clone(),
                relation_type: "defines".into(),
                properties: HashMap::new(),
            });
        }

        // Visit trait body for method signatures
        self.current_scope.push(trait_id);
        if let Some(body) = node.child_by_field_name("body") {
            let mut cursor = body.walk();
            for child in body.children(&mut cursor) {
                self.visit_node(child, source, file_path);
            }
        }
        self.current_scope.pop();
    }

    fn extract_enum(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        let name_node = node.child_by_field_name("name");
        let Some(name_node) = name_node else { return };
        let name = &source[name_node.byte_range()];

        let enum_id = EntityId(format!("enum:{}:{}", file_path, name));
        self.entities.push(Entity {
            id: enum_id.clone(),
            entity_type: "enum".into(),
            label: name.into(),
            properties: HashMap::from([
                ("file".into(), PropertyValue::String(file_path.into())),
                ("line".into(), PropertyValue::Integer(node.start_position().row as i64 + 1)),
            ]),
        });

        if let Some(scope) = self.current_scope.last() {
            self.relations.push(Relation {
                source: scope.clone(),
                target: enum_id,
                relation_type: "defines".into(),
                properties: HashMap::new(),
            });
        }
    }

    fn extract_call(
        &mut self,
        node: tree_sitter::Node,
        source: &str,
        file_path: &str,
    ) {
        let func_node = node.child_by_field_name("function");
        let Some(func_node) = func_node else { return };
        let callee_name = &source[func_node.byte_range()];

        if let Some(caller) = self.current_scope.last() {
            let callee_id = EntityId(format!("fn:{}", callee_name));
            self.relations.push(Relation {
                source: caller.clone(),
                target: callee_id,
                relation_type: "calls".into(),
                properties: HashMap::from([
                    ("line".into(), PropertyValue::Integer(node.start_position().row as i64 + 1)),
                ]),
            });
        }

        // Recurse into arguments
        let mut cursor = node.walk();
        for child in node.children(&mut cursor) {
            if child.kind() != "identifier" && child.kind() != "field_expression" {
                self.visit_node(child, source, file_path);
            }
        }
    }

    pub fn build(self) -> (Vec<Entity>, Vec<Relation>) {
        (self.entities, self.relations)
    }
}
```

### 6.4 Cross-File Reference Resolution

```rust
use std::collections::HashMap;

/// Resolve cross-file references after all files have been processed.
/// This links unresolved call targets to their definitions.
pub struct CrossFileResolver {
    /// Map: short name -> list of fully qualified entity IDs
    name_index: HashMap<String, Vec<EntityId>>,
    /// Map: import path -> resolved entity ID
    import_resolutions: HashMap<String, EntityId>,
}

impl CrossFileResolver {
    pub fn new(entities: &[Entity]) -> Self {
        let mut name_index: HashMap<String, Vec<EntityId>> = HashMap::new();

        for entity in entities {
            // Index by label (short name)
            name_index
                .entry(entity.label.clone())
                .or_default()
                .push(entity.id.clone());

            // Also index by qualified name if present
            if let Some(PropertyValue::String(qname)) = entity.properties.get("qualified_name") {
                name_index
                    .entry(qname.clone())
                    .or_default()
                    .push(entity.id.clone());
            }
        }

        Self {
            name_index,
            import_resolutions: HashMap::new(),
        }
    }

    /// Resolve a call target name to the most likely entity
    pub fn resolve(&self, name: &str, caller_file: &str) -> Option<EntityId> {
        let candidates = self.name_index.get(name)?;

        if candidates.len() == 1 {
            return Some(candidates[0].clone());
        }

        // Prefer entities in the same file
        if let Some(same_file) = candidates.iter().find(|id| id.0.contains(caller_file)) {
            return Some(same_file.clone());
        }

        // Prefer public entities
        // (would need access to entity properties here; simplified)
        Some(candidates[0].clone())
    }

    /// Resolve all unresolved relations in the graph
    pub fn resolve_relations(&self, relations: &mut Vec<Relation>, entities: &[Entity]) {
        let entity_ids: HashSet<String> = entities.iter().map(|e| e.id.0.clone()).collect();

        for rel in relations.iter_mut() {
            // If target doesn't exist in entity set, try to resolve it
            if !entity_ids.contains(&rel.target.0) {
                // Extract the short name from the target ID
                let short_name = rel.target.0
                    .split(':')
                    .last()
                    .unwrap_or(&rel.target.0);

                // Try to find the caller's file for context
                let caller_file = rel.source.0
                    .split(':')
                    .nth(1)
                    .unwrap_or("");

                if let Some(resolved) = self.resolve(short_name, caller_file) {
                    rel.target = resolved;
                }
            }
        }
    }
}
```

### 6.5 Call Graph Construction

```rust
/// Build a pure call graph (functions only, edges are calls)
pub fn build_call_graph(
    entities: &[Entity],
    relations: &[Relation],
) -> DiGraph<String, CallEdge> {
    let mut graph = DiGraph::new();
    let mut node_map: HashMap<String, NodeIndex> = HashMap::new();

    // Add function nodes
    for entity in entities {
        if entity.entity_type == "function" || entity.entity_type == "method" {
            let idx = graph.add_node(entity.label.clone());
            node_map.insert(entity.id.0.clone(), idx);
        }
    }

    // Add call edges
    for rel in relations {
        if rel.relation_type == "calls" {
            if let (Some(&src), Some(&tgt)) = (
                node_map.get(&rel.source.0),
                node_map.get(&rel.target.0),
            ) {
                let line = rel.properties.get("line")
                    .and_then(|v| match v {
                        PropertyValue::Integer(n) => Some(*n as usize),
                        _ => None,
                    })
                    .unwrap_or(0);
                graph.add_edge(src, tgt, CallEdge { line, is_async: false });
            }
        }
    }
    graph
}

#[derive(Debug, Clone)]
pub struct CallEdge {
    pub line: usize,
    pub is_async: bool,
}
```

### 6.6 Dependency Graph Construction

```rust
/// Build a module-level dependency graph
pub fn build_dependency_graph(
    entities: &[Entity],
    relations: &[Relation],
) -> DiGraph<String, String> {
    let mut graph = DiGraph::new();
    let mut node_map: HashMap<String, NodeIndex> = HashMap::new();

    // Add module nodes
    for entity in entities {
        if entity.entity_type == "module" {
            let idx = graph.add_node(entity.label.clone());
            node_map.insert(entity.id.0.clone(), idx);
        }
    }

    // Add dependency edges (from imports)
    for rel in relations {
        if rel.relation_type == "imports" || rel.relation_type == "depends_on" {
            if let (Some(&src), Some(&tgt)) = (
                node_map.get(&rel.source.0),
                node_map.get(&rel.target.0),
            ) {
                graph.add_edge(src, tgt, rel.relation_type.clone());
            }
        }
    }
    graph
}
```

### 6.7 Type Hierarchy Extraction

```rust
/// Build a type hierarchy (inheritance / implementation graph)
pub fn build_type_hierarchy(
    entities: &[Entity],
    relations: &[Relation],
) -> DiGraph<String, String> {
    let mut graph = DiGraph::new();
    let mut node_map: HashMap<String, NodeIndex> = HashMap::new();

    // Add type nodes (structs, traits, enums, classes)
    for entity in entities {
        match entity.entity_type.as_str() {
            "struct" | "trait" | "enum" | "class" | "interface" => {
                let idx = graph.add_node(format!("{}:{}", entity.entity_type, entity.label));
                node_map.insert(entity.id.0.clone(), idx);
            }
            _ => {}
        }
    }

    // Add hierarchy edges
    for rel in relations {
        match rel.relation_type.as_str() {
            "inherits" | "implements" | "extends" => {
                if let (Some(&src), Some(&tgt)) = (
                    node_map.get(&rel.source.0),
                    node_map.get(&rel.target.0),
                ) {
                    graph.add_edge(src, tgt, rel.relation_type.clone());
                }
            }
            _ => {}
        }
    }
    graph
}
```

---

## 7. Graph Operations for Code Intelligence

### 7.1 Impact Analysis

"What breaks if I change function X?"

```rust
/// Find all entities transitively affected by a change to `changed_entity`
pub fn impact_analysis(
    graph: &PropertyGraph,
    changed_entity: &EntityId,
    max_depth: usize,
) -> Vec<(EntityId, usize, String)> {
    // Traverse INCOMING edges: who depends on this entity?
    let mut results = Vec::new();
    let mut visited = HashSet::new();
    let mut queue = VecDeque::new();

    visited.insert(changed_entity.clone());
    queue.push_back((changed_entity.clone(), 0));

    while let Some((entity_id, depth)) = queue.pop_front() {
        if depth > 0 {
            let entity = graph.get_entity(&entity_id);
            let entity_type = entity.map(|e| e.entity_type.clone()).unwrap_or_default();
            results.push((entity_id.clone(), depth, entity_type));
        }
        if depth >= max_depth { continue; }

        // Get all entities that depend on this one (incoming edges)
        let dependents = graph.neighbors_1hop(
            &entity_id,
            Direction::Incoming,
            None,  // any relation type
        );

        for (dependent, relation) in dependents {
            if visited.insert(dependent.id.clone()) {
                queue.push_back((dependent.id.clone(), depth + 1));
            }
        }
    }

    // Sort by depth (closest impacts first)
    results.sort_by_key(|(_, depth, _)| *depth);
    results
}

/// Focused impact: only follow specific relation types
pub fn impact_analysis_focused(
    graph: &PropertyGraph,
    changed_entity: &EntityId,
    follow_relations: &[&str],
    max_depth: usize,
) -> Vec<(EntityId, usize)> {
    let mut results = Vec::new();
    let mut visited = HashSet::new();
    let mut queue = VecDeque::new();

    visited.insert(changed_entity.clone());
    queue.push_back((changed_entity.clone(), 0));

    while let Some((entity_id, depth)) = queue.pop_front() {
        if depth > 0 {
            results.push((entity_id.clone(), depth));
        }
        if depth >= max_depth { continue; }

        for rel_type in follow_relations {
            let dependents = graph.neighbors_1hop(
                &entity_id,
                Direction::Incoming,
                Some(rel_type),
            );
            for (dep, _) in dependents {
                if visited.insert(dep.id.clone()) {
                    queue.push_back((dep.id.clone(), depth + 1));
                }
            }
        }
    }
    results
}
```

### 7.2 Dead Code Detection

```rust
/// Find unreachable code entities (no path from any entry point)
pub fn find_dead_code(
    graph: &PropertyGraph,
    entry_points: &[EntityId],  // e.g., main, public API functions
) -> Vec<&Entity> {
    let mut reachable = HashSet::new();

    // BFS from each entry point
    for entry in entry_points {
        let Some(&start) = graph.id_to_node.get(entry) else { continue };
        let mut queue = VecDeque::new();
        queue.push_back(start);
        reachable.insert(start);

        while let Some(node) = queue.pop_front() {
            for neighbor in graph.graph.neighbors_directed(node, Direction::Outgoing) {
                if reachable.insert(neighbor) {
                    queue.push_back(neighbor);
                }
            }
        }
    }

    // Everything not reachable is dead code
    graph.graph.node_indices()
        .filter(|&n| !reachable.contains(&n))
        .filter(|&n| {
            // Only report functions/methods, not types or modules
            let entity = &graph.graph[n];
            matches!(entity.entity_type.as_str(), "function" | "method")
        })
        .map(|n| &graph.graph[n])
        .collect()
}

/// Find unused imports
pub fn find_unused_imports(
    graph: &PropertyGraph,
) -> Vec<&Entity> {
    graph.graph.node_indices()
        .filter(|&n| {
            let entity = &graph.graph[n];
            entity.entity_type == "import"
                && graph.graph.neighbors_directed(n, Direction::Incoming).count() == 0
        })
        .map(|n| &graph.graph[n])
        .collect()
}
```

### 7.3 Dependency Ordering

```rust
/// Get build/initialization order for modules
pub fn build_order(graph: &PropertyGraph) -> Result<Vec<EntityId>, Vec<Vec<EntityId>>> {
    // Extract module-level dependency subgraph
    let module_nodes: Vec<NodeIndex> = graph.graph.node_indices()
        .filter(|&n| graph.graph[n].entity_type == "module")
        .collect();

    let mut sub = DiGraph::new();
    let mut node_map: HashMap<NodeIndex, NodeIndex> = HashMap::new();

    for &old_idx in &module_nodes {
        let new_idx = sub.add_node(graph.graph[old_idx].id.clone());
        node_map.insert(old_idx, new_idx);
    }

    for &old_idx in &module_nodes {
        for edge in graph.graph.edges_directed(old_idx, Direction::Outgoing) {
            if let Some(&new_target) = node_map.get(&edge.target()) {
                if edge.weight().relation_type == "depends_on"
                    || edge.weight().relation_type == "imports"
                {
                    sub.add_edge(node_map[&old_idx], new_target, ());
                }
            }
        }
    }

    match toposort(&sub, None) {
        Ok(order) => {
            // Reverse: dependencies first
            Ok(order.into_iter().rev().map(|n| sub[n].clone()).collect())
        }
        Err(_) => {
            // Has cycles -- return SCCs for diagnosis
            let sccs = petgraph::algo::kosaraju_scc(&sub);
            let cycle_groups: Vec<Vec<EntityId>> = sccs
                .into_iter()
                .filter(|scc| scc.len() > 1)
                .map(|scc| scc.into_iter().map(|n| sub[n].clone()).collect())
                .collect();
            Err(cycle_groups)
        }
    }
}
```

### 7.4 Code Similarity via Graph Structure

```rust
/// Compute structural similarity between two functions
/// based on their call neighborhoods (Jaccard index)
pub fn structural_similarity(
    graph: &PropertyGraph,
    fn_a: &EntityId,
    fn_b: &EntityId,
) -> f64 {
    let callees_a: HashSet<EntityId> = graph
        .neighbors_1hop(fn_a, Direction::Outgoing, Some("calls"))
        .iter()
        .map(|(e, _)| e.id.clone())
        .collect();

    let callees_b: HashSet<EntityId> = graph
        .neighbors_1hop(fn_b, Direction::Outgoing, Some("calls"))
        .iter()
        .map(|(e, _)| e.id.clone())
        .collect();

    if callees_a.is_empty() && callees_b.is_empty() {
        return 0.0;
    }

    let intersection = callees_a.intersection(&callees_b).count() as f64;
    let union = callees_a.union(&callees_b).count() as f64;

    intersection / union
}

/// Find functions structurally similar to a given function
pub fn find_similar_functions(
    graph: &PropertyGraph,
    target: &EntityId,
    threshold: f64,
) -> Vec<(EntityId, f64)> {
    let functions: Vec<_> = graph.graph.node_indices()
        .filter(|&n| {
            let e = &graph.graph[n];
            (e.entity_type == "function" || e.entity_type == "method")
                && e.id != *target
        })
        .map(|n| graph.graph[n].id.clone())
        .collect();

    let mut results: Vec<_> = functions
        .iter()
        .map(|fn_id| {
            let sim = structural_similarity(graph, target, fn_id);
            (fn_id.clone(), sim)
        })
        .filter(|(_, sim)| *sim >= threshold)
        .collect();

    results.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    results
}
```

### 7.5 Refactoring Support (Rename Propagation)

```rust
/// Find all locations that need updating when renaming an entity
pub fn rename_propagation(
    graph: &PropertyGraph,
    entity_id: &EntityId,
    new_name: &str,
) -> Vec<RenameAction> {
    let mut actions = Vec::new();

    // 1. The entity definition itself
    if let Some(entity) = graph.get_entity(entity_id) {
        if let Some(PropertyValue::String(file)) = entity.properties.get("file") {
            if let Some(PropertyValue::Integer(line)) = entity.properties.get("line") {
                actions.push(RenameAction {
                    file: file.clone(),
                    line: *line as usize,
                    old_name: entity.label.clone(),
                    new_name: new_name.to_string(),
                    kind: RenameKind::Definition,
                });
            }
        }
    }

    // 2. All call sites (incoming "calls" edges)
    let callers = graph.neighbors_1hop(entity_id, Direction::Incoming, Some("calls"));
    for (caller, relation) in callers {
        if let Some(PropertyValue::String(file)) = caller.properties.get("file") {
            if let Some(PropertyValue::Integer(line)) = relation.properties.get("line") {
                actions.push(RenameAction {
                    file: file.clone(),
                    line: *line as usize,
                    old_name: graph.get_entity(entity_id)
                        .map(|e| e.label.clone())
                        .unwrap_or_default(),
                    new_name: new_name.to_string(),
                    kind: RenameKind::CallSite,
                });
            }
        }
    }

    // 3. Import statements that reference this entity
    let importers = graph.neighbors_1hop(entity_id, Direction::Incoming, Some("imports"));
    for (importer, _) in importers {
        if let Some(PropertyValue::String(file)) = importer.properties.get("file") {
            actions.push(RenameAction {
                file: file.clone(),
                line: 0, // would need import line tracking
                old_name: graph.get_entity(entity_id)
                    .map(|e| e.label.clone())
                    .unwrap_or_default(),
                new_name: new_name.to_string(),
                kind: RenameKind::Import,
            });
        }
    }

    // 4. Type references (if renaming a type/struct)
    let type_users = graph.neighbors_1hop(entity_id, Direction::Incoming, Some("uses"));
    for (user, relation) in type_users {
        if let Some(PropertyValue::String(file)) = user.properties.get("file") {
            actions.push(RenameAction {
                file: file.clone(),
                line: 0,
                old_name: graph.get_entity(entity_id)
                    .map(|e| e.label.clone())
                    .unwrap_or_default(),
                new_name: new_name.to_string(),
                kind: RenameKind::TypeReference,
            });
        }
    }

    actions
}

#[derive(Debug)]
pub struct RenameAction {
    pub file: String,
    pub line: usize,
    pub old_name: String,
    pub new_name: String,
    pub kind: RenameKind,
}

#[derive(Debug)]
pub enum RenameKind {
    Definition,
    CallSite,
    Import,
    TypeReference,
}
```

---

## 8. Incremental Updates

### 8.1 Watermark-Based Re-Indexing

```rust
use std::collections::HashMap;
use sha2::{Sha256, Digest};

/// Track which files need re-indexing based on content hashes
pub struct FileWatermark {
    /// file_path -> content_hash
    watermarks: HashMap<String, String>,
}

impl FileWatermark {
    pub fn new() -> Self {
        Self { watermarks: HashMap::new() }
    }

    /// Load watermarks from SQLite
    pub fn load_from_db(conn: &Connection) -> rusqlite::Result<Self> {
        let mut stmt = conn.prepare(
            "SELECT file_path, content_hash FROM file_watermarks"
        )?;
        let watermarks = stmt.query_map([], |row| {
            Ok((row.get::<_, String>(0)?, row.get::<_, String>(1)?))
        })?.collect::<Result<HashMap<_, _>, _>>()?;
        Ok(Self { watermarks })
    }

    /// Compute content hash for a file
    fn hash_content(content: &str) -> String {
        let mut hasher = Sha256::new();
        hasher.update(content.as_bytes());
        format!("{:x}", hasher.finalize())
    }

    /// Check if a file needs re-indexing
    pub fn needs_reindex(&self, file_path: &str, content: &str) -> bool {
        let current_hash = Self::hash_content(content);
        match self.watermarks.get(file_path) {
            Some(stored_hash) => *stored_hash != current_hash,
            None => true, // New file, always index
        }
    }

    /// Update watermark after successful indexing
    pub fn update(&mut self, file_path: &str, content: &str) {
        let hash = Self::hash_content(content);
        self.watermarks.insert(file_path.to_string(), hash);
    }

    /// Save watermarks to SQLite
    pub fn save_to_db(&self, conn: &Connection) -> rusqlite::Result<()> {
        let tx = conn.unchecked_transaction()?;
        for (path, hash) in &self.watermarks {
            tx.execute(
                "INSERT INTO file_watermarks (file_path, content_hash)
                 VALUES (?1, ?2)
                 ON CONFLICT(file_path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    indexed_at = datetime('now')",
                params![path, hash],
            )?;
        }
        tx.commit()
    }

    /// Get list of files that were removed (exist in watermarks but not on disk)
    pub fn find_removed_files(&self, current_files: &[String]) -> Vec<String> {
        let current_set: HashSet<&String> = current_files.iter().collect();
        self.watermarks.keys()
            .filter(|path| !current_set.contains(path))
            .cloned()
            .collect()
    }
}
```

### 8.2 File-Level Diffing

```rust
/// Incremental graph updater: only re-processes changed files
pub struct IncrementalUpdater {
    watermarks: FileWatermark,
    graph_store: SqliteGraphStore,
}

impl IncrementalUpdater {
    /// Determine which files need processing
    pub fn diff_files(
        &self,
        file_contents: &HashMap<String, String>,
    ) -> FileDiff {
        let mut added = Vec::new();
        let mut modified = Vec::new();
        let mut removed = Vec::new();

        // Check for new or modified files
        for (path, content) in file_contents {
            if self.watermarks.needs_reindex(path, content) {
                if self.watermarks.watermarks.contains_key(path.as_str()) {
                    modified.push(path.clone());
                } else {
                    added.push(path.clone());
                }
            }
        }

        // Check for removed files
        let current_files: Vec<String> = file_contents.keys().cloned().collect();
        removed = self.watermarks.find_removed_files(&current_files);

        FileDiff { added, modified, removed }
    }

    /// Apply incremental update
    pub fn update(
        &mut self,
        file_contents: &HashMap<String, String>,
    ) -> Result<UpdateStats, Box<dyn std::error::Error>> {
        let diff = self.diff_files(file_contents);
        let mut stats = UpdateStats::default();

        // Remove stale data for modified and removed files
        for path in diff.modified.iter().chain(diff.removed.iter()) {
            let count = self.graph_store.invalidate_file(path)?;
            stats.entities_removed += count;
        }

        // Re-index added and modified files
        let mut builder = CodeGraphBuilder::new();
        for path in diff.added.iter().chain(diff.modified.iter()) {
            if let Some(content) = file_contents.get(path) {
                builder.process_file(path, content);
                self.watermarks.update(path, content);
            }
        }

        let (entities, relations) = builder.build();
        stats.entities_added = entities.len();
        stats.relations_added = relations.len();

        self.graph_store.batch_upsert(&mut entities.clone(), &relations)?;

        // Clean up watermarks for removed files
        for path in &diff.removed {
            self.watermarks.watermarks.remove(path);
        }

        stats.files_added = diff.added.len();
        stats.files_modified = diff.modified.len();
        stats.files_removed = diff.removed.len();

        Ok(stats)
    }
}

pub struct FileDiff {
    pub added: Vec<String>,
    pub modified: Vec<String>,
    pub removed: Vec<String>,
}

#[derive(Default)]
pub struct UpdateStats {
    pub files_added: usize,
    pub files_modified: usize,
    pub files_removed: usize,
    pub entities_added: usize,
    pub entities_removed: usize,
    pub relations_added: usize,
}
```

### 8.3 Edge Invalidation

```rust
impl SqliteGraphStore {
    /// Remove all edges originating from entities in a specific file
    /// This is more surgical than deleting all entities
    pub fn invalidate_edges_from_file(&self, file_path: &str) -> rusqlite::Result<usize> {
        self.conn.execute(
            "DELETE FROM relations WHERE source_id IN (
                SELECT id FROM entities WHERE file_path = ?1
            )",
            params![file_path],
        )
    }

    /// Remove only specific relation types from a file's entities
    pub fn invalidate_edges_by_type(
        &self,
        file_path: &str,
        relation_types: &[&str],
    ) -> rusqlite::Result<usize> {
        let placeholders: String = relation_types.iter()
            .enumerate()
            .map(|(i, _)| format!("?{}", i + 2))
            .collect::<Vec<_>>()
            .join(",");

        let sql = format!(
            "DELETE FROM relations WHERE source_id IN (
                SELECT id FROM entities WHERE file_path = ?1
            ) AND relation_type IN ({})",
            placeholders
        );

        let mut params: Vec<Box<dyn rusqlite::types::ToSql>> = Vec::new();
        params.push(Box::new(file_path.to_string()));
        for rt in relation_types {
            params.push(Box::new(rt.to_string()));
        }

        self.conn.execute(
            &sql,
            rusqlite::params_from_iter(params.iter().map(|p| p.as_ref())),
        )
    }

    /// Atomic file update: remove old data and insert new in one transaction
    pub fn atomic_file_update(
        &mut self,
        file_path: &str,
        new_entities: &[Entity],
        new_relations: &[Relation],
    ) -> rusqlite::Result<()> {
        let tx = self.conn.transaction()?;

        // 1. Remove old entities (cascade removes relations)
        tx.execute(
            "DELETE FROM entities WHERE file_path = ?1",
            params![file_path],
        )?;

        // 2. Insert new entities
        for e in new_entities {
            tx.execute(
                "INSERT INTO entities (id, entity_type, label, properties, file_path, line_start)
                 VALUES (?1, ?2, ?3, ?4, ?5, ?6)",
                params![
                    e.id.0, e.entity_type, e.label,
                    serde_json::to_string(&e.properties).unwrap(),
                    file_path,
                    e.properties.get("line").and_then(|v| match v {
                        PropertyValue::Integer(n) => Some(*n),
                        _ => None,
                    }),
                ],
            )?;
        }

        // 3. Insert new relations
        for r in new_relations {
            tx.execute(
                "INSERT OR REPLACE INTO relations (source_id, target_id, relation_type, properties)
                 VALUES (?1, ?2, ?3, ?4)",
                params![
                    r.source.0, r.target.0, r.relation_type,
                    serde_json::to_string(&r.properties).unwrap(),
                ],
            )?;
        }

        tx.commit()
    }
}
```

### 8.4 Merge Strategies

```rust
/// Strategy for merging graph updates
pub enum MergeStrategy {
    /// Replace: delete all data for affected files, re-insert
    Replace,
    /// Union: add new data without removing old (may create duplicates)
    Union,
    /// DiffAndPatch: compute delta and apply minimal changes
    DiffAndPatch,
}

/// Diff-and-patch merge: compute the minimum set of changes
pub fn diff_and_patch(
    store: &mut SqliteGraphStore,
    file_path: &str,
    new_entities: &[Entity],
    new_relations: &[Relation],
) -> rusqlite::Result<PatchStats> {
    let mut stats = PatchStats::default();

    // Get existing entities for this file
    let existing_entity_ids: HashSet<String> = {
        let mut stmt = store.conn.prepare(
            "SELECT id FROM entities WHERE file_path = ?1"
        )?;
        stmt.query_map(params![file_path], |row| row.get(0))?
            .collect::<Result<HashSet<String>, _>>()?
    };

    let new_entity_ids: HashSet<String> = new_entities.iter()
        .map(|e| e.id.0.clone())
        .collect();

    // Entities to remove (in old but not in new)
    let to_remove: Vec<_> = existing_entity_ids.difference(&new_entity_ids).collect();
    for id in &to_remove {
        store.conn.execute("DELETE FROM entities WHERE id = ?1", params![id])?;
        stats.entities_removed += 1;
    }

    // Entities to add or update (in new)
    for entity in new_entities {
        if existing_entity_ids.contains(&entity.id.0) {
            // Update existing
            store.upsert_entity(entity)?;
            stats.entities_updated += 1;
        } else {
            // Add new
            store.upsert_entity(entity)?;
            stats.entities_added += 1;
        }
    }

    // For relations: remove all from this file's entities and re-insert
    // (relation diffing is more complex and usually not worth the overhead)
    store.invalidate_edges_from_file(file_path)?;
    for rel in new_relations {
        store.upsert_relation(rel)?;
        stats.relations_added += 1;
    }

    Ok(stats)
}

#[derive(Default)]
pub struct PatchStats {
    pub entities_added: usize,
    pub entities_updated: usize,
    pub entities_removed: usize,
    pub relations_added: usize,
    pub relations_removed: usize,
}
```

---

## 9. Serialization Formats

### 9.1 JSON-Lines (JSONL)

Covered in section 3.2. One record per line, streamable, appendable.

```jsonl
{"type":"entity","id":"fn:main","entity_type":"function","label":"main","properties":{"file":"src/main.rs","line":1}}
{"type":"relation","source":"fn:main","target":"fn:parse_config","relation_type":"calls","properties":{}}
```

### 9.2 GraphML

XML-based format, widely supported by graph visualization tools.

```rust
/// Export to GraphML format
pub fn to_graphml(graph: &PropertyGraph) -> String {
    let mut xml = String::new();
    xml.push_str(r#"<?xml version="1.0" encoding="UTF-8"?>
<graphml xmlns="http://graphml.graphstruct.org/graphml">
  <key id="label" for="node" attr.name="label" attr.type="string"/>
  <key id="entity_type" for="node" attr.name="entity_type" attr.type="string"/>
  <key id="relation_type" for="edge" attr.name="relation_type" attr.type="string"/>
  <graph id="G" edgedefault="directed">
"#);

    for node in graph.graph.node_indices() {
        let entity = &graph.graph[node];
        xml.push_str(&format!(
            r#"    <node id="{}">
      <data key="label">{}</data>
      <data key="entity_type">{}</data>
    </node>
"#,
            xml_escape(&entity.id.0),
            xml_escape(&entity.label),
            xml_escape(&entity.entity_type),
        ));
    }

    for edge in graph.graph.edge_indices() {
        if let Some((src, tgt)) = graph.graph.edge_endpoints(edge) {
            let rel = &graph.graph[edge];
            let src_id = &graph.graph[src].id.0;
            let tgt_id = &graph.graph[tgt].id.0;
            xml.push_str(&format!(
                r#"    <edge source="{}" target="{}">
      <data key="relation_type">{}</data>
    </edge>
"#,
                xml_escape(src_id),
                xml_escape(tgt_id),
                xml_escape(&rel.relation_type),
            ));
        }
    }

    xml.push_str("  </graph>\n</graphml>\n");
    xml
}

fn xml_escape(s: &str) -> String {
    s.replace('&', "&amp;")
     .replace('<', "&lt;")
     .replace('>', "&gt;")
     .replace('"', "&quot;")
}
```

### 9.3 DOT (Graphviz)

```rust
/// Export to DOT format for Graphviz visualization
pub fn to_dot(graph: &PropertyGraph) -> String {
    let mut dot = String::from("digraph CodeGraph {\n");
    dot.push_str("  rankdir=LR;\n");
    dot.push_str("  node [shape=box, style=filled];\n\n");

    // Color mapping by entity type
    let colors = |t: &str| match t {
        "function" => "lightblue",
        "struct" => "lightyellow",
        "trait" => "lightgreen",
        "module" => "lightgray",
        "enum" => "lightsalmon",
        _ => "white",
    };

    for node in graph.graph.node_indices() {
        let entity = &graph.graph[node];
        let color = colors(&entity.entity_type);
        dot.push_str(&format!(
            "  \"{}\" [label=\"{}\\n({})\", fillcolor={}];\n",
            entity.id.0, entity.label, entity.entity_type, color,
        ));
    }

    dot.push('\n');

    for edge in graph.graph.edge_indices() {
        if let Some((src, tgt)) = graph.graph.edge_endpoints(edge) {
            let rel = &graph.graph[edge];
            let src_id = &graph.graph[src].id.0;
            let tgt_id = &graph.graph[tgt].id.0;
            dot.push_str(&format!(
                "  \"{}\" -> \"{}\" [label=\"{}\"];\n",
                src_id, tgt_id, rel.relation_type,
            ));
        }
    }

    dot.push_str("}\n");
    dot
}
```

### 9.4 Adjacency List

```rust
/// Export as adjacency list (compact text format)
/// Format: source_id -> target_id [relation_type]
pub fn to_adjacency_list(graph: &PropertyGraph) -> String {
    let mut result = String::new();

    for node in graph.graph.node_indices() {
        let entity = &graph.graph[node];
        let outgoing: Vec<String> = graph.graph
            .edges_directed(node, Direction::Outgoing)
            .map(|edge| {
                let target = &graph.graph[edge.target()];
                format!("{} [{}]", target.id.0, edge.weight().relation_type)
            })
            .collect();

        if !outgoing.is_empty() {
            result.push_str(&format!("{} -> {}\n", entity.id.0, outgoing.join(", ")));
        }
    }
    result
}
```

### 9.5 Edge List

```rust
/// Export as edge list (simplest format, one edge per line)
/// Format: source_id\ttarget_id\trelation_type
pub fn to_edge_list(graph: &PropertyGraph) -> String {
    let mut result = String::new();

    for edge in graph.graph.edge_indices() {
        if let Some((src, tgt)) = graph.graph.edge_endpoints(edge) {
            let rel = &graph.graph[edge];
            result.push_str(&format!(
                "{}\t{}\t{}\n",
                graph.graph[src].id.0,
                graph.graph[tgt].id.0,
                rel.relation_type,
            ));
        }
    }
    result
}

/// Import from edge list
pub fn from_edge_list(text: &str) -> Vec<(String, String, String)> {
    text.lines()
        .filter(|line| !line.trim().is_empty())
        .filter_map(|line| {
            let parts: Vec<&str> = line.split('\t').collect();
            if parts.len() >= 3 {
                Some((parts[0].to_string(), parts[1].to_string(), parts[2].to_string()))
            } else {
                None
            }
        })
        .collect()
}
```

### 9.6 Serde with petgraph (Rust)

petgraph supports serde natively with the `serde-1` feature.

```rust
use petgraph::graph::DiGraph;
use serde::{Serialize, Deserialize};

// With petgraph's serde-1 feature, DiGraph<N, E> is serializable
// if N: Serialize + Deserialize and E: Serialize + Deserialize

#[derive(Serialize, Deserialize)]
pub struct SerializableGraph {
    pub graph: DiGraph<Entity, Relation>,
    pub metadata: GraphMetadata,
}

#[derive(Serialize, Deserialize)]
pub struct GraphMetadata {
    pub version: String,
    pub created_at: String,
    pub source_root: String,
    pub file_count: usize,
    pub entity_count: usize,
    pub relation_count: usize,
}

impl SerializableGraph {
    /// Save to JSON file
    pub fn save_json(&self, path: &str) -> std::io::Result<()> {
        let file = std::fs::File::create(path)?;
        let writer = std::io::BufWriter::new(file);
        serde_json::to_writer_pretty(writer, self)?;
        Ok(())
    }

    /// Load from JSON file
    pub fn load_json(path: &str) -> std::io::Result<Self> {
        let file = std::fs::File::open(path)?;
        let reader = std::io::BufReader::new(file);
        let graph = serde_json::from_reader(reader)?;
        Ok(graph)
    }

    /// Save to bincode (much smaller, faster)
    pub fn save_bincode(&self, path: &str) -> std::io::Result<()> {
        let file = std::fs::File::create(path)?;
        let writer = std::io::BufWriter::new(file);
        bincode::serialize_into(writer, self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
    }

    /// Load from bincode
    pub fn load_bincode(path: &str) -> std::io::Result<Self> {
        let file = std::fs::File::open(path)?;
        let reader = std::io::BufReader::new(file);
        bincode::deserialize_from(reader)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
    }

    /// Save to MessagePack (good balance of size and compatibility)
    pub fn save_msgpack(&self, path: &str) -> std::io::Result<()> {
        let bytes = rmp_serde::to_vec(self)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))?;
        std::fs::write(path, bytes)
    }

    /// Load from MessagePack
    pub fn load_msgpack(path: &str) -> std::io::Result<Self> {
        let bytes = std::fs::read(path)?;
        rmp_serde::from_slice(&bytes)
            .map_err(|e| std::io::Error::new(std::io::ErrorKind::Other, e))
    }
}
```

---

## Quick Reference: Cargo.toml Dependencies

```toml
[dependencies]
petgraph = { version = "0.7", features = ["serde-1"] }
serde = { version = "1", features = ["derive"] }
serde_json = "1"
rusqlite = { version = "0.31", features = ["bundled"] }
tree-sitter = "0.22"
tree-sitter-rust = "0.21"
sha2 = "0.10"
bincode = "1"
rmp-serde = "1"
rand = "0.8"
```

---

## Summary of Key Decisions

| Decision | Recommended Default |
|----------|-------------------|
| Data model | Property graph (via petgraph) |
| Primary storage | SQLite with FTS5 |
| Serialization | JSONL for interchange, bincode for speed |
| Incremental updates | Watermark + file-level invalidation |
| Graph library (Rust) | petgraph with StableDiGraph |
| AST parsing | tree-sitter |
| Visualization | DOT export for Graphviz |
| Cross-file resolution | Name index + file proximity heuristic |
