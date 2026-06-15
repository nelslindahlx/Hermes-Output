# ModelReduce: Master Implementation Plan

**Status:** Ready for Session 1  
**Package:** `/Users/nelslindahl/Hermes-Output/knowledgereduce/`  
**Philosophy:** Models are ore. KnowledgeReduce is the refinery. Shards are pure metal.

---

## Executive Summary

**ModelReduce** extends KnowledgeReduce to systematically harvest knowledge from abandoned models via structured prompt probing, cross-model verification, and distillation into model-agnostic training shards.

**Core Insight:** Prompt probing is the practical path. Weight/activation analysis is research-grade, architecture-specific, and still requires forward passes. The model's *output tokens* are its own decoder from weights to language — use that decoder.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                        MODELREDUCE PIPELINE                                 │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ABANDONED MODELS                                                           │
│  ├─ Ollama (local quantized)                                                │
│  ├─ HuggingFace checkpoints                                                 │
│  ├─ GGUF files                                                              │
│  ├─ vLLM endpoints                                                          │
│  └─ OpenAI-compatible APIs                                                  │
│        │                                                                    │
│        ▼                                                                    │
│  ┌─────────────────┐    ┌──────────────────┐    ┌──────────────────────┐   │
│  │  MODEL PROBE    │───▶│  MODEL DROPS     │───▶│  CROSS-MODEL         │   │
│  │  (Session 1)    │    │  (Session 2)     │    │  VERIFICATION        │   │
│  │                 │    │                  │    │  (Session 2)         │   │
│  │ • Backend-agnostic     │ • Provenance   │    │                      │   │
│  │ • Domain templates  │ • Prompt+Response│    │ • Semantic clustering│   │
│  │ • Batched gen       │ • Gen params     │    │ • Agreement counting │   │
│  └─────────────────┘    └──────────────────┘    └──────────┬───────────┘   │
│                                                            │               │
│                                                            ▼               │
│  ┌─────────────────┐    ┌──────────────────┐    ┌──────────────────────┐   │
│  │  MODEL DISTILL  │◀───│  KNOWLEDGE GRAPH │◀───│  LIFECYCLE           │   │
│  │  (Session 3)    │    │  + STORE         │    │  PROMOTION           │   │
│  │                 │    │  (Existing)      │    │  (Existing)          │   │
│  │ • Filter: min_model_agreement             │    │                      │   │
│  │ • Dedup: cross-model Jaccard              │    │ • 2 models = LIKELY  │   │
│  │ • Rank: quality × agreement               │    │ • 3 models = VERIFIED│   │
│  │ • Output: chat/inst/RAG + manifest        │    └──────────────────────┘   │
│  └────────┬────────┘                                                        │
│           │                                                                 │
│           ▼                                                                 │
│  ┌─────────────────┐    ┌──────────────────┐    ┌──────────────────────┐   │
│  │  GRAVEYARD CLI  │    │  EVALUATION      │    │  GRAPH TOOLS + MCP   │   │
│  │  (Session 4)    │    │  (Session 5)     │    │  (Session 6)         │   │
│  │                 │    │                  │    │                      │   │
│  │ • Model discovery  │ • Gold sets      │    │ • Cypher queries     │   │
│  │ • Resource mgmt    │ • Calibrated     │    │ • NL → Cypher        │   │
│  │ • Resume/checkpoint│   thresholds    │    │ • MCP server         │   │
│  │ • Rich progress    │ • CI gates       │    │ • LLM tool use       │   │
│  └────────┬────────┘    └────────┬─────────┘    └──────────────────────┘   │
│           │                      │                                          │
│           └──────────┬───────────┘                                          │
│                      ▼                                                       │
│           ┌─────────────────────┐                                           │
│           │  TRAINING RUN       │                                           │
│           │  (Session 7)        │                                           │
│           │                     │                                           │
│           │ • Compile shards    │                                           │
│           │ • LoRA/qlora SFT    │                                           │
│           │ • Benchmark vs base │                                           │
│           │ • Faithfulness eval │                                           │
│           └──────────┬──────────┘                                           │
│                      │                                                       │
│                      ▼                                                       │
│           ┌─────────────────────┐                                           │
│           │  DOCS + RELEASE     │                                           │
│           │  (Session 8)        │                                           │
│           │                     │                                           │
│           │ • Tutorial notebook │                                           │
│           │ • PyPI extra        │                                           │
│           │ • Docker + CI       │                                           │
│           └─────────────────────┘                                           │
│                                                                             │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Session Plan (8 Sessions)

