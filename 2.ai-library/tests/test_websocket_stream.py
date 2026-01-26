# tests/test_websocket_stream.py
"""WebSocket stream contract tests."""

from datetime import datetime
from unittest.mock import AsyncMock

from fastapi.testclient import TestClient

from src.api.main import create_app
from src.api.dependencies import get_session_manager
from src.conversation.flow import PlanEvent, PlanEventType
from src.models.session import ExtractionSession, SessionPhase, PendingQuestion
from src.models.content_mode import ContentMode


class DummySessionManager:
    """Minimal session manager for WebSocket tests."""

    def __init__(self, session, cleanup_events=None):
        self._session = session
        self._cleanup_events = cleanup_events or []
        self.storage = AsyncMock()

    async def get_session(self, session_id: str):
        return self._session

    async def generate_cleanup_plan_with_ai(self, session_id: str):
        for event in self._cleanup_events:
            yield event

    async def generate_routing_plan_with_ai(self, session_id: str):
        return
        yield  # pragma: no cover


def _build_client(manager) -> TestClient:
    app = create_app()

    async def override_get_session_manager(config=None):
        return manager

    app.dependency_overrides[get_session_manager] = override_get_session_manager
    return TestClient(app)


def test_websocket_user_message_event_includes_timestamp():
    session = ExtractionSession(
        id="sess_ws",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.INITIALIZED,
        source=None,
        library_path="./library",
        content_mode=ContentMode.STRICT,
    )
    manager = DummySessionManager(session)
    client = _build_client(manager)

    with client.websocket_connect("/api/sessions/sess_ws/stream") as websocket:
        connected = websocket.receive_json()
        assert "timestamp" in connected

        websocket.send_json({"command": "user_message", "message": "Hello"})
        event = websocket.receive_json()

    assert event["event_type"] == "user_message"
    assert "timestamp" in event
    assert event["data"]["role"] == "user"
    assert event["data"]["content"] == "Hello"


def test_websocket_question_pause_and_answer_resume():
    question = PendingQuestion(
        id="q1",
        question="Need clarification?",
        created_at=datetime.now(),
    )
    session = ExtractionSession(
        id="sess_ws_q",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.INITIALIZED,
        source=None,
        library_path="./library",
        content_mode=ContentMode.STRICT,
        pending_questions=[question],
    )
    events = [
        PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Working",
            data={"step": "analysis"},
            timestamp=datetime.now(),
        )
    ]
    manager = DummySessionManager(session, cleanup_events=events)
    client = _build_client(manager)

    with client.websocket_connect("/api/sessions/sess_ws_q/stream") as websocket:
        websocket.receive_json()  # connected

        websocket.send_json({"command": "generate_cleanup"})
        question_event = websocket.receive_json()
        assert question_event["event_type"] == "question"
        assert question_event["data"]["question"] == "Need clarification?"

        websocket.send_json({"command": "answer", "answer": "Here is the answer"})
        answer_event = websocket.receive_json()
        assert answer_event["event_type"] == "user_message"

        websocket.send_json({"command": "generate_cleanup"})
        progress_event = websocket.receive_json()
        assert progress_event["event_type"] == "progress"
        assert "timestamp" in progress_event
