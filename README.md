# AI-Powered Cloud Cost Optimizer (CLI)

This project is a Python-based command-line application that analyzes a cloud project
description and generates cost insights and optimization recommendations. The tool
simulates cloud billing data and produces structured cost analysis reports to help
understand potential cloud infrastructure costs.

---

## Features
- Interactive and user-friendly CLI workflow
- Project description ingestion
- Cloud project profile generation
- Mock cloud billing data generation
- Cost analysis and optimization recommendations
- Report generation in JSON format

---

## Tech Stack
- Python 3.13
- Standard Python libraries
- HuggingFace LLM API 

---

## Setup Instructions

### 1. Clone the repository
```bash
git clone https://github.com/lalithya-k/AI-cloud-cost-optimizer
cd cost-optimization
````

### 2. Create and activate a virtual environment

```bash
python -m venv .venv
.venv\Scripts\activate   # Windows
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Run the application

```bash
python cli.py
```

---

## CLI Usage

When the application starts, the following menu options are displayed:

1. Enter new project description
2. Run complete cost analysis (with Retry)
3. View recommendations
4. Export report (JSON)
5. Export report (HTML)
6. Exit

Follow the prompts to generate and analyze cloud cost data based on the provided project
description.

---

## Example Input and Output Files

The repository includes sample input and output files in the `outputs/` directory to
demonstrate expected usage:

* `project_description.txt` – Sample project description input
* `project_profile.json` – Generated cloud project profile
* `mock_billing.json` – Example mock cloud billing data
* `cost_optimization_report.json` – Final cost analysis and optimization report
* `cost_optimization_report.html` - Final report in HTML

These files serve as reference examples for running the CLI.

---

## Tools Used

* ChatGPT (OpenAI) – Used for design guidance, debugging assistance, and clarification
  during development. 

---


````