from __future__ import annotations

import json
import os
from collections.abc import Iterable
from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from pydantic import ValidationError

from services.models import Profile

DEFAULT_STORAGE_DIR = Path.home() / ".matte_diagnostics"


def _storage_path() -> Path:
    override = os.getenv("MATTE_PROFILES_PATH")
    if override:
        return Path(override)
    return DEFAULT_STORAGE_DIR / "profiles.json"


def load_profiles() -> list[Profile]:
    path = _storage_path()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return []
    profiles: list[Profile] = []
    for entry in raw:
        try:
            profile = Profile.model_validate(entry)
        except ValidationError:
            continue
        profiles.append(profile)
    profiles.sort(key=lambda profile: profile.created_at)
    return profiles


def save_profiles(profiles: Iterable[Profile]) -> None:
    path = _storage_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = [profile.model_dump(mode="json") for profile in profiles]
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def list_profiles() -> list[Profile]:
    return load_profiles()


def get_profile(profile_id: str | None) -> Profile | None:
    if not profile_id:
        return None
    for profile in load_profiles():
        if profile.id == profile_id:
            return profile
    return None


def create_profile(name: str, grade: int) -> Profile:
    trimmed = name.strip() if name else ""
    now = datetime.now(UTC)
    profile = Profile(
        id=uuid4().hex,
        name=trimmed or "Elev",
        last_grade=int(grade),
        last_topic=None,
        created_at=now,
        updated_at=now,
    )
    profiles = load_profiles()
    profiles.append(profile)
    save_profiles(profiles)
    return profile


def update_profile(
    profile_id: str,
    *,
    name: str | None = None,
    last_grade: int | None = None,
    last_topic: str | None = None,
) -> Profile:
    profiles = load_profiles()
    updated: Profile | None = None
    new_profiles: list[Profile] = []
    for profile in profiles:
        if profile.id != profile_id:
            new_profiles.append(profile)
            continue
        data = profile.model_dump()
        if name is not None:
            trimmed = name.strip()
            if trimmed:
                data["name"] = trimmed
        if last_grade is not None:
            data["last_grade"] = int(last_grade)
        if last_topic is not None:
            data["last_topic"] = last_topic
        data["updated_at"] = datetime.now(UTC)
        updated = Profile.model_validate(data)
        new_profiles.append(updated)
    if updated is None:
        raise ValueError(f"Profile {profile_id} not found")
    save_profiles(new_profiles)
    return updated


def delete_profile(profile_id: str) -> None:
    profiles = [profile for profile in load_profiles() if profile.id != profile_id]
    save_profiles(profiles)
