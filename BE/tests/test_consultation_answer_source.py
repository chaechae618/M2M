from types import SimpleNamespace

from app.api.v1.consultations import answer_source_data


def test_rag_json_source_is_exposed_for_llm_direct_answer() -> None:
    answer = SimpleNamespace(
        route="llm_direct",
        source_ids=["itda_011", "itda_093"],
    )

    assert answer_source_data(answer) == {
        "mode": "rag_json_db",
        "jsonDatabase": "mentor_answers.json",
        "answerIds": ["itda_011", "itda_093"],
    }


def test_general_llm_source_is_distinguished_from_rag() -> None:
    answer = SimpleNamespace(route="llm_direct", source_ids=[])

    assert answer_source_data(answer) == {
        "mode": "llm_general_knowledge",
        "jsonDatabase": None,
        "answerIds": [],
    }


def test_persona_answer_does_not_claim_llm_direct_json_source() -> None:
    answer = SimpleNamespace(route="mentor_needed", source_ids=[])

    assert answer_source_data(answer) is None
