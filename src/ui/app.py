"""
AIdea Lab - 아이디어 분석 워크숍 UI

이 모듈은 Streamlit을 이용한 챗봇 인터페이스를 제공합니다.
사용자는 아이디어를 입력하고 AI 페르소나들의 분석 결과를 챗봇 형태로 볼 수 있습니다.
"""

import os
import sys
import asyncio
import streamlit as st
from dotenv import load_dotenv
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.orchestrator.main_orchestrator import AIdeaLabOrchestrator
from src.session_manager import SessionManager  # 새로 추가된 SessionManager import
from config.personas import PERSONA_CONFIGS, PersonaType, ORCHESTRATOR_CONFIG, PERSONA_SEQUENCE
from config.models import get_model_display_options, MODEL_CONFIGS, ModelType, DEFAULT_MODEL

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit 페이지 설정
st.set_page_config(
    page_title="AIdea Lab - 아이디어 분석 워크숍",
    page_icon="🧠",
    layout="centered"  # 챗봇 UI에 적합한 centered 레이아웃
)

# 앱 정보
APP_NAME = "AIdea Lab"
USER_ID = "streamlit_user"

# 세션 관리자 초기화
session_manager = SessionManager(APP_NAME, USER_ID)

# 시스템 안내 메시지 템플릿 정의
SYSTEM_MESSAGES = {
    "welcome": "👋 안녕하세요! AIdea Lab 아이디어 분석 워크숍에 오신 것을 환영합니다. 자유롭게 아이디어를 입력해주세요.",
    "analysis_start": "🚀 아이디어 분석을 시작합니다. 1단계에서는 3가지 다른 관점의 페르소나가 순차적으로 아이디어를 분석합니다.",
    "marketer_intro": "💡 먼저, 창의적 마케터가 아이디어의 매력적인 가치와 시장 잠재력을 분석합니다.",
    "critic_intro": "🔍 다음은 비판적 분석가가 아이디어의 잠재적 문제점과 리스크를 검토합니다.",
    "engineer_intro": "⚙️ 이제 현실적 엔지니어가 아이디어의 기술적 실현 가능성을 평가합니다.",
    "summary_intro": "📝 모든 페르소나의 의견을 종합하여 최종 요약을 생성합니다.",
    "phase1_complete": "✅ 모든 페르소나의 1단계 분석이 완료되었습니다. 이 분석 결과를 바탕으로 아이디어를 더욱 발전시키는 2단계 토론을 진행하시겠습니까?",
    "phase2_intro": "🔄 2단계 아이디어 발전 토론을 시작합니다. 토론 촉진자가 페르소나들 간의 토론을 진행합니다.",
    "analysis_end": "🏁 분석을 종료합니다. 새로운 아이디어가 있다면 언제든지 다시 찾아주세요!",
}

# 텍스트 데이터를 표시용으로 처리하는 함수
def process_text_for_display(text_data):
    """
    텍스트 데이터를 표시용으로 처리하는 함수
    
    Args:
        text_data: 처리할 텍스트 또는 데이터
        
    Returns:
        처리된 텍스트
    """
    # 텍스트 데이터가 문자열이 아닌 경우 문자열로 변환
    if not isinstance(text_data, str):
        text_data = str(text_data)
    
    return text_data

def add_message(role, content, avatar=None):
    """
    메시지를 세션 상태에 추가하는 통합 함수 (UI에 직접 표시하지 않음)
    
    Args:
        role (str): 메시지 역할 ('user', 'assistant')
        content (str): 메시지 내용
        avatar (str, optional): 아바타 이모지
    """
    # 중복 메시지 방지
    if any(msg.get("role") == role and msg.get("content") == content for msg in st.session_state.messages):
        return
        
    # 메시지 세션 상태에 추가
    st.session_state.messages.append({
        "role": role,
        "content": content,
        "avatar": avatar
    })

def show_system_message(message_key):
    """시스템 안내 메시지를 세션 상태에 추가합니다 (UI에 직접 표시하지 않음)"""
    if message_key in SYSTEM_MESSAGES:
        message_content = SYSTEM_MESSAGES[message_key]
        add_message("assistant", message_content, avatar="⚙️")

