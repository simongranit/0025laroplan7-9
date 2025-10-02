from __future__ import annotations

from services import content


def test_load_questions() -> None:
    store = content.get_store()
    assert len(store.questions) >= 30
    assert store.questions["g7_aritmetik_001"].answer == "10"


def test_list_topics() -> None:
    topics = content.list_topics(7)
    assert "Taluppfattning" in topics


def test_get_random_questions() -> None:
    questions = content.get_random_questions(7, "Taluppfattning", 2)
    assert len(questions) == 2
    assert all(q.topic == "Taluppfattning" for q in questions)
