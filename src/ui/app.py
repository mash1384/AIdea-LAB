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
from config.personas import PERSONA_CONFIGS, PersonaType, ORCHESTRATOR_CONFIG
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

# 세션 서비스 초기화
session_service = InMemorySessionService()

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

def show_system_message(message_key, rerun=False):
    """시스템 안내 메시지를 채팅창에 표시합니다"""
    if message_key in SYSTEM_MESSAGES:
        st.session_state.messages.append({
            "role": "assistant", 
            "avatar": "⚙️", 
            "content": SYSTEM_MESSAGES[message_key]
        })
        if rerun:
            st.rerun()  # UI 즉시 업데이트

def create_session():
    """새로운 세션 생성"""
    session_id = f"session_{st.session_state.get('session_counter', 0)}"
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    return session, session_id

async def analyze_idea(idea_text, session, session_id):
    # ...
    orchestrator = AIdeaLabOrchestrator(model_name=st.session_state.selected_model)
    
    current_session = session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=session_id)
    if not current_session:
         current_session = session
    current_session.state["initial_idea"] = idea_text

    results = {}
    
    workflow_agent = orchestrator.get_workflow_agent()
    
    content = types.Content(
        role="user",
        parts=[types.Part(text=f"다음 아이디어를 분석해주세요: {idea_text}")]
    )
    
    runner = Runner(
        agent=workflow_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    
    # 에이전트 비동기 실행 결과를 변수에 할당 (await 없이)
    event_stream = runner.run_async(
        user_id=USER_ID,
        session_id=session_id,
        new_message=content
    )
    
    # 이벤트 비동기 처리 (event_stream 사용)
    async for event in event_stream: # 수정된 변수명 사용
        if event.is_final_response():
            # 최종 응답 처리 로직 (필요하다면)
            # 예를 들어, 최종 응답 내용을 별도로 저장하거나 할 수 있습니다.
            # 현재 코드는 단순히 break만 하고 있어서, 
            # SequentialAgent의 마지막 에이전트(summary_agent)의 최종 응답이 나올 때까지 기다리게 됩니다.
            # 이는 SequentialAgent가 모든 하위 에이전트를 실행하고 
            # 그 결과가 session.state에 누적되도록 하는 올바른 흐름입니다.
            pass # 특별한 처리가 없다면 pass 또는 break 유지
            
    # 세션에서 각 페르소나의 결과 가져오기
    updated_session = session_service.get_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=session_id
    )
    
    output_keys = orchestrator.get_output_keys()
    if updated_session and hasattr(updated_session, 'state'):
        for persona_key_name, state_key in output_keys.items():
            if state_key in updated_session.state:
                results[persona_key_name] = updated_session.state[state_key]
            
    return results

# (상단 import 및 설정은 기존과 동일)

# ... create_session, analyze_idea 함수 정의는 기존과 유사하게 유지 ...
# analyze_idea 함수는 이제 채팅 메시지를 st.session_state.messages에 직접 추가하고,
# UI 업데이트는 main 루프에서 st.session_state.messages를 다시 그리는 방식으로 변경될 수 있습니다.
# 또는 analyze_idea 내에서 st.chat_message().write_stream()을 직접 호출할 수도 있습니다.

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
    # ... 기타 필요한 상태 변수들 ...

