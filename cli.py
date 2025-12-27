import json
from pathlib import Path

from llm_client import HuggingFaceLLMClient, LLMClientError
from profile_extractor import extract_project_profile, ProfileValidationError
from billing_generator import generate_mock_billing, BillingValidationError
from cost_analyzer import analyze_costs
from recommendations_generator import generate_recommendations, RecommendationsError
from report_builder import build_report, write_report
from html_report_exporter import export_report_to_html


OUTPUTS_DIR = Path("outputs")
DESC_PATH = OUTPUTS_DIR / "project_description.txt"
PROFILE_PATH = OUTPUTS_DIR / "project_profile.json"
BILLING_PATH = OUTPUTS_DIR / "mock_billing.json"
REPORT_PATH = OUTPUTS_DIR / "cost_optimization_report.json"


def print_menu() -> None:
    print("\n AI-Powered Cloud Cost Optimizer: ")
    print("1. Enter new project description")
    print("2. Run Complete Cost Analysis (with Retry)")
    print("3. View Recommendations")
    print("4. Export Report (JSON)")
    print("5. Export Report (HTML)")
    print("6. Exit")


def enter_description() -> None:
    print("\nEnter your project description. End input with an empty line:\n")
    lines = []
    while True:
        line = input()
        if line.strip() == "":
            break
        lines.append(line)

    text = "\n".join(lines).strip()
    if not text:
        print("Description cannot be empty.")
        return

    OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
    DESC_PATH.write_text(text, encoding="utf-8")
    print(f"Saved description to: {DESC_PATH}")


def run_complete_pipeline(llm: HuggingFaceLLMClient) -> None:

    try:
        profile = extract_project_profile(llm, DESC_PATH, PROFILE_PATH)
        print(f"Generated: {PROFILE_PATH}")

        billing = generate_mock_billing(llm, PROFILE_PATH, BILLING_PATH)
        print(f"Generated: {BILLING_PATH} ({len(billing)} records)")

        analysis = analyze_costs(PROFILE_PATH, BILLING_PATH)
        print("Cost analysis complete.")
        print(f"Total monthly cost: {analysis['total_monthly_cost']} INR")
        print(f"Budget: {analysis['budget']} INR")
        print(f"Over budget: {analysis['is_over_budget']}")

        recommendations = generate_recommendations(llm, profile, analysis)
        print(f"Generated {len(recommendations)} recommendations.")

        report = build_report(profile, analysis, recommendations)
        write_report(report, REPORT_PATH)
        print(f"Report written to: {REPORT_PATH}")

    except (ProfileValidationError, BillingValidationError, RecommendationsError) as e:
        print(f"\n Pipeline failed: {e}")
    except FileNotFoundError as e:
        print(f"\n Missing file: {e}")
    except LLMClientError as e:
        print(f"\n LLM error: {e}")
    except Exception as e:
        print(f"\n Unexpected error: {e}")


def run_complete_pipeline_with_retry(llm: HuggingFaceLLMClient) -> None:

    while True:
        # remove old report so we don't incorrectly assume success from a previous run
        if REPORT_PATH.exists():
            try:
                REPORT_PATH.unlink()
            except OSError:
                pass

        run_complete_pipeline(llm)

        # Success heuristic: if report exists, assume pipeline succeeded.
        if REPORT_PATH.exists():
            print("Pipeline completed (report generated).")
            break

        choice = input("Pipeline did not generate a report. Retry? (y/n): ").strip().lower()
        if choice != "y":
            print("Returning to main menu.")
            break


def view_recommendations() -> None:
    if not REPORT_PATH.exists():
        print("No report found. Run 'Complete Cost Analysis' first.")
        return

    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    recos = report.get("recommendations", [])

    if not recos:
        print("No recommendations found in report.")
        return

    print("\n Recommendations ")
    for idx, r in enumerate(recos, start=1):
        print(f"\n{idx}. {r.get('title')}")
        print(f"   Service: {r.get('service')}")
        print(f"   Current Cost: {r.get('current_cost')} INR")
        print(f"   Potential Savings: {r.get('potential_savings')} INR")
        print(f"   Effort: {r.get('implementation_effort')} | Risk: {r.get('risk_level')}")
        print(f"   Providers: {', '.join(r.get('cloud_providers', []))}")
        print(f"   Description: {r.get('description')}")
        print("   Steps:")
        for s in r.get("steps", []):
            print(f"     - {s}")


def export_report_json() -> None:
    if not REPORT_PATH.exists():
        print("No report found to export. Run pipeline first.")
        return
    print(f"Report already saved at: {REPORT_PATH}")
    print("You can submit this JSON. Use option 5 to export an HTML version.")


def main() -> None:
    model_id = "meta-llama/Meta-Llama-3-8B-Instruct"

    try:
        llm = HuggingFaceLLMClient(model_id=model_id)
    except LLMClientError as e:
        print(f" Cannot start: {e}")
        print("Fix your .env (HF_API_KEY) and try again.")
        return

    while True:
        print_menu()
        choice = input("Choose an option (1-6): ").strip()

        if choice == "1":
            enter_description()
        elif choice == "2":
            run_complete_pipeline_with_retry(llm)
        elif choice == "3":
            view_recommendations()
        elif choice == "4":
            export_report_json()
        elif choice == "5":
            export_report_to_html()
        elif choice == "6":
            print("Exiting...")
            break
        else:
            print("Invalid choice. Enter 1-6.")


if __name__ == "__main__":
    main()
