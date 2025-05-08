import pytest
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

def test_analyze_idea(mock_app_session_service, mock_runner): # 수정된 픽스처 이름 사용
    """아이디어 분석 함수 테스트"""
    mock_service, dummy_session = mock_app_session_service

    with patch("src.ui.app.CriticPersonaAgent") as mock_critic_agent_class:
        mock_critic_agent_instance = mock_critic_agent_class.return_value
        mock_critic_agent_instance.get_agent.return_value = MagicMock()
        mock_critic_agent_instance.get_output_key.return_value = "critic_response"

        # dummy_session.state는 초기에 비어있으므로,
        # updated_session.state.get("critic_response", response_text)는
        # response_text ("모의 분석 결과입니다.")를 반환할 것입니다.
        # 따라서 dummy_session.state를 미리 설정할 필요가 없습니다.

        # analyze_idea에 전달되는 session 인자는 dummy_session입니다.
        # analyze_idea 내부에서 session_service.get_session() 호출 시에도
        # mock_app_session_service에 의해 동일한 dummy_session이 반환됩니다.
        result = analyze_idea("테스트 아이디어", dummy_session, "test_session_id")

        # 검증
        assert result == "모의 분석 결과입니다." # Runner가 세션 상태를 업데이트하지 않으므로, LLM 이벤트의 텍스트가 반환됨
        assert dummy_session.state["initial_idea"] == "테스트 아이디어" # 이 부분은 analyze_idea가 직접 설정
        mock_runner.run.assert_called_once()
        mock_service.get_session.assert_called_once_with(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id="test_session_id"
        )

# if __name__ == "__main__": # 테스트 파일에서 이 부분은 일반적으로 제거합니다.
#     pytest.main(["-v", __file__])