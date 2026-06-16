"""
Cross-model verification (ModelReduce Session 2).

A single model asserting a fact is not evidence the fact is true -- models
hallucinate confidently. The corroboration signal we trust is **independent
agreement**: when several architecturally distinct models, probed separately,
emit the *same* fact, that fact earns a higher reliability rating.

:class:`CrossModelVerifier` runs an identical probe set across N models,
converts every model's structured output into facts (via
:func:`model_drop.probe_output_to_facts`), clusters semantically-equivalent
facts together, and counts how many *distinct models* back each cluster. That
count drives promotion up the reliability ladder:

    1 model   -> POSSIBLY_TRUE   (a lone claim)
    2 models  -> LIKELY_TRUE     (corroborated)
    >=3 models -> VERIFIED        (consensus)

The verifier is backend-agnostic: it is constructed from a list of
:class:`~knowledge_graph_pkg.model_probe.ModelProbe` instances (tests inject
fakes; production uses Ollama-backed probes via :meth:`from_ollama`). The
clustering reuses the same dependency-free Jaccard similarity the distiller
uses, so no NLP model is required.
"""

from collections import OrderedDict
from typing import Any, Dict, List, Optional

from .model_drop import probe_output_to_facts

# Reliability tier assigned by number of agreeing distinct models.
_AGREEMENT_RELIABILITY = {
    1: "POSSIBLY_TRUE",
    2: "LIKELY_TRUE",
}
_VERIFIED = "VERIFIED"


def _norm(s: Any) -> str:
    return " ".join(str(s or "").lower().split())


def jaccard(a: str, b: str) -> float:
    """Dependency-free Jaccard word-overlap similarity in ``[0, 1]``."""
    if a == b:
        return 1.0
    wa, wb = set(a.lower().split()), set(b.lower().split())
    if not wa or not wb:
        return 0.0
    return len(wa & wb) / len(wa | wb)


def reliability_for_agreement(n_models: int) -> str:
    """Map a distinct-model agreement count to a reliability rating."""
    if n_models >= 3:
        return _VERIFIED
    return _AGREEMENT_RELIABILITY.get(max(n_models, 0), "UNVERIFIED")


