# KnowledgeReduce Ultimate

A comprehensive knowledge graph framework with advanced capabilities for creating, managing, and analyzing knowledge graphs with cutting-edge features.

## Advanced Features

### Core Functionality
- Create and manage knowledge graphs with reliability ratings
- Add, update, and query facts with rich metadata
- Visualize knowledge graphs with customizable layouts
- Import and export knowledge graphs in various formats

### Enhanced Performance
- LRU caching for improved query performance
- Batch operations for efficient data manipulation
- Change tracking and auto-saving capabilities
- Optimized data structures for large knowledge graphs

### Semantic Capabilities
- Entity extraction from unstructured text
- Relationship identification between entities
- Automatic fact creation from text
- Semantic similarity calculation between facts

### Scalability
- Sharding for distributed knowledge graphs
- Efficient handling of very large datasets
- Optimized shard management and balancing
- Cross-shard search and query capabilities

### Vector Embeddings
- Vector-based semantic search
- Fact clustering and categorization
- Query expansion for improved search results
- Similarity matching between facts

### Real-time Streaming
- Event-driven knowledge graph updates
- Real-time data integration
- Streaming data processing
- Event history tracking

### Blockchain Verification
- Immutable fact history
- Blockchain-based verification
- Distributed consensus mechanisms
- Tamper-proof knowledge graphs

## Installation

```bash
pip install knowledge-graph-pkg
```

## Quick Start

```python
from knowledge_graph_pkg import (
    KnowledgeGraph, 
    ReliabilityRating,
    EnhancedKnowledgeGraph,
    VectorKnowledgeGraph,
    StreamingKnowledgeGraph,
    BlockchainKnowledgeGraph
)

# Create an enhanced knowledge graph with caching
kg = EnhancedKnowledgeGraph(cache_enabled=True)

# Add facts with reliability ratings
kg.add_fact(
    fact_id="earth_sun",
    fact_statement="The Earth orbits the Sun",
    category="Astronomy",
    tags=["earth", "sun", "orbit"],
    date_recorded=datetime.now(),
    last_updated=datetime.now(),
    reliability_rating=ReliabilityRating.VERIFIED,
    source_id="astronomy_textbook",
    source_title="Principles of Astronomy",
    author_creator="Dr. Neil Stargazer",
    publication_date=datetime.now(),
    url_reference="https://example.com/astronomy",
    related_facts=[],
    contextual_notes="Fundamental astronomical fact",
    access_level="public",
    usage_count=100
)

# Use vector-based semantic search
vector_kg = VectorKnowledgeGraph(kg)
vector_kg.generate_embeddings()
results = vector_kg.semantic_search("planets orbiting stars")

# Set up real-time streaming
streaming_kg = StreamingKnowledgeGraph(kg)
streaming_kg.add_fact_from_stream({
    'fact_id': 'streaming_fact_1',
    'fact_statement': 'Jupiter has 79 known moons',
    'category': 'Astronomy',
    'tags': ['jupiter', 'moons', 'solar system']
}, source_id='nasa_feed')

# Use blockchain verification
blockchain_kg = BlockchainKnowledgeGraph(kg)
tx_hash = blockchain_kg.add_fact(
    fact_id="blockchain_fact_1",
    fact_statement="Saturn has rings made of ice particles",
    category="Astronomy",
    tags=["saturn", "rings", "solar system"],
    reliability_rating=ReliabilityRating.VERIFIED,
    source_id="astronomy_journal"
)
verification = blockchain_kg.verify_fact("blockchain_fact_1")
```

## Knowledge Distillation (the "reduce" step)

KnowledgeReduce can distill a populated knowledge graph into compact,
high-quality, **model-absorbable** training data. The pipeline is:

```
raw text -> semantic extraction (+ optional coreference)
         -> reliability-rated knowledge graph
         -> distillation: filter -> deduplicate -> rank -> top_k
         -> model-absorbable output (text digest / instruction JSONL / chat JSONL)
```

```python
from knowledge_graph_pkg import (
    KnowledgeGraph, SemanticKnowledgeGraph, KnowledgeDistiller, ReliabilityRating,
)

kg = KnowledgeGraph()
skg = SemanticKnowledgeGraph(kg)

# Extract facts from text. resolve_coref rewrites leading pronouns
# (e.g. "She discovered radium" -> "Marie Curie discovered radium").
skg.create_facts_from_text(
    "Marie Curie was born in Warsaw. She discovered radium.",
    source_id="demo",
    reliability=ReliabilityRating.LIKELY_TRUE,
    resolve_coref=True,
)

# Distill: keep only reliable facts, dedup near-duplicates, rank by quality.
distiller = KnowledgeDistiller(
    kg,
    min_reliability=ReliabilityRating.LIKELY_TRUE,
    dedup_threshold=0.85,
)

print(distiller.to_text())          # ranked plain-text digest (RAG context)
distiller.distill_to_file("train.jsonl", fmt="chat")          # chat SFT JSONL
distiller.distill_to_file("instruct.jsonl", fmt="instruction")  # instruction JSONL
print(distiller.stats())            # {'total_facts', 'selected_facts', 'reduction_ratio', ...}
```

Generated chat records use **real questions** derived from the relation
(via `QAGenerator`), not generic prompts:

```json
{"messages": [{"role": "user", "content": "Where was Marie Curie born?"},
              {"role": "assistant", "content": "Warsaw"}]}
{"messages": [{"role": "user", "content": "What did Marie Curie discover?"},
              {"role": "assistant", "content": "radium"}]}
```

### Ingesting documents from disk

```python
skg.create_facts_from_file("source.txt", reliability=ReliabilityRating.LIKELY_TRUE)
```

## Testing

```bash
python -m venv .venv && source .venv/bin/activate
pip install networkx numpy requests beautifulsoup4 matplotlib pytest
python -m pytest -q          # 40 tests
```

## Examples

See the `examples` directory for detailed usage examples:
- `basic_usage.py`: Simple knowledge graph operations
- `enhanced_features.py`: Advanced features demonstration
- `ultimate_features.py`: Comprehensive example of all capabilities
- `distillation_pipeline.py`: End-to-end text -> facts -> distilled JSONL

## Documentation

For detailed documentation, see the docstrings in the source code or run:

```python
help(knowledge_graph_pkg)
```

## License

MIT