### Session 1: Model Probe Infrastructure
**Target:** `knowledge_graph_pkg/model_probe.py`, `probe_templates.py`

**Backend Support (pluggable, lazy-loaded):**
```python
class ProbeBackend(Protocol):
    def generate(self, prompts: List[str], **gen_kwargs) -> List[str]: ...

# Implementations:
class OllamaBackend(ProbeBackend): ...
class HFBackend(ProbeBackend): ...      # transformers + accelerate
class VLLMBackend(ProbeBackend): ...    # vllm.LLM
class APIBackend(ProbeBackend): ...     # OpenAI-compatible
```

**Prompt Templates (domain-parameterized):**
| Type | Template | Use Case |
|------|----------|----------|
| `entity` | "State a verified fact about {entity} in {domain}." | Atomic facts |
| `relation` | "What is the relationship between {e1} and {e2} in {domain}?" | Relations |
| `concept` | "Explain {concept} in {domain} with 3 key facts." | Conceptual |
| `list` | "List 5 verified facts about {topic} in {domain}." | Coverage |
| `negative` | "What is a common misconception about {topic} in {domain}?" | Error mining |

**Seed Entity Extraction:** Bootstrap entities from existing KnowledgeGraph to generate targeted probes.

**Output Schema:**
```json
{
  "model": "model-name",
  "backend": "ollama|hf|vllm|api",
  "domain": "biochemistry",
  "prompt_type": "entity|relation|concept|list|negative",
  "prompt": "...",
  "response": "...",
  "gen_config": {"temperature": 0.3, "top_p": 0.9, "max_tokens": 512, "seed": 42},
  "timestamp": "2026-06-15T..."
}
```

**Verification:**
```bash
python -c "
from knowledge_graph_pkg.model_probe import ModelProbe
probe = ModelProbe(backend='ollama', model='qwen2.5:14b')
outputs = probe.probe_domain('biochemistry', n_prompts=10)
assert len(outputs) == 10
assert all('response' in o for o in outputs)
print('✓ Session 1 verified')
"
```

---

### Session 2: Model Drops + Cross-Model Verification
**Target:** `knowledge_graph_pkg/model_drop.py`, `cross_model.py`

**ModelDrop Class:**
- Extends existing `Drop` with `model_provenance` field
- Stores: prompt, response, model_id, backend, gen_config, prompt_type
- Content hash includes model identity (same prompt + different model = different drop)

**CrossModelVerifier:**
```python
verifier = CrossModelVerifier(models=['qwen2.5:14b', 'phi4:latest', 'deepseek:7b'])
results = verifier.probe_domain('biochemistry', n_prompts=500)

# Results structure:
{
  "clusters": [
    {
      "canonical_fact": "Mitochondria produce ATP via oxidative phosphorylation",
      "supporting_models": ["qwen2.5:14b", "phi4:latest", "deepseek:7b"],
      "model_responses": {...},
      "extracted_facts": [...],  # SVO extraction per model
      "agreement_count": 3,
      "jaccard_similarity": 0.92
    },
    ...
  ],
  "verified": 842,      # agreement >= 3
  "likely_true": 1234,  # agreement == 2
  "singletons": 567,    # agreement == 1
  "conflicts": [...],   # same subject, different objects
}
```

**Semantic Clustering:**
- Extract SVO facts from each model's response independently
- Cluster by Jaccard similarity (threshold 0.85 cross-model, 0.9 intra-model)
- Cluster representative = highest quality_score fact
- Agreement count = distinct models in cluster