# 1단계 분석을 위한 함수
def run_phase1_analysis_and_update_ui(idea_text):
    """1단계 분석을 실행하고 결과를 저장합니다."""
    try:
        # 분석 상태 설정
        st.session_state.analysis_phase = "phase1_running"
        st.session_state.phase1_step = "analysis_started"
        
        # 분석 시작 메시지 저장 (UI에 즉시 표시하지 않음)
        show_system_message("analysis_start")

        # 사용자 추가 정보 가져오기
        user_goal = st.session_state.get("user_goal", "")
        user_constraints = st.session_state.get("user_constraints", "")
        user_values = st.session_state.get("user_values", "")
        
        # 세션 관리자를 통해 새 세션 시작
        session, session_id = session_manager.start_new_idea_session(
            initial_idea=idea_text,
            user_goal=user_goal,
            user_constraints=user_constraints,
            user_values=user_values
        )
        
        # Streamlit 세션 상태에 ADK 세션 ID 저장
        st.session_state.adk_session_id = session_id
        
        # 오케스트레이터 생성
        orchestrator = AIdeaLabOrchestrator(model_name=st.session_state.selected_model)
        
        # 1단계 워크플로우 에이전트 가져오기
        phase1_workflow_agent = orchestrator.get_phase1_workflow()
        
        # Runner 생성
        runner = Runner(
            agent=phase1_workflow_agent,
            app_name=APP_NAME,
            session_service=session_manager.session_service
        )

        # Runner 실행을 위한 초기 메시지
        initial_content_for_runner = types.Content(
            role="user", 
            parts=[types.Part(text=f"다음 아이디어에 대한 1단계 분석을 시작합니다: {idea_text}")]
        )

        # Runner 실행 (동기 방식으로 변경)
        asyncio.run(_run_phase1_analysis(runner, USER_ID, session_id, initial_content_for_runner, phase1_workflow_agent))
        
        # 최신 세션 상태 가져오기
        current_session = session_manager.get_session(session_id)
        if not current_session:
            raise Exception("세션을 찾을 수 없습니다.")
        
        # 1단계 output 키 맵 가져오기
        output_keys = orchestrator.get_output_keys_phase1()
        
        # 모든 페르소나 결과를 한 번에 저장하여 UI 업데이트 최소화
        all_results_collected = []
        
        # 페르소나 순서에 맞게 결과 저장
        for persona_type in PERSONA_SEQUENCE:
            if persona_type == PersonaType.MARKETER:
                persona_key = "marketer"
            elif persona_type == PersonaType.CRITIC:
                persona_key = "critic"
            elif persona_type == PersonaType.ENGINEER:
                persona_key = "engineer"
            else:
                continue
                
            # 해당 페르소나의 output_key 가져오기
            output_key = output_keys.get(persona_key)
            if not output_key or output_key not in current_session.state:
                # 디버깅을 위한 로그
                print(f"Warning: {persona_key}의 결과를 찾을 수 없습니다. 키: {output_key}")
                continue
                
            # 페르소나 소개 메시지 및 분석 결과를 수집
            intro_message_key = f"{persona_key}_intro"
            persona_response = current_session.state.get(output_key)
            
            if persona_response:
                # 페르소나 아이콘 가져오기
                if persona_key == "marketer":
                    avatar_icon = PERSONA_CONFIGS[PersonaType.MARKETER].get("icon", "💡")
                elif persona_key == "critic":
                    avatar_icon = PERSONA_CONFIGS[PersonaType.CRITIC].get("icon", "🔍")
                elif persona_key == "engineer":
                    avatar_icon = PERSONA_CONFIGS[PersonaType.ENGINEER].get("icon", "⚙️")
                else:
                    avatar_icon = "🤖"
                
                # 소개 메시지와 결과를 수집 (아직 session_state에 추가하지 않음)
                all_results_collected.append({
                    "intro_key": intro_message_key,
                    "content": process_text_for_display(persona_response),
                    "avatar": avatar_icon
                })
        
        # 최종 요약 결과 수집
        summary_key = output_keys.get("summary_phase1")
        summary_result = None
        if summary_key and summary_key in current_session.state:
            summary_response = current_session.state.get(summary_key)
            if summary_response:
                summary_icon = ORCHESTRATOR_CONFIG.get("icon", "📝")
                summary_result = {
                    "intro_key": "summary_intro",
                    "content": process_text_for_display(summary_response),
                    "avatar": summary_icon
                }
        
        # 이제 모든 결과를 세션 상태에 한 번에 추가 (UI 갱신 최소화)
        for result in all_results_collected:
            # 먼저 소개 메시지 추가
            show_system_message(result["intro_key"])
            # 그 다음 분석 결과 추가
            add_message("assistant", result["content"], avatar=result["avatar"])
        
        # 최종 요약 결과 추가
        if summary_result:
            show_system_message(summary_result["intro_key"])
            add_message("assistant", summary_result["content"], avatar=summary_result["avatar"])
        
        # 1단계 분석 완료 처리
        st.session_state.analysis_phase = "phase1_complete"
        st.session_state.phase1_step = "complete"
        st.session_state.analyzed_idea = idea_text  # 분석 완료된 아이디어 기록
        
        # 1단계 완료 메시지 저장
        show_system_message("phase1_complete")
        
        # 분석 완료 표시 (단 한 번만 UI 업데이트 트리거)
        st.session_state.need_rerun = True

    except Exception as e:
        error_message = f"분석 중 오류가 발생했습니다: {str(e)}"
        
        # 오류 메시지 저장
        add_message("assistant", error_message, avatar="⚠️")
        
        # 디버깅용 로그
        print(f"Error in run_phase1_analysis_and_update_ui: {str(e)}")
        
        st.session_state.analysis_phase = "error"
        st.session_state.phase1_step = "error"
        st.session_state.need_rerun = True

