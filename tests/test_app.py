import pytest
import asyncio
from unittest.mock import patch, MagicMock
# streamlit을 직접 임포트할 필요는 없지만, app.py가 임포트하므로 테스트 환경에 따라 필요할 수 있습니다.
# import streamlit as st
from src.ui.app import analyze_idea, APP_NAME, USER_ID # create_session 제거됨
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
        # st.session_state.get() 호출에 대한 반환값 설정
        def side_effect(key, default=None):
            if key == "user_goal":
                return "테스트 목표"
            elif key == "user_constraints":
                return "테스트 제약 조건"
            elif key == "user_values":
                return "테스트 가치"
            else:
                return default
            
        mock_session_state.get.side_effect = side_effect
        # 선택된 모델 세션 상태 설정
        mock_session_state.selected_model = "gemini-1.0-pro"
        # 추가 정보 필드 설정
        mock_session_state.user_goal = "테스트 목표"
        mock_session_state.user_constraints = "테스트 제약 조건"
        mock_session_state.user_values = "테스트 가치"
        yield mock_session_state

@pytest.fixture
def mock_session_manager():
    """SessionManager 클래스를 모킹하는 fixture"""
    with patch("src.ui.app.session_manager") as mock_manager:
        dummy_session = DummySession()
        session_id = "test_session_id"
        
        # SessionManager 메서드 모킹
        mock_manager.start_new_idea_session.return_value = (dummy_session, session_id)
        mock_manager.get_session.return_value = dummy_session
        mock_manager.session_service = MagicMock()
        
        yield mock_manager, dummy_session, session_id

@pytest.fixture
def mock_runner():
    """Runner 클래스를 모킹하는 fixture"""
    # app.py에서 Runner 클래스의 인스턴스를 생성하므로 클래스 자체를 모킹
    with patch("src.ui.app.Runner") as mock_runner_class:
        mock_runner_instance = mock_runner_class.return_value # Runner() 호출 시 반환될 모의 객체
        
        # 비동기 run_async 메서드 모킹
        async def mock_run_async(*args, **kwargs):
            mock_event = MagicMock()
            mock_event.is_final_response.return_value = True
            mock_event.content.parts = [MagicMock(text="모의 분석 결과입니다.")]
            yield mock_event
        
        mock_runner_instance.run_async = mock_run_async
        yield mock_runner_instance

@pytest.fixture
def mock_orchestrator():
    """AIdeaLabOrchestrator 클래스를 모킹하는 fixture"""
    with patch("src.ui.app.AIdeaLabOrchestrator") as mock_orchestrator_class:
        mock_orchestrator_instance = mock_orchestrator_class.return_value
        
        # 오케스트레이터의 메서드 모킹
        mock_workflow_agent = MagicMock()
        mock_orchestrator_instance.get_workflow_agent.return_value = mock_workflow_agent
        mock_orchestrator_instance.get_phase1_workflow.return_value = mock_workflow_agent
        mock_orchestrator_instance.get_output_keys_phase1.return_value = {
            "marketer": "marketer_report_phase1",
            "critic": "critic_report_phase1",
            "engineer": "engineer_report_phase1",
            "summary_phase1": "summary_report_phase1"
        }
        
        yield mock_orchestrator_class, mock_orchestrator_instance, mock_workflow_agent

