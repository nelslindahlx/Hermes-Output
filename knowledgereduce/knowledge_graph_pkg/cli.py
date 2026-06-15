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
    d.add_argument("--engine", choices=["svo", "spacy"], default="svo",
                   help="Extraction engine (default: svo; spacy needs [nlp] extra).")
    d.add_argument("--max-object-len", type=int, default=80,
                   help="Max object length for the quality filter (default: 80).")
    d.add_argument("--dedup", type=float, default=0.9,
                   help="Dedup similarity threshold 0..1 (default: 0.9; 0 disables).")
    d.add_argument("--min-reliability",
                   choices=["unverified", "possibly_true", "likely_true", "verified"],
                   default="likely_true",
                   help="Minimum reliability to keep (default: likely_true).")
    d.add_argument("--split", type=float, default=None,
                   help="Train/val split ratio (e.g. 0.9). Writes <out> and "
                        "<out>.val. Default: no split.")
    d.add_argument("--max-tokens", type=int, default=None,
                   help="Cap output to ~N tokens (keeps highest-ranked facts).")
    d.add_argument("--dedup-store", default=None,
                   help="Path to a persistent fact store JSON for cross-run "
                        "dedup (skips facts seen in previous runs).")
    d.add_argument("--seed", type=int, default=42,
                   help="Random seed for the train/val split (default: 42).")

    e = sub.add_parser("eval", help="Score the extractor against a gold set.")
    e.add_argument("--gold", default="data/gold_set.json",
                   help="Path to the gold-set JSON (default: data/gold_set.json).")

    p = sub.add_parser("drop", help="Ingest a source into the knowledge store (one drop per effort).")
    p.add_argument("input", help="Path to the input document.")
    p.add_argument("--store", default="store",
                   help="Knowledge store directory (default: store).")
    p.add_argument("--filter", choices=["none", "standard", "strict"],
                   default="standard", help="Quality filter (default: standard).")
    p.add_argument("--coref", action="store_true",
                   help="Resolve leading pronouns before extraction.")
    p.add_argument("--engine", choices=["svo", "spacy"], default="svo",
                   help="Extraction engine (default: svo).")
    p.add_argument("--max-object-len", type=int, default=80,
                   help="Max object length for the quality filter (default: 80).")
    p.add_argument("--dedup", type=float, default=0.9,
                   help="Dedup similarity threshold 0..1 (default: 0.9).")
    p.add_argument("--min-reliability",
                   choices=["unverified", "possibly_true", "likely_true", "verified"],
                   default="likely_true",
                   help="Minimum reliability to keep (default: likely_true).")
    p.add_argument("--force", action="store_true",
                   help="Write a drop even if this exact source was already ingested.")

    c = sub.add_parser("catalog", help="Index the store and show stats / query facts.")
    c.add_argument("--store", default="store", help="Knowledge store directory.")
    c.add_argument("--source", help="Filter: facts from this source.")
    c.add_argument("--reliability",
                   choices=["UNVERIFIED", "POSSIBLY_TRUE", "LIKELY_TRUE", "VERIFIED"],
                   help="Filter: minimum reliability label.")
    c.add_argument("--category", help="Filter: facts in this category.")
    c.add_argument("--min-quality", type=int, help="Filter: minimum quality score.")
    c.add_argument("--limit", type=int, default=20, help="Max rows to print (default 20).")

    cp = sub.add_parser("compile", help="Compile a training set from the store (a reproducible view).")
    cp.add_argument("-o", "--output", required=True, help="Output file path.")
    cp.add_argument("--store", default="store", help="Knowledge store directory.")
    cp.add_argument("--format", choices=["chat", "instruction", "text"],
                    default="chat", help="Output format (default: chat).")
    cp.add_argument("--source", help="Filter: only facts from this source.")
    cp.add_argument("--reliability",
                    choices=["UNVERIFIED", "POSSIBLY_TRUE", "LIKELY_TRUE", "VERIFIED"],
                    help="Filter: reliability label.")
    cp.add_argument("--category", help="Filter: facts in this category.")
    cp.add_argument("--min-quality", type=int, help="Filter: minimum quality score.")
    cp.add_argument("--split", type=float, default=None,
                    help="Train/val split ratio (writes <out> + <out>.val).")
    cp.add_argument("--max-tokens", type=int, default=None,
                    help="Cap output to ~N tokens (highest quality first).")
    cp.add_argument("--seed", type=int, default=42, help="Split seed (default 42).")
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

    # Resolve the extraction engine (svo default; spacy needs the [nlp] extra).
    extractor = None
    if getattr(args, "engine", "svo") != "svo":
        from .extractor_base import get_extractor
        try:
            extractor = get_extractor(args.engine)
        except ImportError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3

    kg = KnowledgeGraph()
    skg = SemanticKnowledgeGraph(kg)
    ids = skg.create_facts_from_file(
        args.input, reliability=reliability, resolve_coref=args.coref,
        extractor=extractor,
    )

    quality_filter = _make_filter(args.filter, args.max_object_len)
    distiller = KnowledgeDistiller(
        kg,
        min_reliability=reliability,
        dedup_threshold=args.dedup,
        quality_filter=quality_filter,
    )

    # Build serialized records (one per selected fact).
    serializer = {
        "chat": distiller.to_chat_jsonl,
        "instruction": distiller.to_instruction_jsonl,
        "text": distiller.to_text,
    }[args.format]
    selected = distiller.select_facts()
    records = [line for line in serializer().splitlines() if line.strip()]

    # Cross-run dedup via a persistent fact store (by fact statement).
    if args.dedup_store:
        from .factstore import FactStore
        store = FactStore(path=args.dedup_store).load()
        kept_records = []
        for fact, rec in zip(selected, records):
            if store.add(fact.get("fact_statement", rec)):
                kept_records.append(rec)
        records = kept_records
        store.save()

    # Token budget: keep the highest-ranked records that fit.
    if args.max_tokens is not None:
        from .export import budget_records
        records = budget_records(records, args.max_tokens)

    def _write(path, lines):
        with open(path, "w", encoding="utf-8") as fh:
            for ln in lines:
                fh.write(ln + "\n")

    # Optional train/val split.
    if args.split is not None:
        from .export import split_records
        train, val = split_records(records, ratio=args.split, seed=args.seed)
        val_path = args.output + ".val"
        _write(args.output, train)
        _write(val_path, val)
        print(
            f"Extracted {len(ids)} raw facts; wrote {len(train)} train -> "
            f"{args.output} and {len(val)} val -> {val_path}."
        )
    else:
        _write(args.output, records)
        stats = distiller.stats()
        print(
            f"Extracted {len(ids)} raw facts; "
            f"wrote {len(records)} {args.format} pairs to {args.output} "
            f"(reduction ratio {stats['reduction_ratio']:.2f})."
        )
    return 0


