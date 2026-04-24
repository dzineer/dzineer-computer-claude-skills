# Vector Databases and Similarity Search -- Comprehensive Reference

## 1. What is a Vector Database

A vector database stores, indexes, and queries **embedding vectors** -- dense numerical arrays that encode semantic meaning of text, code, images, or other data into high-dimensional space (typically 128-1536 dimensions).

### Why Traditional Indexes Fail for Vectors

Traditional B-tree and hash indexes work on discrete, low-dimensional data (strings, integers). They rely on exact match or range comparisons. Vectors break these assumptions:

- **High dimensionality**: A 384-dim vector has 384 independent axes. B-trees cannot partition this space efficiently.
- **Curse of dimensionality**: In high dimensions, all points become roughly equidistant. Range queries return either everything or nothing.
- **Semantic similarity**: We need "closest" not "equal" -- there is no useful equality or ordering for vectors.
- **No natural sort order**: You cannot sort 384-dimensional vectors in a single linear order that preserves proximity.

Vector databases solve this with specialized **approximate nearest neighbor (ANN)** index structures that trade a small amount of accuracy for orders-of-magnitude speedup.

### Core Operations

```
Text/Code --> Embedding Model --> [0.12, -0.45, 0.78, ...] (vector)
                                          |
                                    Vector Database
                                    - Store (upsert)
                                    - Index (build ANN structure)
                                    - Search (find k nearest neighbors)
                                    - Filter (metadata predicates)
```

---

## 2. Embedding Models

### What Are Text Embeddings

Text embeddings are dense vector representations produced by transformer encoder models. The process:

1. **Tokenization**: Text is split into sub-word tokens (WordPiece, BPE, SentencePiece)
2. **Transformer encoding**: Tokens pass through multiple self-attention layers that capture contextual relationships
3. **Pooling**: Token-level representations are aggregated (mean pooling, CLS token, or learned pooling) into a single fixed-size vector
4. **Normalization**: Output vector is L2-normalized to unit length (for cosine similarity)

The result: semantically similar text produces vectors that are close together in the embedding space.

### Model Comparison

| Model | Dimensions | Size | Quality | Speed | Use Case |
|-------|-----------|------|---------|-------|----------|
| all-MiniLM-L6-v2 | 384 | 23MB | Good | Very Fast | General purpose, small footprint |
| BGE-small-en-v1.5 | 384 | 34MB | Better | Fast | Retrieval-optimized, MTEB leader |
| nomic-embed-text-v1.5 | 768 | 137MB | Very Good | Medium | Long context (8192 tokens), Matryoshka |
| OpenAI text-embedding-ada-002 | 1536 | API-only | Excellent | API latency | Highest quality, requires network |
| BGE-M3 | 1024 | 570MB | Excellent | Slow | Multilingual, multi-granularity |

### Dimensions vs Quality Tradeoffs

- **Lower dimensions (384)**: Faster search, less memory, slightly lower semantic fidelity. Ideal for <100K documents or constrained environments.
- **Medium dimensions (768)**: Good balance. Recommended for most production use cases.
- **Higher dimensions (1024-1536)**: Better semantic capture, but diminishing returns past ~768. 4x memory cost of 384-dim. Search time scales linearly with dimensions.
- **Matryoshka embeddings** (nomic, some BGE models): Trained to be useful at truncated dimensions. You can use the first 256 dims of a 768-dim model with moderate quality loss, enabling adaptive precision.

### Local Embedding in Rust: fastembed

The `fastembed` crate runs ONNX models locally with zero configuration. It auto-downloads models from HuggingFace on first use.

```toml
# Cargo.toml
[dependencies]
fastembed = "5"
```

```rust
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};

// Initialize with a specific model
let model = TextEmbedding::try_new(
    InitOptions::new(EmbeddingModel::AllMiniLML6V2)
        .with_show_download_progress(true),
)?;

// Embed documents (returns Vec<Vec<f32>>)
let documents = vec![
    "Rust's ownership model prevents data races at compile time",
    "The borrow checker ensures memory safety without garbage collection",
    "Python uses reference counting with a cycle collector for memory management",
];
let embeddings = model.embed(documents, None)?;

// Each embedding is a Vec<f32> with dimensionality matching the model
assert_eq!(embeddings.len(), 3);
assert_eq!(embeddings[0].len(), 384); // all-MiniLM-L6-v2 = 384 dims

// Embed a single query
let query_embedding = model.embed(vec!["memory safety in systems programming"], None)?;
```

**Key fastembed models (EmbeddingModel enum)**:

- `AllMiniLML6V2` / `AllMiniLML6V2Q` -- 384 dims, fastest, good quality
- `AllMiniLML12V2` / `AllMiniLML12V2Q` -- 384 dims, slightly better quality
- `BGESmallENV15` / `BGESmallENV15Q` -- 384 dims, retrieval-optimized
- `BGEBaseENV15` / `BGEBaseENV15Q` -- 768 dims
- `BGELargeENV15` / `BGELargeENV15Q` -- 1024 dims
- `NomicEmbedTextV1` / `NomicEmbedTextV15` -- 768 dims, long context
- `BGEM3` -- 1024 dims, multilingual
- `JinaEmbeddingsV2BaseCode` -- 768 dims, code-optimized
- `JinaEmbeddingsV2BaseEN` -- 768 dims, English
- `MultilingualE5Small` / `MultilingualE5Base` / `MultilingualE5Large` -- multilingual
- `SnowflakeArcticEmbedM` / variants -- various sizes
- `ClipVitB32` -- multimodal (text + image)

Quantized variants (suffix `Q`) use INT8 quantization: ~4x smaller, ~2x faster, minimal quality loss.

### Chunking Strategies

#### Fixed-size chunking
Split text every N tokens/characters with optional overlap.
```
Chunk 1: tokens[0..512]
Chunk 2: tokens[448..960]   // 64-token overlap
Chunk 3: tokens[896..1408]
```
Simple but can split mid-sentence or mid-concept.

#### Sentence-level chunking
Split at sentence boundaries, group sentences until target size reached. Better semantic coherence.

#### Semantic chunking
Embed each sentence, split when cosine similarity between consecutive sentences drops below threshold. Groups semantically related content together.

#### Code-aware chunking (most important for code)
```
Per-function: Each function/method becomes one chunk
Per-class:    Class definition + all methods as one chunk
Per-file:     Entire file as one chunk (only for small files <500 lines)
AST-aware:    Use tree-sitter to split at AST node boundaries
              (function_definition, class_definition, impl_block)
```

#### Observation-based (for knowledge graphs)
Concatenate entity metadata into a single embedding document:
```
"Entity: AuthService | Type: struct | Module: auth |
 Observations: Handles JWT token validation. Implements the Authenticator trait.
 Depends on TokenStore for persistence. Has methods: validate(), refresh(), revoke()."
```