**Integration with Existing Lifecycle:**
```python
# Extend promote_reliability in lifecycle.py
def promote_reliability(store, min_sources=2, min_models=2):
    # min_sources = distinct source documents
    # min_models = distinct models agreeing
    # Both criteria must pass for promotion
```

**Verification:**
```bash
python -c "
from knowledge_graph_pkg.cross_model import CrossModelVerifier
verifier = CrossModelVerifier(models=['qwen2.5:14b', 'phi4:latest'])
report = verifier.probe_domain('biochemistry', n_prompts=100)
assert report['verified'] > 0
assert report['likely_true'] > 0
print(f'Verified: {report[\"verified\"]}, Likely: {report[\"likely_true\"]}')
"
```

---

### Session 3: Model Distillation Pipeline + CLI
**Target:** `knowledge_graph_pkg/model_distill.py`, CLI extensions in `cli.py`

**ModelKnowledgeDistiller:**
```python
class ModelKnowledgeDistiller(KnowledgeDistiller):
    """Specialized distiller for model-derived facts with provenance."""
    
    def __init__(self, kg, min_model_agreement=2, min_reliability=LIKELY_TRUE, ...):
        self.min_model_agreement = min_model_agreement
        # Inherits: dedup_threshold, quality_filter, top_k
    
    def select_facts(self) -> List[Dict]:
        # Filter: model_agreement >= min_model_agreement
        # Filter: reliability >= min_reliability
        # Quality filter (existing FactQualityFilter)
        # Cross-model dedup: Jaccard >= 0.85
        # Rank: quality_score * log(model_agreement + 1)
        # Top-k truncation
        ...
```

**Output Formats (extended with provenance):**
```json
// chat.jsonl - SFT format
{"messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}], 
 "metadata": {"source_models": ["m1", "m2"], "agreement": 2, "reliability": "VERIFIED"}}

// instruction.jsonl - IFT format  
{"instruction": "...", "input": "", "output": "...", 
 "metadata": {"source_models": ["m1", "m2"], "agreement": 2}}

// rag.txt - RAG corpus with citations
"1. Mitochondria produce ATP via oxidative phosphorylation [qwen2.5:14b, phi4:latest; VERIFIED]"

// manifest.json - Shard provenance
{
  "shard": "biochem_v1",
  "created": "2026-06-15T...",
  "models_probed": ["qwen2.5:14b", "phi4:latest"],
  "total_facts": 5000,
  "verified": 3200,
  "likely_true": 1800,
  "domains": ["biochemistry"],
  "min_agreement": 2,
  "dedup_threshold": 0.85
}
```

**CLI Commands:**
```bash
# Probe models
knowledgereduce model-probe --models qwen2.5:14b,phi4:latest \
  --domains biochem,physics --n-prompts 500 --output ./model_drops/

# Distill drops into shards
knowledgereduce model-distill ./model_drops/ --output ./shards/ \
  --format chat,instruction,text --min-agreement 2 \
  --max-tokens 100000 --split 0.9
```

**Verification:**
```bash
knowledgereduce model-probe --models qwen2.5:14b,phi4:latest \
  --domains biochem --n-prompts 100 --output /tmp/test_drops

knowledgereduce model-distill /tmp/test_drops --output /tmp/test_shards \
  --format chat --min-agreement 2 --max-tokens 5000

# Verify output
head -3 /tmp/test_shards/biochem_chat.jsonl | jq '.metadata.source_models'
wc -l /tmp/test_shards/biochem_chat.jsonl
cat /tmp/test_shards/manifest.json | jq '.verified'
```

---

### Session 4: Graveyard CLI + Batch Orchestration
**Target:** `knowledgereduce graveyard` subcommand

**Model Discovery:**
```python
def discover_models(path: str) -> List[ModelSpec]:
    # Ollama: `ollama list` → parse names
    # HF checkpoints: folders with config.json
    # GGUF: *.gguf files
    # vLLM: config.yaml with endpoint list
    # Return: [{name, backend, path, size_gb, quantization}, ...]
```