def _cmd_eval(args) -> int:
    import os
    from .evaluation import load_gold_set, evaluate, format_report
    from .extraction import SVOExtractor
    if not os.path.isfile(args.gold):
        print(f"error: gold set not found: {args.gold}", file=sys.stderr)
        return 2
    report = evaluate(SVOExtractor(), load_gold_set(args.gold))
    print(format_report(report))
    return 0


def _cmd_drop(args) -> int:
    import os
    from .ingest import load_text
    from .store import KnowledgeStore, Drop, content_hash

    if not os.path.isfile(args.input):
        print(f"error: input file not found: {args.input}", file=sys.stderr)
        return 2

    text = load_text(args.input)
    src_hash = content_hash(text)
    store = KnowledgeStore(args.store)

    # Idempotency: skip if this exact source content was already dropped.
    if not args.force and store.has_source_hash(src_hash):
        print(f"skip: source already ingested (hash {src_hash[:12]}); use --force to re-drop.")
        return 0

    reliability = _RELIABILITY[args.min_reliability]

    extractor = None
    if args.engine != "svo":
        from .extractor_base import get_extractor
        try:
            extractor = get_extractor(args.engine)
        except ImportError as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 3

    kg = KnowledgeGraph()
    skg = SemanticKnowledgeGraph(kg)
    skg.create_facts_from_text(text, source_id=os.path.basename(args.input),
                               reliability=reliability, resolve_coref=args.coref,
                               extractor=extractor)

    quality_filter = _make_filter(args.filter, args.max_object_len)
    distiller = KnowledgeDistiller(kg, min_reliability=reliability,
                                   dedup_threshold=args.dedup,
                                   quality_filter=quality_filter)
    facts = distiller.select_facts()

    # Build a deterministic drop id from source basename + hash prefix.
    base = os.path.splitext(os.path.basename(args.input))[0]
    drop_id = f"{base}-{src_hash[:12]}"

    drop = Drop(
        drop_id=drop_id,
        source=args.input,
        source_hash=src_hash,
        facts=facts,
        engine=args.engine,
        filter_name=args.filter,
        coref=args.coref,
        source_text=text,
    )
    shard = store.write_drop(drop)
    print(
        f"Dropped {len(facts)} facts from {args.input} -> {shard} "
        f"(store now has {store.stats()['total_drops']} drops, "
        f"{store.stats()['total_facts']} facts)."
    )
    return 0