# 1단계 분석을 위한 비동기 래퍼 함수 (UI 업데이트 포함)
async def run_phase1_analysis_and_update_ui(idea_text, adk_session_id_to_use):
    """1단계 분석을 실행하고 UI에 결과를 스트리밍합니다."""
    try:
        st.session_state.analysis_phase = "phase1_running"
        st.session_state.phase1_step = "analysis_started"

        # ADK 세션 가져오기 또는 생성 (create_session 함수 활용)
        current_adk_session = session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=adk_session_id_to_use)
        if not current_adk_session:
            st.error("ADK 세션을 찾을 수 없습니다.")
            st.session_state.analysis_phase = "error"
            return

        # 사용자 목표/제약 등 추가 정보 ADK 세션에 저장
        current_adk_session.state["initial_idea"] = idea_text
        if st.session_state.get("user_goal"):
            current_adk_session.state["user_goal"] = st.session_state.user_goal
        if st.session_state.get("user_constraints"):
            current_adk_session.state["user_constraints"] = st.session_state.user_constraints
        if st.session_state.get("user_values"):
            current_adk_session.state["user_values"] = st.session_state.user_values

        orchestrator = AIdeaLabOrchestrator(model_name=st.session_state.selected_model)
        phase1_workflow_agent = orchestrator.get_phase1_workflow()  # 1단계용 워크플로우 에이전트 사용

        runner = Runner(
            agent=phase1_workflow_agent,
            app_name=APP_NAME,
            session_service=session_service
        )

        # Runner 실행을 위한 초기 메시지
        initial_content_for_runner = types.Content(role="user", parts=[types.Part(text=f"다음 아이디어에 대한 1단계 분석을 시작합니다: {idea_text}")])

        event_stream = runner.run_async(
            user_id=USER_ID,
            session_id=adk_session_id_to_use,
            new_message=initial_content_for_runner
        )

        # 각 페르소나의 이름을 미리 정의 (output_key와 매칭되도록)
        persona_names_in_order = [
            (orchestrator.marketer_agent.get_output_key(), "마케터", "💡", "marketer_intro"), # (output_key, 표시이름, 아이콘, 소개메시지키)
            (orchestrator.critic_agent.get_output_key(), "비판적 분석가", "🔍", "critic_intro"),
            (orchestrator.engineer_agent.get_output_key(), "현실적 엔지니어", "⚙️", "engineer_intro"),
            (orchestrator.summary_agent.get_output_key(), "1단계 요약", "📝", "summary_intro") # summary_agent는 orchestrator 내에 정의되어 있음
        ]
        
        current_persona_index = 0

        async for event in event_stream:
            if event.is_final_response() and event.agent_name != phase1_workflow_agent.name: # SequentialAgent 자체의 최종 응답이 아닌, sub_agent의 최종 응답
                if current_persona_index < len(persona_names_in_order):
                    output_key, display_name, avatar_icon, intro_message_key = persona_names_in_order[current_persona_index]
                    
                    # 페르소나 소개 메시지 표시 (rerun 없이 메시지만 추가)
                    show_system_message(intro_message_key, rerun=True)
                    
                    # 페르소나 단계 상태 업데이트
                    st.session_state.phase1_step = f"{display_name.lower().replace(' ', '_')}_analyzing"
                    
                    # 해당 output_key로 session.state에서 결과 가져오기
                    updated_adk_session = session_service.get_session(app_name=APP_NAME, user_id=USER_ID, session_id=adk_session_id_to_use)
                    persona_response = updated_adk_session.state.get(output_key)

                    if persona_response:
                        # 실제 페르소나 응답 스트리밍
                        async def stream_data(text_data):
                            for chunk in text_data.split(): # 간단한 예시: 단어 단위
                                yield chunk + " "
                                await asyncio.sleep(0.02) # 약간의 딜레이로 스트리밍 효과

                        with st.chat_message("assistant", avatar=avatar_icon):
                            st.write_stream(stream_data(persona_response))
                        
                        st.session_state.messages.append({"role": "assistant", "avatar": avatar_icon, "content": persona_response})
                        current_persona_index += 1
                        
                        # 다음 페르소나를 위한 UI 업데이트
                        if current_persona_index < len(persona_names_in_order):
                            # 다음 페르소나로 진행하기 전에 잠시 지연
                            await asyncio.sleep(0.5)
                
                if current_persona_index >= len(persona_names_in_order): # 모든 sub_agent 완료
                    break 
        
        st.session_state.analysis_phase = "phase1_complete"
        st.session_state.phase1_step = "complete"
        st.session_state.analyzed_idea = idea_text # 분석 완료된 아이디어 기록
        
        # 1단계 완료 메시지 표시
        show_system_message("phase1_complete")

    except Exception as e:
        error_message = f"분석 중 오류가 발생했습니다: {str(e)}"
        st.session_state.messages.append({"role": "assistant", "avatar": "⚠️", "content": error_message})
        st.session_state.analysis_phase = "error"
        st.session_state.phase1_step = "error"
    finally:
        st.rerun() # UI 최종 업데이트

