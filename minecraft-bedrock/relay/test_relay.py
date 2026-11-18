import sqlite3
import tempfile
from pathlib import Path

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient

import app as relay_module
from app import RelayStore, app, store


client = TestClient(app)


def setup_function():
    store.reset()


def pair():
    started = client.post("/v1/pair/start").json()
    claimed_response = client.post(
        "/v1/pair/claim",
        json={"pairing_code": started["pairing_code"]},
    )
    assert claimed_response.status_code == 200
    claimed = claimed_response.json()
    return started["app_token"], claimed["server_token"], claimed["session_id"]


def auth(token):
    return {"Authorization": f"Bearer {token}"}


def make_event(event_id="evt-test-0001", **overrides):
    event = {
        "event_id": event_id,
        "event_type": "interaction",
        "player": "PlayerOne",
        "npc": "Villager",
        "npc_id": "entity-7f31",
        "npc_type": "minecraft:villager",
        "message": "Olá!",
        "world_id": "test-world",
    }
    event.update(overrides)
    return event


def test_pairing_is_one_time_and_tokens_are_side_scoped():
    app_token, server_token, _ = pair()
    assert client.get("/v1/app/events", headers=auth(app_token)).status_code == 200
    assert client.get("/v1/server/replies", headers=auth(app_token)).status_code == 401
    assert client.get("/v1/app/events", headers=auth(server_token)).status_code == 401
    assert client.get("/v1/server/replies", headers=auth(server_token)).status_code == 200


def test_pairing_code_cannot_be_claimed_twice():
    started = client.post("/v1/pair/start").json()
    first = client.post("/v1/pair/claim", json={"pairing_code": started["pairing_code"]})
    second = client.post("/v1/pair/claim", json={"pairing_code": started["pairing_code"]})
    assert first.status_code == 200
    assert second.status_code == 400


def test_event_round_trip_stays_inside_paired_session():
    app_token, server_token, _ = pair()
    event = make_event()
    assert client.post("/v1/server/events", json=event, headers=auth(server_token)).status_code == 202
    assert client.get("/v1/app/events", headers=auth(app_token)).json()["events"] == [event]

    reply = {
        "event_id": event["event_id"],
        "message": "Bom dia! Como posso ajudar?",
        "npc": "Aldeão",
    }
    assert client.post("/v1/app/replies", json=reply, headers=auth(app_token)).status_code == 202
    assert client.get("/v1/app/events", headers=auth(app_token)).json()["events"] == []
    assert client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"] == [reply]
    assert client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"] == [reply]

    ack = client.post(
        "/v1/server/ack",
        json={"event_id": event["event_id"]},
        headers=auth(server_token),
    )
    assert ack.status_code == 200
    assert client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"] == []


def test_sessions_are_isolated_and_duplicate_events_rejected():
    app_one, server_one, _ = pair()
    app_two, server_two, _ = pair()
    event = make_event(
        "evt-isolated-01",
        event_type="chat",
        npc="Guard",
        message="Quem é você?",
        world_id="world-one",
    )
    assert client.post("/v1/server/events", json=event, headers=auth(server_one)).status_code == 202
    assert client.get("/v1/app/events", headers=auth(app_two)).json()["events"] == []
    assert client.post("/v1/server/events", json=event, headers=auth(server_one)).status_code == 409
    assert client.get("/v1/app/events", headers=auth(app_one)).json()["events"] == [event]
    assert client.get("/v1/server/replies", headers=auth(server_two)).json()["replies"] == []


def test_app_cannot_reply_to_event_from_another_session():
    _, server_one, _ = pair()
    app_two, _, _ = pair()
    event = make_event("evt-private-01", player="P1", message="", world_id="world-one")
    client.post("/v1/server/events", json=event, headers=auth(server_one))
    reply = {"event_id": event["event_id"], "message": "Resposta", "npc": "Villager"}
    assert client.post("/v1/app/replies", json=reply, headers=auth(app_two)).status_code == 404


def test_event_queue_overflow_is_rejected_without_dropping_existing_events():
    app_token, server_token, session_id = pair()
    for index in range(64):
        store.enqueue_event(session_id, f"evt-fill-{index:04d}", make_event(f"evt-fill-{index:04d}"))
    overflow = make_event("evt-overflow-0001", message="Olá")
    response = client.post("/v1/server/events", json=overflow, headers=auth(server_token))
    assert response.status_code == 429
    assert "Fila de eventos cheia" in response.json()["detail"]
    assert len(client.get("/v1/app/events", headers=auth(app_token)).json()["events"]) == 64