---

## 3. Distance Metrics

### Cosine Similarity (most common for text embeddings)

Measures the angle between two vectors, ignoring magnitude.

```
cosine_similarity(a, b) = dot(a, b) / (||a|| * ||b||)

Range: [-1, 1]  (1 = identical direction, 0 = orthogonal, -1 = opposite)
cosine_distance = 1 - cosine_similarity
Range: [0, 2]   (0 = identical, 2 = opposite)
```

**When to use**: Text embeddings (most embedding models L2-normalize their output, so cosine similarity equals dot product). Default choice for semantic search.

**Normalization**: If vectors are already L2-normalized (unit length), cosine similarity = dot product. Most embedding models output normalized vectors, but always verify.

```rust
fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b).map(|(x, y)| x * y).sum();
    let norm_a: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let norm_b: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    dot / (norm_a * norm_b)
}
```

### Euclidean Distance (L2)

Straight-line distance in the vector space.

```
L2(a, b) = sqrt(sum((a_i - b_i)^2))

Range: [0, infinity)  (0 = identical)
```

**When to use**: When magnitude matters (e.g., vectors encode intensity or frequency, not just direction). Image embeddings, some scientific data.

**Normalization**: If vectors are L2-normalized, L2 distance is monotonically related to cosine distance: `L2^2 = 2 - 2*cos_sim`. So for normalized vectors, L2 and cosine give equivalent rankings.

### Dot Product (Inner Product)

```
dot(a, b) = sum(a_i * b_i)

Range: (-infinity, infinity)  (higher = more similar)
```

**When to use**: When vectors are already normalized (equivalent to cosine similarity). Also used when magnitude encodes relevance (e.g., popularity-weighted embeddings). Fastest to compute (no normalization step).

### Manhattan Distance (L1)

```
L1(a, b) = sum(|a_i - b_i|)

Range: [0, infinity)  (0 = identical)
```

**When to use**: Sparse or discrete features, high-dimensional spaces where L2 distance concentrates. Less common for dense text embeddings.

### Metric Selection Guide

| Scenario | Metric | Reason |
|----------|--------|--------|
| Text search (embeddings from sentence-transformers) | Cosine | Standard for normalized text embeddings |
| Pre-normalized vectors | Dot Product | Fastest, equivalent to cosine for unit vectors |
| Image similarity | Euclidean (L2) | Magnitude can be meaningful |
| Binary/sparse features | Hamming / L1 | Efficient for discrete data |
| Recommendation systems | Dot Product | Magnitude encodes popularity/relevance |

---

## 4. Indexing Algorithms (ANN -- Approximate Nearest Neighbor)

### HNSW (Hierarchical Navigable Small World)

The dominant ANN algorithm. Used by usearch, qdrant, chromadb, pgvector, Milvus.

**How it works:**

1. **Multi-layer graph**: Builds a hierarchy of navigable small world graphs. Layer 0 contains all vectors. Each higher layer contains an exponentially decreasing subset (controlled by `mL = 1/ln(M)`).

2. **Construction**: When inserting a vector, a random maximum layer `l` is drawn from an exponential distribution. The vector is added to layers 0 through `l`. At each layer, it connects to its M nearest already-inserted neighbors via greedy search.

3. **Search (query time)**:
   - Start at the entry point (a node in the highest layer)
   - **Greedy descent**: At each layer, greedily walk to the nearest neighbor of the query. When no closer neighbor exists, descend to the next layer.
   - **Beam search at layer 0**: At the bottom layer, perform a beam search with width `efSearch`, maintaining a priority queue of candidates. Return the top-k results.

4. **Key parameters**:
   - `M`: Max connections per node per layer (typical: 16-64). Higher M = better recall, more memory, slower build.
   - `M0`: Max connections at layer 0 (typically 2*M).
   - `efConstruction`: Beam width during index build (typical: 100-200). Higher = better index quality, slower build.
   - `efSearch`: Beam width during query (typical: 50-200). Higher = better recall, slower query. Tunable at query time.

```
Layer 3:  [A] ---- [D]                    (few nodes, long-range links)
Layer 2:  [A] -- [C] -- [D] -- [F]        (more nodes, medium links)
Layer 1:  [A]-[B]-[C]-[D]-[E]-[F]-[G]     (most nodes, short links)
Layer 0:  [A][B][C][D][E][F][G][H][I][J]   (all nodes, local links)

Query: Start at top layer entry point, greedily descend,
       beam search at layer 0 for final results.
```

**Complexity**: Build O(N log N), Search O(log N), Memory O(N * M)

### IVF (Inverted File Index)

Used by FAISS. Partitions vector space using Voronoi cells.

**How it works:**

1. **Training**: K-means clustering divides all vectors into `nlist` clusters (centroids).
2. **Indexing**: Each vector is assigned to its nearest centroid. Vectors within each cluster are stored in an inverted list.
3. **Search**: Query vector is compared to all centroids. The `nprobe` nearest clusters are searched exhaustively.

**Key parameters**:
- `nlist`: Number of clusters (typical: sqrt(N) to 4*sqrt(N))
- `nprobe`: Number of clusters to search (typical: 1-nlist, tradeoff recall vs speed)

**Tradeoff**: Fast search but requires training data upfront. Not incremental -- adding vectors requires periodic re-training. Best for static, very large datasets (>1M vectors).

### Product Quantization (PQ)

Compression technique, often combined with IVF (IVF-PQ).

**How it works:**

1. **Sub-vector splitting**: Each D-dimensional vector is split into `m` sub-vectors of D/m dimensions.
2. **Codebook learning**: For each sub-vector group, k-means learns a codebook of 256 centroids (1 byte per sub-vector).
3. **Encoding**: Each vector is represented by m bytes (its centroid IDs), instead of D*4 bytes (raw floats).
4. **Search**: Distance computed using precomputed lookup tables (Asymmetric Distance Computation).

**Memory savings example**: 768-dim float32 vector = 3072 bytes. With PQ (m=96 sub-vectors) = 96 bytes. **32x compression**.

**Tradeoff**: Lossy compression. Recall drops compared to flat index, but enables billion-scale search in RAM.

### Random Projection / LSH (Locality-Sensitive Hashing)

Used by Annoy (Spotify), arroy (Meilisearch).

**How it works:**

1. **Random hyperplanes**: Choose random hyperplanes that split the vector space in half.
2. **Binary encoding**: Each vector gets a binary hash based on which side of each hyperplane it falls on.
3. **Tree structure**: Build binary trees where each internal node is a random split. Leaves contain clusters of similar vectors.
4. **Multiple trees**: Build `n_trees` independent random trees. At query time, collect candidate sets from all trees and compute exact distances.

