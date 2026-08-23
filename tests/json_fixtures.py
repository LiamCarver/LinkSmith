from __future__ import annotations

import json
from pathlib import Path
from typing import Any

FIXTURE_ROOT = Path(__file__).resolve().parents[1] / "fixtures" / "tests"


def load_fixture_json(
    relative_path: str | Path,
    *,
    key: str | None = None,
    substitutions: dict[str, str] | None = None,
) -> Any:
    payload = json.loads((FIXTURE_ROOT / relative_path).read_text(encoding="utf-8"))
    if key is not None:
        payload = payload[key]
    if substitutions:
        payload = _apply_substitutions(payload, substitutions)
    return payload


def _apply_substitutions(value: Any, substitutions: dict[str, str]) -> Any:
    if isinstance(value, str):
        result = value
        for name, replacement in substitutions.items():
            result = result.replace(f"__{name}__", replacement)
        return result
    if isinstance(value, list):
        return [_apply_substitutions(item, substitutions) for item in value]
    if isinstance(value, dict):
        return {key: _apply_substitutions(item, substitutions) for key, item in value.items()}
    return value
