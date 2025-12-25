import json
from collections import defaultdict
from pathlib import Path
from typing import Dict, Any, List


class CostAnalysisError(Exception):
    pass


def analyze_costs(profile_path: Path, billing_path: Path) -> Dict[str, Any]:

    if not profile_path.exists():
        raise FileNotFoundError(f"Project profile not found: {profile_path}")

    if not billing_path.exists():
        raise FileNotFoundError(f"Billing data not found: {billing_path}")

    profile = json.loads(profile_path.read_text(encoding="utf-8"))
    billing_records: List[Dict[str, Any]] = json.loads(billing_path.read_text(encoding="utf-8"))

    budget = float(profile.get("budget_inr_per_month", 0) or 0)

    monthly_total = defaultdict(float)
    service_total_all_months = defaultdict(float)

    service_total_latest_month = defaultdict(float)

    # Collect all valid months
    months_seen = set()

    for record in billing_records:
        month = str(record.get("month", "")).strip()
        service = str(record.get("service", "Unknown")).strip()

        try:
            cost = float(record.get("cost_inr", 0) or 0)
        except (TypeError, ValueError):
            cost = 0.0

        if month:
            months_seen.add(month)
            monthly_total[month] += cost

        service_total_all_months[service] += cost

    if not months_seen:
        raise CostAnalysisError("No valid 'month' values found in billing records.")

    latest_month = sorted(months_seen)[-1]

    # Compute per-service costs for latest month
    for record in billing_records:
        if str(record.get("month", "")).strip() == latest_month:
            service = str(record.get("service", "Unknown")).strip()
            try:
                cost = float(record.get("cost_inr", 0) or 0)
            except (TypeError, ValueError):
                cost = 0.0
            service_total_latest_month[service] += cost

    total_monthly_cost = monthly_total[latest_month]
    budget_variance = total_monthly_cost - budget
    is_over_budget = budget_variance > 0

    # Sort high-cost services for better recommendations
    high_cost_services_latest = dict(
        sorted(service_total_latest_month.items(), key=lambda x: x[1], reverse=True)
    )

    analysis = {
        "month_analyzed": latest_month,
        "total_monthly_cost": round(total_monthly_cost, 2),

        "budget": round(budget, 2),
        "budget_variance": round(budget_variance, 2),
        "is_over_budget": is_over_budget,

        # Useful transparency
        "monthly_costs": {m: round(v, 2) for m, v in sorted(monthly_total.items())},

        # Use latest month breakdown for recommendations
        "service_costs": {s: round(v, 2) for s, v in service_total_latest_month.items()},
        "high_cost_services": {s: round(v, 2) for s, v in high_cost_services_latest.items()},

        "service_costs_all_months": {s: round(v, 2) for s, v in service_total_all_months.items()},
    }

    return analysis
