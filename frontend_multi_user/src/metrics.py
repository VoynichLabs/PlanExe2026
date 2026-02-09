import json
import logging
import os
from typing import Dict

import requests

logger = logging.getLogger(__name__)

OPENROUTER_API_KEY = os.environ.get("OPENROUTER_API_KEY")
OPENROUTER_MODEL = os.environ.get("OPENROUTER_MODEL", "google/gemini-2.0-flash-001")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")
EMBED_MODEL = os.environ.get("EMBED_MODEL", "text-embedding-3-small")


def _openrouter_chat(prompt: str) -> str:
    if not OPENROUTER_API_KEY:
        raise RuntimeError("OPENROUTER_API_KEY not set")
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": OPENROUTER_MODEL,
        "messages": [
            {"role": "user", "content": prompt}
        ],
        "temperature": 0.2,
        "max_tokens": 2048
    }
    resp = requests.post(url, headers={"Authorization": f"Bearer {OPENROUTER_API_KEY}"}, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    return data["choices"][0]["message"]["content"]


def _openai_embed(text: str) -> list[float]:
    if not OPENAI_API_KEY:
        raise RuntimeError("OPENAI_API_KEY not set")
    url = "https://api.openai.com/v1/embeddings"
    payload = {"model": EMBED_MODEL, "input": text}
    resp = requests.post(url, headers={"Authorization": f"Bearer {OPENAI_API_KEY}"}, json=payload, timeout=60)
    resp.raise_for_status()
    data = resp.json()
    embedding = data.get("data", [{}])[0].get("embedding")
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

    text = _openrouter_chat(kpi_prompt)
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

    text = _openrouter_chat(prompt).strip().lower()
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
    return _openai_embed(prompt)
