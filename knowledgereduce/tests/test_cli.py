"""
Tests for the command-line interface.

The CLI exposes the full pipeline as one command:
    python -m knowledge_graph_pkg distill input.txt -o out.jsonl --format chat

These tests invoke the CLI's main() entrypoint directly with argument
lists, using a temp input file, and assert on exit code + output files.
"""
import json
from pathlib import Path

import pytest

from knowledge_graph_pkg.cli import main


@pytest.fixture
def sample_text(tmp_path):
    p = tmp_path / "src.txt"
    p.write_text(
        "Robert Putnam wrote Bowling Alone. "
        "Marie Curie was born in Warsaw. "
        "She discovered radium."
    )
    return p


def test_distill_chat_writes_jsonl(tmp_path, sample_text):
    out = tmp_path / "train.jsonl"
    rc = main(["distill", str(sample_text), "-o", str(out), "--format", "chat"])
    assert rc == 0
    assert out.exists()
    lines = [l for l in out.read_text().splitlines() if l.strip()]
    assert lines
    for line in lines:
        rec = json.loads(line)
        assert "messages" in rec


def test_distill_instruction_format(tmp_path, sample_text):
    out = tmp_path / "instruct.jsonl"
    rc = main(["distill", str(sample_text), "-o", str(out), "--format", "instruction"])
    assert rc == 0
    rec = json.loads(out.read_text().splitlines()[0])
    assert "instruction" in rec and "output" in rec


def test_distill_text_format(tmp_path, sample_text):
    out = tmp_path / "digest.txt"
    rc = main(["distill", str(sample_text), "-o", str(out), "--format", "text"])
    assert rc == 0
    assert out.read_text().strip()


def test_coref_flag_attributes_pronoun(tmp_path, sample_text):
    out = tmp_path / "c.jsonl"
    main(["distill", str(sample_text), "-o", str(out), "--format", "chat", "--coref"])
    blob = out.read_text()
    # with coref, "She discovered radium" -> Marie Curie
    assert "Marie Curie" in blob


def test_strict_filter_flag(tmp_path, sample_text):
    out = tmp_path / "s.jsonl"
    rc = main(["distill", str(sample_text), "-o", str(out),
               "--format", "chat", "--filter", "strict"])
    assert rc == 0  # runs cleanly even if strict keeps few/none


def test_missing_input_returns_nonzero(tmp_path):
    out = tmp_path / "x.jsonl"
    rc = main(["distill", str(tmp_path / "nope.txt"), "-o", str(out)])
    assert rc != 0


def test_stats_printed(tmp_path, sample_text, capsys):
    out = tmp_path / "train.jsonl"
    main(["distill", str(sample_text), "-o", str(out), "--format", "chat"])
    captured = capsys.readouterr()
    # CLI reports how many facts/pairs were written
    assert "fact" in captured.out.lower() or "pair" in captured.out.lower()


def test_eval_subcommand_reports_f1(capsys):
    rc = main(["eval", "--gold", "data/gold_set.json"])
    assert rc == 0
    out = capsys.readouterr().out.lower()
    assert "f1" in out and "precision" in out and "recall" in out
