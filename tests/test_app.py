import pytest
import asyncio
from unittest.mock import patch, MagicMock
# streamlit을 직접 임포트할 필요는 없지만, app.py가 임포트하므로 테스트 환경에 따라 필요할 수 있습니다.
# import streamlit as st
from src.ui.app import create_session, analyze_idea, APP_NAME, USER_ID # app.py의 전역변수 임포트
from google.adk.sessions import Session # Session 사용되지 않으면 제거 가능
# from google.adk.sessions import State # State 사용되지 않으면 제거 가능

class DummySession:
    """테스트용 더미 세션 클래스"""
    def __init__(self):
        self.state = {}
        self.id = "test_session_id"
        self.app_name = "AIdea Lab"
        self.user_id = "streamlit_user"
        self.events = [] # 테스트에 따라 필요 없을 수 있음
        self.last_update_time = 0 # 테스트에 따라 필요 없을 수 있음

@pytest.fixture
def mock_streamlit():
    """Streamlit 모듈을 모킹하는 fixture"""
    # app.py에서 st.session_state를 사용하므로 이를 모킹합니다.
    with patch("streamlit.session_state", new_callable=MagicMock) as mock_session_state:
        mock_session_state.session_counter = 0
        # st.session_state.get('session_counter', 0)을 모킹
        mock_session_state.get.return_value = 0
        # 선택된 모델 세션 상태 설정
        mock_session_state.selected_model = "gemini-1.0-pro"
        yield mock_session_state

@pytest.fixture
def mock_app_session_service(): # 픽스처 이름 명확화
    """src.ui.app.session_service 인스턴스를 모킹하는 fixture"""
    # app.py 내의 전역 변수 session_service를 모킹
    with patch("src.ui.app.session_service") as mock_service_instance:
        dummy_session = DummySession()
        mock_service_instance.create_session.return_value = dummy_session
        mock_service_instance.get_session.return_value = dummy_session
        yield mock_service_instance, dummy_session

@pytest.fixture
def mock_runner():
    """Runner 클래스를 모킹하는 fixture"""
    # app.py에서 Runner 클래스의 인스턴스를 생성하므로 클래스 자체를 모킹
    with patch("src.ui.app.Runner") as mock_runner_class:
        mock_runner_instance = mock_runner_class.return_value # Runner() 호출 시 반환될 모의 객체
        mock_event = MagicMock()
        mock_event.is_final_response.return_value = True
        mock_event.content.parts = [MagicMock(text="모의 분석 결과입니다.")]
        mock_runner_instance.run.return_value = [mock_event]
        yield mock_runner_instance

@pytest.fixture
def mock_orchestrator():
    """AIdeaLabOrchestrator 클래스를 모킹하는 fixture"""
    with patch("src.ui.app.AIdeaLabOrchestrator") as mock_orchestrator_class:
        mock_orchestrator_instance = mock_orchestrator_class.return_value
        
        # 오케스트레이터의 메서드 모킹
        mock_workflow_agent = MagicMock()
        mock_orchestrator_instance.get_workflow_agent.return_value = mock_workflow_agent
        mock_orchestrator_instance.get_output_keys.return_value = {
            "marketer": "marketer_response",
            "critic": "critic_response",
            "engineer": "engineer_response",
            "summary": "final_summary"
        }
        
        yield mock_orchestrator_class, mock_orchestrator_instance, mock_workflow_agent

def test_create_session(mock_streamlit, mock_app_session_service): # 수정된 픽스처 이름 사용
    """세션 생성 함수 테스트"""
    mock_service, dummy_session_obj = mock_app_session_service

    # 함수 호출
    returned_session, returned_session_id = create_session() # app.py의 create_session 호출

    # 검증
    assert isinstance(returned_session_id, str)
    assert returned_session_id.startswith("session_")
    # 모킹된 app.session_service의 create_session 메소드가 호출되었는지 확인
    mock_service.create_session.assert_called_once_with(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id="session_0" # mock_streamlit의 get 반환값이 0이므로
    )
    assert returned_session == dummy_session_obj

@pytest.mark.asyncio
async def test_analyze_idea(mock_streamlit, mock_app_session_service, mock_runner, mock_orchestrator): # 수정된 픽스처 이름 사용
    """아이디어 분석 함수 테스트"""
    mock_service, dummy_session = mock_app_session_service
    mock_orchestrator_class, mock_orchestrator_instance, mock_workflow_agent = mock_orchestrator
    
    # 세션 상태에 결과 설정 (각 페르소나 및 요약 결과)
    dummy_session.state = {
        "initial_idea": "테스트 아이디어",
        "marketer_response": "마케터 분석 결과",
        "critic_response": "비평가 분석 결과",
        "engineer_response": "엔지니어 분석 결과",
        "final_summary": "최종 요약 결과"
    }

    # analyze_idea 비동기 함수 호출
    results = await analyze_idea("테스트 아이디어", dummy_session, "test_session_id")

    # 검증
    # 1. AIdeaLabOrchestrator가 올바른 model_name으로 생성되었는지 확인
    mock_orchestrator_class.assert_called_once_with(model_name=mock_streamlit.selected_model)
    
    # 2. 워크플로우 에이전트를 가져오는 get_workflow_agent 메서드가 호출되었는지 확인
    mock_orchestrator_instance.get_workflow_agent.assert_called_once()
    
    # 3. Runner가 올바른 워크플로우 에이전트로 생성되었는지 확인
    from src.ui.app import Runner
    Runner.assert_called_once_with(
        agent=mock_workflow_agent,
        app_name="AIdea Lab",
        session_service=mock_service
    )
    
    # 4. 결과 딕셔너리에 모든 페르소나의 결과와 요약이 포함되어 있는지 확인
    assert "marketer" in results
    assert "critic" in results
    assert "engineer" in results
    assert "summary" in results
    assert results["marketer"] == "마케터 분석 결과"
    assert results["critic"] == "비평가 분석 결과"
    assert results["engineer"] == "엔지니어 분석 결과"
    assert results["summary"] == "최종 요약 결과"

# if __name__ == "__main__": # 테스트 파일에서 이 부분은 일반적으로 제거합니다.
#     pytest.main(["-v", __file__])