@pytest.mark.asyncio
async def test_analyze_idea(mock_streamlit, mock_session_manager, mock_runner, mock_orchestrator):
    """아이디어 분석 함수 테스트"""
    mock_manager, dummy_session, session_id = mock_session_manager
    mock_orchestrator_class, mock_orchestrator_instance, mock_workflow_agent = mock_orchestrator
    
    # 세션 상태에 결과 설정 (각 페르소나 및 요약 결과)
    dummy_session.state = {
        "initial_idea": "테스트 아이디어",
        "marketer_report_phase1": "마케터 분석 결과",
        "critic_report_phase1": "비평가 분석 결과",
        "engineer_report_phase1": "엔지니어 분석 결과",
        "summary_report_phase1": "최종 요약 결과"
    }

    # analyze_idea 비동기 함수 호출
    results = await analyze_idea("테스트 아이디어")

    # 검증
    # 1. SessionManager.start_new_idea_session이 올바른 파라미터로 호출되었는지 확인
    mock_manager.start_new_idea_session.assert_called_once_with(
        initial_idea="테스트 아이디어",
        user_goal="테스트 목표",
        user_constraints="테스트 제약 조건",
        user_values="테스트 가치"
    )
    
    # 2. AIdeaLabOrchestrator가 올바른 model_name으로 생성되었는지 확인
    mock_orchestrator_class.assert_called_once_with(model_name=mock_streamlit.selected_model)
    
    # 3. 워크플로우 에이전트를 가져오는 메서드가 호출되었는지 확인
    mock_orchestrator_instance.get_workflow_agent.assert_called_once()
    
    # 4. Runner가 올바른 워크플로우 에이전트로 생성되었는지 확인
    from src.ui.app import Runner
    Runner.assert_called_once_with(
        agent=mock_workflow_agent,
        app_name=APP_NAME,
        session_service=mock_manager.session_service
    )
    
    # 5. 결과 딕셔너리에 모든 페르소나의 결과와 요약이 포함되어 있는지 확인
    assert "marketer" in results
    assert "critic" in results
    assert "engineer" in results
    assert "summary_phase1" in results
    assert results["marketer"] == "마케터 분석 결과"
    assert results["critic"] == "비평가 분석 결과"
    assert results["engineer"] == "엔지니어 분석 결과"
    assert results["summary_phase1"] == "최종 요약 결과"

@pytest.mark.asyncio
async def test_run_phase1_analysis_and_update_ui(mock_streamlit, mock_session_manager, mock_runner, mock_orchestrator):
    """1단계 분석 및 UI 업데이트 함수 테스트"""
    from src.ui.app import run_phase1_analysis_and_update_ui
    
    mock_manager, dummy_session, session_id = mock_session_manager
    mock_orchestrator_class, mock_orchestrator_instance, mock_workflow_agent = mock_orchestrator
    
    # 세션 상태에 결과 설정 (각 페르소나 및 요약 결과)
    dummy_session.state = {
        "initial_idea": "테스트 아이디어",
        "marketer_report_phase1": "마케터 분석 결과",
        "critic_report_phase1": "비평가 분석 결과",
        "engineer_report_phase1": "엔지니어 분석 결과",
        "summary_report_phase1": "최종 요약 결과"
    }
    
    # run_phase1_analysis_and_update_ui가 streamlit 상태를 변경하는 것을 가로채기 위해 
    # 비동기 함수 호출 후 예외를 던져 중단시킴 (단순 테스트 목적)
    with patch("src.ui.app.show_system_message") as mock_show_message:
        # 첫 번째 호출 시 에러 발생이 아닌 None 반환하도록 설정
        mock_show_message.side_effect = lambda *args, **kwargs: None
        
        # st.session_state.adk_session_id 설정 부분을 패치
        with patch.object(mock_streamlit, '__setitem__') as mock_setitem:
            try:
                # 함수 호출
                await run_phase1_analysis_and_update_ui("테스트 아이디어")
            except Exception:
                # 예외 발생 시 무시 - 테스트에서는 실제 UI 업데이트를 할 수 없으므로
                pass
    
    # 검증
    # 1. SessionManager.start_new_idea_session이 올바른 파라미터로 호출되었는지 확인
    mock_manager.start_new_idea_session.assert_called_once_with(
        initial_idea="테스트 아이디어",
        user_goal="테스트 목표",
        user_constraints="테스트 제약 조건",
        user_values="테스트 가치"
    )
    
    # 2. AIdeaLabOrchestrator가 올바른 model_name으로 생성되었는지 확인
    mock_orchestrator_class.assert_called_once_with(model_name=mock_streamlit.selected_model)
    
    # 3. Phase 1 워크플로우 에이전트를 가져오는 메서드가 호출되었는지 확인
    mock_orchestrator_instance.get_phase1_workflow.assert_called_once()

# if __name__ == "__main__": # 테스트 파일에서 이 부분은 일반적으로 제거합니다.
#     pytest.main(["-v", __file__])