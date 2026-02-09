import json
import logging
import os
from typing import Dict, List, Any, Tuple

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


def _limit_words(text: str, max_words: int = 30) -> str:
    words = (text or "").strip().split()
    if len(words) <= max_words:
        return " ".join(words)
    return " ".join(words[:max_words])


def _plan_summary(plan_json: Dict[str, Any]) -> str:
    if not plan_json:
        return "(no plan data)"
    prompt = plan_json.get("prompt") or ""
    title = plan_json.get("title") or ""
    wbs = plan_json.get("wbs") or {}
    wbs_depth = 0
    if isinstance(wbs, dict) and wbs:
        wbs_depth = max((len(k.split('.')) for k in wbs.keys()), default=0)
    estimated_cost = plan_json.get("estimated_cost_cents")
    duration = plan_json.get("duration_months") or plan_json.get("duration_days")
    summary_parts = []
    if title:
        summary_parts.append(f"Title: {title}")
    if prompt:
        summary_parts.append(f"Prompt: {prompt}")
    if wbs_depth:
        summary_parts.append(f"WBS depth: {wbs_depth}")
    if estimated_cost is not None:
        summary_parts.append(f"Estimated cost cents: {estimated_cost}")
    if duration is not None:
        summary_parts.append(f"Duration: {duration}")
    return "\n".join(summary_parts) if summary_parts else "(no plan data)"


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


def compare_two_kpis(plan_a: Dict[str, Any], plan_b: Dict[str, Any]) -> Tuple[float, List[Dict[str, Any]]]:
    summary_a = _plan_summary(plan_a)
    summary_b = _plan_summary(plan_b)

    prompt = f"""You are a neutral evaluator. Compare two PlanExe plans.

Your task:
1) Choose 5-7 KPIs that are relevant to BOTH plans.
2) Add ONE additional KPI for remaining considerations not covered above. You must choose the name yourself.
3) Score each KPI on a Likert 1-5 integer scale for Plan A and Plan B.
4) Provide a reasoning string of MAX 30 words for why those values were chosen.

Return ONLY valid JSON as an array of objects with this schema:
{{"name": "<KPI name>", "plan_a": <int 1-5>, "plan_b": <int 1-5>, "reasoning": "<<=30 words>"}}

Plan A:
{summary_a}

Plan B:
{summary_b}
"""

    text = _openrouter_chat(prompt)
    try:
        kpis = json.loads(text)
    except Exception as exc:
        logger.error("Failed to parse comparison KPI JSON: %s", exc)
        raise

    if not isinstance(kpis, list) or not kpis:
        raise ValueError("Comparison KPI output must be a non-empty list")

    total_a = 0
    total_b = 0
    cleaned: List[Dict[str, Any]] = []
    for item in kpis:
        if not isinstance(item, dict):
            continue
        name = str(item.get("name") or "").strip()
        plan_a_score = int(round(float(item.get("plan_a", 3))))
        plan_b_score = int(round(float(item.get("plan_b", 3))))
        plan_a_score = max(1, min(5, plan_a_score))
        plan_b_score = max(1, min(5, plan_b_score))
        reasoning = _limit_words(str(item.get("reasoning") or ""), 30)
        cleaned.append({
            "name": name or "(unnamed KPI)",
            "plan_a": plan_a_score,
            "plan_b": plan_b_score,
            "reasoning": reasoning,
        })
        total_a += plan_a_score
        total_b += plan_b_score

    if not cleaned:
        return 0.5, []

    diff = total_a - total_b
    if diff >= 3:
        prob_a = 0.9
    elif diff == 2:
        prob_a = 0.7
    elif diff == 1:
        prob_a = 0.6
    elif diff == 0:
        prob_a = 0.5
    elif diff == -1:
        prob_a = 0.4
    elif diff == -2:
        prob_a = 0.3
    else:
        prob_a = 0.1

    return prob_a, cleaned


def update_elo(elo_a: float, elo_b: float, prob_a: float, k: float = 32.0) -> tuple[float, float]:
    expected_a = 1.0 / (1.0 + 10 ** ((elo_b - elo_a) / 400))
    expected_b = 1.0 - expected_a
    new_a = elo_a + k * (prob_a - expected_a)
    new_b = elo_b + k * ((1 - prob_a) - expected_b)
    return new_a, new_b


def embed_prompt(prompt: str) -> list[float]:
    return _openai_embed(prompt)
