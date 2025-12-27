import json
from pathlib import Path

OUTPUTS_DIR = Path("outputs")
REPORT_PATH = OUTPUTS_DIR / "cost_optimization_report.json"
HTML_REPORT_PATH = OUTPUTS_DIR / "cost_optimization_report.html"


def export_report_to_html() -> None:
    if not REPORT_PATH.exists():
        print("No report found. Run pipeline first.")
        return

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    data = json.loads(REPORT_PATH.read_text(encoding="utf-8"))

    title = data.get("project", {}).get("name") or "Cloud Cost Optimization Report"

    html = f"""<!doctype html>
<html>
<head>
  <meta charset="utf-8" />
  <title>{title}</title>
  <style>
    body {{ font-family: Arial, sans-serif; margin: 32px; }}
    h1 {{ margin-bottom: 10px; }}
    pre {{ background: #f6f8fa; padding: 12px; border-radius: 8px; }}
  </style>
</head>
<body>
  <h1>{title}</h1>
  <pre>{json.dumps(data, indent=2)}</pre>
</body>
</html>
"""

    HTML_REPORT_PATH.write_text(html, encoding="utf-8")
    print(f"HTML report exported to: {HTML_REPORT_PATH}")