**Graveyard Command:**
```bash
knowledgereduce graveyard /path/to/models/ \
  --domains biochem,physics,law,coding,math \
  --models-per-domain 3 \
  --promote-threshold 2 \
  --output-shards ./shards/ \
  --backend auto \           # auto-detect per model
  --resume \                 # checkpoint per model/domain
  --max-concurrent 1         # sequential GPU unload
```

**Resource Management:**
- Load model → probe all domains → unload → next model
- GPU memory cleanup between models (`torch.cuda.empty_cache()`)
- Checkpoint: `./graveyard_state/{model}_{domain}.json`
- Resume skips completed model-domain pairs

**Progress Reporting:**
```
┌──────────────┬────────────┬──────────┬──────────┬──────────┐
│ Model        │ Domain     │ Prompts  │ Facts    │ Verified │
├──────────────┼────────────┼──────────┼──────────┼──────────┤
│ qwen2.5:14b  │ biochem    │ 500      │ 1,247    │ 342      │
│ qwen2.5:14b  │ physics    │ 500      │ 1,156    │ 298      │
│ phi4:latest  │ biochem    │ 500      │ 1,089    │ 267      │
│ phi4:latest  │ physics    │ 500      │ 1,134    │ 312      │
├──────────────┼────────────┼──────────┼──────────┼──────────┤
│ TOTAL        │ biochem    │ 1,000    │ 2,156    │ 842★     │
│ TOTAL        │ physics    │ 1,000    │ 2,290    │ 610★     │
└──────────────┴────────────┴──────────┴──────────┴──────────┘
★ = cross-model verified (agreement ≥ 2)
```

**Verification:**
```bash
# Test with 2 local Ollama models
knowledgereduce graveyard --models qwen2.5:14b,phi4:latest \
  --domains biochem --n-prompts 50 --output-shards /tmp/test_graveyard

ls -la /tmp/test_graveyard/
cat /tmp/test_graveyard/manifest.json | jq '.models_probed, .verified'
```

---

### Session 5: Evaluation Framework + Quality Gates
**Target:** `knowledge_graph_pkg/model_eval.py`, gold sets, CI config

**Gold Set Construction (per domain):**
```json
// data/gold_biochem.json
{
  "domain": "biochemistry",
  "facts": [
    {"statement": "Mitochondria produce ATP via oxidative phosphorylation", "verified": true},
    {"statement": "DNA polymerase synthesizes DNA in 5' to 3' direction", "verified": true},
    {"statement": "Glucose is the primary energy source for brain cells", "verified": true},
    ...
  ],
  "negative": [
    {"statement": "Mitochondria perform photosynthesis", "verified": false},
    ...
  ]
}
```

**Evaluator:**
```python
class ModelShardEvaluator:
    def evaluate_shard(self, shard_path: str, gold_path: str) -> EvaluationReport:
        # Load shard facts + gold facts
        # Match by semantic similarity (Jaccard ≥ 0.8)
        # Compute per-tier metrics:
        return {
            "verified": {"precision": 0.96, "recall": 0.72, "f1": 0.82, "count": 3200},
            "likely_true": {"precision": 0.88, "recall": 0.65, "f1": 0.75, "count": 1800},
            "singletons": {"precision": 0.45, "recall": 0.31, "f1": 0.37, "count": 567},
            "hallucination_rate": 0.03,    # shard facts contradicted by gold negative
            "coverage": 0.68,              # % of gold facts recovered
            "agreement_calibration": {
                "2_models": {"precision": 0.88, "n": 4200},
                "3_models": {"precision": 0.96, "n": 3200},
                "4_models": {"precision": 0.98, "n": 1100}
            }
        }
```

**Quality Gates (CI-ready):**
```yaml
# .github/workflows/model-reduce.yml
gates:
  min_precision_verified: 0.95
  min_recall_verified: 0.60
  min_precision_likely_true: 0.80
  max_hallucination_rate: 0.05
  min_coverage: 0.55
  min_facts_per_domain: 1000
```

