#!/usr/bin/env python3
"""Seed plan_corpus from PlanExe-web _data/examples.yml (real data only)."""
import os
import uuid
import json
import psycopg2
from psycopg2.extras import execute_values

try:
    import yaml  # type: ignore
except Exception as exc:
    raise SystemExit("PyYAML is required. Install with: pip install pyyaml") from exc

EXAMPLES_PATH = os.environ.get("PLANEXE_WEB_EXAMPLES_PATH")
DATABASE_URL = os.environ.get("DATABASE_URL")

if not EXAMPLES_PATH:
    raise SystemExit("PLANEXE_WEB_EXAMPLES_PATH is required (path to PlanExe-web/_data/examples.yml)")
if not DATABASE_URL:
    raise SystemExit("DATABASE_URL is required")

with open(EXAMPLES_PATH, "r", encoding="utf-8") as f:
    data = yaml.safe_load(f)

examples = data.get("examples") or []
if not examples:
    raise SystemExit("No examples found in examples.yml")

rows = []
base_dir = os.path.dirname(EXAMPLES_PATH)
for rec in examples:
    plan_id = uuid.uuid4()
    title = rec.get("title") or "(untitled)"
    url = rec.get("url") or ""
    json_path = rec.get("json_path") or None
    json_data = None
    if json_path:
        resolved_path = json_path
        if not os.path.isabs(resolved_path):
            resolved_path = os.path.join(base_dir, json_path)
        if os.path.exists(resolved_path):
            try:
                with open(resolved_path, "r", encoding="utf-8") as jf:
                    json_data = json.load(jf)
            except Exception:
                json_data = None
    rows.append((plan_id, title, url, json_path, json_data))

conn = psycopg2.connect(DATABASE_URL)
with conn:
    with conn.cursor() as cur:
        execute_values(
            cur,
            """
            INSERT INTO plan_corpus (id, title, url, json_path, json_data)
            VALUES %s
            ON CONFLICT (id) DO NOTHING
            """,
            rows
        )

print(f"Inserted {len(rows)} rows into plan_corpus")
