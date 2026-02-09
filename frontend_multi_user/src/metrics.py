import json
import logging
import os
from typing import Dict, Any

import requests
from google.oauth2 import service_account
from google.auth.transport.requests import Request as GoogleRequest

logger = logging.getLogger(__name__)

VERTEX_LOCATION = os.environ.get("VERTEX_LOCATION", "us-central1")
VERTEX_PROJECT_ID = os.environ.get("VERTEX_PROJECT_ID")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash-001")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-004")


def _get_service_account_credentials():
    json_blob = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS_JSON")
    json_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    if json_blob:
        info = json.loads(json_blob)
        return service_account.Credentials.from_service_account_info(info, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    if json_path:
        return service_account.Credentials.from_service_account_file(json_path, scopes=["https://www.googleapis.com/auth/cloud-platform"])
    raise RuntimeError("Missing Google credentials: set GOOGLE_APPLICATION_CREDENTIALS_JSON or GOOGLE_APPLICATION_CREDENTIALS")


def _get_access_token() -> str:
    creds = _get_service_account_credentials()
    creds.refresh(GoogleRequest())
    return creds.token


def _vertex_generate(prompt: str) -> dict:
    if not VERTEX_PROJECT_ID:
        raise RuntimeError("VERTEX_PROJECT_ID not set")

    url = f"https://{VERTEX_LOCATION}-aiplatform.googleapis.com/v1/projects/{VERTEX_PROJECT_ID}/locations/{VERTEX_LOCATION}/publishers/google/models/{GEMINI_MODEL}:generateContent"
    token = _get_access_token()
    payload = {
        "contents": [
            {"role": "user", "parts": [{"text": prompt}]}
        ],
        "generationConfig": {
            "response_mime_type": "application/json",
            "temperature": 0.2,
        }
    }
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    return data


def _vertex_embed(text: str) -> list[float]:
    if not VERTEX_PROJECT_ID:
        raise RuntimeError("VERTEX_PROJECT_ID not set")
    url = f"https://{VERTEX_LOCATION}-aiplatform.googleapis.com/v1/projects/{VERTEX_PROJECT_ID}/locations/{VERTEX_LOCATION}/publishers/google/models/{EMBED_MODEL}:predict"
    token = _get_access_token()
    payload = {
        "instances": [{"content": text}]
    }
    resp = requests.post(url, headers={"Authorization": f"Bearer {token}"}, json=payload, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("predictions", [{}])[0].get("embeddings", {}).get("values")
    if not embedding:
        raise RuntimeError("Embedding response missing values")
    return embedding


def extract_raw_kpis(plan_json: dict, budget_cents: int) -> Dict[str, float]:
    prompt = plan_json.get("prompt", "")
    wbs = plan_json.get("wbs", {})
    estimated_cost = plan_json.get("estimated_cost_cents", 0)

    kpi_prompt = f"""You are an evaluator. Given the PlanExe plan JSON metadata, return KPI scores as JSON with float values from 0.0 to 1.0.

Required keys:
- novelty_score
- prompt_quality
- technical_completeness
- feasibility
- impact_estimate

Plan metadata:
- prompt: {prompt}
- wbs_depth: {max((len(k.split('.')) for k in wbs.keys()), default=0)}
- wbs_dependency_edges: {sum(len(v.get('depends_on', [])) for v in wbs.values()) if isinstance(wbs, dict) else 0}
- estimated_cost_cents: {estimated_cost}
- budget_cents: {budget_cents}

Return ONLY valid JSON.
"""

    data = _vertex_generate(kpi_prompt)
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "{}")
    try:
        kpis = json.loads(text)
    except Exception as exc:
        logger.error("Failed to parse KPI JSON: %s", exc)
        raise

    required = ["novelty_score", "prompt_quality", "technical_completeness", "feasibility", "impact_estimate"]
    for key in required:
        if key not in kpis:
            raise ValueError(f"Missing KPI: {key}")
    return kpis


def compare_two_kpis(kpis_a: Dict[str, float], kpis_b: Dict[str, float]) -> float:
    prompt = f"""You are a neutral evaluator. Given the KPI vectors for two plans, decide which plan is better overall.
Plan A KPIs:
- Novelty: {kpis_a['novelty_score']:.2f}
- Prompt quality: {kpis_a['prompt_quality']:.2f}
- Technical completeness: {kpis_a['technical_completeness']:.2f}
- Feasibility: {kpis_a['feasibility']:.2f}
- Impact estimate: {kpis_a['impact_estimate']:.2f}

Plan B KPIs:
- Novelty: {kpis_b['novelty_score']:.2f}
- Prompt quality: {kpis_b['prompt_quality']:.2f}
- Technical completeness: {kpis_b['technical_completeness']:.2f}
- Feasibility: {kpis_b['feasibility']:.2f}
- Impact estimate: {kpis_b['impact_estimate']:.2f}

Respond with one term: strongly prefer A | weakly prefer A | neutral | weakly prefer B | strongly prefer B
"""

    data = _vertex_generate(prompt)
    text = data.get("candidates", [{}])[0].get("content", {}).get("parts", [{}])[0].get("text", "").strip().lower()
    mapping = {
        "strongly prefer a": 0.9,
        "weakly prefer a": 0.7,
        "neutral": 0.5,
        "weakly prefer b": 0.3,
        "strongly prefer b": 0.1,
    }
    return mapping.get(text, 0.5)


def update_elo(elo_a: float, elo_b: float, prob_a: float, k: float = 32.0) -> tuple[float, float]:
    expected_a = 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))
    expected_b = 1.0 - expected_a
    new_a = elo_a + k * (prob_a - expected_a)
    new_b = elo_b + k * ((1 - prob_a) - expected_b)
    return new_a, new_b


def embed_prompt(prompt: str) -> list[float]:
    return _vertex_embed(prompt)
