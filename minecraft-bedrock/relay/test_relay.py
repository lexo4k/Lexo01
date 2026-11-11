from fastapi.testclient import TestClient

from app import app, store


client = TestClient(app)


def setup_function():
    with store.lock:
        store.pairings.clear()
        store.sessions.clear()
        store.token_index.clear()
        store.ip_requests.clear()


def pair():
    started = client.post("/v1/pair/start").json()
    claimed = client.post("/v1/pair/claim", json={"pairing_code": started["pairing_code"]})
    assert claimed.status_code == 200
    return started["app_token"], claimed.json()["server_token"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def test_pairing_is_one_time_and_tokens_are_side_scoped():
    app_token, server_token = pair()
    assert client.get("/v1/app/events", headers=auth(app_token)).status_code == 200
    assert client.get("/v1/server/replies", headers=auth(app_token)).status_code == 401
    assert client.post("/v1/pair/claim", json={"pairing_code": "00000000"}).status_code == 400
    assert client.get("/v1/server/replies", headers=auth(server_token)).status_code == 200


def test_event_round_trip_stays_inside_paired_session():
    app_token, server_token = pair()
    event = {
        "event_id": "evt-test-0001",
        "event_type": "interaction",
        "player": "PlayerOne",
        "npc": "Villager",
        "message": "Olá!",
        "world_id": "test-world",
    }
    assert client.post("/v1/server/events", json=event, headers=auth(server_token)).status_code == 202
    assert client.get("/v1/app/events", headers=auth(app_token)).json()["events"] == [event]
    reply = {"event_id": event["event_id"], "message": "Bom dia! Como posso ajudar?", "npc": "Aldeão"}
    assert client.post("/v1/app/replies", json=reply, headers=auth(app_token)).status_code == 202
    assert client.get("/v1/app/events", headers=auth(app_token)).json()["events"] == []
    assert client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"] == [reply]
    assert client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"] == [reply]
    ack = client.post("/v1/server/ack", json={"event_id": event["event_id"]}, headers=auth(server_token))
    assert ack.status_code == 200
    assert client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"] == []


def test_sessions_are_isolated_and_duplicate_events_rejected():
    app_one, server_one = pair()
    app_two, server_two = pair()
    event = {
        "event_id": "evt-isolated-01",
        "event_type": "chat",
        "player": "PlayerOne",
        "npc": "Guard",
        "message": "Quem é você?",
        "world_id": "world-one",
    }
    assert client.post("/v1/server/events", json=event, headers=auth(server_one)).status_code == 202
    assert client.get("/v1/app/events", headers=auth(app_two)).json()["events"] == []
    assert client.post("/v1/server/events", json=event, headers=auth(server_one)).status_code == 409
    assert client.get("/v1/app/events", headers=auth(app_one)).json()["events"] == [event]
    assert client.get("/v1/server/replies", headers=auth(server_two)).json()["replies"] == []


def test_app_cannot_reply_to_event_from_another_session():
    app_one, server_one = pair()
    app_two, _ = pair()
    event = {
        "event_id": "evt-private-01",
        "event_type": "interaction",
        "player": "P1",
        "npc": "Villager",
        "message": "",
        "world_id": "world-one",
    }
    client.post("/v1/server/events", json=event, headers=auth(server_one))
    reply = {"event_id": event["event_id"], "message": "Resposta", "npc": "Villager"}
    assert client.post("/v1/app/replies", json=reply, headers=auth(app_two)).status_code == 404


def test_event_queue_overflow_is_rejected_without_dropping_existing_events():
    app_token, server_token = pair()
    with store.lock:
        session_id, _ = store.token_index[__import__("hashlib").sha256(app_token.encode()).hexdigest()]
        session = store.sessions[session_id]
        for index in range(64):
            event = {
                "event_id": f"evt-fill-{index:04d}",
                "event_type": "interaction",
                "player": "PlayerOne",
                "npc": "Villager",
                "message": "",
                "world_id": "test-world",
            }
            session.event_ids.add(event["event_id"])
            session.event_order.append(event["event_id"])
            session.events.append(event)
    overflow = {
        "event_id": "evt-overflow-0001",
        "event_type": "interaction",
        "player": "PlayerOne",
        "npc": "Villager",
        "message": "Olá",
        "world_id": "test-world",
    }
    response = client.post("/v1/server/events", json=overflow, headers=auth(server_token))
    assert response.status_code == 429
    assert "Fila de eventos cheia" in response.json()["detail"]
    assert len(client.get("/v1/app/events", headers=auth(app_token)).json()["events"]) == 64


def test_reply_queue_overflow_is_rejected_without_dropping_existing_replies():
    app_token, server_token = pair()
    with store.lock:
        session_id, _ = store.token_index[__import__("hashlib").sha256(app_token.encode()).hexdigest()]
        session = store.sessions[session_id]
        for index in range(64):
            event_id = f"evt-reply-{index:04d}"
            session.event_ids.add(event_id)
            session.replies.append({"event_id": event_id, "message": "Resposta", "npc": "Villager"})
    response = client.post(
        "/v1/app/replies",
        json={"event_id": "evt-reply-overflow", "message": "Nova resposta", "npc": "Villager"},
        headers=auth(app_token),
    )
    assert response.status_code == 429
    assert "Fila de respostas cheia" in response.json()["detail"]
    assert len(client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"]) == 64
