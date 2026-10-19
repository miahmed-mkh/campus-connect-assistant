import httpx

from backend.app.services import llm_service

URL_ATTENDUE = "http://llm-test:11434/api/chat"


class FakeResponse:
    def __init__(self, payload=None, error=None):
        self._payload = payload
        self._error = error

    def raise_for_status(self) -> None:
        if self._error is not None:
            raise self._error

    def json(self):
        return self._payload


def activer(monkeypatch) -> None:
    monkeypatch.setattr(llm_service.settings, "llm_enabled", True)
    monkeypatch.setattr(llm_service.settings, "llm_base_url", "http://llm-test:11434")
    monkeypatch.setattr(llm_service.settings, "llm_model", "modele-test")


def reponse_ok(texte: str) -> FakeResponse:
    return FakeResponse({"message": {"content": texte}})


def test_service_inactif_par_defaut(monkeypatch) -> None:
    def interdit(*args, **kwargs):
        raise AssertionError("aucun appel reseau attendu")

    monkeypatch.setattr(llm_service.httpx, "post", interdit)
    monkeypatch.setattr(llm_service.settings, "llm_enabled", False)

    assert llm_service.rephrase_answer("question", "passage") is None


def test_reformulation_renvoyee_et_requete_correcte(monkeypatch) -> None:
    activer(monkeypatch)
    envoi = {}

    def fake_post(url, json=None, timeout=None):
        envoi["url"] = url
        envoi["json"] = json
        envoi["timeout"] = timeout
        return reponse_ok("  Deposez votre demande en ligne.  ")

    monkeypatch.setattr(llm_service.httpx, "post", fake_post)

    texte = llm_service.rephrase_answer("Comment faire ?", "Deposez la demande.")

    assert texte == "Deposez votre demande en ligne."
    assert envoi["url"] == URL_ATTENDUE
    assert envoi["json"]["model"] == "modele-test"
    assert envoi["json"]["stream"] is False
    assert envoi["json"]["options"]["temperature"] == 0
    contenu_utilisateur = envoi["json"]["messages"][1]["content"]
    assert "Deposez la demande." in contenu_utilisateur
    assert "Comment faire ?" in contenu_utilisateur
    assert envoi["timeout"] == llm_service.settings.llm_timeout_seconds


def test_erreur_reseau_donne_none(monkeypatch) -> None:
    activer(monkeypatch)

    def fake_post(*args, **kwargs):
        raise httpx.ConnectError("indisponible")

    monkeypatch.setattr(llm_service.httpx, "post", fake_post)

    assert llm_service.rephrase_answer("q", "p") is None


def test_delai_depasse_donne_none(monkeypatch) -> None:
    activer(monkeypatch)

    def fake_post(*args, **kwargs):
        raise httpx.ReadTimeout("trop lent")

    monkeypatch.setattr(llm_service.httpx, "post", fake_post)

    assert llm_service.rephrase_answer("q", "p") is None


def test_erreur_http_donne_none(monkeypatch) -> None:
    activer(monkeypatch)
    erreur = httpx.ReadError("erreur serveur")
    monkeypatch.setattr(
        llm_service.httpx,
        "post",
        lambda *args, **kwargs: FakeResponse(error=erreur),
    )

    assert llm_service.rephrase_answer("q", "p") is None


def test_json_inattendu_donne_none(monkeypatch) -> None:
    activer(monkeypatch)
    monkeypatch.setattr(
        llm_service.httpx,
        "post",
        lambda *args, **kwargs: FakeResponse({"autre": "chose"}),
    )

    assert llm_service.rephrase_answer("q", "p") is None


def test_reponse_vide_donne_none(monkeypatch) -> None:
    activer(monkeypatch)
    monkeypatch.setattr(
        llm_service.httpx,
        "post",
        lambda *args, **kwargs: reponse_ok("   "),
    )

    assert llm_service.rephrase_answer("q", "p") is None


def test_refus_du_modele_donne_none(monkeypatch) -> None:
    activer(monkeypatch)
    monkeypatch.setattr(
        llm_service.httpx,
        "post",
        lambda *args, **kwargs: reponse_ok("Je n'ai pas cette information."),
    )

    assert llm_service.rephrase_answer("q", "p") is None


def test_caracteres_cjk_donnent_none(monkeypatch) -> None:
    activer(monkeypatch)
    monkeypatch.setattr(
        llm_service.httpx,
        "post",
        lambda *args, **kwargs: reponse_ok("Deposez la demande 你好"),
    )

    assert llm_service.rephrase_answer("q", "p") is None

def test_passage_trop_long_donne_none_sans_appel(monkeypatch) -> None:
    activer(monkeypatch)
    monkeypatch.setattr(llm_service.settings, "llm_max_passage_chars", 10)

    def interdit(*args, **kwargs):
        raise AssertionError("aucun appel reseau attendu")

    monkeypatch.setattr(llm_service.httpx, "post", interdit)

    assert llm_service.rephrase_answer("q", "x" * 11) is None