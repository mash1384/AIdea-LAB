"""
SessionManager 클래스를 위한 단위 테스트

이 모듈은 src/session_manager.py의 SessionManager 클래스에 대한 
단위 테스트를 제공합니다.
"""

import pytest
from src.session_manager import SessionManager
from google.adk.sessions import Session
from google.adk.events import Event, EventActions
from typing import Dict, Any, Optional
from unittest.mock import patch, MagicMock


@pytest.fixture
def session_manager():
    """SessionManager 인스턴스를 제공하는 픽스처"""
    app_name = "test_app"
    user_id = "test_user"
    manager = SessionManager(app_name=app_name, user_id=user_id)
    return manager


class TestSessionManager:
    """SessionManager 클래스 테스트 스위트"""

    def test_create_session_without_initial_state(self, session_manager):
        """초기 상태 없이 세션 생성 테스트"""
        # Given
        # 픽스처로부터 SessionManager 인스턴스 제공

        # When
        session, session_id = session_manager.create_session()

        # Then
        assert session is not None
        assert isinstance(session, Session)
        assert session_id.startswith("session_")
        assert len(session_id) > 8  # session_<uuid_part>
        assert session_manager.active_sessions[session_manager.user_id] == session_id
        assert session.state == {}

    def test_create_session_with_initial_state(self, session_manager):
        """초기 상태와 함께 세션 생성 테스트"""
        # Given
        initial_state = {"key1": "value1", "key2": "value2"}

        # When
        session, session_id = session_manager.create_session(initial_state=initial_state)

        # Then
        assert session is not None
        assert isinstance(session, Session)
        assert session_id.startswith("session_")
        assert session_manager.active_sessions[session_manager.user_id] == session_id
        assert session.state == initial_state
        assert session.state["key1"] == "value1"
        assert session.state["key2"] == "value2"

    def test_get_session_with_existing_id(self, session_manager):
        """존재하는 세션 ID로 세션 조회 테스트"""
        # Given
        session, session_id = session_manager.create_session(initial_state={"test_key": "test_value"})

        # When
        retrieved_session = session_manager.get_session(session_id)

        # Then
        assert retrieved_session is not None
        assert isinstance(retrieved_session, Session)
        assert retrieved_session.id == session_id
        assert retrieved_session.state["test_key"] == "test_value"

    def test_get_session_with_nonexistent_id(self, session_manager):
        """존재하지 않는 세션 ID로 세션 조회 테스트"""
        # Given
        nonexistent_id = "session_nonexistent"

        # When
        retrieved_session = session_manager.get_session(nonexistent_id)

        # Then
        assert retrieved_session is None

    def test_get_session_without_id_returns_active_session(self, session_manager):
        """session_id 없이 호출 시 활성 세션 반환 테스트"""
        # Given
        session, session_id = session_manager.create_session(initial_state={"test_key": "test_value"})
        # create_session이 active_session_id를 설정함

        # When
        retrieved_session = session_manager.get_session()

        # Then
        assert retrieved_session is not None
        assert retrieved_session.id == session_id
        assert retrieved_session.state["test_key"] == "test_value"

    def test_get_session_without_id_returns_none_when_no_active_session(self, session_manager):
        """활성 세션이 없을 때 session_id 없이 호출 시 None 반환 테스트"""
        # Given
        # 활성 세션이 없는 상태로 시작

        # When
        retrieved_session = session_manager.get_session()

        # Then
        assert retrieved_session is None

    def test_get_active_session_id(self, session_manager):
        """get_active_session_id 메서드 테스트"""
        # Given
        session, session_id = session_manager.create_session()

        # When
        active_id = session_manager.get_active_session_id()

        # Then
        assert active_id == session_id

    def test_set_active_session_id(self, session_manager):
        """set_active_session_id 메서드 테스트"""
        # Given
        new_session_id = "session_custom_id"

        # When
        session_manager.set_active_session_id(new_session_id)

        # Then
        assert session_manager.get_active_session_id() == new_session_id
        assert session_manager.active_sessions[session_manager.user_id] == new_session_id

    def test_update_session_state_success(self, session_manager):
        """세션 상태 업데이트 성공 테스트"""
        # Given
        session, session_id = session_manager.create_session(initial_state={"initial_key": "initial_value"})
        state_updates = {"new_key": "new_value", "initial_key": "updated_value"}

        # When
        result = session_manager.update_session_state(state_updates)

        # Then
        assert result is True
        updated_session = session_manager.get_session(session_id)
        assert updated_session.state["new_key"] == "new_value"
        assert updated_session.state["initial_key"] == "updated_value"

    def test_update_session_state_with_no_active_session(self, session_manager):
        """활성 세션이 없을 때 상태 업데이트 실패 테스트"""
        # Given
        # 활성 세션을 설정하지 않음
        session_manager.active_sessions = {}  # 활성 세션 비우기
        state_updates = {"key": "value"}

        # When
        result = session_manager.update_session_state(state_updates)

        # Then
        assert result is False

    @patch('src.session_manager.EventActions')
    @patch('src.session_manager.Event')
    def test_update_session_state_creates_proper_event(self, mock_event, mock_event_actions, session_manager):
        """update_session_state가 올바른 이벤트를 생성하는지 테스트"""
        # Given
        session, session_id = session_manager.create_session()
        state_updates = {"test_key": "test_value"}
        
        # Mock 설정
        mock_event_actions_instance = MagicMock()
        mock_event.return_value = MagicMock()
        mock_event_actions.return_value = mock_event_actions_instance

        # When
        session_manager.update_session_state(state_updates)

        # Then
        # EventActions가 올바른 state_delta로 생성되었는지 확인
        mock_event_actions.assert_called_once_with(state_delta=state_updates)
        
        # Event가 올바른 파라미터로 생성되었는지 확인
        mock_event.assert_called_once_with(
            author=session_manager.app_name,
            actions=mock_event_actions_instance,
            content=None
        )

    def test_get_session_state_value_existing_key(self, session_manager):
        """존재하는 키로 세션 상태 값 조회 테스트"""
        # Given
        test_key = "test_key"
        test_value = "test_value"
        session, _ = session_manager.create_session(initial_state={test_key: test_value})

        # When
        value = session_manager.get_session_state_value(test_key)

        # Then
        assert value == test_value

    def test_get_session_state_value_nonexistent_key(self, session_manager):
        """존재하지 않는 키로 세션 상태 값 조회 테스트"""
        # Given
        session, _ = session_manager.create_session(initial_state={"some_key": "some_value"})
        nonexistent_key = "nonexistent_key"
        default_value = "default"

        # When
        value = session_manager.get_session_state_value(nonexistent_key, default=default_value)

        # Then
        assert value == default_value

    def test_get_session_state_value_no_session(self, session_manager):
        """세션이 없을 때 세션 상태 값 조회 테스트"""
        # Given
        session_manager.active_sessions = {}  # 활성 세션 비우기
        default_value = "default"

        # When
        value = session_manager.get_session_state_value("any_key", default=default_value)

        # Then
        assert value == default_value

    def test_start_new_idea_session_with_minimum_params(self, session_manager):
        """최소 파라미터로 아이디어 세션 시작 테스트"""
        # Given
        initial_idea = "Test idea"

        # When
        session, session_id = session_manager.start_new_idea_session(initial_idea)

        # Then
        assert session is not None
        assert session_id is not None
        assert session.state.get("initial_idea") == initial_idea
        assert session.state.get("current_phase") == "phase1"
        assert "user_goal" not in session.state
        assert "user_constraints" not in session.state
        assert "user_values" not in session.state
        assert session_manager.get_active_session_id() == session_id

    def test_start_new_idea_session_with_all_params(self, session_manager):
        """모든 파라미터로 아이디어 세션 시작 테스트"""
        # Given
        initial_idea = "Test idea"
        user_goal = "Test goal"
        user_constraints = "Test constraints"
        user_values = "Test values"

        # When
        session, session_id = session_manager.start_new_idea_session(
            initial_idea, user_goal, user_constraints, user_values
        )

        # Then
        assert session is not None
        assert session_id is not None
        assert session.state.get("initial_idea") == initial_idea
        assert session.state.get("current_phase") == "phase1"
        assert session.state.get("user_goal") == user_goal
        assert session.state.get("user_constraints") == user_constraints
        assert session.state.get("user_values") == user_values
        assert session_manager.get_active_session_id() == session_id

    def test_transition_to_phase2_success(self, session_manager):
        """Phase 2로 전환 성공 테스트"""
        # Given
        session, _ = session_manager.create_session(initial_state={"current_phase": "phase1"})

        # When
        result = session_manager.transition_to_phase2()

        # Then
        assert result is True
        updated_session = session_manager.get_session()
        assert updated_session.state.get("current_phase") == "phase2"
        assert "discussion_history_phase2" in updated_session.state
        assert isinstance(updated_session.state.get("discussion_history_phase2"), list)
        assert len(updated_session.state.get("discussion_history_phase2")) == 0

    def test_transition_to_phase2_no_active_session(self, session_manager):
        """활성 세션이 없을 때 Phase 2로 전환 실패 테스트"""
        # Given
        session_manager.active_sessions = {}  # 활성 세션 비우기

        # When
        result = session_manager.transition_to_phase2()

        # Then
        assert result is False

    @patch('src.session_manager.EventActions')
    @patch('src.session_manager.Event')
    def test_transition_to_phase2_creates_proper_event(self, mock_event, mock_event_actions, session_manager):
        """transition_to_phase2가 올바른 이벤트를 생성하는지 테스트"""
        # Given
        session, _ = session_manager.create_session(initial_state={"current_phase": "phase1"})
        expected_state_delta = {
            "current_phase": "phase2",
            "discussion_history_phase2": []
        }
        
        # Mock 설정
        mock_event_actions_instance = MagicMock()
        mock_event.return_value = MagicMock()
        mock_event_actions.return_value = mock_event_actions_instance

        # When
        session_manager.transition_to_phase2()

        # Then
        # EventActions가 올바른 state_delta로 생성되었는지 확인
        mock_event_actions.assert_called_once_with(state_delta=expected_state_delta)
        
        # Event가 올바른 파라미터로 생성되었는지 확인
        mock_event.assert_called_once_with(
            author="system_phase_manager",
            actions=mock_event_actions_instance
        ) 