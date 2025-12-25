import json
from typing import Any, Dict, List

from llm_client import HuggingFaceLLMClient, LLMClientError
from json_utils import loads_json_strict, JsonExtractionError


class RecommendationsError(Exception):
    pass


REQUIRED_RECO_KEYS = {
    "title": str,
    "service": str,
    "current_cost": (int, float),
    "potential_savings": (int, float),
    "recommendation_type": str,
    "description": str,
    "implementation_effort": str,  # low/medium/high
    "risk_level": str,             # low/medium/high
    "steps": list,
    "cloud_providers": list,
}


def build_recommendations_prompt(project_profile: Dict[str, Any], analysis: Dict[str, Any]) -> str:

    return f"""
You are a cloud cost optimization assistant.

Return ONLY valid JSON (no markdown, no backticks, no explanation).
Return a JSON array with 6 to 10 recommendations.

Project profile:
{json.dumps(project_profile, indent=2)}

Cost analysis:
{json.dumps(analysis, indent=2)}

Rules:
- Recommendations must be realistic and tied to the high-cost services.
- Must include multi-cloud options across AWS, Azure, and GCP.
- Include at least 1 open-source or free alternative where applicable. 
Examples: Prometheus+Grafana, OpenTelemetry, Loki, ELK/OpenSearch, Nginx, Varnish, Redis, Kubernetes autoscaling.
- Each recommendation MUST contain exactly these keys:
  title, service, current_cost, potential_savings, recommendation_type,
  description, implementation_effort, risk_level, steps, cloud_providers
- steps must be a list of short actionable steps (3 to 6 items).
- implementation_effort and risk_level must be one of: low, medium, high.
- potential_savings must be <= current_cost and must be a number.

Return ONLY the JSON array.
""".strip()


def parse_json_array_strict(text: str) -> List[Dict[str, Any]]:
    try:
        data = loads_json_strict(text)
    except JsonExtractionError as e:
        raise RecommendationsError(f"LLM did not return valid JSON. Error: {e}\nRaw:\n{text}") from e

    if not isinstance(data, list):
        raise RecommendationsError(f"Expected a JSON array (list), got: {type(data).__name__}")

    return data


def validate_recommendations(recos: List[Dict[str, Any]]) -> None:
    if not (6 <= len(recos) <= 10):
        raise RecommendationsError(f"Expected 6–10 recommendations, got {len(recos)}")

    for i, r in enumerate(recos, start=1):
        if not isinstance(r, dict):
            raise RecommendationsError(f"Recommendation #{i} must be a JSON object")

        for key, expected_type in REQUIRED_RECO_KEYS.items():
            if key not in r:
                raise RecommendationsError(f"Recommendation #{i} missing key: '{key}'")
            if not isinstance(r[key], expected_type):
                raise RecommendationsError(
                    f"Recommendation #{i} invalid type for '{key}'. Expected {expected_type}, got {type(r[key]).__name__}"
                )

        # Extra sanity checks (so you can defend your output)
        if r["potential_savings"] > r["current_cost"]:
            raise RecommendationsError(f"Recommendation #{i} has potential_savings > current_cost")

        if r["implementation_effort"] not in {"low", "medium", "high"}:
            raise RecommendationsError(f"Recommendation #{i} invalid implementation_effort")

        if r["risk_level"] not in {"low", "medium", "high"}:
            raise RecommendationsError(f"Recommendation #{i} invalid risk_level")

        if not all(isinstance(s, str) for s in r["steps"]):
            raise RecommendationsError(f"Recommendation #{i} steps must be a list of strings")

        if not all(isinstance(p, str) for p in r["cloud_providers"]):
            raise RecommendationsError(f"Recommendation #{i} cloud_providers must be a list of strings")


def generate_recommendations(
    llm: HuggingFaceLLMClient,
    project_profile: Dict[str, Any],
    analysis: Dict[str, Any],
) -> List[Dict[str, Any]]:
    prompt = build_recommendations_prompt(project_profile, analysis)

    try:
        raw = llm.generate(prompt, max_new_tokens=1200, temperature=0.2)
    except LLMClientError as e:
        raise RecommendationsError(f"LLM call failed: {e}") from e

    recos = parse_json_array_strict(raw)
    validate_recommendations(recos)
    return recos