# SequentialAgent 실행 및 결과 기다리는 비동기 함수
async def _run_phase1_analysis(runner, user_id, session_id, initial_content, phase1_workflow_agent):
    """SequentialAgent를 실행하고 완료될 때까지 기다립니다."""
    
    # Runner 실행 및 최종 결과 기다리기
    event_stream = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=initial_content
    )
    
    # SequentialAgent 전체 실행이 완료될 때까지 기다림
    # 중간 스트리밍 결과를 건너뛰고 최종 결과만 기다림 (스크롤 문제 해결)
    async for event in event_stream:
        # SequentialAgent의 최종 완료 이벤트 확인
        if event.is_final_response() and hasattr(event, 'agent_name') and event.agent_name == phase1_workflow_agent.name:
            # SequentialAgent의 실행이 완료됨
            print(f"SequentialAgent completed: {phase1_workflow_agent.name}")
            break

def initialize_session_state():
    """세션 상태 초기화"""
    if 'session_counter' not in st.session_state:
        st.session_state.session_counter = 0
    
    # 선택된 모델 세션 상태 초기화
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL.value
    
    # 채팅 관련 세션 상태 초기화
    if 'messages' not in st.session_state:
        st.session_state.messages = [] # {"role": "user/assistant/system", "content": "...", "avatar": "🧑‍💻/🧠/⚙️"}
        # 초기 환영 메시지 추가 (메시지 초기화 시 한 번만 추가)
        add_message("assistant", SYSTEM_MESSAGES["welcome"], avatar="⚙️")
    
    # 아이디어 및 분석 상태
    if 'current_idea' not in st.session_state: # 사용자가 현재 입력한 아이디어 (분석 전)
        st.session_state.current_idea = ""
    if 'analyzed_idea' not in st.session_state: # 분석이 완료된 아이디어 (중복 실행 방지용)
        st.session_state.analyzed_idea = ""
    if 'analysis_phase' not in st.session_state: # "idle", "phase1_running", "phase1_complete", "phase2_running", ...
        st.session_state.analysis_phase = "idle"
    if 'phase1_step' not in st.session_state: # 1단계 분석의 세부 상태 ("awaiting_idea", "idea_submitted", "analysis_started", ...)
        st.session_state.phase1_step = "awaiting_idea"
    if 'adk_session_id' not in st.session_state:
        st.session_state.adk_session_id = None
    if 'user_goal' not in st.session_state: # 사용자 추가 정보
        st.session_state.user_goal = ""
    if 'user_constraints' not in st.session_state: # 사용자 제약 조건
        st.session_state.user_constraints = ""
    if 'user_values' not in st.session_state: # 사용자 중요 가치
        st.session_state.user_values = ""
    if 'show_additional_info' not in st.session_state: # 추가 정보 입력 필드 표시 여부
        st.session_state.show_additional_info = False
    if 'need_rerun' not in st.session_state: # rerun 필요 여부 플래그
        st.session_state.need_rerun = False