class CrossModelVerifier:
    """Probe N models with identical prompts and corroborate their facts."""

    def __init__(self, probes: List[Any], similarity_threshold: float = 0.8):
        if not probes:
            raise ValueError("CrossModelVerifier needs at least one probe.")
        self.probes = list(probes)
        self.similarity_threshold = similarity_threshold

    # ------------------------------------------------------------------ #
    # Construction helpers
    # ------------------------------------------------------------------ #
    @classmethod
    def from_ollama(cls, models: List[str], host: str = "http://localhost:11434",
                    similarity_threshold: float = 0.8) -> "CrossModelVerifier":
        """Build a verifier backed by local Ollama models."""
        from .model_probe import ModelProbe, OllamaBackend
        probes = [ModelProbe(backend=OllamaBackend(model=m, host=host), model=m)
                  for m in models]
        return cls(probes, similarity_threshold=similarity_threshold)

    # ------------------------------------------------------------------ #
    # Core verification
    # ------------------------------------------------------------------ #
    def probe_domain(self, domain: str, entities: Optional[List[str]] = None,
                     n_prompts: int = 10, seed: int = 42,
                     **gen_kwargs) -> Dict[str, Any]:
        """Probe every model over ``domain`` with the *same* prompts, then
        cross-verify. Returns a report (see :meth:`verify`)."""
        outputs_by_model: Dict[str, List[Dict[str, Any]]] = OrderedDict()
        for probe in self.probes:
            outs = probe.probe_domain(domain, entities=entities,
                                      n_prompts=n_prompts, seed=seed, **gen_kwargs)
            outputs_by_model.setdefault(probe.model, []).extend(outs)
        return self.verify(outputs_by_model)

    def verify(self, outputs_by_model: Dict[str, List[Dict[str, Any]]]) -> Dict[str, Any]:
        """Cluster facts across models and assign agreement-based reliability.

        ``outputs_by_model`` maps a model name to its list of probe outputs.
        Returns a report with the agreement clusters and tier counts.
        """
        # Flatten to (model, fact) pairs.
        all_facts: List[Dict[str, Any]] = []
        for model, outputs in outputs_by_model.items():
            for fact in _facts_from_outputs(outputs):
                fact = dict(fact)
                fact["_model"] = model
                all_facts.append(fact)

        clusters = self._cluster(all_facts)

        report_clusters: List[Dict[str, Any]] = []
        verified = likely = possibly = 0
        for cl in clusters:
            models = sorted({f["_model"] for f in cl})
            n = len(models)
            reliability = reliability_for_agreement(n)
            if reliability == _VERIFIED:
                verified += 1
            elif reliability == "LIKELY_TRUE":
                likely += 1
            else:
                possibly += 1
            # Representative = highest-quality fact in the cluster.
            rep = max(cl, key=lambda f: f.get("quality_score", 0))
            report_clusters.append({
                "statement": rep["fact_statement"],
                "subject": rep.get("subject"),
                "predicate": rep.get("predicate"),
                "object": rep.get("object"),
                "category": rep.get("category"),
                "models": models,
                "n_models": n,
                "reliability": reliability,
                "cross_model_agreement": n,
                "member_count": len(cl),
            })

        # Most-corroborated first for readable reports.
        report_clusters.sort(key=lambda c: (-c["n_models"], -c["member_count"],
                                            c["statement"]))
        return {
            "clusters": report_clusters,
            "n_clusters": len(report_clusters),
            "verified": verified,
            "likely_true": likely,
            "possibly_true": possibly,
            "models": sorted(outputs_by_model.keys()),
            "total_facts": len(all_facts),
        }

    # ------------------------------------------------------------------ #
    def _cluster(self, facts: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
        """Greedy single-pass clustering by statement similarity.

        Two facts join the same cluster when their normalized statements'
        Jaccard similarity meets ``similarity_threshold`` OR they share an
        identical (subject, predicate, object) triple (exact-match fast path,
        robust to phrasing differences).
        """
        clusters: List[List[Dict[str, Any]]] = []
        reps: List[Dict[str, str]] = []  # parallel: cached norm keys per cluster
        for fact in facts:
            stmt = _norm(fact.get("fact_statement"))
            spo = (_norm(fact.get("subject")), _norm(fact.get("predicate")),
                   _norm(fact.get("object")))
            placed = False
            for idx, rep in enumerate(reps):
                if rep["spo"] == "\x00".join(spo):
                    clusters[idx].append(fact)
                    placed = True
                    break
                if jaccard(stmt, rep["stmt"]) >= self.similarity_threshold:
                    clusters[idx].append(fact)
                    placed = True
                    break
            if not placed:
                clusters.append([fact])
                reps.append({"stmt": stmt, "spo": "\x00".join(spo)})
        return clusters

    # ------------------------------------------------------------------ #
    def verified_facts(self, report: Dict[str, Any], min_models: int = 2) -> List[Dict[str, Any]]:
        """Extract corroborated facts from a report as store-ready fact dicts.

        Keeps clusters backed by ``>= min_models`` distinct models and emits
        one fact per cluster, carrying the promoted reliability, the agreeing
        models, and a question/answer pair for distillation.
        """
        out: List[Dict[str, Any]] = []
        for cl in report["clusters"]:
            if cl["n_models"] < min_models:
                continue
            statement = cl["statement"]
            subject = cl.get("subject") or ""
            category = cl.get("category") or "General"
            reliability = cl["reliability"]
            quality = {"VERIFIED": 40, "LIKELY_TRUE": 30}.get(reliability, 20)
            quality += cl["n_models"]  # tie-break toward broader consensus
            out.append({
                "fact_statement": statement,
                "subject": subject,
                "predicate": cl.get("predicate"),
                "object": cl.get("object"),
                "category": category,
                "reliability_rating": reliability,
                "quality_score": quality,
                "question": f"State a verified fact about {subject}." if subject
                            else f"State a verified fact about {category}.",
                "answer": statement,
                "cross_model_agreement": cl["n_models"],
                "source_models": cl["models"],
            })
        return out


def _facts_from_outputs(outputs: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Convert a model's probe outputs to facts (POSSIBLY_TRUE per claim)."""
    facts: List[Dict[str, Any]] = []
    for po in outputs:
        facts.extend(probe_output_to_facts(po, reliability="POSSIBLY_TRUE"))
    return facts
