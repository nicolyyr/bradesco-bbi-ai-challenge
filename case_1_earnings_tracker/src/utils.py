"""Small I/O helpers for Case 1 outputs."""

from __future__ import annotations

import json
import os


def _ensure_parent(file_path: str) -> None:
    parent = os.path.dirname(os.path.abspath(file_path))
    os.makedirs(parent, exist_ok=True)


def save_json(data, file_path: str) -> None:
    _ensure_parent(file_path)
    with open(file_path, "w", encoding="utf-8") as fh:
        json.dump(data, fh, indent=4, ensure_ascii=False)


def save_text(content: str, file_path: str) -> None:
    _ensure_parent(file_path)
    with open(file_path, "w", encoding="utf-8") as fh:
        fh.write(content)
