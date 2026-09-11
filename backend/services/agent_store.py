import json
import os
import threading
from typing import Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
AGENTS_FILE = os.path.join(DATA_DIR, "agents.json")

_lock = threading.Lock()


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_all() -> Dict[str, dict]:
    _ensure_dir()
    if not os.path.exists(AGENTS_FILE):
        return {}
    with open(AGENTS_FILE, "r") as f:
        return json.load(f)


def save_all(agents: Dict[str, dict]):
    _ensure_dir()
    with open(AGENTS_FILE, "w") as f:
        json.dump(agents, f, indent=2)


def get(agent_id: str) -> Optional[dict]:
    with _lock:
        agents = load_all()
        return agents.get(agent_id)


def get_all() -> List[dict]:
    with _lock:
        return list(load_all().values())


def upsert(agent_id: str, agent_data: dict):
    with _lock:
        agents = load_all()
        existing = agents.get(agent_id, {})
        merged = {**existing, **agent_data}
        agents[agent_id] = merged
        save_all(agents)


def delete(agent_id: str) -> bool:
    with _lock:
        agents = load_all()
        if agent_id in agents:
            del agents[agent_id]
            save_all(agents)
            return True
        return False