**CLI:**
```bash
knowledgereduce model-eval --shard ./shards/biochem_chat.jsonl \
  --gold ./data/gold_biochem.json --output ./eval_report.json

# CI mode: exits non-zero if gates fail
knowledgereduce model-eval --shard ./shards/ --gold ./data/ --ci
```

---

### Session 6: Graph Query Interface + MCP Server
**Target:** `knowledge_graph_pkg/graph_tool.py`, MCP server

**Graph Tools (LLM-callable):**
```python
def graph_query(cypher: str, domain: str = None, limit: int = 100) -> List[Dict]:
    """Execute Cypher query on KnowledgeGraph."""
    # Uses networkx + custom Cypher subset parser

def graph_get_fact(fact_id: str) -> Dict:
    """Retrieve full fact with provenance, sources, model agreements."""

def graph_find_related(fact_id: str, hops: int = 1, rel_types: List[str] = None) -> List[Dict]:
    """Graph traversal from a fact."""

def graph_find_by_subject(subject: str, domain: str = None) -> List[Dict]:
    """Find all facts about a subject entity."""

def graph_stats(domain: str = None) -> Dict:
    """Return fact counts by reliability, category, model agreement."""
```

**Natural Language → Cypher (template-based):**
```python
NL_TEMPLATES = {
    "facts_about": "MATCH (f) WHERE f.subject CONTAINS '{subject}' AND f.reliability IN {reliability} RETURN f LIMIT {limit}",
    "verified_in_domain": "MATCH (f) WHERE f.domain = '{domain}' AND f.reliability = 'VERIFIED' RETURN f LIMIT {limit}",
    "model_agreement": "MATCH (f) WHERE f.model_agreement >= {n} RETURN f LIMIT {limit}",
    "contradictions": "MATCH (f1), (f2) WHERE f1.subject = f2.subject AND f1.object != f2.object RETURN f1, f2",
}
```

**MCP Server:**
```bash
knowledgereduce serve-mcp --store ./store --port 8080 --host 0.0.0.0
```

**Tool Schema (auto-generated for LLM function calling):**
```json
{
  "name": "graph_query",
  "description": "Query the knowledge graph with Cypher",
  "parameters": {
    "type": "object",
    "properties": {
      "cypher": {"type": "string", "description": "Cypher query"},
      "domain": {"type": "string", "description": "Filter by domain"},
      "limit": {"type": "integer", "default": 100}
    },
    "required": ["cypher"]
  }
}
```

---

### Session 7: End-to-End Training Run
**Target:** Trained model + evaluation report

**Compile Training Mix:**
```bash
knowledgereduce compile --store ./store --output ./training_mix.jsonl \
  --format chat --min-quality 0.7 \
  --reliability LIKELY_TRUE,VERIFIED \
  --max-tokens 200000 --split 0.95 \
  --domains biochem,physics,law,coding,math
```

**SFT Training (any trainer):**
```bash
# HF SFTTrainer example
python train_sft.py \
  --model_name_or_path Qwen/Qwen2.5-7B \
  --dataset ./training_mix.jsonl \
  --output_dir ./modelreduce-qwen-7b \
  --lora_rank 32 --lora_alpha 64 \
  --learning_rate 2e-4 --num_epochs 3 \
  --per_device_train_batch_size 4 \
  --gradient_accumulation_steps 4 \
  --bf16 --gradient_checkpointing
```

**Evaluation Suite:**
| Benchmark | Metric | Target |
|-----------|--------|--------|
| Domain QA (biochem, physics, law, coding, math) | Accuracy | > base model +10% |
| Hallucination rate (TruthfulQA-style) | % false claims | < base model -50% |
| Faithfulness to KG | % answers traceable to KG facts | > 90% |
| Contradiction detection | F1 on known conflicts | > 0.85 |
| General capability (MMLU, GSM8K) | No regression | ±2% |

**Deliverable:** `modelreduce-qwen-7b/` checkpoint + `TRAINING_REPORT.md`

---

### Session 8: Documentation, Tutorial, Release
**Target:** Production-ready package

