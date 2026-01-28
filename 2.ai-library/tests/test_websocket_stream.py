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
from src.models.cleanup_mode_setting import CleanupModeSetting


class DummySessionManager:
    """Minimal session manager for WebSocket tests."""

    def __init__(self, session, cleanup_events=None):
        self._session = session
        self._cleanup_events = cleanup_events or []
        self.storage = AsyncMock()
        self.last_cleanup_mode = None  # Track the cleanup_mode passed to generate_cleanup_plan_with_ai

    async def get_session(self, session_id: str):
        return self._session

    async def generate_cleanup_plan_with_ai(self, session_id: str, cleanup_mode=None):
        self.last_cleanup_mode = cleanup_mode
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


def test_websocket_generate_cleanup_with_cleanup_mode():
    """Test that generate_cleanup command accepts and passes cleanup_mode parameter."""
    session = ExtractionSession(
        id="sess_ws_mode",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.INITIALIZED,
        source=None,
        library_path="./library",
        content_mode=ContentMode.STRICT,
    )
    events = [
        PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Starting cleanup",
            data={"step": "analysis"},
            timestamp=datetime.now(),
        )
    ]
    manager = DummySessionManager(session, cleanup_events=events)
    client = _build_client(manager)

    with client.websocket_connect("/api/sessions/sess_ws_mode/stream") as websocket:
        websocket.receive_json()  # connected

        # Test with aggressive cleanup mode
        websocket.send_json({"command": "generate_cleanup", "cleanup_mode": "aggressive"})
        progress_event = websocket.receive_json()
        assert progress_event["event_type"] == "progress"

    # Verify the cleanup_mode was passed correctly
    assert manager.last_cleanup_mode == CleanupModeSetting.AGGRESSIVE


def test_websocket_generate_cleanup_with_conservative_mode():
    """Test that generate_cleanup command works with conservative cleanup_mode."""
    session = ExtractionSession(
        id="sess_ws_conservative",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.INITIALIZED,
        source=None,
        library_path="./library",
        content_mode=ContentMode.STRICT,
    )
    events = [
        PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Starting cleanup",
            data={"step": "analysis"},
            timestamp=datetime.now(),
        )
    ]
    manager = DummySessionManager(session, cleanup_events=events)
    client = _build_client(manager)

    with client.websocket_connect("/api/sessions/sess_ws_conservative/stream") as websocket:
        websocket.receive_json()  # connected

        # Test with conservative cleanup mode
        websocket.send_json({"command": "generate_cleanup", "cleanup_mode": "conservative"})
        progress_event = websocket.receive_json()
        assert progress_event["event_type"] == "progress"

    # Verify the cleanup_mode was passed correctly
    assert manager.last_cleanup_mode == CleanupModeSetting.CONSERVATIVE


def test_websocket_generate_cleanup_defaults_to_balanced():
    """Test that generate_cleanup command defaults to balanced mode when not specified."""
    session = ExtractionSession(
        id="sess_ws_default",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.INITIALIZED,
        source=None,
        library_path="./library",
        content_mode=ContentMode.STRICT,
    )
    events = [
        PlanEvent(
            type=PlanEventType.PROGRESS,
            message="Starting cleanup",
            data={"step": "analysis"},
            timestamp=datetime.now(),
        )
    ]
    manager = DummySessionManager(session, cleanup_events=events)
    client = _build_client(manager)

    with client.websocket_connect("/api/sessions/sess_ws_default/stream") as websocket:
        websocket.receive_json()  # connected

        # Test without cleanup_mode (should default to balanced)
        websocket.send_json({"command": "generate_cleanup"})
        progress_event = websocket.receive_json()
        assert progress_event["event_type"] == "progress"

    # Verify the cleanup_mode defaulted to balanced
    assert manager.last_cleanup_mode == CleanupModeSetting.BALANCED


def test_websocket_generate_cleanup_invalid_mode_returns_error():
    """Test that generate_cleanup command rejects invalid cleanup_mode values."""
    session = ExtractionSession(
        id="sess_ws_invalid",
        created_at=datetime.now(),
        updated_at=datetime.now(),
        phase=SessionPhase.INITIALIZED,
        source=None,
        library_path="./library",
        content_mode=ContentMode.STRICT,
    )
    manager = DummySessionManager(session)
    client = _build_client(manager)

    with client.websocket_connect("/api/sessions/sess_ws_invalid/stream") as websocket:
        websocket.receive_json()  # connected

        # Test with invalid cleanup_mode
        websocket.send_json({"command": "generate_cleanup", "cleanup_mode": "invalid_mode"})
        error_event = websocket.receive_json()

        assert error_event["event_type"] == "error"
        assert "Invalid cleanup_mode" in error_event["data"]["message"]
        assert "invalid_mode" in error_event["data"]["message"]

    # Verify the cleanup method was never called
    assert manager.last_cleanup_mode is None
