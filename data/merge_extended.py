import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(r"d:\Arogya\Final_project-20260618T083014Z-3-001\Final_project")
sys.path.insert(0, str(PROJECT_ROOT))

from data.medicine_db import DISEASES
from data.extended_diseases import EXTENDED_DISEASES

# Merge dictionaries
new_count = 0
for k, v in EXTENDED_DISEASES.items():
    if k not in DISEASES:
        DISEASES[k] = v
        new_count += 1

print(f"Added {new_count} new diseases.")

# Now rewrite medicine_db.py to include the new diseases
# We will just append the EXTENDED_DISEASES dictionary string directly to medicine_db.py
# and add a line that updates the DISEASES dictionary.

with open(PROJECT_ROOT / "data" / "medicine_db.py", "a", encoding="utf-8") as f:
    f.write("\n\n# ── EXTENDED DISEASES IMPORT ──\n")
    f.write("from .extended_diseases import EXTENDED_DISEASES\n")
    f.write("DISEASES.update(EXTENDED_DISEASES)\n")

print("Successfully updated medicine_db.py")
