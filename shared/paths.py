"""Repository-root path resolution.

Lets every entrypoint build absolute paths regardless of the current working
directory, fixing the original "only runs from repo root" fragility.
"""

from __future__ import annotations

import os

# shared/paths.py -> repo root is one level up from this file's directory.
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))


def repo_path(*parts: str) -> str:
    """Return an absolute path under the repository root."""
    return os.path.join(REPO_ROOT, *parts)
