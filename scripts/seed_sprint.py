#!/usr/bin/env python3
"""
LyfSync 2.0 — GitHub Sprint Seeder
Creates milestone, label, and issues for the current sprint tasks
and adds them to the GitHub Project board.
"""

import subprocess
import time

OWNER = "aasish-bodapati"
REPO = "lyfsync_2.0"
PROJECT_NUMBER = 3
MILESTONE_TITLE = "Sprint 1: Nutrition Persistence"

# --- Active Sprint Tasks ---
SPRINT_TASKS = [
    {
        "title": "Define SQLModel tables",
        "body": "Add database schema class definitions for `Meal` and `FoodItem` with relationship linking in `backend/main.py`.",
        "labels": ["engineering", "nutrition"]
    },
    {
        "title": "Setup SQLite engine and session",
        "body": "Initialize the SQLite database engine for `lyfsync.db` and set up standard session dependencies or context managers in `backend/main.py`.",
        "labels": ["engineering", "nutrition"]
    },
    {
        "title": "Initialize database on startup",
        "body": "Add a FastAPI startup handler to trigger table creation automatically when the server runs.",
        "labels": ["engineering", "nutrition"]
    },
    {
        "title": "Persist parent Meal on parse",
        "body": "Update the `POST /api/v1/meals/parse` endpoint to write the parsed meal structure to SQLite first.",
        "labels": ["engineering", "nutrition"]
    },
    {
        "title": "Persist child FoodItems on parse",
        "body": "Save all individual items linked to the newly created parent meal ID in the transaction.",
        "labels": ["engineering", "nutrition"]
    },
    {
        "title": "Handle session rollback on parse error",
        "body": "Ensure any failure in database operations rolls back the current session to avoid partial database inserts.",
        "labels": ["engineering", "nutrition"]
    },
    {
        "title": "Create GET /meals endpoint",
        "body": "Implement a simple GET route returning history of all logged meals and their food items.",
        "labels": ["engineering", "nutrition"]
    }
]

def run(cmd):
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    return result.stdout.strip(), result.stderr.strip(), result.returncode

def ensure_label(name):
    cmd = [
        "gh", "label", "create", name,
        "--repo", f"{OWNER}/{REPO}",
        "--color", "d93f0b" if name == "engineering" else "0e8a16"
    ]
    subprocess.run(cmd, capture_output=True)

def create_milestone():
    cmd = (
        f'gh api repos/{OWNER}/{REPO}/milestones '
        f'-f title="{MILESTONE_TITLE}" '
        f'-f description="First sprint focusing strictly on Nutrition Backend Database Persistence" '
        f'-f state="open" 2>&1'
    )
    run(cmd)

def create_issue(title, body, labels):
    cmd = [
        "gh", "issue", "create",
        "--title", title,
        "--body", body,
        "--milestone", MILESTONE_TITLE,
        "--repo", f"{OWNER}/{REPO}"
    ]
    for label in labels:
        cmd.extend(["--label", label])
        
    result = subprocess.run(cmd, capture_output=True, text=True)
    out = result.stdout.strip()
    err = result.stderr.strip()
    code = result.returncode
    
    if code == 0:
        issue_num = out.split("/")[-1]
        print(f"  ✓ Created issue #{issue_num}: {title}")
        return issue_num
    else:
        print(f"  ✗ FAILED: {title} | {err}")
        return None

def add_to_project(issue_num):
    cmd = [
        "gh", "project", "item-add", str(PROJECT_NUMBER),
        "--owner", OWNER,
        "--url", f"https://github.com/{OWNER}/{REPO}/issues/{issue_num}"
    ]
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode == 0:
        print(f"    → Added to Project Board #{PROJECT_NUMBER}")
    else:
        print(f"    ✗ Project add failed: {result.stderr.strip()[:80]}")

def main():
    print("🚀 Seeding Sprint Tasks to GitHub Project Board")
    print("=" * 50)
    
    # Ensure labels exist
    for label in ["engineering", "nutrition"]:
        ensure_label(label)
        
    create_milestone()
    
    for task in SPRINT_TASKS:
        issue_num = create_issue(task["title"], task["body"], task["labels"])
        if issue_num:
            add_to_project(issue_num)
            time.sleep(0.5)
            
    print("\n✅ Seeding completed! View your board at:")
    print(f"https://github.com/users/{OWNER}/projects/{PROJECT_NUMBER}")

if __name__ == "__main__":
    main()
