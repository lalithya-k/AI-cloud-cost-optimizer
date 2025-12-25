import json
import re
from typing import Any


class JsonExtractionError(Exception):
    pass


def extract_json_text(raw: str) -> str:

    text = raw.strip()

    # Remove fenced code blocks like ```json ... ``` or ``` ... ```
    fence = re.compile(r"^```(?:json)?\s*([\s\S]*?)\s*```$", re.IGNORECASE)
    m = fence.match(text)
    if m:
        text = m.group(1).strip()

    return text


def loads_json_strict(raw: str) -> Any:

    cleaned = extract_json_text(raw)
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError as e:
        raise JsonExtractionError(f"Invalid JSON after cleanup.\nCleaned:\n{cleaned}\n\nRaw:\n{raw}") from e
