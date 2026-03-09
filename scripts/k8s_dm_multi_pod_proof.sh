#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
NAMESPACE="${NAMESPACE:-community-local}"
TIMEOUT_SECONDS="${TIMEOUT_SECONDS:-20}"

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    echo "$1 명령이 필요합니다."
    exit 1
  fi
}

require_cmd kubectl

if ! kubectl -n "${NAMESPACE}" get deploy community-be >/dev/null 2>&1; then
  echo "community-be deployment가 없습니다. 먼저 ./scripts/k8s_up_local.sh 를 실행하세요."
  exit 1
fi

kubectl -n "${NAMESPACE}" rollout status deploy/community-be --timeout=240s >/dev/null
kubectl -n "${NAMESPACE}" rollout status deploy/community-redis --timeout=240s >/dev/null

POD_DATA_RAW="$(kubectl -n "${NAMESPACE}" get pod -l app=community-be -o jsonpath='{range .items[*]}{.metadata.name}{" "}{.status.podIP}{"\n"}{end}' | sort)"
POD_COUNT="$(printf '%s\n' "${POD_DATA_RAW}" | sed '/^$/d' | wc -l | tr -d ' ')"
if [[ "${POD_COUNT}" -lt 2 ]]; then
  echo "[ERROR] backend Pod가 2개 이상 필요합니다. 현재: ${POD_COUNT}"
  exit 1
fi

POD_A_LINE="$(printf '%s\n' "${POD_DATA_RAW}" | sed -n '1p')"
POD_B_LINE="$(printf '%s\n' "${POD_DATA_RAW}" | sed -n '2p')"
POD_A_NAME="${POD_A_LINE%% *}"
POD_A_IP="${POD_A_LINE##* }"
POD_B_NAME="${POD_B_LINE%% *}"
POD_B_IP="${POD_B_LINE##* }"
RUNNER_POD="${POD_A_NAME}"

kubectl -n "${NAMESPACE}" exec -i "${RUNNER_POD}" -- env \
  POD_A_NAME="${POD_A_NAME}" \
  POD_A_IP="${POD_A_IP}" \
  POD_B_NAME="${POD_B_NAME}" \
  POD_B_IP="${POD_B_IP}" \
  TIMEOUT_SECONDS="${TIMEOUT_SECONDS}" \
  python - <<'PY'
import asyncio
import json
import os
import time

import requests
import websockets

POD_A_NAME = os.environ["POD_A_NAME"]
POD_A_IP = os.environ["POD_A_IP"]
POD_B_NAME = os.environ["POD_B_NAME"]
POD_B_IP = os.environ["POD_B_IP"]
TIMEOUT_SECONDS = int(os.environ.get("TIMEOUT_SECONDS", "20"))

BASE_A = f"http://{POD_A_IP}:8000"
BASE_B = f"http://{POD_B_IP}:8000"
WS_A = f"ws://{POD_A_IP}:8000"
WS_B = f"ws://{POD_B_IP}:8000"
PASSWORD = "Qa!12345Aa"
seed = str(int(time.time() * 1000))
EMAIL_A = f"dmproof-a-{seed}@example.com"
EMAIL_B = f"dmproof-b-{seed}@example.com"
NICK_A = f"dma{seed[-4:]}"
NICK_B = f"dmb{seed[-4:]}"


def ensure_status(response, expected, label):
    if response.status_code != expected:
        raise SystemExit(f"[FAIL] {label}: expected {expected}, got {response.status_code}, body={response.text}")


def signup(session, base_url, email, nickname):
    response = session.post(
        f"{base_url}/v1/auth/signup",
        json={"email": email, "password": PASSWORD, "nickname": nickname},
        timeout=TIMEOUT_SECONDS,
    )
    ensure_status(response, 201, f"signup {email}")


def login(session, base_url, email):
    response = session.post(
        f"{base_url}/v1/auth/login",
        json={"email": email, "password": PASSWORD},
        timeout=TIMEOUT_SECONDS,
    )
    ensure_status(response, 200, f"login {email}")
    if "session_id" not in session.cookies:
        raise SystemExit(f"[FAIL] login {email}: session_id cookie missing")


