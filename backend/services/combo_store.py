import json
import os
import threading
from typing import Dict, List, Optional

DATA_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")
COMBOS_FILE = os.path.join(DATA_DIR, "combos.json")

_lock = threading.Lock()


def _ensure_dir():
    os.makedirs(DATA_DIR, exist_ok=True)


def load_all() -> Dict[str, dict]:
    _ensure_dir()
    if not os.path.exists(COMBOS_FILE):
        return {}
    with open(COMBOS_FILE, "r") as f:
        return json.load(f)


def save_all(combos: Dict[str, dict]):
    _ensure_dir()
    with open(COMBOS_FILE, "w") as f:
        json.dump(combos, f, indent=2)


def get(combo_id: str) -> Optional[dict]:
    with _lock:
        combos = load_all()
        return combos.get(combo_id)


def get_all() -> List[dict]:
    with _lock:
        return list(load_all().values())


def upsert(combo_id: str, combo_data: dict):
    with _lock:
        combos = load_all()
        combos[combo_id] = combo_data
        save_all(combos)


def delete(combo_id: str) -> bool:
    with _lock:
        combos = load_all()
        if combo_id in combos:
            del combos[combo_id]
            save_all(combos)
            return True
        return False