def _cmd_catalog(args) -> int:
    import os
    from .store import KnowledgeStore
    from .catalog import Catalog
    if not os.path.isdir(args.store):
        print(f"error: store not found: {args.store}", file=sys.stderr)
        return 2
    store = KnowledgeStore(args.store)
    cat = Catalog(os.path.join(args.store, "catalog.db"))
    cat.rebuild(store)

    any_filter = any([args.source, args.reliability, args.category, args.min_quality])
    if any_filter:
        rows = cat.query(source=args.source, reliability=args.reliability,
                         category=args.category, min_quality=args.min_quality,
                         limit=args.limit)
        print(f"{len(rows)} matching facts (showing up to {args.limit}):")
        for r in rows:
            print(f"  [{r['reliability']}/{r['quality']}] {r['statement']}  <- {r['source']}")
    else:
        s = cat.stats()
        print("Knowledge store catalog")
        print(f"  total facts: {s['total_facts']}")
        print(f"  total drops: {s['total_drops']}")
        print(f"  sources:     {s['sources']}")
        print("  by reliability:")
        for rel, n in sorted(s["by_reliability"].items()):
            print(f"    {rel}: {n}")
    cat.close()
    return 0


def _row_to_record(row, fmt):
    """Turn a catalog row into a serialized record line for the given format."""
    import json as _json
    q = row.get("question") or f"Tell me a fact about {row.get('category') or 'General'}."
    a = row.get("answer") or row.get("statement") or ""
    if fmt == "chat":
        return _json.dumps({"messages": [
            {"role": "user", "content": q},
            {"role": "assistant", "content": a},
        ]}, ensure_ascii=False)
    if fmt == "instruction":
        return _json.dumps({"instruction": q, "input": "", "output": a}, ensure_ascii=False)
    # text
    return f"- {row.get('statement') or a}"


def _cmd_compile(args) -> int:
    import os
    from .store import KnowledgeStore
    from .catalog import Catalog
    if not os.path.isdir(args.store):
        print(f"error: store not found: {args.store}", file=sys.stderr)
        return 2

    store = KnowledgeStore(args.store)
    cat = Catalog(os.path.join(args.store, "catalog.db"))
    cat.rebuild(store)

    rows = cat.query(source=args.source, reliability=args.reliability,
                     category=args.category, min_quality=args.min_quality)
    records = [_row_to_record(r, args.format) for r in rows]
    drops_used = sorted({r["drop_id"] for r in rows})
    cat.close()

    if args.max_tokens is not None:
        from .export import budget_records
        records = budget_records(records, args.max_tokens)

    def _write(path, lines):
        with open(path, "w", encoding="utf-8") as fh:
            for ln in lines:
                fh.write(ln + "\n")

    if args.split is not None:
        from .export import split_records
        train, val = split_records(records, ratio=args.split, seed=args.seed)
        _write(args.output, train)
        _write(args.output + ".val", val)
        print(
            f"Compiled {len(records)} facts from {len(drops_used)} drop(s) -> "
            f"{len(train)} train ({args.output}) + {len(val)} val ({args.output}.val)."
        )
    else:
        _write(args.output, records)
        print(
            f"Compiled {len(records)} facts from {len(drops_used)} drop(s) -> "
            f"{args.output} (format {args.format})."
        )
    return 0


def main(argv: Optional[List[str]] = None) -> int:
    """CLI entrypoint. Returns a process exit code."""
    parser = _build_parser()
    args = parser.parse_args(argv)
    if args.command == "distill":
        return _cmd_distill(args)
    if args.command == "eval":
        return _cmd_eval(args)
    if args.command == "drop":
        return _cmd_drop(args)
    if args.command == "catalog":
        return _cmd_catalog(args)
    if args.command == "compile":
        return _cmd_compile(args)
    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