**Tradeoff**: Simple, fast builds, but lower recall than HNSW for same memory. Works well when you can afford many trees. Memory-mappable (Annoy/arroy use LMDB).

### Flat / Brute-Force

Compute distance from query to every stored vector. **Exact** nearest neighbors.

**When to use**: Dataset < 10K vectors, or as a baseline for recall measurement. Some libraries (usearch, FAISS) offer SIMD-accelerated brute-force that handles up to ~100K vectors in acceptable time.

### Algorithm Comparison

| Algorithm | Recall@10 | QPS (1M vecs) | Memory | Build Time | Incremental | Best For |
|-----------|-----------|---------------|--------|------------|-------------|----------|
| HNSW | 95-99% | 5K-50K | High (M*N*4B) | Medium | Yes (add/remove) | General purpose, <100M vecs |
| IVF-PQ | 85-95% | 10K-100K | Low (compressed) | Slow (training) | No (rebuild) | Billion-scale, static data |
| IVF-Flat | 95-99% | 1K-10K | High | Slow (training) | No (rebuild) | Large static, high recall |
| Random Proj | 85-95% | 5K-20K | Medium | Fast | No (rebuild trees) | Memory-mapped, multi-process |
| Flat | 100% | 100-1K | Baseline | None | Yes | <10K vectors, ground truth |

---

## 5. Vector Database Options for Rust (Local, No Network)

### usearch -- Minimal HNSW

The simplest option. Single-header C++ core with Rust bindings. HNSW algorithm with SIMD acceleration.

```toml
[dependencies]
usearch = "2"
```

```rust
use usearch::{Index, IndexOptions, MetricKind, ScalarKind};

// --- CREATE INDEX ---
let mut options = IndexOptions::default();
options.dimensions = 384;           // Must match your embedding model
options.metric = MetricKind::Cos;   // Cosine similarity
options.quantization = ScalarKind::F32;  // Storage precision

let index = Index::new(&options).expect("Failed to create index");
index.reserve(100_000).expect("Failed to reserve capacity");

// --- ADD VECTORS ---
let embedding: Vec<f32> = vec![0.1; 384]; // From your embedding model
let key: u64 = 42;                        // Unique ID for this vector
index.add(key, &embedding).expect("Failed to add vector");

// Add multiple vectors
for (id, vec) in vectors.iter().enumerate() {
    index.add(id as u64, vec).expect("Failed to add");
}

// --- SEARCH ---
let query: Vec<f32> = vec![0.2; 384]; // Query embedding
let k = 10; // Number of results
let results = index.search(&query, k).expect("Search failed");

for (key, distance) in results.keys.iter().zip(results.distances.iter()) {
    let similarity = 1.0 - distance; // Cosine distance -> similarity
    println!("ID: {}, Similarity: {:.4}", key, similarity);
}

// --- PERSISTENCE ---
index.save("index.usearch").expect("Failed to save");

// Later, load it back
let loaded_index = Index::new(&options).expect("Failed to create index");
loaded_index.load("index.usearch").expect("Failed to load");
loaded_index.search(&query, k).expect("Search on loaded index");

// --- REMOVE ---
index.remove(42).expect("Failed to remove vector");

// --- INFO ---
println!("Size: {}", index.size());       // Number of vectors
println!("Capacity: {}", index.capacity()); // Reserved capacity
println!("Dimensions: {}", index.dimensions());
```

**Pros**: Minimal API, very fast, SIMD-accelerated, custom metrics possible, supports f16/i8/binary vectors.
**Cons**: No metadata filtering, no built-in persistence format beyond flat file, no query language.

### lancedb -- Persistent Columnar Vector Store

Full-featured embedded vector database using the Lance columnar format. Supports metadata, versioning, filtering.

```toml
[dependencies]
lancedb = "0.23"
arrow-array = "53"
arrow-schema = "53"
tokio = { version = "1", features = ["full"] }
```

```rust
use std::sync::Arc;
use arrow_array::{
    Int32Array, StringArray, Float32Array, FixedSizeListArray,
    RecordBatch, RecordBatchIterator,
    types::Float32Type,
};
use arrow_schema::{DataType, Field, Schema};
use lancedb::index::Index;

#[tokio::main]
async fn main() -> Result<(), Box<dyn std::error::Error>> {
    // --- CONNECT ---
    let db = lancedb::connect("data/my-vector-db").execute().await?;

    // --- DEFINE SCHEMA ---
    let dims: i32 = 384;
    let schema = Arc::new(Schema::new(vec![
        Field::new("id", DataType::Int32, false),
        Field::new("text", DataType::Utf8, true),
        Field::new("entity_type", DataType::Utf8, true),
        Field::new(
            "vector",
            DataType::FixedSizeList(
                Arc::new(Field::new("item", DataType::Float32, true)),
                dims,
            ),
            true,
        ),
    ]));

    // --- CREATE TABLE WITH DATA ---
    let ids = Int32Array::from(vec![1, 2, 3]);
    let texts = StringArray::from(vec!["fn main()", "struct Config", "trait Handler"]);
    let types = StringArray::from(vec!["function", "struct", "trait"]);
    let vectors = FixedSizeListArray::from_iter_primitive::<Float32Type, _, _>(
        (0..3).map(|i| Some(vec![Some(i as f32 * 0.1); dims as usize])),
        dims,
    );

    let batch = RecordBatch::try_new(
        schema.clone(),
        vec![
            Arc::new(ids),
            Arc::new(texts),
            Arc::new(types),
            Arc::new(vectors),
        ],
    )?;

    let table = db.create_table("code_entities", batch)
        .execute()
        .await?;

    // --- CREATE VECTOR INDEX (for large tables) ---
    table.create_index(&["vector"], Index::Auto)
        .execute()
        .await?;

    // --- VECTOR SEARCH ---
    let query_vec: Vec<f32> = vec![0.1; dims as usize];
    let results = table.query()
        .nearest_to(&query_vec)?
        .limit(10)
        .execute()
        .await?
        .try_collect::<Vec<_>>()
        .await?;

    // --- VECTOR SEARCH WITH METADATA FILTER ---
    let filtered_results = table.query()
        .nearest_to(&query_vec)?
        .limit(5)
        .only_if("entity_type = 'function'")  // SQL-like filter
        .execute()
        .await?
        .try_collect::<Vec<_>>()
        .await?;

    // --- DELETE ---
    table.delete("id = 3").await?;

    // --- UPSERT (merge by key) ---
    // Add new data with merge_insert
    let new_batch = /* ... build a RecordBatch ... */;
    table.merge_insert(&["id"])
        .when_matched_update_all()
        .when_not_matched_insert_all()
        .execute(Box::new(RecordBatchIterator::new(
            vec![Ok(new_batch)],
            schema.clone(),
        )))
        .await?;

    Ok(())
}
```

