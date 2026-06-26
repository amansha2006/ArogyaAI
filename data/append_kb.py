import os

project_dir = r"d:\Arogya\Final_project-20260618T083014Z-3-001\Final_project"
extras_path = os.path.join(project_dir, "data", "medicine_db_extras.py")
main_path = os.path.join(project_dir, "data", "medicine_db.py")

with open(extras_path, "r", encoding="utf-8") as f:
    extras_content = f.read()

interactions_content = """

# ── Drug Interactions Knowledge Base ──────────────────────────────────────────
INTERACTIONS = [
    {
        "d1": "Metformin", "d2": "Ashwagandha", 
        "sev": "Moderate", 
        "effect": "Enhanced hypoglycemia risk", 
        "mgmt": "Monitor blood glucose closely when starting Ashwagandha."
    },
    {
        "d1": "Levothyroxine", "d2": "Calcium/Iron supplements", 
        "sev": "Major", 
        "effect": "Decreased levothyroxine absorption", 
        "mgmt": "Separate doses by at least 4 hours."
    },
    {
        "d1": "Aspirin", "d2": "Ginkgo Biloba", 
        "sev": "Major", 
        "effect": "Increased risk of bleeding", 
        "mgmt": "Avoid combination or monitor closely."
    }
]
"""

with open(main_path, "a", encoding="utf-8") as f:
    f.write("\n" + extras_content + "\n" + interactions_content)

print("Successfully appended extras and INTERACTIONS to medicine_db.py")
