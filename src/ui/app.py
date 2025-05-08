"""
AIdea Lab - 아이디어 분석 워크숍 UI

이 모듈은 Streamlit을 이용한 기본 사용자 인터페이스를 제공합니다.
사용자는 아이디어를 입력하고 분석을 요청할 수 있습니다.
"""

import os
import streamlit as st
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from src.agents.critic_agent import CriticPersonaAgent

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit 페이지 설정
st.set_page_config(
    page_title="AIdea Lab - 아이디어 분석 워크숍",
    page_icon="🧠",
    layout="wide"
)

# 앱 정보
APP_NAME = "AIdea Lab"
USER_ID = "streamlit_user"

# 세션 서비스 초기화
session_service = InMemorySessionService()

def create_session():
    """새로운 세션 생성"""
    session_id = f"session_{st.session_state.get('session_counter', 0)}"
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    return session, session_id

def analyze_idea(idea_text, session, session_id):
    """
    사용자 아이디어를 분석하는 함수
    
    Args:
        idea_text (str): 사용자가 입력한 아이디어 텍스트
        session: 현재 세션 객체
        session_id (str): 세션 ID
        
    Returns:
        str: 분석 결과 텍스트
    """
    # 페르소나 에이전트 생성
    critic_agent = CriticPersonaAgent()
    
    # 세션 상태에 아이디어 저장
    session.state["initial_idea"] = idea_text
    
    # Runner 생성
    runner = Runner(
        agent=critic_agent.get_agent(),
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # 입력 메시지 생성
    content = types.Content(
        role="user",
        parts=[types.Part(text=f"다음 아이디어를 분석해주세요: {idea_text}")]
    )
    
    # Runner를 통해 에이전트 실행
    events = runner.run(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content
    )
    
    # 응답 처리
    response_text = None
    for event in events:
        if event.is_final_response() and event.content and event.content.parts:
            response_text = event.content.parts[0].text
            break
    
    # 세션 상태에서 응답 확인
    updated_session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    
    # 세션에 저장된 응답 또는 직접 받은 응답 반환
    output_key = critic_agent.get_output_key()
    if updated_session and hasattr(updated_session, 'state'):
        return updated_session.state.get(output_key, response_text)
    return response_text

def main():
    """메인 애플리케이션 함수"""
    st.title("🧠 AIdea Lab - 아이디어 분석 워크숍")
    
    # 세션 스테이트 초기화
    if 'session_counter' not in st.session_state:
        st.session_state.session_counter = 0
    
    if 'analysis_result' not in st.session_state:
        st.session_state.analysis_result = None
    
    st.markdown("""
    ### 💡 아이디어 분석 서비스
    자유롭게 아이디어를 입력하시면, AI 페르소나가 다양한 관점에서 분석해드립니다.
    """)
    
    # 아이디어 입력 영역
    idea_text = st.text_area(
        "아이디어를 입력해주세요:",
        height=150,
        placeholder="예: 수면 중 꿈을 기록하고 분석해주는 웨어러블 기기"
    )
    
    # 분석 요청 버튼
    if st.button("아이디어 분석 요청"):
        if not idea_text:
            st.error("아이디어를 입력해주세요!")
        else:
            # API 키 확인
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key or api_key == "YOUR_API_KEY":
                st.error("GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일에 API 키를 설정해주세요.")
            else:
                # 새 세션 생성
                session, session_id = create_session()
                st.session_state.session_counter += 1
                
                # 로딩 상태 표시
                with st.spinner("AI 페르소나가 아이디어를 분석 중입니다..."):
                    try:
                        # 아이디어 분석 실행
                        analysis_result = analyze_idea(idea_text, session, session_id)
                        st.session_state.analysis_result = analysis_result
                    except Exception as e:
                        st.error(f"분석 중 오류가 발생했습니다: {str(e)}")
    
    # 분석 결과 표시
    if st.session_state.analysis_result:
        st.markdown("### 🔍 비판적 분석가의 분석 결과")
        st.markdown(st.session_state.analysis_result)

if __name__ == "__main__":
    main() 