**Pros**: Persistent, versioned, metadata filtering, SQL-like queries, auto-indexing (IVF-PQ), columnar compression.
**Cons**: Heavier dependency (arrow ecosystem), async-only API, Rust API not fully stable yet.

### arroy -- LMDB-backed, Multi-process Safe

Built by Meilisearch. Uses random projection trees stored in LMDB. Memory-mapped, so multiple processes can read concurrently.

```toml
[dependencies]
arroy = "0.5"
heed = "0.20"       # LMDB bindings
rand = "0.8"
tempfile = "3"
```

```rust
use std::num::NonZeroUsize;
use arroy::distances::Cosine;  // Also: Euclidean, Manhattan, DotProduct
use arroy::{Database as ArroyDatabase, Writer, Reader};
use rand::rngs::StdRng;
use rand::SeedableRng;

const TWO_GIB: usize = 2 * 1024 * 1024 * 1024;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    // --- SETUP LMDB ---
    let dir = tempfile::tempdir()?;
    let env = unsafe {
        heed::EnvOpenOptions::new()
            .map_size(TWO_GIB)
            .open(dir.path())?
    };

    // --- CREATE DATABASE ---
    let mut wtxn = env.write_txn()?;
    let db: ArroyDatabase<Cosine> = env.create_database(&mut wtxn, None)?;

    // --- WRITE VECTORS ---
    let index = 0;       // You can have multiple indexes in one DB
    let dimensions = 384;
    let writer = Writer::<Cosine>::new(db, index, dimensions);

    writer.add_item(&mut wtxn, 0, &vec![0.1; 384])?;
    writer.add_item(&mut wtxn, 1, &vec![0.2; 384])?;
    writer.add_item(&mut wtxn, 2, &vec![0.3; 384])?;
    writer.add_item(&mut wtxn, 3, &vec![0.4; 384])?;

    // --- BUILD INDEX ---
    let mut rng = StdRng::seed_from_u64(42);
    writer.builder(&mut rng)
        .n_trees(10)         // More trees = better recall, more memory
        .build(&mut wtxn)?;

    wtxn.commit()?;  // Now readers can query

    // --- SEARCH ---
    let rtxn = env.read_txn()?;
    let reader = Reader::<Cosine>::open(&rtxn, index, db)?;

    let n_results = 10;
    let mut query = reader.nns(n_results);

    // Optional: increase search quality
    query.search_k(
        NonZeroUsize::new(n_results * reader.n_trees() * 15).unwrap()
    );

    // Search by vector
    let query_vec = vec![0.15; 384];
    let results = query.by_vector(&rtxn, &query_vec)?.unwrap();
    for (item_id, distance) in &results {
        println!("Item: {}, Distance: {:.4}", item_id, distance);
    }

    // Search by existing item ID (find similar items)
    let similar = reader.nns(5).by_item(&rtxn, 0)?.unwrap();

    // --- DELETE ---
    let mut wtxn2 = env.write_txn()?;
    let writer2 = Writer::<Cosine>::new(db, index, dimensions);
    writer2.del_item(&mut wtxn2, 3)?;
    // Must rebuild after modifications
    writer2.builder(&mut rng).build(&mut wtxn2)?;
    wtxn2.commit()?;

    Ok(())
}
```

**Pros**: LMDB memory-mapping (zero-copy reads), multi-process safe, ACID transactions, very memory efficient.
**Cons**: Must rebuild index after modifications (not incremental), random projection has lower recall than HNSW.

**Note**: Meilisearch v1.29+ uses **hannoy** (HNSW + LMDB), the successor to arroy, offering ~10x faster search and 2x smaller index. The `hannoy` crate may be available separately.

### hora -- Multiple Algorithms

Pure Rust library supporting HNSW, SSG, PQIVF, and brute-force. SIMD acceleration.

```toml
[dependencies]
hora = "0.1"
```

```rust
use hora::core::ann_index::ANNIndex;
use hora::index::hnsw_idx::HNSWIndex;

fn main() -> Result<(), Box<dyn std::error::Error>> {
    let dimensions = 384;

    // --- CREATE HNSW INDEX ---
    let mut index = HNSWIndex::<f32, usize>::new(
        dimensions,
        &hora::index::hnsw_params::HNSWParams::<f32>::default(),
    );

    // --- ADD VECTORS ---
    index.add(&vec![0.1; 384], 0)?;  // (vector, id)
    index.add(&vec![0.2; 384], 1)?;
    index.add(&vec![0.3; 384], 2)?;

    // --- BUILD INDEX ---
    index.build(hora::core::metrics::Metric::Euclidean)?;

    // --- SEARCH ---
    let results: Vec<usize> = index.search(&vec![0.15; 384], 5);  // returns IDs
    println!("Nearest neighbors: {:?}", results);

    Ok(())
}
```

**Pros**: Pure Rust, multiple algorithm choices, SIMD.
**Cons**: Less actively maintained (last update 2022), minimal documentation, no persistence built-in.

### qdrant -- Server Mode (not truly embeddable)

Qdrant is primarily a client-server architecture. There is no official "embedded mode" crate. You must run the Qdrant server process and connect via gRPC/HTTP. Not suitable for a local-only, in-process solution. Use usearch or lancedb instead.

### SQLite + sqlite-vec Extension

Brute-force vector search inside SQLite using virtual tables. Ideal when you already use SQLite for metadata.

```toml
[dependencies]
rusqlite = { version = "0.31", features = ["bundled"] }
sqlite-vec = "0.1"
zerocopy = { version = "0.7", features = ["derive"] }
```

```rust
use rusqlite::{ffi::sqlite3_auto_extension, Connection, Result};
use sqlite_vec::sqlite3_vec_init;
use zerocopy::AsBytes;

fn main() -> Result<()> {
    // --- LOAD EXTENSION ---
    unsafe {
        sqlite3_auto_extension(Some(
            std::mem::transmute(sqlite3_vec_init as *const ())
        ));
    }

    let db = Connection::open("vectors.db")?;

    // --- CREATE VIRTUAL TABLE ---
    db.execute(
        "CREATE VIRTUAL TABLE IF NOT EXISTS vec_items USING vec0(
            embedding float[384]
        )",
        [],
    )?;

    // --- INSERT VECTORS ---
    let items: Vec<(i64, Vec<f32>)> = vec![
        (1, vec![0.1; 384]),
        (2, vec![0.2; 384]),
        (3, vec![0.3; 384]),
    ];

    let mut stmt = db.prepare(
        "INSERT INTO vec_items(rowid, embedding) VALUES (?, ?)"
    )?;
    for (id, vec) in &items {
        stmt.execute(rusqlite::params![id, vec.as_bytes()])?;
    }

    // --- VECTOR SEARCH (KNN) ---
    let query: Vec<f32> = vec![0.15; 384];
    let results: Vec<(i64, f64)> = db
        .prepare(
            "SELECT rowid, distance
             FROM vec_items
             WHERE embedding MATCH ?1
             ORDER BY distance
             LIMIT 10"
        )?
        .query_map([query.as_bytes()], |row| {
            Ok((row.get(0)?, row.get(1)?))
        })?
        .collect::<Result<Vec<_>, _>>()?;

    for (id, distance) in &results {
        println!("ID: {}, Distance: {:.4}", id, distance);
    }

    // --- DELETE ---
    db.execute("DELETE FROM vec_items WHERE rowid = 3", [])?;

    // --- UPSERT (via INSERT OR REPLACE) ---
    db.execute(
        "INSERT OR REPLACE INTO vec_items(rowid, embedding) VALUES (?, ?)",
        rusqlite::params![1, vec![0.15f32; 384].as_bytes()],
    )?;

    Ok(())
}
```