def test_reply_queue_overflow_is_rejected_without_dropping_existing_replies():
    app_token, server_token, session_id = pair()
    for index in range(64):
        event_id = f"evt-reply-{index:04d}"
        store.enqueue_event(session_id, event_id, make_event(event_id))
        store.enqueue_reply(
            session_id,
            event_id,
            {"event_id": event_id, "message": "Resposta", "npc": "Villager"},
        )
    next_event = make_event("evt-reply-overflow")
    store.enqueue_event(session_id, next_event["event_id"], next_event)
    response = client.post(
        "/v1/app/replies",
        json={
            "event_id": next_event["event_id"],
            "message": "Nova resposta",
            "npc": "Villager",
        },
        headers=auth(app_token),
    )
    assert response.status_code == 429
    assert "Fila de respostas cheia" in response.json()["detail"]
    assert len(client.get("/v1/server/replies", headers=auth(server_token)).json()["replies"]) == 64


def test_sqlite_store_recovers_pairing_session_events_and_replies_after_restart():
    with tempfile.TemporaryDirectory() as directory:
        database = str(Path(directory) / "relay.sqlite3")
        first = RelayStore(database)
        started = first.start_pairing()
        claimed = first.claim_pairing(started["pairing_code"])
        event = make_event("evt-persist-0001")
        first.enqueue_event(claimed["session_id"], event["event_id"], event)
        first.close()

        second = RelayStore(database)
        assert second.storage_mode == "sqlite_file"
        app_session = second.authenticate(f"Bearer {started['app_token']}", "app")
        server_session = second.authenticate(f"Bearer {claimed['server_token']}", "server")
        assert app_session == server_session == claimed["session_id"]
        assert second.get_events(app_session) == [event]
        reply = {"event_id": event["event_id"], "message": "Ainda me lembro.", "npc": "Villager"}
        second.enqueue_reply(app_session, event["event_id"], reply)
        second.close()

        third = RelayStore(database)
        assert third.get_events(app_session) == []
        assert third.get_replies(server_session) == [reply]
        assert third.acknowledge_reply(server_session, event["event_id"]) is True
        assert third.get_replies(server_session) == []
        third.close()


def test_sqlite_store_persists_rate_limits_and_never_stores_plaintext_tokens():
    with tempfile.TemporaryDirectory() as directory:
        database = str(Path(directory) / "relay.sqlite3")
        first = RelayStore(database)
        started = first.start_pairing()
        for _ in range(10):
            first.rate_limit_ip("198.51.100.10")
        first.close()

        connection = sqlite3.connect(database)
        try:
            raw = connection.execute("SELECT app_token_hash FROM pairings").fetchone()[0]
            assert started["app_token"] not in raw
            assert len(raw) == 64
        finally:
            connection.close()

        second = RelayStore(database)
        with pytest.raises(HTTPException) as error:
            second.rate_limit_ip("198.51.100.10")
        assert error.value.status_code == 429
        second.close()


def test_production_pairing_is_blocked_when_storage_is_ephemeral(monkeypatch):
    monkeypatch.setenv("AURION_REQUIRE_PERSISTENT_STORAGE", "true")
    health = client.get("/health").json()
    assert health["status"] == "degraded"
    assert health["storage"] == "memory_ephemeral"
    assert health["pairing_available"] is False

    response = client.post("/v1/pair/start")
    assert response.status_code == 503
    assert "volume persistente privado" in response.json()["detail"]


def test_production_pairing_is_allowed_with_sqlite_file(monkeypatch, tmp_path):
    monkeypatch.setenv("AURION_REQUIRE_PERSISTENT_STORAGE", "true")
    durable = RelayStore(str(tmp_path / "relay.sqlite3"))
    monkeypatch.setattr(relay_module, "store", durable)
    try:
        health = client.get("/health").json()
        assert health["status"] == "ok"
        assert health["storage"] == "sqlite_file"
        assert health["pairing_available"] is True
        response = client.post("/v1/pair/start")
        assert response.status_code == 200
    finally:
        durable.close()


def test_health_reports_ephemeral_mode_instead_of_claiming_durability():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["storage"] == "memory_ephemeral"
