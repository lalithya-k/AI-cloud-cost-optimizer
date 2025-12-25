import json
from pathlib import Path
from typing import Any, Dict, List


def build_report(
    project_profile: Dict[str, Any],
    analysis: Dict[str, Any],
    recommendations: List[Dict[str, Any]],
) -> Dict[str, Any]:
    total_savings = sum(r.get("potential_savings", 0) for r in recommendations)
    total_cost = analysis.get("total_monthly_cost", 0) or 0

    savings_pct = (total_savings / total_cost * 100) if total_cost else 0

    report = {
        "project_name": project_profile.get("name", "Unknown Project"),
        "analysis": analysis,
        "recommendations": recommendations,
        "summary": {
            "total_potential_savings": round(total_savings, 2),
            "savings_percentage": round(savings_pct, 2),
            "recommendations_count": len(recommendations),
        },
    }
    return report


def write_report(report: Dict[str, Any], output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
