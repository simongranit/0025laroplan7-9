from __future__ import annotations

from services import profiles


def test_profile_lifecycle(monkeypatch, tmp_path) -> None:
    storage_path = tmp_path / "profiles.json"
    monkeypatch.setenv("MATTE_PROFILES_PATH", str(storage_path))

    created = profiles.create_profile("Test Elev", 8)
    assert created.name == "Test Elev"
    assert created.last_grade == 8

    loaded = profiles.list_profiles()
    assert len(loaded) == 1
    assert loaded[0].id == created.id

    updated = profiles.update_profile(created.id, last_topic="Algebra")
    assert updated.last_topic == "Algebra"

    fetched = profiles.get_profile(created.id)
    assert fetched is not None
    assert fetched.last_topic == "Algebra"

    profiles.delete_profile(created.id)
    assert profiles.list_profiles() == []
