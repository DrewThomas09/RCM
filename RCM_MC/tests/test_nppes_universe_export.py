"""CSV/JSON export helpers for CDD outputs (incl. formula-injection defang)."""
from __future__ import annotations

import csv
import io
import json

from connectors.nppes import export


def test_rows_to_csv_basic():
    rows = [{"geo": "TX", "n": 10}, {"geo": "IL", "n": 7}]
    text = export.rows_to_csv(rows)
    parsed = list(csv.DictReader(io.StringIO(text)))
    assert [r["geo"] for r in parsed] == ["TX", "IL"]
    assert parsed[0]["n"] == "10"


def test_rows_to_csv_empty():
    assert export.rows_to_csv([]) == ""


def test_nested_values_json_encoded():
    rows = [{"sys": "BAYLOR", "states": ["TX", "OK"], "comp": {"a": 1}}]
    text = export.rows_to_csv(rows)
    parsed = list(csv.DictReader(io.StringIO(text)))[0]
    assert json.loads(parsed["states"]) == ["TX", "OK"]
    assert json.loads(parsed["comp"]) == {"a": 1}


def test_formula_injection_defanged():
    rows = [{"name": "=cmd|'/c calc'!A1", "ok": "+1", "safe": "Baylor"}]
    text = export.rows_to_csv(rows)
    parsed = list(csv.DictReader(io.StringIO(text)))[0]
    assert parsed["name"].startswith("'=")
    assert parsed["ok"].startswith("'+")
    assert parsed["safe"] == "Baylor"


def test_write_csv_and_json(tmp_path):
    rows = [{"a": 1, "b": "x"}]
    n = export.write_csv(rows, str(tmp_path / "o.csv"))
    assert n == 1
    assert (tmp_path / "o.csv").read_text().startswith("a,b")
    export.write_json({"k": [1, 2]}, str(tmp_path / "o.json"))
    assert json.loads((tmp_path / "o.json").read_text()) == {"k": [1, 2]}


def test_column_order_override():
    rows = [{"a": 1, "b": 2, "c": 3}]
    text = export.rows_to_csv(rows, columns=["c", "a"])
    assert text.splitlines()[0] == "c,a"
