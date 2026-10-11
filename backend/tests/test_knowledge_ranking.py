import logging

from backend.app.services import knowledge_service as knowledge_module
from backend.app.services.knowledge_ranking import (
    build_candidate,
    explain_ranking,
    rank_candidates,
    select_answer,
)


def make(service, confidence, minimum, category="info"):
    return build_candidate(
        service,
        {
            "answer": f"réponse {service}",
            "source": f"source {service}",
            "category": category,
            "confidence": confidence,
        },
        minimum,
    )


def fake_search(answer, category, confidence):
    def search(question):
        return {
            "answer": answer,
            "source": "source test",
            "category": category,
            "confidence": confidence,
        }

    return search


def test_margin_beats_raw_confidence() -> None:
    faq = make("faq", 0.70, 0.65)
    document = make("document", 0.70, 0.55)

    ranked = rank_candidates((faq, document))

    assert [candidate.service for candidate in ranked] == ["document", "faq"]
    assert faq.margin == 0.05
    assert document.margin == 0.15


def test_tie_resolved_by_service_priority() -> None:
    faq = make("faq", 0.80, 0.65)
    procedure = make("procedure", 0.80, 0.65)
    schedule = make("schedule", 0.80, 0.65)

    ranked = rank_candidates((faq, procedure, schedule))

    assert [candidate.service for candidate in ranked] == [
        "schedule",
        "procedure",
        "faq",
    ]


def test_rejected_candidate_never_selected() -> None:
    rejected = make("contact", 0.64, 0.65, category="unknown")
    accepted = make("faq", 0.66, 0.65)

    ranked = rank_candidates((rejected, accepted))

    assert ranked[0].service == "faq"
    assert rejected.accepted is False
    assert accepted.accepted is True


def test_acceptance_depends_on_category_not_confidence() -> None:
    rejected = make("document", 0.99, 0.55, category="unknown")
    accepted = make("faq", 0.66, 0.65)

    ranked = rank_candidates((rejected, accepted))

    assert ranked[0].service == "faq"


def test_fallback_when_nothing_accepted() -> None:
    fallback = {
        "answer": "réponse de repli",
        "source": None,
        "category": "unknown",
        "confidence": 0.3,
    }
    ranked = rank_candidates(
        (
            make("faq", 0.30, 0.65, category="unknown"),
            make("document", 0.50, 0.55, category="unknown"),
        )
    )

    assert select_answer(ranked, fallback) is fallback

    explanation = explain_ranking(ranked)
    assert explanation["selected"] is None
    assert explanation["candidates"][0]["service"] == "document"
    assert explanation["candidates"][0]["reason"].startswith("rejeté")


def test_explanation_structure() -> None:
    ranked = rank_candidates(
        (
            make("faq", 0.70, 0.65),
            make("contact", 0.60, 0.65, category="unknown"),
        )
    )

    explanation = explain_ranking(ranked)

    assert explanation["selected"] == "faq"
    assert len(explanation["candidates"]) == 2
    first = explanation["candidates"][0]
    assert set(first) == {
        "service",
        "category",
        "confidence",
        "minimum_confidence",
        "margin",
        "accepted",
        "reason",
    }
    assert first["accepted"] is True
    assert first["reason"].startswith("accepté")


def test_as_result_matches_api_contract() -> None:
    candidate = make("procedure", 0.90, 0.65)

    result = candidate.as_result()

    assert set(result) == {"answer", "source", "category", "confidence"}
    assert result["answer"] == "réponse procedure"


def test_search_knowledge_prefers_larger_margin(monkeypatch) -> None:
    unknown = fake_search(None, "unknown", 0.1)
    monkeypatch.setattr(
        knowledge_module.knowledge_service,
        "search",
        fake_search("réponse faq", "faq_cat", 0.70),
    )
    monkeypatch.setattr(
        knowledge_module.document_service,
        "search",
        fake_search("réponse document", "doc_cat", 0.70),
    )
    monkeypatch.setattr(knowledge_module.procedure_service, "search", unknown)
    monkeypatch.setattr(knowledge_module.contact_service, "search", unknown)
    monkeypatch.setattr(knowledge_module.schedule_service, "search", unknown)

    result = knowledge_module.search_knowledge("question de test")

    assert result["answer"] == "réponse document"
    assert result["category"] == "doc_cat"
    assert set(result) == {"answer", "source", "category", "confidence"}


def test_search_knowledge_logs_explanation(monkeypatch, caplog) -> None:
    unknown = fake_search(None, "unknown", 0.1)
    monkeypatch.setattr(knowledge_module.knowledge_service, "search", unknown)
    monkeypatch.setattr(knowledge_module.procedure_service, "search", unknown)
    monkeypatch.setattr(knowledge_module.contact_service, "search", unknown)
    monkeypatch.setattr(knowledge_module.document_service, "search", unknown)
    monkeypatch.setattr(
        knowledge_module.schedule_service,
        "search",
        fake_search("réponse schedule", "schedule_cat", 0.80),
    )
    caplog.set_level(
        logging.DEBUG,
        logger="backend.app.services.knowledge_service",
    )

    result = knowledge_module.search_knowledge("question de test")

    assert result.get("answer") == "réponse schedule"
    assert "knowledge ranking" in caplog.text
    assert "'selected': 'schedule'" in caplog.text
    assert "'accepted': True" in caplog.text
    assert "rejeté" in caplog.text