**Pros**: Familiar SQL, metadata joins with regular tables, single-file database, ACID, works everywhere SQLite works.
**Cons**: Brute-force only (no ANN index), O(N) search. Fine for <100K vectors, too slow for millions.

### tinyvector

Minimal in-memory vector store. ~600 lines of Rust. Good for prototyping but not production. No crate published -- typically vendored as source. Brute-force search only.

---

## 6. Hybrid Search (Vector + Text)

### Why Hybrid Search

Vector search captures semantic similarity ("meaning") but can miss exact keyword matches. Full-text search (BM25) captures exact terms but misses paraphrases. Combining both gives the best retrieval quality.

### Score Normalization and Weighted Combination

```rust
/// Normalize a score to [0, 1] range using min-max normalization
fn normalize_score(score: f32, min: f32, max: f32) -> f32 {
    if (max - min).abs() < f32::EPSILON {
        return 0.5;
    }
    (score - min) / (max - min)
}

/// Weighted combination of vector and text search scores
fn hybrid_score(
    vector_similarity: f32,  // Already 0-1 (cosine similarity)
    bm25_score: f32,         // Raw BM25 score, needs normalization
    bm25_min: f32,
    bm25_max: f32,
    vector_weight: f32,      // Typical: 0.6
    text_weight: f32,        // Typical: 0.4
) -> f32 {
    let norm_bm25 = normalize_score(bm25_score, bm25_min, bm25_max);
    vector_weight * vector_similarity + text_weight * norm_bm25
}
```

### Reciprocal Rank Fusion (RRF)

RRF merges ranked lists by position rather than score. This avoids the score normalization problem entirely.

```
RRF_score(doc) = SUM over each ranker r:  weight_r / (k + rank_r(doc))

where k is a constant (typically 60) that dampens the effect of high rankings.
```

```rust
use std::collections::HashMap;

/// Reciprocal Rank Fusion
/// results: Vec of ranked lists, each list is Vec<(doc_id, _score)> in rank order
/// k: smoothing constant (default 60)
/// weights: per-list weight (default all 1.0)
fn reciprocal_rank_fusion(
    result_lists: &[Vec<String>],  // Each list: doc IDs in rank order
    weights: &[f32],               // Weight per list
    k: f32,                        // Smoothing constant (typically 60)
) -> Vec<(String, f32)> {
    let mut scores: HashMap<String, f32> = HashMap::new();

    for (list_idx, list) in result_lists.iter().enumerate() {
        let weight = weights.get(list_idx).copied().unwrap_or(1.0);
        for (rank, doc_id) in list.iter().enumerate() {
            let rrf_score = weight / (k + (rank as f32 + 1.0));
            *scores.entry(doc_id.clone()).or_insert(0.0) += rrf_score;
        }
    }

    let mut merged: Vec<(String, f32)> = scores.into_iter().collect();
    merged.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap());
    merged
}

// Usage:
let vector_results = vec!["doc_a", "doc_c", "doc_b"];  // Ranked by cosine sim
let bm25_results = vec!["doc_b", "doc_a", "doc_d"];    // Ranked by BM25

let fused = reciprocal_rank_fusion(
    &[
        vector_results.iter().map(|s| s.to_string()).collect(),
        bm25_results.iter().map(|s| s.to_string()).collect(),
    ],
    &[0.6, 0.4],  // Weight vector search higher
    60.0,
);
// Result: doc_a (appears high in both) > doc_b > doc_c > doc_d
```

### De-duplication

When merging results from vector and text search, the same document may appear in both lists. Use a HashMap keyed by document ID to accumulate scores and naturally de-duplicate.

### Metadata Boosting

Apply score multipliers based on metadata:

```rust
fn apply_boost(base_score: f32, entity_type: &str, is_public: bool) -> f32 {
    let mut boost = 1.0f32;

    // Boost public APIs higher
    if is_public { boost *= 1.2; }

    // Boost structs and traits over internal functions
    match entity_type {
        "trait" => boost *= 1.3,
        "struct" => boost *= 1.1,
        "function" => boost *= 1.0,
        _ => boost *= 0.9,
    }

    base_score * boost
}
```

---

## 7. Metadata Filtering

### Pre-filter vs Post-filter

**Pre-filter** (filter BEFORE ANN search):
- Apply metadata predicates to narrow the candidate set before running vector search.
- Pros: Faster search (smaller candidate set). Guarantees all results match filter.
- Cons: May degrade ANN recall if filter is very selective (too few candidates for HNSW to navigate effectively).
- Used by: LanceDB, Qdrant.

**Post-filter** (filter AFTER ANN search):
- Run ANN search first to get top-K candidates, then filter by metadata.
- Pros: ANN recall unaffected. Simple implementation.
- Cons: May return fewer than K results if many candidates are filtered out. Must over-fetch (search for 5x K, then filter to K).
- Used by: Simple implementations, sqlite-vec (via SQL WHERE).

**Best practice**: Pre-filter when filter selectivity is moderate (>10% of data passes). Post-filter for very broad filters. Some databases (Qdrant, LanceDB) use adaptive strategies.

### Common Filter Fields for Code Search

```rust
struct EntityMetadata {
    entity_type: String,    // "function", "struct", "trait", "module"
    module: String,         // "auth::jwt", "db::queries"
    language: String,       // "rust", "typescript"
    file_path: String,      // "src/auth/jwt.rs"
    visibility: String,     // "pub", "pub(crate)", "private"
    last_modified: i64,     // Unix timestamp
}
```

### Performance Implications

- Pre-filtering on indexed metadata columns: O(log N) filter + ANN search on subset
- Post-filtering: Full ANN search O(log N) + linear scan filter O(K)
- Highly selective filters (<1% pass rate) with pre-filtering: ANN quality may suffer, consider brute-force on the filtered subset

---

## 8. Chunking Strategies for Code

### Per-function Chunks (Recommended Default)