**Documentation:**
- `README.md` — ModelReduce architecture + quickstart
- `docs/model_reduce.md` — Full API reference
- `examples/model_reduce_tutorial.ipynb` — End-to-end notebook:
  1. Probe 2 Ollama models
  2. Cross-verify on biochemistry
  3. Distill to shards
  4. Compile training mix
  5. Train LoRA
  6. Evaluate

**Packaging:**
```toml
# pyproject.toml additions
[project.optional-dependencies]
model-reduce = [
    "ollama>=0.3.0",
    "vllm>=0.4.0",
    "accelerate>=0.25.0",
    "transformers>=4.37.0",
]
```

**Dockerfile:**
```dockerfile
FROM nvidia/cuda:12.1-runtime-ubuntu22.04
# Ollama + vLLM + HF + KnowledgeReduce
# Entrypoint: knowledgereduce
```

**CI/CD:**
- GitHub Actions: test with mock models (fast)
- Nightly: real model probe on 2 Ollama models
- Release: PyPI on tag

---

## Dependency Management

**Core (always):** `networkx>=2.5`, `numpy>=1.19.0`  
**Existing Extras:** `ingest`, `pdf`, `nlp`, `viz`, `dev`  
**New Extra:** `model-reduce` = `ollama`, `vllm`, `accelerate`, `transformers`

**Lazy Import Pattern (all backends):**
```python
# model_probe.py
def _import_ollama():
    try:
        import ollama
        return ollama
    except ImportError:
        raise ImportError("Ollama backend requires: pip install knowledgereduce[model-reduce]")
```

---

## Session Dependency Graph

```
Session 1 (ModelProbe)
    ↓
Session 2 (ModelDrop + CrossModel) ← needs Session 1
    ↓
Session 3 (ModelDistill + CLI) ← needs Session 2
    ↓
Session 4 (Graveyard CLI) ← needs Session 3
    ├────────────────────┐
    ↓                    ↓
Session 5 (Eval)    Session 6 (Graph Tools + MCP) ← needs Sessions 1-3
    ↓                    ↓
    └──────────┬─────────┘
               ↓
         Session 7 (Training Run) ← needs 4,5,6
               ↓
         Session 8 (Docs + Release) ← needs 7
```

---

## Quick-Start Prompts for Each Session

### Session 1
> Continue ModelReduce Session 1. Build `ModelProbe` with Ollama/HF/vLLM/API backends and domain prompt templates. Deliverable: `model_probe.py`, `probe_templates.py`. Verify: probe 10 biochem prompts on qwen2.5:14b.

### Session 2
> Continue ModelReduce Session 2. Build `ModelDrop` + `CrossModelVerifier`. Cluster facts by Jaccard, count model agreement, integrate with lifecycle promotion. Deliverable: `model_drop.py`, `cross_model.py`. Verify: 2 models, 100 prompts, report verified/likely counts.

### Session 3
> Continue ModelReduce Session 3. Build `ModelKnowledgeDistiller` + CLI commands `model-probe` and `model-distill`. Provenance in output metadata. Deliverable: `model_distill.py`, CLI extensions. Verify: end-to-end probe → distill → shards with manifest.

### Session 4
> Continue ModelReduce Session 4. Build `graveyard` subcommand: model discovery, sequential GPU unload, resume checkpoints, rich progress table. Deliverable: graveyard command. Verify: 2 models, 1 domain, shards + manifest produced.

### Session 5
> Continue ModelReduce Session 5. Build evaluation framework with gold sets, agreement calibration, CI gates. Deliverable: `model_eval.py`, gold sets, CI config. Verify: eval report with precision/recall per tier, gates pass/fail.

### Session 6
> Continue ModelReduce Session 6. Build graph query tools + MCP server. Cypher subset, NL templates, auto-generated tool schemas. Deliverable: `graph_tool.py`, MCP server. Verify: LLM calls graph_query via MCP, returns facts.

### Session 7
> Continue ModelReduce Session 7. Compile shards → train LoRA on Qwen2.5-7B → evaluate on domain QA, hallucination, faithfulness. Deliverable: trained checkpoint + TRAINING_REPORT.md. Verify: +10% domain accuracy, -50% hallucination vs base.

