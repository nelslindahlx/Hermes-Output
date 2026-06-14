"""
Semantic knowledge graph operations with NLP integration.

This module provides advanced semantic capabilities for knowledge graphs
by integrating natural language processing techniques for entity extraction,
relationship identification, and semantic similarity.
"""

import re
import string
from datetime import datetime
from typing import Dict, List, Any, Union, Optional, Tuple, Set, Callable
from .core import KnowledgeGraph, ReliabilityRating

class SemanticKnowledgeGraph:
    """
    Class for adding semantic capabilities to knowledge graphs.
    
    This class provides methods for semantic analysis, entity extraction,
    and natural language processing integration with knowledge graphs.
    
    Attributes:
        kg: The knowledge graph to enhance with semantic capabilities
        nlp_enabled: Whether NLP features are enabled
    """
    
    def __init__(self, knowledge_graph: KnowledgeGraph, nlp_enabled: bool = True):
        """
        Initialize a SemanticKnowledgeGraph with a knowledge graph.
        
        Args:
            knowledge_graph: KnowledgeGraph instance to enhance
            nlp_enabled: Whether to enable NLP features
        """
        self.kg = knowledge_graph
        self.nlp_enabled = nlp_enabled
        self._entity_cache = {}
        self._relation_patterns = self._compile_relation_patterns()
        
    def extract_entities_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract entities from text using NLP techniques.
        
        This is a simplified implementation. For production use,
        consider using spaCy, NLTK, or other NLP libraries.
        
        Args:
            text: Text to extract entities from
            
        Returns:
            List of dictionaries containing entity information
        """
        entities = []
        
        # Simple named entity extraction using regex patterns
        # In a real implementation, this would use proper NLP libraries
        
        # Extract potential people (capitalized names)
        person_pattern = r'([A-Z][a-z]+ [A-Z][a-z]+)'
        for match in re.finditer(person_pattern, text):
            name = match.group(1)
            if self._is_likely_name(name):
                entities.append({
                    'text': name,
                    'type': 'PERSON',
                    'start': match.start(),
                    'end': match.end()
                })
        
        # Extract potential organizations (all caps or capitalized with Inc, Corp, etc.)
        org_pattern = r'([A-Z][A-Za-z]+ (?:Inc|Corp|LLC|Company|Organization))|([A-Z]{2,})'
        for match in re.finditer(org_pattern, text):
            org = match.group(0)
            entities.append({
                'text': org,
                'type': 'ORGANIZATION',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract potential locations (capitalized followed by geographic terms)
        loc_pattern = r'([A-Z][a-z]+ (?:City|State|Country|River|Mountain|Lake|Ocean|Sea|Island))'
        for match in re.finditer(loc_pattern, text):
            loc = match.group(1)
            entities.append({
                'text': loc,
                'type': 'LOCATION',
                'start': match.start(),
                'end': match.end()
            })
        
        # Extract dates (simple patterns)
        date_pattern = r'\b(\d{1,2}/\d{1,2}/\d{2,4})|(\d{1,2}-\d{1,2}-\d{2,4})|(\d{1,2} (?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]* \d{2,4})\b'
        for match in re.finditer(date_pattern, text):
            date = match.group(0)
            entities.append({
                'text': date,
                'type': 'DATE',
                'start': match.start(),
                'end': match.end()
            })
        
        return entities
    
    def extract_relations_from_text(self, text: str) -> List[Dict[str, Any]]:
        """
        Extract potential relations between entities in text.
        
        Args:
            text: Text to extract relations from
            
        Returns:
            List of dictionaries containing relation information
        """
        relations = []
        
        # Extract entities first
        entities = self.extract_entities_from_text(text)
        
        # Look for relation patterns between entities
        for pattern_name, pattern in self._relation_patterns.items():
            for match in re.finditer(pattern, text):
                # Find entities that overlap with the match
                match_start, match_end = match.span()
                
                # Find entities before and after the relation
                entities_before = [e for e in entities if e['end'] <= match_start]
                entities_after = [e for e in entities if e['start'] >= match_end]
                
                # If we have entities before and after, create a relation
                if entities_before and entities_after:
                    # Use the closest entities to the relation
                    subject = max(entities_before, key=lambda e: e['end'])
                    object_ = min(entities_after, key=lambda e: e['start'])
                    
                    relations.append({
                        'subject': subject['text'],
                        'subject_type': subject['type'],
                        'predicate': pattern_name,
                        'object': object_['text'],
                        'object_type': object_['type'],
                        'text': text[subject['start']:object_['end']]
                    })
        
        return relations
    
    def create_facts_from_text(self, text: str, source_id: str, reliability: ReliabilityRating = ReliabilityRating.UNVERIFIED) -> List[str]:
        """
        Automatically create facts from text using NLP extraction.
        
        Args:
            text: Text to extract facts from
            source_id: Source identifier for the facts
            reliability: Reliability rating for the extracted facts
            
        Returns:
            List of created fact IDs
        """
        created_facts = []
        
        # Extract relations
        relations = self.extract_relations_from_text(text)
        
        # Current time for timestamps
        now = datetime.now()
        
        # Create facts from relations
        for i, relation in enumerate(relations):
            fact_id = f"auto_{source_id}_{i}"
            
            # Create fact statement from relation
            fact_statement = f"{relation['subject']} {relation['predicate']} {relation['object']}"
            
            # Determine category based on entity types
            if relation['subject_type'] == 'PERSON' and relation['object_type'] == 'ORGANIZATION':
                category = 'Employment'
            elif relation['subject_type'] == 'PERSON' and relation['object_type'] == 'LOCATION':
                category = 'Location'
            elif relation['subject_type'] == 'ORGANIZATION' and relation['object_type'] == 'LOCATION':
                category = 'Business'
            else:
                category = 'General'
            
            # Create tags from entity types and text
            tags = [
                relation['subject_type'].lower(),
                relation['object_type'].lower(),
                relation['predicate'].lower()
            ]
            
            try:
                # Add the fact to the knowledge graph
                self.kg.add_fact(
                    fact_id=fact_id,
                    fact_statement=fact_statement,
                    category=category,
                    tags=tags,
                    date_recorded=now,
                    last_updated=now,
                    reliability_rating=reliability,
                    source_id=source_id,
                    source_title=f"Auto-extracted from text",
                    author_creator="Semantic Extractor",
                    publication_date=now,
                    url_reference="",
                    related_facts=[],
                    contextual_notes=f"Extracted from text: {relation['text']}",
                    access_level="public",
                    usage_count=1
                )
                
                created_facts.append(fact_id)
                
            except Exception as e:
                print(f"Error creating fact from relation: {e}")
        
        return created_facts
    
    def find_semantically_similar_facts(self, fact_id: str, threshold: float = 0.5) -> List[Tuple[str, float]]:
        """
        Find facts that are semantically similar to a given fact.
        
        Args:
            fact_id: ID of the fact to find similar facts for
            threshold: Similarity threshold (0-1)
            
        Returns:
            List of tuples containing (fact_id, similarity_score)
        """
        # Get the target fact
        target_fact = self.kg.get_fact(fact_id)
        target_statement = target_fact['fact_statement']
        
        similarities = []
        
        # Compare with all other facts
        for node, data in self.kg.graph.nodes(data=True):
            if node == fact_id:
                continue
                
            if 'fact_statement' in data:
                similarity = self._calculate_semantic_similarity(
                    target_statement, 
                    data['fact_statement']
                )
                
                if similarity >= threshold:
                    similarities.append((node, similarity))
        
        # Sort by similarity score
        return sorted(similarities, key=lambda x: x[1], reverse=True)
    
    def suggest_fact_connections(self, min_similarity: float = 0.4) -> List[Tuple[str, str, float]]:
        """
        Suggest connections between facts based on semantic similarity.
        
        Args:
            min_similarity: Minimum similarity threshold
            
        Returns:
            List of tuples containing (fact_id1, fact_id2, similarity_score)
        """
        suggestions = []
        
        # Get all facts
        facts = list(self.kg.graph.nodes(data=True))
        
        # Compare each pair of facts
        for i in range(len(facts)):
            node_i, data_i = facts[i]
            
            for j in range(i+1, len(facts)):
                node_j, data_j = facts[j]
                
                # Skip if already connected
                if self.kg.graph.has_edge(node_i, node_j) or self.kg.graph.has_edge(node_j, node_i):
                    continue
                
                # Skip if facts don't have statements
                if 'fact_statement' not in data_i or 'fact_statement' not in data_j:
                    continue
                
                # Calculate similarity
                similarity = self._calculate_semantic_similarity(
                    data_i['fact_statement'],
                    data_j['fact_statement']
                )
                
                if similarity >= min_similarity:
                    suggestions.append((node_i, node_j, similarity))
        
        # Sort by similarity score
        return sorted(suggestions, key=lambda x: x[2], reverse=True)
    
    def _is_likely_name(self, text: str) -> bool:
        """
        Check if text is likely to be a person's name.
        
        Args:
            text: Text to check
            
        Returns:
            True if likely a name, False otherwise
        """
        # Check if text contains common name parts
        common_titles = ['Mr', 'Mrs', 'Ms', 'Dr', 'Prof']
        for title in common_titles:
            if text.startswith(f"{title} "):
                return True
        
        # Check if text has exactly two capitalized words
        parts = text.split()
        if len(parts) == 2 and all(p[0].isupper() for p in parts):
            return True
            
        return False
    
    def _compile_relation_patterns(self) -> Dict[str, str]:
        """
        Compile regex patterns for common relations.
        
        Returns:
            Dictionary mapping relation names to compiled regex patterns
        """
        patterns = {
            'works_for': r'\b(?:works for|is employed by|is a member of)\b',
            'located_in': r'\b(?:is located in|is based in|is situated in|is in)\b',
            'founded': r'\b(?:founded|established|created|started)\b',
            'owns': r'\b(?:owns|possesses|has|maintains)\b',
            'part_of': r'\b(?:is part of|belongs to|is a division of)\b',
            'born_in': r'\b(?:was born in|born in|originated from)\b',
            'died_in': r'\b(?:died in|passed away in|deceased in)\b',
            'married_to': r'\b(?:is married to|wed|wedded|spouse of)\b',
            'parent_of': r'\b(?:is the parent of|is the father of|is the mother of)\b',
            'child_of': r'\b(?:is the child of|is the son of|is the daughter of)\b',
            'discovered': r'\b(?:discovered|found|identified|detected)\b',
            'invented': r'\b(?:invented|created|designed|developed)\b',
            'wrote': r'\b(?:wrote|authored|composed|penned)\b',
            'directed': r'\b(?:directed|produced|oversaw|managed)\b',
            'acted_in': r'\b(?:acted in|starred in|performed in|appeared in)\b',
        }
        
        # Compile patterns
        return {name: re.compile(pattern, re.IGNORECASE) for name, pattern in patterns.items()}
    
    def _calculate_semantic_similarity(self, text1: str, text2: str) -> float:
        """
        Calculate semantic similarity between two texts.
        
        This is a simplified implementation using word overlap and TF-IDF weighting.
        For production use, consider using word embeddings or transformer models.
        
        Args:
            text1: First text
            text2: Second text
            
        Returns:
            Similarity score between 0 and 1
        """
        # Preprocess texts
        def preprocess(text):
            # Convert to lowercase
            text = text.lower()
            # Remove punctuation
            text = text.translate(str.maketrans('', '', string.punctuation))
            # Split into words
            words = text.split()
            # Remove stop words (simplified list)
            stop_words = {'the', 'a', 'an', 'and', 'or', 'but', 'is', 'are', 'was', 'were', 
                         'in', 'on', 'at', 'to', 'for', 'with', 'by', 'of', 'from'}
            return [w for w in words if w not in stop_words]
        
        words1 = preprocess(text1)
        words2 = preprocess(text2)
        
        if not words1 or not words2:
            return 0.0
        
        # Calculate word frequencies
        freq1 = {}
        for word in words1:
            freq1[word] = freq1.get(word, 0) + 1
            
        freq2 = {}
        for word in words2:
            freq2[word] = freq2.get(word, 0) + 1
        
        # Find common words
        common_words = set(freq1.keys()) & set(freq2.keys())
        
        if not common_words:
            return 0.0
        
        # Calculate dot product with TF-IDF-like weighting
        dot_product = 0
        for word in common_words:
            # Simple inverse document frequency weight: log(3/2) if word appears in both texts
            idf = 0.405  # log(3/2) ≈ 0.405
            dot_product += freq1[word] * freq2[word] * idf
        
        # Calculate magnitudes
        mag1 = sum(freq1[word]**2 for word in freq1)
        mag2 = sum(freq2[word]**2 for word in freq2)
        
        # Calculate cosine similarity
        similarity = dot_product / (mag1**0.5 * mag2**0.5)
        
        return similarity