```rust
// Each function becomes one document for embedding
// Chunk text: "fn validate_token(token: &str) -> Result<Claims, AuthError> { ... }"
// Metadata: { entity_type: "function", module: "auth", file: "src/auth.rs" }
```

Best for: Most codebases. Functions are natural semantic units. Embedding captures what the function does.

### Per-class / Per-impl-block Chunks

```rust
// Entire impl block as one chunk
// "impl AuthService { fn new() { ... } fn validate() { ... } fn refresh() { ... } }"
// Captures the full interface of a type
```

Best for: When you want to find "which type handles authentication?" rather than individual methods.

### Per-file Chunks

Only viable for small files (<300 lines). Embedding quality degrades for very long text (most models truncate at 512 tokens).

### Sliding Window with Overlap

```rust
fn sliding_window_chunks(text: &str, window_size: usize, overlap: usize) -> Vec<String> {
    let words: Vec<&str> = text.split_whitespace().collect();
    let mut chunks = Vec::new();
    let mut start = 0;
    while start < words.len() {
        let end = (start + window_size).min(words.len());
        chunks.push(words[start..end].join(" "));
        start += window_size - overlap;
    }
    chunks
}
```

### AST-aware Chunking

Use tree-sitter to parse code and split at AST node boundaries:

```rust
// Pseudocode for AST-aware chunking
fn ast_chunk(source: &str, language: tree_sitter::Language) -> Vec<Chunk> {
    let mut parser = tree_sitter::Parser::new();
    parser.set_language(language).unwrap();
    let tree = parser.parse(source, None).unwrap();

    let mut chunks = Vec::new();
    let root = tree.root_node();

    for child in root.children(&mut root.walk()) {
        match child.kind() {
            "function_item" | "impl_item" | "struct_item"
            | "enum_item" | "trait_item" | "mod_item" => {
                let text = &source[child.byte_range()];
                chunks.push(Chunk {
                    text: text.to_string(),
                    node_kind: child.kind().to_string(),
                    byte_range: child.byte_range(),
                });
            }
            _ => {} // Skip use statements, comments, etc.
        }
    }
    chunks
}
```

### Observation Text as Documents

For knowledge graph entities, concatenate structured data into embeddable text:

```rust
fn entity_to_embedding_text(entity: &Entity) -> String {
    format!(
        "Entity: {} | Type: {} | Module: {} | Observations: {}",
        entity.name,
        entity.entity_type,
        entity.module,
        entity.observations.join(". "),
    )
}
// Example output:
// "Entity: AuthService | Type: struct | Module: auth |
//  Observations: Handles JWT validation. Implements Authenticator trait.
//  Has methods validate(), refresh(), revoke()."
```

---

## 9. Persistence and Updates

### Upsert (Add or Replace by ID)

```rust
// usearch: remove + add
fn upsert_usearch(index: &Index, key: u64, vector: &[f32]) -> Result<()> {
    let _ = index.remove(key); // Ignore error if not found
    index.add(key, vector)?;
    Ok(())
}

// sqlite-vec: INSERT OR REPLACE
db.execute(
    "INSERT OR REPLACE INTO vec_items(rowid, embedding) VALUES (?, ?)",
    params![id, vector.as_bytes()],
)?;

// lancedb: merge_insert
table.merge_insert(&["id"])
    .when_matched_update_all()
    .when_not_matched_insert_all()
    .execute(Box::new(batch_iter))
    .await?;
```

### Delete by ID

```rust
// usearch
index.remove(42)?;

// arroy (requires rebuild after)
writer.del_item(&mut wtxn, 42)?;
writer.builder(&mut rng).build(&mut wtxn)?;

// sqlite-vec
db.execute("DELETE FROM vec_items WHERE rowid = ?", [42])?;

// lancedb
table.delete("id = 42").await?;
```

### Delete by Metadata Filter

```rust
// lancedb -- SQL-like filter
table.delete("entity_type = 'function' AND module = 'deprecated'").await?;

// sqlite-vec -- join with metadata table
db.execute(
    "DELETE FROM vec_items WHERE rowid IN (
        SELECT id FROM entities WHERE entity_type = 'function' AND module = 'deprecated'
    )",
    [],
)?;
```

### Incremental Indexing

Only embed new or changed entities:

```rust
use std::collections::HashMap;

fn incremental_update(
    store: &mut dyn VectorStore,
    embedder: &TextEmbedding,
    entities: &[Entity],
    existing_hashes: &HashMap<String, u64>,  // id -> content hash
) -> Result<()> {
    let mut to_embed = Vec::new();

    for entity in entities {
        let content = entity_to_embedding_text(entity);
        let hash = seahash::hash(content.as_bytes());

        match existing_hashes.get(&entity.id) {
            Some(&old_hash) if old_hash == hash => continue, // Unchanged
            Some(_) => {
                // Changed: delete old, will re-add
                store.delete(&entity.id)?;
            }
            None => {} // New entity
        }
        to_embed.push((entity.id.clone(), content, hash));
    }

    if !to_embed.is_empty() {
        let texts: Vec<&str> = to_embed.iter().map(|(_, t, _)| t.as_str()).collect();
        let embeddings = embedder.embed(texts, None)?;

        for ((id, _, hash), embedding) in to_embed.iter().zip(embeddings) {
            store.upsert(id, &embedding, hash)?;
        }
    }

    Ok(())
}
```

### Index Rebuild Strategies

- **HNSW (usearch)**: Incremental by nature. add/remove are O(log N). No rebuild needed.
- **Random projection (arroy)**: Must call `writer.builder().build()` after any modification. Full rebuild.
- **IVF-PQ (lancedb)**: Rebuild index periodically when >20% of data has changed. Use `table.create_index()` to rebuild.
- **sqlite-vec**: No index to rebuild (brute-force). Insertions and deletions are immediate.

---

## 10. Rust Implementation Patterns

### VectorStore Trait Abstraction

