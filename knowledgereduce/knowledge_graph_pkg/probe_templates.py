"""
Domain-parameterized prompt templates for model probing.

Five probe types extract different kinds of knowledge from a model:

* ``entity``   -- atomic facts about a single entity
* ``relation`` -- the relationship between two entities
* ``concept``  -- a concept explained as several facts
* ``list``     -- a coverage sweep ("list 5 facts about ...")
* ``negative`` -- misconception mining (surfaces what the model gets wrong)

:func:`generate_probes` builds a deterministic, balanced set of probes for a
domain, drawing entity/relation prompts from seed entities (bootstrapped from
an existing KnowledgeGraph) and falling back to domain-only prompts when no
entities are available.
"""

import random
from typing import Any, Dict, List

PROMPT_TEMPLATES = {
    "entity": "State a single verified, factual statement about {entity} in the field of {domain}.",
    "relation": "What is the relationship between {e1} and {e2} in the field of {domain}? State it as a fact.",
    "concept": "Explain the concept of {entity} in {domain} as three concise, verified facts.",
    "list": "List five verified, factual statements about {domain}.",
    "negative": "What is a common misconception about {domain}, and what is the correct fact?",
}

PROMPT_TYPES = tuple(PROMPT_TEMPLATES.keys())

# Probe types that require at least one seed entity.
_NEEDS_ENTITY = {"entity", "concept"}
_NEEDS_TWO = {"relation"}


def render_prompt(prompt_type: str, **kwargs: Any) -> str:
    """Render one prompt template. Raises ValueError on unknown type or
    missing template fields."""
    if prompt_type not in PROMPT_TEMPLATES:
        raise ValueError(
            f"Unknown prompt_type '{prompt_type}'. Expected one of: {', '.join(PROMPT_TYPES)}."
        )
    try:
        return PROMPT_TEMPLATES[prompt_type].format(**kwargs)
    except KeyError as exc:
        raise ValueError(f"Missing template field {exc} for prompt_type '{prompt_type}'.") from exc


def generate_probes(domain: str, entities: List[str], n_prompts: int = 10,
                    seed: int = 42) -> List[Dict[str, Any]]:
    """Build a deterministic, balanced list of probe specs for ``domain``.

    Each spec is ``{"domain", "prompt_type", "prompt"}``. Entity-dependent
    templates are only used when ``entities`` is non-empty; otherwise the
    generator falls back to domain-level templates (list/negative).
    """
    rng = random.Random(seed)
    ents = list(entities or [])

    # Which probe types are usable given the seed entities we have.
    usable = []
    for t in PROMPT_TYPES:
        if t in _NEEDS_TWO and len(ents) < 2:
            continue
        if t in _NEEDS_ENTITY and len(ents) < 1:
            continue
        usable.append(t)
    if not usable:  # no entities at all -> domain-only templates
        usable = ["list", "negative"]

    probes: List[Dict[str, Any]] = []
    for _ in range(n_prompts):
        ptype = rng.choice(usable)
        if ptype in _NEEDS_TWO:
            e1, e2 = rng.sample(ents, 2)
            prompt = render_prompt(ptype, domain=domain, e1=e1, e2=e2)
        elif ptype in _NEEDS_ENTITY:
            prompt = render_prompt(ptype, domain=domain, entity=rng.choice(ents))
        else:
            prompt = render_prompt(ptype, domain=domain)
        probes.append({"domain": domain, "prompt_type": ptype, "prompt": prompt})
    return probes


def seed_entities_from_graph(kg, limit: int = 50) -> List[str]:
    """Bootstrap probe entities from an existing KnowledgeGraph's fact subjects."""
    seen: List[str] = []
    for _node, data in kg.graph.nodes(data=True):
        subj = data.get("subject")
        if subj and subj not in seen:
            seen.append(subj)
        if len(seen) >= limit:
            break
    return seen
