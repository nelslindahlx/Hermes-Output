# Knowledge Graph Package

This Python package facilitates creating and managing portable knowledge graphs.

## Installation
pip install knowledge_graph_pkg

## Usage
from knowledge_graph_pkg import KnowledgeGraph

kg = KnowledgeGraph()
kg.add_fact('fact1', {'detail': 'Example fact data'})
print(kg.get_fact('fact1'))