```rust
use std::collections::HashMap;

/// A single search result
#[derive(Debug, Clone)]
pub struct SearchResult {
    pub id: String,
    pub score: f32,          // 0.0 to 1.0 similarity
    pub metadata: HashMap<String, String>,
}

/// Abstraction over any vector storage backend
pub trait VectorStore: Send + Sync {
    /// Insert or update a vector with metadata
    fn upsert(
        &mut self,
        id: &str,
        vector: &[f32],
        metadata: HashMap<String, String>,
    ) -> Result<(), VectorStoreError>;

    /// Search for the k nearest vectors to the query
    fn search(
        &self,
        query: &[f32],
        k: usize,
        filter: Option<&MetadataFilter>,
    ) -> Result<Vec<SearchResult>, VectorStoreError>;

    /// Delete a vector by ID
    fn delete(&mut self, id: &str) -> Result<bool, VectorStoreError>;

    /// Delete all vectors matching a metadata filter
    fn delete_by_filter(
        &mut self,
        filter: &MetadataFilter,
    ) -> Result<usize, VectorStoreError>;

    /// Number of vectors stored
    fn count(&self) -> Result<usize, VectorStoreError>;

    /// Flush/persist to disk
    fn flush(&mut self) -> Result<(), VectorStoreError>;
}

#[derive(Debug, Clone)]
pub struct MetadataFilter {
    pub field: String,
    pub op: FilterOp,
    pub value: String,
}

#[derive(Debug, Clone)]
pub enum FilterOp {
    Eq,
    Ne,
    In(Vec<String>),
}

#[derive(Debug, thiserror::Error)]
pub enum VectorStoreError {
    #[error("Index error: {0}")]
    Index(String),
    #[error("Embedding error: {0}")]
    Embedding(String),
    #[error("IO error: {0}")]
    Io(#[from] std::io::Error),
    #[error("Not found: {0}")]
    NotFound(String),
}
```

### Full Pipeline: Text -> Embedding -> Index -> Search -> Results

```rust
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};
use usearch::{Index, IndexOptions, MetricKind, ScalarKind};
use std::collections::HashMap;

/// Complete vector search pipeline using fastembed + usearch
pub struct VectorSearchPipeline {
    embedder: TextEmbedding,
    index: Index,
    id_map: HashMap<u64, String>,      // usearch key -> entity ID
    reverse_map: HashMap<String, u64>, // entity ID -> usearch key
    metadata_store: HashMap<String, HashMap<String, String>>,
    next_key: u64,
    dimensions: usize,
}

impl VectorSearchPipeline {
    pub fn new(dimensions: usize) -> Result<Self, Box<dyn std::error::Error>> {
        let embedder = TextEmbedding::try_new(
            InitOptions::new(EmbeddingModel::AllMiniLML6V2)
                .with_show_download_progress(true),
        )?;

        let mut options = IndexOptions::default();
        options.dimensions = dimensions;
        options.metric = MetricKind::Cos;
        options.quantization = ScalarKind::F32;

        let index = Index::new(&options)?;
        index.reserve(10_000)?;

        Ok(Self {
            embedder,
            index,
            id_map: HashMap::new(),
            reverse_map: HashMap::new(),
            metadata_store: HashMap::new(),
            next_key: 0,
            dimensions,
        })
    }

    /// Add a document: embed text, store in index
    pub fn add(
        &mut self,
        id: &str,
        text: &str,
        metadata: HashMap<String, String>,
    ) -> Result<(), Box<dyn std::error::Error>> {
        // Remove existing if present (upsert)
        if let Some(&old_key) = self.reverse_map.get(id) {
            let _ = self.index.remove(old_key);
            self.id_map.remove(&old_key);
        }

        // Embed the text
        let embeddings = self.embedder.embed(vec![text], None)?;
        let vector = &embeddings[0];

        // Store in index
        let key = self.next_key;
        self.next_key += 1;
        self.index.add(key, vector)?;

        // Track mappings
        self.id_map.insert(key, id.to_string());
        self.reverse_map.insert(id.to_string(), key);
        self.metadata_store.insert(id.to_string(), metadata);

        Ok(())
    }

    /// Search for similar documents
    pub fn search(
        &self,
        query_text: &str,
        k: usize,
        filter: Option<(&str, &str)>,  // (field, value) simple eq filter
    ) -> Result<Vec<SearchResult>, Box<dyn std::error::Error>> {
        // Embed query
        let query_embeddings = self.embedder.embed(vec![query_text], None)?;
        let query_vec = &query_embeddings[0];

        // Over-fetch if filtering (post-filter strategy)
        let fetch_k = if filter.is_some() { k * 5 } else { k };
        let results = self.index.search(query_vec, fetch_k)?;

        let mut search_results = Vec::new();

        for (usearch_key, distance) in results.keys.iter().zip(results.distances.iter()) {
            if let Some(entity_id) = self.id_map.get(usearch_key) {
                let metadata = self.metadata_store
                    .get(entity_id)
                    .cloned()
                    .unwrap_or_default();

                // Apply filter if present
                if let Some((field, value)) = filter {
                    if metadata.get(field).map(|v| v.as_str()) != Some(value) {
                        continue;
                    }
                }

                let similarity = 1.0 - distance; // cosine distance -> similarity
                search_results.push(SearchResult {
                    id: entity_id.clone(),
                    score: similarity,
                    metadata,
                });

                if search_results.len() >= k {
                    break;
                }
            }
        }

        Ok(search_results)
    }

    /// Delete by entity ID
    pub fn delete(&mut self, id: &str) -> Result<bool, Box<dyn std::error::Error>> {
        if let Some(key) = self.reverse_map.remove(id) {
            self.index.remove(key)?;
            self.id_map.remove(&key);
            self.metadata_store.remove(id);
            Ok(true)
        } else {
            Ok(false)
        }
    }

    /// Persist index to disk
    pub fn save(&self, path: &str) -> Result<(), Box<dyn std::error::Error>> {
        self.index.save(path)?;
        // Also serialize id_map and metadata_store with serde
        let maps = serde_json::json!({
            "id_map": self.id_map.iter()
                .map(|(k, v)| (k.to_string(), v.clone()))
                .collect::<HashMap<String, String>>(),
            "reverse_map": &self.reverse_map,
            "metadata": &self.metadata_store,
            "next_key": self.next_key,
        });
        std::fs::write(
            format!("{}.meta.json", path),
            serde_json::to_string_pretty(&maps)?,
        )?;
        Ok(())
    }

    /// Get count of stored vectors
    pub fn count(&self) -> usize {
        self.index.size()
    }
}

// --- USAGE EXAMPLE ---
fn main() -> Result<(), Box<dyn std::error::Error>> {
    let mut pipeline = VectorSearchPipeline::new(384)?;

    // Add code entities
    pipeline.add(
        "auth::validate_token",
        "fn validate_token(token: &str) -> Result<Claims, AuthError> validates JWT tokens, checks expiry, verifies signature",
        HashMap::from([
            ("entity_type".into(), "function".into()),
            ("module".into(), "auth".into()),
            ("file".into(), "src/auth/jwt.rs".into()),
        ]),
    )?;

    pipeline.add(
        "auth::AuthService",
        "struct AuthService handles authentication and authorization, manages JWT lifecycle",
        HashMap::from([
            ("entity_type".into(), "struct".into()),
            ("module".into(), "auth".into()),
            ("file".into(), "src/auth/service.rs".into()),
        ]),
    )?;

    pipeline.add(
        "db::UserStore",
        "struct UserStore provides CRUD operations for user records in SQLite",
        HashMap::from([
            ("entity_type".into(), "struct".into()),
            ("module".into(), "db".into()),
            ("file".into(), "src/db/users.rs".into()),
        ]),
    )?;

    // Search
    let results = pipeline.search("JWT token validation", 5, None)?;
    for r in &results {
        println!("{}: {:.4}", r.id, r.score);
    }

    // Search with metadata filter
    let filtered = pipeline.search(
        "authentication",
        5,
        Some(("entity_type", "struct")),
    )?;

    // Persist
    pipeline.save("code_index.usearch")?;

    println!("Total vectors: {}", pipeline.count());
    Ok(())
}
```

