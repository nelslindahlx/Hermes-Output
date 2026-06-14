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

## Examples

See the `examples` directory for detailed usage examples:
- `basic_usage.py`: Simple knowledge graph operations
- `enhanced_features.py`: Advanced features demonstration
- `ultimate_features.py`: Comprehensive example of all capabilities

## Documentation

For detailed documentation, see the docstrings in the source code or run:

```python
help(knowledge_graph_pkg)
```

## License

MIT
