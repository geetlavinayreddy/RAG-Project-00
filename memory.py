import json
from pathlib import Path


MEMORY_PATH = Path(__file__).resolve().parent / "data" / "conversation_memory.json"


def load_memory() -> list[dict[str, str]]:
    if not MEMORY_PATH.exists():
        return []
    try:
        value = json.loads(MEMORY_PATH.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as error:
        raise RuntimeError(f"Unable to read conversation memory: {error}") from error
    if not isinstance(value, list):
        raise RuntimeError("Conversation memory must contain a JSON list.")
    return value


def save_memory(history: list[dict[str, str]]) -> None:
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)
    MEMORY_PATH.write_text(json.dumps(history[-40:], indent=2), encoding="utf-8")
