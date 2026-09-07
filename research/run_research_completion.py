"""Run the non-fabricating research-completion analysis pipeline."""
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = [
    "validate_factory_region_mapping.py",
    "regional_bias_analysis.py",
    "user_evaluation_analysis.py",
    "generate_thesis_evidence.py",
]

for script in SCRIPTS:
    path = ROOT / "research" / script
    print(f"\n=== {script} ===")
    subprocess.run([sys.executable, str(path)], cwd=ROOT, check=True)

print("\nResearch-completion pipeline finished. Pending inputs remain explicitly marked pending.")