def create_room(session, base_url, target_user_id):
    response = session.post(
        f"{base_url}/v1/dm/rooms",
        json={"targetUserId": target_user_id},
        timeout=TIMEOUT_SECONDS,
    )
    ensure_status(response, 200, "create room")
    return response.json()["data"]["roomId"]


def get_me(session, base_url):
    response = session.get(f"{base_url}/v1/auth/me", timeout=TIMEOUT_SECONDS)
    ensure_status(response, 200, "get me")
    return response.json()["data"]


def get_messages(session, base_url, room_id):
    response = session.get(f"{base_url}/v1/dm/rooms/{room_id}/messages", timeout=TIMEOUT_SECONDS)
    ensure_status(response, 200, "get messages")
    return response.json()["data"]


def get_rooms(session, base_url):
    response = session.get(f"{base_url}/v1/dm/rooms", timeout=TIMEOUT_SECONDS)
    ensure_status(response, 200, "get rooms")
    return response.json()["data"]


async def receive_until(ws, expected_types, timeout_seconds):
    found = {}
    start = time.time()
    while time.time() - start < timeout_seconds:
        remaining = timeout_seconds - (time.time() - start)
        raw = await asyncio.wait_for(ws.recv(), timeout=remaining)
        payload = json.loads(raw)
        payload_type = payload.get("type")
        if payload_type in expected_types:
            found[payload_type] = payload
            if all(t in found for t in expected_types):
                return found
    raise TimeoutError(f"Timed out waiting for events: {expected_types}")


async def main():
    session_a = requests.Session()
    session_b = requests.Session()

    signup(session_a, BASE_A, EMAIL_A, NICK_A)
    signup(session_b, BASE_B, EMAIL_B, NICK_B)
    login(session_a, BASE_A, EMAIL_A)
    login(session_b, BASE_B, EMAIL_B)

    me_a = get_me(session_a, BASE_A)
    me_b = get_me(session_b, BASE_B)
    room_id = create_room(session_a, BASE_A, me_b["userId"])

    get_messages(session_a, BASE_A, room_id)
    get_messages(session_b, BASE_B, room_id)

    cookie_a = f"session_id={session_a.cookies['session_id']}"
    cookie_b = f"session_id={session_b.cookies['session_id']}"

    async with websockets.connect(f"{WS_A}/ws/dm/{room_id}", additional_headers={"Cookie": cookie_a}) as ws_a, \
        websockets.connect(f"{WS_B}/ws/dm/{room_id}", additional_headers={"Cookie": cookie_b}) as ws_b:
        await receive_until(ws_a, ["connected"], TIMEOUT_SECONDS)
        await receive_until(ws_b, ["connected"], TIMEOUT_SECONDS)

        content = f"redis-proof-{seed}"
        await ws_a.send(json.dumps({"type": "send_message", "content": content}, ensure_ascii=False))

        received_b = await receive_until(ws_b, ["message_created"], TIMEOUT_SECONDS)
        received_a = await receive_until(ws_a, ["message_created", "messages_read"], TIMEOUT_SECONDS)

        rooms_a = get_rooms(session_a, BASE_A)
        rooms_b = get_rooms(session_b, BASE_B)
        room_a = next(room for room in rooms_a["rooms"] if int(room["roomId"]) == int(room_id))
        room_b = next(room for room in rooms_b["rooms"] if int(room["roomId"]) == int(room_id))

        print(json.dumps({
            "roomId": room_id,
            "podA": POD_A_NAME,
            "podB": POD_B_NAME,
            "messageContent": received_b["message_created"]["data"]["content"],
            "receiverIsMine": received_b["message_created"]["data"]["isMine"],
            "senderIsMine": received_a["message_created"]["data"]["isMine"],
            "readEventType": received_a["messages_read"]["type"],
            "roomAUnread": room_a["unreadCount"],
            "roomBUnread": room_b["unreadCount"],
        }, ensure_ascii=False))


asyncio.run(main())
PY
