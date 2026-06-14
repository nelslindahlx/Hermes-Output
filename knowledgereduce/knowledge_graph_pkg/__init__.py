"""
KnowledgeReduce Ultimate: A comprehensive knowledge graph framework.

This package provides advanced tools for creating, managing, and analyzing knowledge graphs
with reliability ratings, semantic capabilities, performance optimizations, real-time
streaming, vector embeddings, and blockchain verification.
"""

from .core import KnowledgeGraph, ReliabilityRating
from .enhanced import EnhancedKnowledgeGraph
from .semantic import SemanticKnowledgeGraph
from .sharding import ShardedKnowledgeGraph
from .vector import VectorKnowledgeGraph
from .streaming import StreamingKnowledgeGraph
from .blockchain import BlockchainKnowledgeGraph

__version__ = "2.0.0"
__all__ = [
    'KnowledgeGraph',
    'ReliabilityRating',
    'EnhancedKnowledgeGraph',
    'SemanticKnowledgeGraph',
    'ShardedKnowledgeGraph',
    'VectorKnowledgeGraph',
    'StreamingKnowledgeGraph',
    'BlockchainKnowledgeGraph'
]
