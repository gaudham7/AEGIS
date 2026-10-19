"""
Simple local file-based persistence.

PostgreSQL is not required for this implementation. All metadata, analysis
results and model artifacts are stored as JSON / joblib files on disk,
namespaced by dataset_id. This keeps the architecture easy to extend to a
real database later (each function below is the natural seam to swap in a
DB-backed implementation).
"""
import json
import shutil
from pathlib import Path
from typing import Any, Optional

from app.config import DATA_DIR, MODELS_DIR, UPLOADS_DIR

REGISTRY_FILE = DATA_DIR / "registry.json"


def _dataset_dir(dataset_id: str) -> Path:
    d = MODELS_DIR / dataset_id
    d.mkdir(parents=True, exist_ok=True)
    return d


def upload_path(dataset_id: str) -> Path:
    return UPLOADS_DIR / f"{dataset_id}.csv"


def save_json(dataset_id: str, name: str, data: Any) -> None:
    path = _dataset_dir(dataset_id) / f"{name}.json"
    with open(path, "w") as f:
        json.dump(data, f, indent=2, default=str)


def load_json(dataset_id: str, name: str) -> Optional[Any]:
    path = _dataset_dir(dataset_id) / f"{name}.json"
    if not path.exists():
        return None
    with open(path) as f:
        return json.load(f)


def artifact_path(dataset_id: str, name: str) -> Path:
    return _dataset_dir(dataset_id) / name


def register_dataset(dataset_id: str, meta: dict) -> None:
    registry = {}
    if REGISTRY_FILE.exists():
        with open(REGISTRY_FILE) as f:
            registry = json.load(f)
    registry[dataset_id] = meta
    with open(REGISTRY_FILE, "w") as f:
        json.dump(registry, f, indent=2, default=str)


def get_registry() -> dict:
    if not REGISTRY_FILE.exists():
        return {}
    with open(REGISTRY_FILE) as f:
        return json.load(f)


def latest_dataset_id() -> Optional[str]:
    registry = get_registry()
    if not registry:
        return None
    return sorted(registry.items(), key=lambda kv: kv[1].get("uploaded_at", ""))[-1][0]


def delete_dataset(dataset_id: str) -> None:
    shutil.rmtree(_dataset_dir(dataset_id), ignore_errors=True)
    p = upload_path(dataset_id)
    if p.exists():
        p.unlink()
