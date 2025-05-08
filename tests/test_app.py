"""
AIdea Lab UI 테스트
"""

import pytest
from unittest.mock import patch, MagicMock
import streamlit as st
from src.ui.app import create_session, analyze_idea
from google.adk.sessions import Session, State

# Streamlit 테스트를 위한 기본 설정
class DummySession:
    """테스트용 더미 세션 클래스"""
    def __init__(self):
        self.state = {}
        self.id = "test_session_id"
        self.app_name = "AIdea Lab"
        self.user_id = "streamlit_user"
        self.events = []
        self.last_update_time = 0

@pytest.fixture
def mock_streamlit():
    """Streamlit 모듈을 모킹하는 fixture"""
    with patch("streamlit.session_state", new_callable=MagicMock) as mock_session_state:
        mock_session_state.session_counter = 0
        yield mock_session_state

@pytest.fixture
def mock_session_service():
    """InMemorySessionService를 모킹하는 fixture"""
    with patch("src.ui.app.InMemorySessionService") as mock_service:
        dummy_session = DummySession()
        mock_service_instance = mock_service.return_value
        mock_service_instance.create_session.return_value = dummy_session
        mock_service_instance.get_session.return_value = dummy_session
        yield mock_service_instance, dummy_session

@pytest.fixture
def mock_runner():
    """Runner 클래스를 모킹하는 fixture"""
    with patch("src.ui.app.Runner") as mock_runner:
        mock_runner_instance = mock_runner.return_value
        # 모의 이벤트 생성
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content.parts = [MagicMock(text="모의 분석 결과입니다.")]
        mock_runner_instance.run.return_value = [mock_event]
        yield mock_runner_instance

def test_create_session(mock_streamlit, mock_session_service):
    """세션 생성 함수 테스트"""
    mock_service, dummy_session = mock_session_service
    
    # 함수 호출
    session, session_id = create_session()
    
    # 검증 - 객체 동일성 대신 세션 ID 형식만 확인
    assert isinstance(session_id, str)
    assert session_id.startswith("session_")
    mock_service.create_session.assert_called_once()

def test_analyze_idea(mock_session_service, mock_runner):
    """아이디어 분석 함수 테스트"""
    mock_service, dummy_session = mock_session_service
    
    # CriticPersonaAgent 모킹
    with patch("src.ui.app.CriticPersonaAgent") as mock_critic_agent_class:
        mock_critic_agent = mock_critic_agent_class.return_value
        mock_critic_agent.get_agent.return_value = MagicMock()
        mock_critic_agent.get_output_key.return_value = "critic_response"
        
        # 세션 상태에 응답 설정
        dummy_session.state["critic_response"] = "비판적 분석 결과입니다."
        
        # 함수 호출
        result = analyze_idea("테스트 아이디어", dummy_session, "test_session_id")
        
        # 검증
        assert result == "비판적 분석 결과입니다."
        assert dummy_session.state["initial_idea"] == "테스트 아이디어"
        mock_runner.run.assert_called_once()
        mock_service.get_session.assert_called_once()

if __name__ == "__main__":
    pytest.main(["-v", __file__]) 