"""Write boundary: the engine may only write inside data_dir and the mirror folder."""
from __future__ import annotations

import shutil
from pathlib import Path


class BoundaryError(Exception):
    pass


def check_writable(profile, path: Path) -> Path:
    path = Path(path).resolve()
    allowed = [profile.data_dir] + ([profile.mirror_to] if profile.mirror_to else [])
    if not any(path == a or a in path.parents for a in allowed if a):
        raise BoundaryError(f"refusing to write outside data_dir/mirror_to: {path}")
    return path


def write_text(profile, path: Path, text: str) -> Path:
    path = check_writable(profile, path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def mirror(profile, path: Path) -> Path | None:
    if not profile.mirror_to:
        return None
    dest = check_writable(profile, profile.mirror_to / Path(path).name)
    dest.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(path, dest)
    return dest
