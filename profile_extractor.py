import json
import re
from pathlib import Path
from typing import Any, Dict, Optional

from llm_client import HuggingFaceLLMClient, LLMClientError
from json_utils import loads_json_strict, JsonExtractionError


class ProfileValidationError(Exception):
    pass


REQUIRED_PROFILE_KEYS = {
    "name": str,
    "budget_inr_per_month": (int, float, type(None)),  # allow null when not provided
    "description": str,
    "tech_stack": dict,
    "non_functional_requirements": list,
}


def build_profile_prompt(project_description: str) -> str:

    return f"""
You are an INFORMATION EXTRACTION engine. Your job is to COPY facts from the text.

Output rules:
- Return ONLY valid JSON. No markdown, no backticks, no explanation.
- Do NOT add words like "preferably", "suggest", "might", "could".
- Do NOT recommend alternatives. Do NOT invent values.

Budget rules (VERY IMPORTANT):
- If the description contains an explicit monthly budget, you MUST copy it EXACTLY.
- Do NOT change the number. Do NOT round. Do NOT estimate.
- If budget is not mentioned, set budget_inr_per_month to null.

Tech stack rules:
- If a technology is explicitly mentioned, copy it exactly.
- If not mentioned, omit that sub-key from tech_stack (do NOT guess).

Non-functional requirements:
- Extract them if mentioned; otherwise use an empty array.

Return a JSON object with EXACTLY these keys:
name, budget_inr_per_month, description, tech_stack, non_functional_requirements

User project description:
{project_description}
""".strip()


def extract_budget_from_text(text: str) -> Optional[float]:

    patterns = [
        r"(?:monthly\s+budget|budget)\s*[:\-]?\s*₹?\s*([0-9,]+)",
        r"₹\s*([0-9,]+)\s*(?:per\s+month|monthly)?",
    ]
    for p in patterns:
        m = re.search(p, text, flags=re.IGNORECASE)
        if m:
            val = m.group(1).replace(",", "")
            try:
                return float(val)
            except ValueError:
                return None
    return None


def clean_tech_stack(ts: Dict[str, Any]) -> Dict[str, Any]:

    cleaned: Dict[str, Any] = {}
    for k, v in ts.items():
        if isinstance(v, str):
            v2 = re.sub(r"\bpreferably\b", "", v, flags=re.IGNORECASE).strip()
            # also clean repeated spaces created by removal
            v2 = re.sub(r"\s{2,}", " ", v2).strip()
            cleaned[k] = v2
        else:
            cleaned[k] = v
    return cleaned


def parse_json_strict(text: str) -> Dict[str, Any]:

    try:
        data = loads_json_strict(text)
    except JsonExtractionError as e:
        raise ProfileValidationError(str(e)) from e

    if not isinstance(data, dict):
        raise ProfileValidationError(f"Expected a JSON object, got: {type(data).__name__}")

    return data


def validate_profile(profile: Dict[str, Any]) -> None:

    for key, expected_type in REQUIRED_PROFILE_KEYS.items():
        if key not in profile:
            raise ProfileValidationError(f"Missing required key: '{key}'")

        if not isinstance(profile[key], expected_type):
            raise ProfileValidationError(
                f"Invalid type for '{key}'. Expected {expected_type}, got {type(profile[key]).__name__}"
            )

    nfr = profile.get("non_functional_requirements", [])
    if not all(isinstance(x, str) for x in nfr):
        raise ProfileValidationError("non_functional_requirements must be a list of strings")


def extract_project_profile(
    llm: HuggingFaceLLMClient,
    description_path: Path,
    output_path: Path,
) -> Dict[str, Any]:
    """
    End-to-end flow:
    - Read description
    - Build strict prompt
    - Call LLM
    - Parse + validate JSON
    - Apply deterministic overrides for explicitly stated budget
    - Clean tech stack suggestion phrasing if present
    - Save project_profile.json
    """
    if not description_path.exists():
        raise FileNotFoundError(f"Project description file not found: {description_path}")

    project_description = description_path.read_text(encoding="utf-8").strip()
    if not project_description:
        raise ValueError("Project description is empty. Enter a description first.")

    prompt = build_profile_prompt(project_description)

    # Attempt 1
    try:
        raw = llm.generate(prompt, max_new_tokens=900, temperature=0.1)
        profile = parse_json_strict(raw)
        validate_profile(profile)
    except (LLMClientError, ProfileValidationError) as first_err:
        # Attempt 2: stronger reminder if the first output is invalid
        retry_prompt = (
            prompt
            + "\n\nIMPORTANT: Your previous output was invalid. "
              "Return ONLY COMPLETE valid JSON with no extra text. "
              "Do NOT use markdown code fences."
        )
        try:
            raw = llm.generate(retry_prompt, max_new_tokens=1100, temperature=0.0)
            profile = parse_json_strict(raw)
            validate_profile(profile)
        except (LLMClientError, ProfileValidationError) as second_err:
            raise ProfileValidationError(
                "Failed to generate a valid project profile after 2 attempts.\n"
                f"First error: {first_err}\n"
                f"Second error: {second_err}"
            ) from second_err

    # Deterministic budget override (only if user explicitly gave a budget)
    user_budget = extract_budget_from_text(project_description)
    if user_budget is not None:
        profile["budget_inr_per_month"] = user_budget

    # Clean suggestion-like phrasing in tech_stack if present
    profile["tech_stack"] = clean_tech_stack(profile.get("tech_stack", {}))

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(profile, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    return profile
