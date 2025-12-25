import json
from collections import defaultdict
from pathlib import Path
from typing import Any, Dict, List, Tuple

from llm_client import HuggingFaceLLMClient, LLMClientError
from json_utils import loads_json_strict, JsonExtractionError


class BillingValidationError(Exception):
    pass


REQUIRED_BILLING_KEYS = {
    "month": str,
    "service": str,
    "resource_id": str,
    "region": str,
    "usage_type": str,
    "usage_quantity": (int, float),
    "unit": str,
    "cost_inr": (int, float),
    "desc": str,
}


def build_billing_prompt(project_profile: Dict[str, Any]) -> str:
    budget = project_profile.get("budget_inr_per_month", 0)
    name = project_profile.get("name", "Unknown Project")
    tech_stack = project_profile.get("tech_stack", {})

    return f"""
Return ONLY valid JSON. No markdown. No backticks. No explanations.

Generate a JSON array of 12 to 20 realistic cloud billing records.

Project name: {name}
Monthly budget (INR): {budget}
Tech stack: {json.dumps(tech_stack)}

Rules:
- Use EXACTLY 3 months of data (YYYY-MM).
- Target 4–6 records per month (total must be 12–20).
- Spread across services: Compute, Database, Storage, Networking, Monitoring, Logging, CDN (optional Analytics/Email).
- Avoid creating multiple records for the same (month, service) unless necessary.
- Regions:
  - Use a primary region like ap-south-1 for core resources (compute/db).
  - Include at least one secondary region like ap-southeast-1 for replicas/backups/analytics.
  - Use "global" region for CDN.
- Networking should be realistic: data-transfer-out-gb, nat-gateway-hour, load-balancer-hour.
  Do NOT use "vpc-hour".
- Monitoring and Logging should appear in every month (small recurring costs).
- Each record must contain exactly these keys:
  month, service, resource_id, region, usage_type, usage_quantity, unit, cost_inr, desc
- Keep monthly totals budget-aware (near the budget but can be under).

Return ONLY the JSON array.
""".strip()


def parse_json_array_strict(text: str) -> List[Dict[str, Any]]:

    try:
        data = loads_json_strict(text)
    except JsonExtractionError as e:
        raise BillingValidationError(
            f"LLM did not return valid JSON. Error: {e}\nRaw:\n{text}"
        ) from e

    if not isinstance(data, list):
        raise BillingValidationError(f"Expected a JSON array (list), got: {type(data).__name__}")

    return data


def validate_billing_records(records: List[Dict[str, Any]]) -> None:
    if not (12 <= len(records) <= 20):
        raise BillingValidationError(f"Billing must have 12–20 records, got {len(records)}")

    for i, rec in enumerate(records, start=1):
        if not isinstance(rec, dict):
            raise BillingValidationError(f"Record #{i} must be an object/dict, got {type(rec).__name__}")

        # exact keys check
        expected_keys = set(REQUIRED_BILLING_KEYS.keys())
        actual_keys = set(rec.keys())
        if actual_keys != expected_keys:
            missing = expected_keys - actual_keys
            extra = actual_keys - expected_keys
            parts = []
            if missing:
                parts.append(f"missing={sorted(missing)}")
            if extra:
                parts.append(f"extra={sorted(extra)}")
            raise BillingValidationError(f"Record #{i} has incorrect keys: {', '.join(parts)}")

        for key, expected_type in REQUIRED_BILLING_KEYS.items():
            if not isinstance(rec[key], expected_type):
                raise BillingValidationError(
                    f"Record #{i} invalid type for '{key}'. "
                    f"Expected {expected_type}, got {type(rec[key]).__name__}"
                )


def enforce_record_count(records: List[Dict[str, Any]], min_n: int, max_n: int) -> List[Dict[str, Any]]:

    if not isinstance(records, list):
        return records

    if len(records) <= max_n:
        return records

    # 1) Deduplicate by (month, service)
    seen: set[Tuple[str, str]] = set()
    deduped: List[Dict[str, Any]] = []
    for r in records:
        month = str(r.get("month", "")).strip()
        service = str(r.get("service", "")).strip()
        key = (month, service)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(r)

    if len(deduped) <= max_n:
        return deduped

    # 2) Group by month and take in chronological order
    month_map: Dict[str, List[Dict[str, Any]]] = defaultdict(list)
    for r in deduped:
        month_map[str(r.get("month", "")).strip()].append(r)

    months_sorted = sorted(month_map.keys())
    trimmed: List[Dict[str, Any]] = []
    for m in months_sorted:
        for r in month_map[m]:
            trimmed.append(r)
            if len(trimmed) == max_n:
                return trimmed

    return trimmed[:max_n]


def generate_mock_billing(
    llm: HuggingFaceLLMClient,
    profile_path: Path,
    output_path: Path,
) -> List[Dict[str, Any]]:
    if not profile_path.exists():
        raise FileNotFoundError(f"Project profile not found: {profile_path}")

    project_profile = json.loads(profile_path.read_text(encoding="utf-8"))
    prompt = build_billing_prompt(project_profile)

    def _postprocess_and_validate(raw_text: str) -> List[Dict[str, Any]]:
        records_local = parse_json_array_strict(raw_text)
        # trim before validation so "got 32" doesn't fail immediately
        records_local = enforce_record_count(records_local, 12, 20)
        validate_billing_records(records_local)
        return records_local

    # Attempt 1
    try:
        raw = llm.generate(prompt, max_new_tokens=3500, temperature=0.05)
        records = _postprocess_and_validate(raw)
    except (BillingValidationError, LLMClientError) as first_err:
        # Attempt 2: stricter retry
        retry_prompt = (
            prompt
            + "\n\nIMPORTANT:\n"
              "- Return ONLY a COMPLETE valid JSON array.\n"
              "- Must be BETWEEN 12 AND 20 RECORDS (inclusive).\n"
              "- Do NOT exceed 20 records.\n"
              "- No extra text, no markdown, no explanations.\n"
        )

        try:
            raw = llm.generate(retry_prompt, max_new_tokens=2600, temperature=0.1)
            records = _postprocess_and_validate(raw)
        except (BillingValidationError, LLMClientError) as second_err:
            raise BillingValidationError(
                "Failed to generate valid billing JSON after 2 attempts.\n"
                f"First error: {first_err}\n"
                f"Second error: {second_err}"
            ) from second_err

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(records, indent=2), encoding="utf-8")
    return records
