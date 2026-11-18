import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent
ECOSYSTEM_PATH = ROOT / "ecosystem.json"
PLAN_PATH = ROOT / "data" / "agent_plans.json"


def load_ecosystem() -> list[dict[str, str]]:
    with ECOSYSTEM_PATH.open(encoding="utf-8") as file:
        return json.load(file)["sources"]


def create_plan(goal: str) -> list[dict[str, str]]:
    normalized = re.sub(r"\s+", " ", goal.strip())
    if not normalized:
        raise ValueError("A plan goal is required.")
    plan = [
        {"step": "Understand", "owner": "Coordinator", "action": f"Clarify requirements for: {normalized}", "status": "pending"},
        {"step": "Retrieve", "owner": "Researcher", "action": "Search the local knowledge base and open-source metadata.", "status": "pending"},
        {"step": "Reason", "owner": "Analyst", "action": "Combine evidence, identify gaps, and prepare a grounded answer.", "status": "pending"},
        {"step": "Verify", "owner": "Reviewer", "action": "Check claims against retrieved source context and reject unsupported facts.", "status": "pending"},
        {"step": "Deliver", "owner": "Coordinator", "action": "Produce the answer, source list, and next actions.", "status": "pending"},
    ]
    PLAN_PATH.parent.mkdir(parents=True, exist_ok=True)
    PLAN_PATH.write_text(json.dumps({"goal": normalized, "plan": plan}, indent=2), encoding="utf-8")
    return plan


def build_agent_prompt(goal: str, role: str, context: str, sources: str) -> str:
    instructions = {
        "Coordinator": "Organize work, resolve uncertainty, and produce a clear final response.",
        "Researcher": "Find relevant evidence in the supplied context and preserve source attribution.",
        "Analyst": "Synthesize evidence, compare alternatives, and state tradeoffs.",
        "Reviewer": "Detect unsupported claims, contradictions, and missing sources.",
    }
    return (
        f"You are the {role} in a supervised multi-agent system.\n"
        f"{instructions.get(role, 'Complete the assigned work.')}\n"
        "Do not invent facts. Use only the context below.\n\n"
        f"Goal: {goal}\n\nContext:\n{context}\n\nSources:\n{sources}"
    )