def update_setting(key, value):
    """
    설정을 업데이트하는 함수
    
    Args:
        key (str): 업데이트할 설정 키
        value: 설정할 값
    """
    # 설정 업데이트
    setattr(st.session_state, key, value)

def main():
    """메인 애플리케이션 함수"""
    st.title("🧠 AIdea Lab - 아이디어 분석 워크숍")
    
    initialize_session_state()
    
    # 설명 텍스트와 고급 설정을 포함할 사이드 영역 컨테이너
    side_content = st.container()
    
    # 채팅 메시지를 표시할 전용 컨테이너 (명확한 채팅 영역 생성)
    chat_area = st.container()
    
    # 먼저 사이드 콘텐츠 표시
    with side_content:
        # 분석 상태에 따른 설명 텍스트
        if st.session_state.analysis_phase == "idle": # 초기 상태 또는 이전 분석 완료 후
            st.markdown("""
            ### 💡 아이디어 분석 서비스
            자유롭게 아이디어를 입력하시면, 다양한 AI 페르소나가 여러 관점에서 분석해드리고 최종 정리까지 해드립니다.
            """)
        
        # 고급 설정 expander (Streamlit이 자체적으로 상태 관리하도록 함)
        with st.expander("⚙️ 고급 설정"):
            model_options = get_model_display_options()
            
            st.selectbox(
                "AI 모델 선택:",
                options=list(model_options.keys()),
                format_func=lambda x: x,
                index=list(model_options.values()).index(st.session_state.selected_model),
                key="model_display_name_selectbox",
                on_change=lambda: update_setting('selected_model', model_options[st.session_state.model_display_name_selectbox])
            )
            
            current_model_type = next((mt for mt in ModelType if mt.value == st.session_state.selected_model), None)
            if current_model_type:
                st.info(f"선택된 모델: {MODEL_CONFIGS[current_model_type]['description']}")
            
            # 추가 정보 입력 표시 토글
            st.checkbox(
                "아이디어에 대한 추가 정보 입력", 
                value=st.session_state.show_additional_info, 
                key="show_additional_info_checkbox", 
                on_change=lambda: update_setting('show_additional_info', st.session_state.show_additional_info_checkbox)
            )
            
            # 추가 정보 입력 필드 (체크박스 선택 시에만 표시)
            if st.session_state.show_additional_info:
                st.text_input(
                    "아이디어의 핵심 목표:", 
                    key="user_goal_input", 
                    value=st.session_state.user_goal, 
                    on_change=lambda: update_setting('user_goal', st.session_state.user_goal_input),
                    help="아이디어를 통해 달성하고자 하는 주요 목표를 입력해주세요."
                )
                
                st.text_input(
                    "주요 제약 조건:", 
                    key="user_constraints_input", 
                    value=st.session_state.user_constraints, 
                    on_change=lambda: update_setting('user_constraints', st.session_state.user_constraints_input),
                    help="아이디어 구현 시 고려해야 할 주요 제약 조건이나 한계를 입력해주세요."
                )
                
                st.text_input(
                    "중요 가치:", 
                    key="user_values_input", 
                    value=st.session_state.user_values, 
                    on_change=lambda: update_setting('user_values', st.session_state.user_values_input),
                    help="이 아이디어가 중요하게 여기는 핵심 가치나 원칙을 입력해주세요."
                )
    
    # 이제 채팅 영역 표시 (명확하게 구분된 영역)
    with chat_area:
        # 모든 메시지를 채팅 형식으로 표시 (추가 스타일링 없이 기본 Streamlit 채팅 UI 사용)
        for message in st.session_state.messages:
            role = message.get("role", "assistant")
            content = message.get("content", "")
            avatar = message.get("avatar")
            
            # 기본 아바타 처리
            if not avatar and role == "assistant":
                avatar = "🧠"
            
            # 명시적으로 Streamlit 채팅 UI 요소 사용
            with st.chat_message(role, avatar=avatar):
                st.write(content)  # st.markdown 대신 st.write 사용
    
    # --- 1단계 분석 완료 후 2단계 진행 버튼 ---
    if st.session_state.analysis_phase == "phase1_complete":
        # 2단계 진행 버튼
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 2단계 토론 시작하기", key="start_phase2_button"):
                # 세션 관리자를 사용하여 Phase 2로 전환
                if st.session_state.adk_session_id:
                    session_manager.set_active_session_id(st.session_state.adk_session_id)
                    success = session_manager.transition_to_phase2()
                    if success:
                        st.session_state.analysis_phase = "phase2_pending" 
                        # 2단계 시작 안내 메시지 추가
                        add_message("assistant", SYSTEM_MESSAGES["phase2_intro"], avatar="⚙️")
                        st.session_state.need_rerun = True
                    else:
                        # 오류 메시지 추가
                        add_message("assistant", "2단계 전환에 실패했습니다. 세션을 찾을 수 없습니다.", avatar="⚠️")
                        st.session_state.need_rerun = True
                else:
                    # 오류 메시지 추가
                    add_message("assistant", "유효한 세션을 찾을 수 없습니다.", avatar="⚠️")
                    st.session_state.need_rerun = True
        with col2:
            if st.button("🏁 여기서 분석 종료하기", key="end_analysis_button"):
                st.session_state.analysis_phase = "idle" # 초기 상태로 복귀
                # 종료 메시지 추가
                add_message("assistant", SYSTEM_MESSAGES["analysis_end"], avatar="⚙️")
                # 필요시 현재 세션 초기화 또는 새 세션 준비
                st.session_state.current_idea = "" 
                st.session_state.analyzed_idea = ""
                st.session_state.need_rerun = True
    
    # --- 이전 상태에 따른 조건부 처리 ---
    # 분석 시작 상태일 때만 스피너와 함께 분석 함수 실행, 스크롤링 문제 최소화
    if st.session_state.phase1_step == "analysis_pending" and st.session_state.analysis_phase == "phase1_pending_start":
        with st.spinner("AI 페르소나들이 아이디어를 분석 중입니다... 잠시만 기다려주세요 ✨"):
            # 분석 시작 준비가 된 상태에서 분석 함수 실행
            # 이 함수 내에서 UI 업데이트를 최소화하도록 수정됨
            run_phase1_analysis_and_update_ui(st.session_state.current_idea)
    
    # --- 채팅 입력 처리 ---
    # 분석 중이 아닐 때만 아이디어 입력 가능하도록
    if st.session_state.analysis_phase in ["idle", "phase1_complete", "error"]:
        if prompt := st.chat_input("아이디어를 입력해주세요... (분석을 원하시면 입력 후 엔터)"):
            # 사용자 입력을 세션 상태에만 추가 (UI에 직접 표시하지 않음)
            add_message("user", prompt)
                
            # 세션 상태 업데이트
            st.session_state.current_idea = prompt
            
            # API 키 검증
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key or api_key == "YOUR_ACTUAL_API_KEY":
                # 오류 메시지 추가
                add_message("assistant", "오류: GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요.", avatar="⚠️")
                st.session_state.analysis_phase = "error"
                st.session_state.need_rerun = True
            # 중복 분석 방지 및 1단계 분석 시작
            elif st.session_state.current_idea != st.session_state.analyzed_idea and st.session_state.analysis_phase != "phase1_running":
                # 분석 시작 준비
                st.session_state.analysis_phase = "phase1_pending_start" 
                st.session_state.phase1_step = "analysis_pending"
                st.session_state.need_rerun = True
    
    # 최종 rerun 호출 (필요한 경우에만) - 스크롤 문제를 최소화하기 위한 최적화
    if st.session_state.need_rerun:
        st.session_state.need_rerun = False
        st.rerun()

if __name__ == "__main__":
    main()