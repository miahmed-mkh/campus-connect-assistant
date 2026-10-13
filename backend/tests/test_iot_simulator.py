import random

import pytest

from backend.app.schemas.iot import TelemetryPayload
from backend.scripts.iot import kiosk_simulator as sim

TELEMETRY_URL = "http://api:8000/api/iot/telemetry"
CHAT_URL = "http://api:8000/api/chat"


def fake_post_factory(calls: list):
    def fake_post(url, payload, headers):
        calls.append((url, payload, headers))
        if url.endswith("/api/iot/telemetry"):
            return 202, {"accepted": len(payload["readings"])}
        return 200, {"category": "faq", "confidence": 0.9}

    return fake_post


@pytest.fixture
def no_sleep(monkeypatch):
    monkeypatch.setattr(sim.time, "sleep", lambda seconds: None)


def run_main(extra_args: list[str]) -> int:
    return sim.main(
        ["--device-key", "k", "--api-url", "http://api:8000/", "--seed", "1"]
        + extra_args
    )


def test_kiosk_emits_a_single_heartbeat() -> None:
    readings = sim.build_readings("kiosk", random.Random(1), {})

    assert [reading["kind"] for reading in readings] == ["heartbeat"]


def test_sensor_emits_temperature_humidity_and_occupancy() -> None:
    readings = sim.build_readings("sensor", random.Random(1), {})

    assert [reading["kind"] for reading in readings] == [
        "temperature",
        "humidity",
        "occupancy",
    ]


def test_sensor_values_stay_in_realistic_bounds() -> None:
    rng = random.Random(42)
    state: dict = {}

    for _ in range(200):
        values = {
            reading["kind"]: reading["value"]
            for reading in sim.build_readings("sensor", rng, state)
        }
        assert 17.0 <= values["temperature"] <= 28.0
        assert 35.0 <= values["humidity"] <= 65.0
        assert 0 <= values["occupancy"] <= 40


def test_same_seed_gives_same_measures() -> None:
    first = sim.build_readings("sensor", random.Random(5), {})
    second = sim.build_readings("sensor", random.Random(5), {})

    assert [r["value"] for r in first] == [r["value"] for r in second]


@pytest.mark.parametrize("role", ["kiosk", "sensor"])
def test_generated_payload_matches_api_schema(role) -> None:
    readings = sim.build_readings(role, random.Random(7), {})

    payload = TelemetryPayload.model_validate(
        {"device_id": sim.DEFAULT_DEVICE_IDS[role], "readings": readings}
    )

    assert len(payload.readings) == len(readings)


def test_main_refuses_to_run_without_device_key(monkeypatch) -> None:
    monkeypatch.delenv("IOT_DEVICE_KEY", raising=False)

    assert sim.main(["--role", "sensor", "--count", "1"]) == 2


def test_main_sends_one_telemetry_per_cycle(monkeypatch, no_sleep) -> None:
    calls: list = []
    monkeypatch.setattr(sim, "post_json", fake_post_factory(calls))

    code = run_main(["--role", "sensor", "--count", "3"])

    assert code == 0
    assert len(calls) == 3
    assert all(url == TELEMETRY_URL for url, _, _ in calls)
    assert calls[0][2] == {"X-Device-Key": "k"}
    assert calls[0][1]["device_id"] == "sensor-b204"


def test_kiosk_asks_a_question_every_cycle_on_kiosk_channel(
    monkeypatch, no_sleep
) -> None:
    calls: list = []
    monkeypatch.setattr(sim, "post_json", fake_post_factory(calls))

    run_main(["--role", "kiosk", "--count", "2", "--chat-every", "1"])

    chat_calls = [call for call in calls if call[0] == CHAT_URL]
    assert len(calls) == 4
    assert len(chat_calls) == 2
    assert all(payload["channel"] == "kiosk" for _, payload, _ in chat_calls)
    assert len({payload["session_id"] for _, payload, _ in chat_calls}) == 2


def test_kiosk_never_chats_when_chat_every_is_zero(monkeypatch, no_sleep) -> None:
    calls: list = []
    monkeypatch.setattr(sim, "post_json", fake_post_factory(calls))

    run_main(["--role", "kiosk", "--count", "3", "--chat-every", "0"])

    assert [url for url, _, _ in calls] == [TELEMETRY_URL] * 3


def test_kiosk_chats_every_second_cycle(monkeypatch, no_sleep) -> None:
    calls: list = []
    monkeypatch.setattr(sim, "post_json", fake_post_factory(calls))

    run_main(["--role", "kiosk", "--count", "4", "--chat-every", "2"])

    assert len([call for call in calls if call[0] == CHAT_URL]) == 2


def test_post_json_returns_zero_when_api_is_unreachable(monkeypatch) -> None:
    def refuse(*args, **kwargs):
        raise sim.urllib.error.URLError("connection refused")

    monkeypatch.setattr(sim.urllib.request, "urlopen", refuse)

    assert sim.post_json("http://unreachable", {}, {}) == (0, None)
