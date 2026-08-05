# models_dependencies/transformers/fhir_flatten.py
"""
Generic, in-memory SQL-on-FHIR ViewDefinition flattening engine.

WHY THIS FILE EXISTS
---------------------
Old flow (per resource, manual, repetitive):
  1. bronze.<resource>_satusehat_data.payload_json exported to raw/*.txt (FlatQuack)
  2. cleaned + converted to *.ndjson (Python script)
  3. flatquack CLI (bun) compiles views/<resource>.vd.json -> views/<resource>.vd.sql
  4. <resource>.vd.sql + a hand-written "unwrap" query thrown at an LLM to produce
     an executable DuckDB/sqlmesh query -> delivered back as a zip
  5. zip extracted, files dropped into models/silver/fhir_resources/*.sql

Every one of those steps produced a file that had to be kept in sync by hand.

New flow (this module):
  bronze DataFrame (already in memory, from sqlmesh context.fetchdf) --> flatten_bronze() --> silver DataFrame

No files are written or read except the *.vd.json ViewDefinition itself, which
was already your source of truth and needs no changes -- FlatQuack's ViewDefinitions
are standard SQL-on-FHIR (no `_invoke`/macro extensions are used by any of the 16
production views), so sqlonfhir consumes them as-is.

sqlonfhir (https://github.com/sassoftware/sqlonfhir) evaluates a ViewDefinition
against FHIR resources directly in Python using fhirpathpy -- it does not generate
SQL. That's the "in-memory" property you're after: no .vd.sql, no .ndjson, no raw
.txt, nothing left behind on disk.

Requires: `pip install sqlonfhir` (pulls in fhirpathpy, antlr4-python3-runtime,
python-dateutil).
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Optional

import pandas as pd

# sqlonfhir.evaluate() is the public API, but it re-normalizes the ViewDefinition
# and spins up a fresh ViewDefinitionEvaluator (and FHIRPath compile cache) on
# *every call*. Calling it once per bronze row would mean recompiling the same
# handful of FHIRPath expressions thousands of times per run. We reuse the
# lower-level pieces instead so the compile cache is shared across an entire
# batch, while still tracking exactly which bronze row each flattened row came
# from (so Frappe/bronze passthrough columns can be reattached).
from sqlonfhir.sqlonfhir import ViewDefinitionEvaluator, normalize


def _repo_root() -> Path:
    # This file lives at models_dependencies/transformers/fhir_flatten.py.
    # Repo root (where flatquack/views/*.vd.json lives) is 2 levels up.
    # NOTE: computed lazily (not as a module-level constant) on purpose --
    # a module-level Path instance is a runtime object with no importable
    # qualified name, and SQLMesh's python-model environment serializer
    # chokes on it ("Object '<repo path>' cannot be serialized") when it
    # walks the globals reachable from a model's execute() function. Doing
    # the computation inside a function keeps the only module-level names
    # that need capturing to plain functions, which SQLMesh *can* serialize.
    return Path(__file__).resolve().parents[2]


def _resolve_vd_path(vd_path: str) -> Path:
    path = Path(vd_path)
    return path if path.is_absolute() else (_repo_root() / path)


def load_view_definition(vd_path: str) -> dict[str, Any]:
    """Load a SQL-on-FHIR ViewDefinition JSON file. Path is relative to repo root,
    e.g. "flatquack/views/procedure.vd.json"."""
    with open(_resolve_vd_path(vd_path), "r", encoding="utf-8") as f:
        return json.load(f)


def _is_missing(value: Any) -> bool:
    if value is None:
        return True
    try:
        return bool(pd.isna(value))
    except (TypeError, ValueError):
        return False


def flatten_bronze(
    df: pd.DataFrame,
    vd_path: str,
    passthrough_columns: list[str],
    payload_col: str = "payload_json",
    is_array_payload: bool = False,
    dtype_overrides: Optional[dict[str, str]] = None,
    idx_column: Optional[str] = None,
    column_renames: Optional[dict[str, str]] = None,
) -> pd.DataFrame:
    """
    Flatten a bronze DataFrame's JSON payload column into a silver DataFrame,
    entirely in-memory, using a SQL-on-FHIR ViewDefinition.

    Parameters
    ----------
    df:
        Bronze rows (e.g. from `context.fetchdf(...)` in a sqlmesh Python model).
        Must contain `payload_col` and every column listed in `passthrough_columns`.
    vd_path:
        Path (relative to repo root) to the .vd.json ViewDefinition, e.g.
        "flatquack/views/procedure.vd.json". Used as-is -- not regenerated.
    passthrough_columns:
        Bronze/Frappe metadata columns carried through unchanged onto every
        flattened row (e.g. frappe_doc_name, modified, patient_ihs, ...).
    payload_col:
        Column in `df` holding the FHIR resource as a JSON string.
    is_array_payload:
        True only when `payload_col` holds a JSON *array* of FHIR resources per
        bronze row (currently only Observation, which bundles several vitals
        into one Frappe doc). Produces one output row per array element and
        adds `idx_column` (0-based), mirroring the old `json_each` unwrap CTE.
        Every other resource is a single resource object per row.
    dtype_overrides:
        Optional {column_name: "TIMESTAMP" | "DATE" | "DOUBLE" | "INT" | "BOOLEAN"}
        to coerce specific flattened columns, matching the explicit CASTs that
        used to live in the generated SQL.
    idx_column:
        Name of the index column to emit when `is_array_payload=True`
        (e.g. "observation_idx"). Required in that case.
    column_renames:
        Optional {vd_column_name: final_column_name} applied after flattening,
        before dtype coercion. Used to keep the existing silver schema stable
        where the old hand-written SQL used a different name than the raw
        ViewDefinition column (e.g. every resource's `id` -> `fhir_id`, and
        `status` -> `fhir_status` for Encounter/MedicationDispense where a
        Frappe-side `status`-like column already occupies the plain name).

    Returns
    -------
    A flat pandas DataFrame ready to be returned from a sqlmesh Python model.
    """
    if is_array_payload and not idx_column:
        raise ValueError("idx_column is required when is_array_payload=True")

    raw_vd = load_view_definition(vd_path)
    normalized_vd = normalize(json.loads(json.dumps(raw_vd)))  # normalize mutates; work on a copy
    resource_type = raw_vd["resource"]

    evaluator = ViewDefinitionEvaluator()  # one instance -> FHIRPath cache shared for the whole batch
    rows: list[dict[str, Any]] = []

    for bronze_row in df.itertuples(index=False):
        row = bronze_row._asdict()
        payload = row.get(payload_col)
        if _is_missing(payload):
            continue
        parsed = json.loads(payload)
        resource_list = parsed if is_array_payload else [parsed]
        passthrough = {col: row.get(col) for col in passthrough_columns}

        for idx, resource in enumerate(resource_list):
            if not resource or resource.get("resourceType") != resource_type:
                continue
            for flat_row in evaluator.call_fn(normalized_vd, resource, raw_vd):
                merged = {**passthrough, **flat_row}
                if is_array_payload:
                    merged[idx_column] = idx
                rows.append(merged)

    result = pd.DataFrame(rows)

    if column_renames:
        result = result.rename(columns=column_renames)

    for col, dtype in (dtype_overrides or {}).items():
        if col not in result.columns:
            continue
        if dtype in ("TIMESTAMP", "DATETIME"):
            result[col] = pd.to_datetime(result[col], errors="coerce", utc=False)
        elif dtype == "DATE":
            result[col] = pd.to_datetime(result[col], errors="coerce").dt.date
        elif dtype in ("DOUBLE", "FLOAT"):
            result[col] = pd.to_numeric(result[col], errors="coerce")
        elif dtype == "INT":
            result[col] = pd.to_numeric(result[col], errors="coerce").astype("Int64")
        elif dtype == "BOOLEAN":
            result[col] = result[col].astype("boolean")

    return result