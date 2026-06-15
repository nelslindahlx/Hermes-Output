"""
Command-line interface for KnowledgeReduce.

Run the full pipeline -- ingest text, extract facts, optionally resolve
coreferences, filter for quality, distill, and write model-absorbable
output -- from a single command:

    python -m knowledge_graph_pkg distill input.txt -o train.jsonl \\
        --format chat --filter standard --coref

Subcommands:
    distill   Extract + distill a document into training data.
"""

import argparse
import sys
from typing import List, Optional

from .core import KnowledgeGraph, ReliabilityRating
from .semantic import SemanticKnowledgeGraph
from .distillation import KnowledgeDistiller
from .quality import FactQualityFilter


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="knowledge_graph_pkg",
        description="KnowledgeReduce: distill documents into model-absorbable facts.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    d = sub.add_parser("distill", help="Extract and distill a document.")
    d.add_argument("input", help="Path to the input text document.")
    d.add_argument("-o", "--output", required=True, help="Output file path.")
    d.add_argument("--format", choices=["chat", "instruction", "text"],
                   default="chat", help="Output format (default: chat).")
    d.add_argument("--filter", choices=["none", "standard", "strict"],
                   default="standard", help="Quality filter (default: standard).")
    d.add_argument("--coref", action="store_true",
                   help="Resolve leading pronouns to named-entity antecedents.")
    d.add_argument("--max-object-len", type=int, default=80,
                   help="Max object length for the quality filter (default: 80).")
    d.add_argument("--dedup", type=float, default=0.9,
                   help="Dedup similarity threshold 0..1 (default: 0.9; 0 disables).")
    d.add_argument("--min-reliability",
                   choices=["unverified", "possibly_true", "likely_true", "verified"],
                   default="likely_true",
                   help="Minimum reliability to keep (default: likely_true).")
    return parser


_RELIABILITY = {
    "unverified": ReliabilityRating.UNVERIFIED,
    "possibly_true": ReliabilityRating.POSSIBLY_TRUE,
    "likely_true": ReliabilityRating.LIKELY_TRUE,
    "verified": ReliabilityRating.VERIFIED,
}


def _make_filter(name: str, max_object_len: int) -> Optional[FactQualityFilter]:
    if name == "none":
        return None
    if name == "strict":
        return FactQualityFilter(max_object_len=min(max_object_len, 60),
                                 require_entity_subject=True)
    return FactQualityFilter(max_object_len=max_object_len)


def _cmd_distill(args) -> int:
    import os
    if not os.path.isfile(args.input):
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2

    reliability = _RELIABILITY[args.min_reliability]

    kg = KnowledgeGraph()
    skg = SemanticKnowledgeGraph(kg)
    ids = skg.create_facts_from_file(
        args.input, reliability=reliability, resolve_coref=args.coref
    )

    quality_filter = _make_filter(args.filter, args.max_object_len)
    distiller = KnowledgeDistiller(
        kg,
        min_reliability=reliability,
        dedup_threshold=args.dedup,
        quality_filter=quality_filter,
    )

    written = distiller.distill_to_file(args.output, fmt=args.format)
    stats = distiller.stats()
    print(
        f"Extracted {len(ids)} raw facts; "
        f"wrote {written} {args.format} pairs to {args.output} "
        f"(reduction ratio {stats['reduction_ratio']:.2f})."
    )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "distill":
        return _cmd_distill(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
