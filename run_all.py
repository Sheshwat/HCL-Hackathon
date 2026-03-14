"""
run_all.py
==========
One-command runner for the entire Insurance Policy Data Engineering Pipeline.

Usage:
    python run_all.py

Steps executed:
    1. Generate source CSV data (12 files)
    2. Run ETL pipeline (validate → standardize → transform → warehouse CSV)
    3. Run all analytics queries (b–g)
    4. Build interactive HTML dashboard
"""

import subprocess
import sys
import os

ROOT = os.path.dirname(os.path.abspath(__file__))

def run(script, label):
    print(f"\n{'='*60}")
    print(f"  STEP: {label}")
    print(f"{'='*60}")
    result = subprocess.run(
        [sys.executable, os.path.join(ROOT, script)],
        cwd=ROOT
    )
    if result.returncode != 0:
        print(f"\n❌  FAILED: {label}")
        sys.exit(1)
    print(f"✅  DONE: {label}")

if __name__ == "__main__":
    print("\n" + "#"*60)
    print("  ABC INSURANCE — FULL PIPELINE RUNNER")
    print("#"*60)

    run("scripts/generate_source_data.py", "Generate 12 source CSV files")
    run("etl/pipeline.py",                 "ETL: Validate → Standardize → Transform → Load")
    run("analytics/queries.py",            "Analytics: Run queries b–g")
    run("scripts/build_dashboard.py",      "Build interactive HTML dashboard")

    print("\n" + "#"*60)
    print("  ALL STEPS COMPLETE!")
    print(f"  Dashboard:  output/insurance_dashboard.html")
    print(f"  Warehouse:  output/warehouse/")
    print(f"  Analytics:  output/analytics/")
    print(f"  Logs:       output/logs/")
    print("#"*60 + "\n")