### Session 8
> Continue ModelReduce Session 8. Write tutorial notebook, package for PyPI, Dockerfile, CI. Deliverable: `model_reduce_tutorial.ipynb`, `pip install knowledgereduce[model-reduce]`. Verify: tutorial runs end-to-end in Colab.

---

## File Structure After Completion

```
knowledgereduce/
├── knowledge_graph_pkg/
│   ├── core.py                    # Existing
│   ├── extraction.py              # Existing (SVOExtractor)
│   ├── distillation.py            # Existing (KnowledgeDistiller)
│   ├── quality.py                 # Existing (FactQualityFilter)
│   ├── lifecycle.py               # Existing (promote_reliability, etc.)
│   ├── semantic.py                # Existing (SemanticKnowledgeGraph)
│   ├── ingest.py                  # Existing
│   ├── store.py / catalog.py      # Existing
│   ├── cli.py                     # Extended: model-probe, model-distill, graveyard, model-eval
│   │
│   ├── model_probe.py          ◀── NEW (Session 1)
│   ├── probe_templates.py      ◀── NEW (Session 1)
│   ├── model_drop.py           ◀── NEW (Session 2)
│   ├── cross_model.py          ◀── NEW (Session 2)
│   ├── model_distill.py        ◀── NEW (Session 3)
│   ├── model_eval.py           ◀── NEW (Session 5)
│   ├── graph_tool.py           ◀── NEW (Session 6)
│   │
│   └── data/
│       ├── gold_biochem.json
│       ├── gold_physics.json
│       ├── gold_law.json
│       ├── gold_coding.json
│       └── gold_math.json
│
├── examples/
│   └── model_reduce_tutorial.ipynb     ◀── NEW (Session 8)
│
├── tests/
│   ├── test_model_probe.py
│   ├── test_cross_model.py
│   ├── test_model_distill.py
│   ├── test_graveyard.py
│   └── test_model_eval.py
│
├── Dockerfile                        ◀── NEW (Session 8)
├── .github/workflows/model-reduce.yml ◀── NEW (Session 5/8)
├── MODELREDUCE_SESSIONS.md           ◀── THIS FILE
├── pyproject.toml                    # Updated with model-reduce extra
└── README.md                         # Updated with ModelReduce section
```

---

## Success Criteria (Definition of Done)

| Milestone | Metric | Target |
|-----------|--------|--------|
| Session 1 | Probe 10 prompts on 2 backends | ✓ No errors, structured output |
| Session 2 | Cross-model verification | ✓ Agreement clusters, promotion works |
| Session 3 | Distill → shards | ✓ 3 formats + manifest, CLI works |
| Session 4 | Graveyard command | ✓ 5 models × 3 domains unattended |
| Session 5 | Evaluation gates | ✓ CI passes on gold sets |
| Session 6 | MCP server | ✓ LLM queries KG, gets facts |
| Session 7 | Training run | ✓ +10% domain acc, -50% hallucination |
| Session 8 | Release | ✓ Tutorial runs in Colab, PyPI install works |

---

## Risk Mitigation

| Risk | Mitigation |
|------|------------|
| Model outputs are low quality | Negative probes + strict quality filter + min_agreement=2 |
| Models disagree on everything | Calibrate Jaccard threshold; use entailment check (future) |
| GPU OOM on large models | Sequential unload, `--max-concurrent 1`, quantized GGUF via Ollama |
| Gold set bias | Multiple annotators per domain; inter-annotator agreement |
| Prompt template coverage gaps | Bootstrap entities from KG; add templates iteratively |
| Legal/license on model outputs | Output shards are *facts*, not model weights; transformative use |

---

## Next Action

**Start Session 1 now:**

```bash
cd /Users/nelslindahl/Hermes-Output/knowledgereduce
# Create model_probe.py and probe_templates.py
# Test with: python -c "from knowledge_graph_pkg.model_probe import ModelProbe; ..."
```

The plan is complete. Sessions are independent, testable, and compose into a working ModelReduce system.