"""Simulateur de borne d'accueil et de capteur de salle (IoT simule).

Exemples :
    python -m backend.scripts.iot.kiosk_simulator --role sensor --count 3 --interval 1
    python -m backend.scripts.iot.kiosk_simulator --role kiosk --chat-every 2
"""

import argparse
import json
import os
import random
import sys
import time
import urllib.error
import urllib.request
import uuid
from datetime import datetime, timezone
from itertools import count as infinite_count

DEFAULT_DEVICE_IDS = {
    "kiosk": "kiosk-hall-01",
    "sensor": "sensor-b204",
}

KIOSK_QUESTIONS = (
    "Comment faire une convention de stage ?",
    "Quel est le contact du service scolarité ?",
    "Quels sont les cours du groupe B1-A lundi ?",
    "Ou se deroule le cours de Machine Learning Avance ?",
)


def utc_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def build_readings(role: str, rng: random.Random, state: dict) -> list[dict]:
    """Construit les mesures d'un cycle d'emission selon le role de l'appareil."""
    now = utc_iso()

    if role == "kiosk":
        return [
            {"kind": "heartbeat", "value": 1, "unit": None, "recorded_at": now},
        ]

    # Capteur de salle : la temperature derive doucement autour de 22 C
    temperature = state.get("temperature", 22.0) + rng.uniform(-0.4, 0.4)
    temperature = min(max(temperature, 17.0), 28.0)
    state["temperature"] = temperature

    return [
        {
            "kind": "temperature",
            "value": round(temperature, 1),
            "unit": "C",
            "recorded_at": now,
        },
        {
            "kind": "humidity",
            "value": round(rng.uniform(35.0, 65.0), 1),
            "unit": "%",
            "recorded_at": now,
        },
        {
            "kind": "occupancy",
            "value": rng.randint(0, 40),
            "unit": "persons",
            "recorded_at": now,
        },
    ]


def post_json(url: str, payload: dict, headers: dict) -> tuple[int, dict | None]:
    """POST JSON avec la bibliotheque standard. Ne leve jamais : renvoie (code, corps)."""
    request = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status, json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as error:
        try:
            body = json.loads(error.read().decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            body = None
        return error.code, body
    except (urllib.error.URLError, TimeoutError) as error:
        print(f"  ! API injoignable : {error}")
        return 0, None


def send_telemetry(api_url: str, device_key: str, device_id: str, readings: list[dict]) -> int:
    status, body = post_json(
        f"{api_url}/api/iot/telemetry",
        {"device_id": device_id, "readings": readings},
        {"X-Device-Key": device_key},
    )
    kinds = ", ".join(f"{r['kind']}={r['value']}" for r in readings)
    print(f"[telemetry] {device_id} -> HTTP {status} ({kinds})")
    if status not in (0, 202) and body:
        print(f"  ! {body.get('detail')}")
    return status


def send_kiosk_question(api_url: str, rng: random.Random) -> int:
    """Simule un visiteur : nouvelle session anonyme, une question, canal 'kiosk'."""
    question = rng.choice(KIOSK_QUESTIONS)
    status, body = post_json(
        f"{api_url}/api/chat",
        {"session_id": str(uuid.uuid4()), "message": question, "channel": "kiosk"},
        {},
    )
    if status == 200 and body:
        print(
            f"[chat] kiosk -> HTTP 200 | {question!r} | "
            f"{body['category']} ({body['confidence']:.2f})"
        )
    else:
        print(f"[chat] kiosk -> HTTP {status} | {question!r}")
    return status


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Simulateur de borne / capteur IoT")
    parser.add_argument("--role", choices=sorted(DEFAULT_DEVICE_IDS), default="sensor")
    parser.add_argument("--device-id", default=None)
    parser.add_argument("--api-url", default=os.environ.get("API_URL", "http://127.0.0.1:8000"))
    parser.add_argument("--device-key", default=os.environ.get("IOT_DEVICE_KEY", ""))
    parser.add_argument("--interval", type=float, default=5.0, help="secondes entre deux envois")
    parser.add_argument("--count", type=int, default=0, help="nombre de cycles (0 = infini)")
    parser.add_argument("--chat-every", type=int, default=3, help="kiosk : une question tous les N cycles (0 = jamais)")
    parser.add_argument("--seed", type=int, default=None)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)

    if not args.device_key:
        print("Erreur : cle d'appareil absente (--device-key ou variable IOT_DEVICE_KEY).")
        return 2

    device_id = args.device_id or DEFAULT_DEVICE_IDS[args.role]
    api_url = args.api_url.rstrip("/")
    rng = random.Random(args.seed)
    state: dict = {}

    print(f"Simulateur demarre : role={args.role} device_id={device_id} api={api_url}")

    cycles = range(args.count) if args.count > 0 else infinite_count()
    try:
        for index in cycles:
            readings = build_readings(args.role, rng, state)
            send_telemetry(api_url, args.device_key, device_id, readings)

            if args.role == "kiosk" and args.chat_every > 0 and index % args.chat_every == 0:
                send_kiosk_question(api_url, rng)

            if args.count == 0 or index < args.count - 1:
                time.sleep(args.interval)
    except KeyboardInterrupt:
        print("\nSimulateur arrete.")

    return 0


if __name__ == "__main__":
    sys.exit(main())