def main():
    """메인 애플리케이션 함수"""
    st.title("🧠 AIdea Lab - 아이디어 분석 워크숍")
    
    initialize_session_state()
    
    model_options = get_model_display_options()
    
    # 초기 환영 메시지가 없는 경우에만 추가 (세션 시작 시 딱 한번만)
    if len(st.session_state.messages) == 0:
        show_system_message("welcome")
    
    # 상태에 따른 조건부 처리
    if st.session_state.phase1_step == "idea_submitted" and st.session_state.analysis_phase == "idle":
        # 아이디어는 입력되었지만 아직 분석은 시작되지 않은 상태
        show_system_message("analysis_start")
        st.session_state.phase1_step = "analysis_ready"
        st.rerun()
    
    if st.session_state.analysis_phase == "idle": # 초기 상태 또는 이전 분석 완료 후
        st.markdown("""
        ### 💡 아이디어 분석 서비스
        자유롭게 아이디어를 입력하시면, 다양한 AI 페르소나가 여러 관점에서 분석해드리고 최종 정리까지 해드립니다.
        """)
    
    with st.expander("⚙️ 고급 설정"):
        st.selectbox(
            "AI 모델 선택:",
            options=list(model_options.keys()),
            format_func=lambda x: x,
            index=list(model_options.values()).index(st.session_state.selected_model),
            key="model_display_name_selectbox", # 이전 key와 다르게 설정하거나, on_change 콜백 내에서 처리
            on_change=lambda: setattr(st.session_state, 'selected_model', model_options[st.session_state.model_display_name_selectbox])
        )
        current_model_type = next((mt for mt in ModelType if mt.value == st.session_state.selected_model), None)
        if current_model_type:
            st.info(f"선택된 모델: {MODEL_CONFIGS[current_model_type]['description']}")
        
        # 추가 정보 입력 표시 토글
        st.checkbox("아이디어에 대한 추가 정보 입력", value=st.session_state.show_additional_info, 
                     key="show_additional_info_checkbox", on_change=lambda: setattr(st.session_state, 'show_additional_info', 
                     st.session_state.show_additional_info_checkbox))
        
        # 추가 정보 입력 필드 (체크박스 선택 시에만 표시)
        if st.session_state.show_additional_info:
            st.text_input("아이디어의 핵심 목표:", key="user_goal_input", 
                         value=st.session_state.user_goal, 
                         on_change=lambda: setattr(st.session_state, 'user_goal', st.session_state.user_goal_input),
                         help="아이디어를 통해 달성하고자 하는 주요 목표를 입력해주세요.")
            
            st.text_input("주요 제약 조건:", key="user_constraints_input", 
                         value=st.session_state.user_constraints, 
                         on_change=lambda: setattr(st.session_state, 'user_constraints', st.session_state.user_constraints_input),
                         help="아이디어 구현 시 고려해야 할 주요 제약 조건이나 한계를 입력해주세요.")
            
            st.text_input("중요 가치:", key="user_values_input", 
                         value=st.session_state.user_values, 
                         on_change=lambda: setattr(st.session_state, 'user_values', st.session_state.user_values_input),
                         help="이 아이디어가 중요하게 여기는 핵심 가치나 원칙을 입력해주세요.")

    # 이전 채팅 메시지 표시
    for message in st.session_state.messages:
        avatar = message.get("avatar") # 아바타가 없는 경우 None
        if not avatar and message["role"] == "assistant": # 기본 AI 아바타
            avatar = "🧠"
        with st.chat_message(message["role"], avatar=avatar):
            st.markdown(message["content"]) # Markdown으로 렌더링

    # --- 1단계 분석 완료 후 2단계 진행 버튼 ---
    if st.session_state.analysis_phase == "phase1_complete":
        # 2단계 진행 버튼 (이미 phase1_complete 메시지는 run_phase1_analysis_and_update_ui 함수에서 표시)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🚀 2단계 토론 시작하기", key="start_phase2_button"):
                st.session_state.analysis_phase = "phase2_pending" # 또는 "phase2_running"
                # 2단계 시작 안내 메시지 추가
                show_system_message("phase2_intro")
                # 여기에 2단계 분석 실행 로직 호출 (예: asyncio.run(run_phase2_analysis_and_update_ui(...)))
                st.rerun()
        with col2:
            if st.button("🏁 여기서 분석 종료하기", key="end_analysis_button"):
                st.session_state.analysis_phase = "idle" # 초기 상태로 복귀
                show_system_message("analysis_end")
                # 필요시 현재 세션 초기화 또는 새 세션 준비
                st.session_state.current_idea = "" 
                st.session_state.analyzed_idea = ""
                # st.session_state.messages = [] # 선택: 이전 대화 초기화
                st.rerun()
    
    # --- 채팅 입력 처리 ---
    # 분석 중이 아닐 때만 아이디어 입력 가능하도록 (또는 새 아이디어 입력 시 상태 초기화)
    if st.session_state.analysis_phase in ["idle", "phase1_complete", "error"]: # 분석 완료 또는 오류 시 새 아이디어 입력 가능
        if prompt := st.chat_input("아이디어를 입력해주세요... (분석을 원하시면 입력 후 엔터)"):
            # 새 아이디어 입력 시 이전 메시지 초기화 여부 결정 (선택 사항)
            # st.session_state.messages = [] 
            
            st.session_state.current_idea = prompt
            st.session_state.messages.append({"role": "user", "content": prompt})
            st.session_state.phase1_step = "idea_submitted"
            
            # API 키 검증
            api_key = os.getenv("GOOGLE_API_KEY")
            if not api_key or api_key == "YOUR_ACTUAL_API_KEY":
                st.session_state.messages.append({"role": "assistant", "avatar": "⚠️", "content": "오류: GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인해주세요."})
                st.session_state.analysis_phase = "error"
                st.rerun()
            # 중복 분석 방지 및 1단계 분석 시작
            elif st.session_state.current_idea != st.session_state.analyzed_idea and st.session_state.analysis_phase != "phase1_running":
                # 분석 시작 시스템 메시지 추가
                show_system_message("analysis_start")
                
                # ADK 세션 ID 생성 또는 가져오기
                # 매번 새 아이디어 분석 시 새 세션을 만들 것인가, 아니면 기존 세션을 이어갈 것인가?
                # 여기서는 새 아이디어마다 새 세션을 만든다고 가정 (더 간단)
                st.session_state.session_counter += 1
                _ , new_adk_session_id = create_session() # create_session은 session_counter를 사용
                st.session_state.adk_session_id = new_adk_session_id

                st.session_state.analysis_phase = "phase1_pending_start" # 분석 시작 대기 상태
                st.session_state.phase1_step = "analysis_pending"
                st.rerun()

    # 분석 시작 버튼 (임시) - 또는 위 chat_input 로직에 통합
    if st.session_state.analysis_phase == "phase1_pending_start":
        if st.session_state.current_idea: # 아이디어가 있을 때만
            with st.spinner("AI 페르소나들이 아이디어를 분석 중입니다... 잠시만 기다려주세요 ✨"):
                # 이미 분석 시작 메시지는 표시되었으므로 바로 분석 실행
                asyncio.run(run_phase1_analysis_and_update_ui(st.session_state.current_idea, st.session_state.adk_session_id))
            # run_phase1_analysis_and_update_ui 내부에서 rerun하므로 여기서는 추가 rerun 불필요할 수 있음

if __name__ == "__main__":
    main()