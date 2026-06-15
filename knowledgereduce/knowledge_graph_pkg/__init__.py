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
from .distillation import KnowledgeDistiller
from .qa import QAGenerator
from .coref import resolve_coreferences
from .extraction import SVOExtractor
from .extractor_base import Extractor, get_extractor
from .quality import FactQualityFilter
from .ingest import load_text
from .export import split_records, budget_records, estimate_tokens
from .factstore import FactStore
from .store import KnowledgeStore, Drop, content_hash, SCHEMA_VERSION
from .catalog import Catalog
from .lifecycle import promote_reliability, find_contradictions, reextract_store
from .factory import batch_drop, scan_folder

__version__ = "2.0.0"
__all__ = [
    'KnowledgeGraph',
    'ReliabilityRating',
    'EnhancedKnowledgeGraph',
    'SemanticKnowledgeGraph',
    'ShardedKnowledgeGraph',
    'VectorKnowledgeGraph',
    'StreamingKnowledgeGraph',
    'BlockchainKnowledgeGraph',
    'KnowledgeDistiller',
    'QAGenerator',
    'resolve_coreferences',
    'SVOExtractor',
    'FactQualityFilter',
    'load_text',
    'Extractor',
    'get_extractor',
    'split_records',
    'budget_records',
    'estimate_tokens',
    'FactStore',
    'KnowledgeStore',
    'Drop',
    'content_hash',
    'SCHEMA_VERSION',
    'Catalog',
    'promote_reliability',
    'find_contradictions',
    'reextract_store',
    'batch_drop',
    'scan_folder'
]