### Cargo.toml for Complete Pipeline

```toml
[dependencies]
fastembed = "5"
usearch = "2"
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"
seahash = "4"          # Fast hashing for change detection
```

### Alternative: LanceDB Pipeline (Persistent, with Metadata Filtering)

```toml
[dependencies]
lancedb = "0.23"
fastembed = "5"
arrow-array = "53"
arrow-schema = "53"
tokio = { version = "1", features = ["full"] }
serde = { version = "1", features = ["derive"] }
```

```rust
use std::sync::Arc;
use arrow_array::{
    StringArray, Float32Array, FixedSizeListArray, RecordBatch,
    RecordBatchIterator, types::Float32Type,
};
use arrow_schema::{DataType, Field, Schema};
use fastembed::{TextEmbedding, InitOptions, EmbeddingModel};

pub struct LanceDBPipeline {
    db: lancedb::Connection,
    embedder: TextEmbedding,
    schema: Arc<Schema>,
    dims: i32,
}

impl LanceDBPipeline {
    pub async fn new(db_path: &str, dims: i32) -> Result<Self, Box<dyn std::error::Error>> {
        let db = lancedb::connect(db_path).execute().await?;

        let embedder = TextEmbedding::try_new(
            InitOptions::new(EmbeddingModel::AllMiniLML6V2)
                .with_show_download_progress(true),
        )?;

        let schema = Arc::new(Schema::new(vec![
            Field::new("id", DataType::Utf8, false),
            Field::new("text", DataType::Utf8, true),
            Field::new("entity_type", DataType::Utf8, true),
            Field::new("module", DataType::Utf8, true),
            Field::new("file_path", DataType::Utf8, true),
            Field::new(
                "vector",
                DataType::FixedSizeList(
                    Arc::new(Field::new("item", DataType::Float32, true)),
                    dims,
                ),
                true,
            ),
        ]));

        Ok(Self { db, embedder, schema, dims })
    }

    pub async fn ensure_table(&self) -> Result<lancedb::Table, Box<dyn std::error::Error>> {
        match self.db.open_table("entities").execute().await {
            Ok(table) => Ok(table),
            Err(_) => {
                // Create with empty batch
                let batch = RecordBatch::new_empty(self.schema.clone());
                Ok(self.db.create_table("entities", batch)
                    .execute().await?)
            }
        }
    }

    pub async fn add_entities(
        &self,
        entities: Vec<(String, String, String, String, String)>, // id, text, type, module, file
    ) -> Result<(), Box<dyn std::error::Error>> {
        let texts: Vec<&str> = entities.iter().map(|(_, t, _, _, _)| t.as_str()).collect();
        let embeddings = self.embedder.embed(texts, None)?;

        let ids = StringArray::from(
            entities.iter().map(|(id, _, _, _, _)| id.as_str()).collect::<Vec<_>>()
        );
        let text_arr = StringArray::from(
            entities.iter().map(|(_, t, _, _, _)| t.as_str()).collect::<Vec<_>>()
        );
        let type_arr = StringArray::from(
            entities.iter().map(|(_, _, et, _, _)| et.as_str()).collect::<Vec<_>>()
        );
        let mod_arr = StringArray::from(
            entities.iter().map(|(_, _, _, m, _)| m.as_str()).collect::<Vec<_>>()
        );
        let file_arr = StringArray::from(
            entities.iter().map(|(_, _, _, _, f)| f.as_str()).collect::<Vec<_>>()
        );

        let vectors = FixedSizeListArray::from_iter_primitive::<Float32Type, _, _>(
            embeddings.iter().map(|emb| {
                Some(emb.iter().map(|&v| Some(v)).collect::<Vec<_>>())
            }),
            self.dims,
        );

        let batch = RecordBatch::try_new(
            self.schema.clone(),
            vec![
                Arc::new(ids),
                Arc::new(text_arr),
                Arc::new(type_arr),
                Arc::new(mod_arr),
                Arc::new(file_arr),
                Arc::new(vectors),
            ],
        )?;

        let table = self.ensure_table().await?;
        table.add(
            RecordBatchIterator::new(vec![Ok(batch)], self.schema.clone())
        ).execute().await?;

        Ok(())
    }

    pub async fn search(
        &self,
        query: &str,
        k: usize,
        type_filter: Option<&str>,
    ) -> Result<Vec<RecordBatch>, Box<dyn std::error::Error>> {
        let query_emb = self.embedder.embed(vec![query], None)?;
        let table = self.ensure_table().await?;

        let mut q = table.query().nearest_to(&query_emb[0])?.limit(k);

        if let Some(entity_type) = type_filter {
            q = q.only_if(&format!("entity_type = '{}'", entity_type));
        }

        let results = q.execute().await?.try_collect::<Vec<_>>().await?;
        Ok(results)
    }
}
```

---

## Quick Decision Matrix

| Need | Recommendation |
|------|---------------|
| Simplest possible, <100K vectors | usearch (in-memory HNSW) |
| Need persistence + metadata filtering | lancedb (Lance format, SQL-like filters) |
| Multi-process access, memory-mapped | arroy/hannoy (LMDB-backed) |
| Already using SQLite, small dataset | sqlite-vec (brute-force, SQL queries) |
| Local embeddings, no network | fastembed (ONNX runtime, auto-downloads) |
| Hybrid vector + text search | RRF fusion of vector results + tantivy/BM25 results |
| Production, billion-scale | Qdrant server or Milvus (not embeddable) |

---

## Key Cargo Dependencies Summary

```toml
# Embedding
fastembed = "5"                       # Local ONNX embeddings

# Vector indexes (pick one)
usearch = "2"                         # HNSW, minimal, fast
lancedb = "0.23"                      # Full-featured, persistent
# arroy = "0.5"                       # LMDB-backed, multi-process
# hora = "0.1"                        # Multi-algorithm, pure Rust

# sqlite-vec approach
# rusqlite = { version = "0.31", features = ["bundled"] }
# sqlite-vec = "0.1"
# zerocopy = { version = "0.7", features = ["derive"] }

# Supporting
arrow-array = "53"                    # For lancedb
arrow-schema = "53"                   # For lancedb
serde = { version = "1", features = ["derive"] }
serde_json = "1"
thiserror = "2"
tokio = { version = "1", features = ["full"] }  # For lancedb async
```
