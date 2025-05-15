"""
AIdea Lab - 아이디어 분석 워크숍 UI

이 모듈은 Streamlit을 이용한 챗봇 인터페이스를 제공합니다.
사용자는 아이디어를 입력하고 AI 페르소나들의 분석 결과를 챗봇 형태로 볼 수 있습니다.
"""

import os
import sys
import asyncio
import streamlit as st
import time # stream_text_generator 에서 사용 (현재 직접 호출되지는 않음)
from dotenv import load_dotenv
from google.adk.runners import Runner # 실제 ADK Runner 임포트
from google.genai import types
from google.adk.events import Event, EventActions

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.orchestrator.main_orchestrator import AIdeaLabOrchestrator
from src.session_manager import SessionManager
from config.personas import PERSONA_CONFIGS, PersonaType, ORCHESTRATOR_CONFIG, PERSONA_SEQUENCE
from config.models import get_model_display_options, MODEL_CONFIGS, ModelType, DEFAULT_MODEL
from src.utils.model_monitor import AIModelMonitor, monitor_model_performance

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit 페이지 설정 (모든 import 후, 다른 Streamlit 명령어 이전에 배치)
st.set_page_config(
    page_title="AIdea Lab - 아이디어 분석 워크숍",
    page_icon="🧠",
    layout="wide"
)

# 앱 정보
APP_NAME = "AIdea Lab"
USER_ID = "streamlit_user"

# 세션 관리자 초기화 (제거: 더 이상 전역 변수로 사용하지 않음)
# session_manager = SessionManager(APP_NAME, USER_ID)

# 시스템 안내 메시지 템플릿 정의
SYSTEM_MESSAGES = {
    "welcome": "**AIdea Lab에 오신 것을 환영합니다.** 당신의 아이디어를 입력하시면 AI 페르소나들이 다양한 관점에서 분석해드립니다.",
    "phase1_start": "**분석을 시작합니다.** 각 AI 페르소나가 순차적으로 의견을 제시할 예정입니다.",
    "marketer_intro": "**💡 아이디어 마케팅 분석가의 의견:**",
    "critic_intro": "**🔍 비판적 분석가의 의견:**",
    "engineer_intro": "**⚙️ 현실주의 엔지니어의 의견:**",
    "summary_phase1_intro": "**📝 최종 요약 및 종합:**", # summary_phase1 키와 일치하도록 수정
    "phase1_complete": "**1단계 분석이 완료되었습니다.**",
    "phase1_error": "**분석 중 오류가 발생했습니다.** 다시 시도하거나 새로운 아이디어를 입력해주세요.",
    # 2단계 관련 메시지 추가
    "phase2_welcome": "**2단계 심층 토론을 시작합니다.** 퍼실리테이터의 진행에 따라 각 페르소나가 아이디어에 대해 토론합니다.",
    "facilitator_intro": "**🎯 토론 퍼실리테이터:**",
    "marketer_phase2_intro": "**💡 마케팅 분석가:**",
    "critic_phase2_intro": "**🔍 비판적 분석가:**",
    "engineer_phase2_intro": "**⚙️ 현실적 엔지니어:**",
    "user_prompt": "**사용자 의견이 필요합니다. 아래 질문에 대한 답변을 입력해주세요:**",
    "final_summary_phase2_intro": "**📊 최종 토론 결과 요약:**",
    "phase2_complete": "**2단계 토론이 완료되었습니다.**",
    "phase2_error": "**토론 중 오류가 발생했습니다.** 다시 시도하거나 새로운 아이디어를 입력해주세요."
}

# 페르소나 아바타 정의
persona_avatars = {
    "marketer": "💡",
    "critic": "🔍",
    "engineer": "⚙️",
    "summary_phase1": "📝", # orchestrator.get_output_keys_phase1()의 키와 일치
    "facilitator": "🎯",
    "user": "🧑‍💻",
    "marketer_phase2": "💡",
    "critic_phase2": "🔍",
    "engineer_phase2": "⚙️",
    "final_summary_phase2": "📊"
}

print(f"Initialized persona avatars: {persona_avatars}")

# 모델 모니터링 인스턴스 생성
model_monitor = AIModelMonitor(log_file_path="logs/model_performance.json")

# monitor_model_performance 데코레이터 적용 (기존 함수 앞에 추가)
@monitor_model_performance(model_monitor)
async def _run_phase1_analysis(runner: Runner, session_id_string: str, content: types.Content, orchestrator: AIdeaLabOrchestrator):
    print(f"DEBUG: _run_phase1_analysis - Starting with session_id: {session_id_string}")
    
    workflow_completed = False
    any_response_processed_successfully = False
    
    # 응답 검증 및 대체 메커니즘 함수
    def validate_agent_response(response_text, agent_name, output_key):
        if not response_text or not isinstance(response_text, str) or len(response_text.strip()) < 20:
            print(f"WARNING: Invalid response from {agent_name} for {output_key}. Generating fallback response.")
            # 기본 대체 응답 생성
            fallback_response = f"[{agent_name}에서 유효한 응답을 받지 못했습니다. 이 메시지는 자동 생성된 대체 응답입니다.]"
            if "summary" in output_key:
                fallback_response = f"**핵심 포인트:**\n- 이 보고서는 요약 중 오류가 발생하여 자동 생성되었습니다.\n\n**종합 요약:**\n해당 페르소나의 원본 보고서를 참고해 주세요."
            return fallback_response
        return response_text
    
    # 부분 결과로 프로세스 완료하는 함수
    async def complete_with_partial_results():
        session = orchestrator.session_manager_instance.get_session(session_id_string)
        if not session:
            return False
            
        # 현재까지 수집된 응답 확인
        state = session.state
        processed_keys = [k for k in state.keys() if k.endswith("_phase1") or k.endswith("_phase1_summary")]
        
        if not processed_keys:
            return False
            
        # 최종 요약이 없는 경우 간단한 요약 생성
        if "summary_report_phase1" not in state or not state["summary_report_phase1"]:
            # 부분 결과를 바탕으로 간단한 요약 메시지 생성
            message = "## 아이디어 분석 요약\n\n"
            message += "일부 페르소나의 분석이 완료되었습니다. 분석 과정에서 일부 오류가 발생했지만, 제공된 정보를 바탕으로 요약합니다.\n\n"
            
            for key in processed_keys:
                if state.get(key) and not key.endswith("_summary"):
                    persona_name = key.split("_")[0].capitalize()
                    message += f"### {persona_name} 분석\n"
                    message += state[key][:300] + "...\n\n"
                    
            add_message("system", "**📝 부분 결과 기반 요약:**", avatar="ℹ️")
            add_message("assistant", process_text_for_display(message), avatar="📝")
            
        return True
    
    try:
        output_keys_map = orchestrator.get_output_keys_phase1() 
        output_key_to_persona_key_map = {v: k for k, v in output_keys_map.items()}

        processed_sub_agent_outputs = set() 
        expected_sub_agent_output_count = len(output_keys_map)
        print(f"DEBUG: Expected sub-agent output count: {expected_sub_agent_output_count}")
        print(f"DEBUG: Output keys to track from orchestrator: {output_keys_map}")

        event_stream = runner.run_async(
            user_id=USER_ID, 
            session_id=session_id_string,
            new_message=content
        )
        
        async for event in event_stream:
            agent_author = getattr(event, 'author', 'N/A') 
            is_final_event = event.is_final_response() if hasattr(event, 'is_final_response') else False
            event_actions = getattr(event, 'actions', None)
            state_delta = getattr(event_actions, 'state_delta', None) if event_actions else None

            print(f"DEBUG_EVENT: Author='{agent_author}', IsFinal='{is_final_event}', HasStateDelta='{state_delta is not None}'")

            if is_final_event and state_delta:
                for output_key_in_delta, response_text in state_delta.items():
                    if output_key_in_delta in output_keys_map.values() and output_key_in_delta not in processed_sub_agent_outputs:
                        # 응답 검증 및 필요 시 대체 응답 생성
                        validated_response = validate_agent_response(response_text, agent_author, output_key_in_delta)
                        
                        if validated_response != response_text:
                            # 대체 응답이 생성되었으면 세션 상태 업데이트
                            try:
                                session = st.session_state.session_manager_instance.get_session(session_id_string)
                                if session:
                                    event_actions = EventActions(
                                        state_delta={output_key_in_delta: validated_response}
                                    )
                                    new_event = Event(
                                        actions=event_actions,
                                        author=f"{agent_author}_fallback"
                                    )
                                    st.session_state.session_manager_instance.session_service.append_event(
                                        app_name=APP_NAME,
                                        user_id=USER_ID,
                                        session_id=session_id_string,
                                        event=new_event
                                    )
                            except Exception as e:
                                print(f"WARNING: Failed to update session with fallback response: {e}")
                        
                        print(f"DEBUG: Valid response text found for output_key '{output_key_in_delta}' from agent '{agent_author}'.")
                        
                        processed_sub_agent_outputs.add(output_key_in_delta)
                        any_response_processed_successfully = True

                        persona_key_for_display = output_key_to_persona_key_map.get(output_key_in_delta)
                        
                        if persona_key_for_display:
                            intro_message_key_base = persona_key_for_display
                            intro_message_key = f"{intro_message_key_base}_intro" 
                            intro_content = SYSTEM_MESSAGES.get(intro_message_key)
                            avatar_char = persona_avatars.get(intro_message_key_base, "🤖")

                            if intro_content:
                                add_message("system", intro_content, avatar="ℹ️")
                            else:
                                print(f"WARNING: Intro message content not found for key '{intro_message_key}' (Persona key: {persona_key_for_display})")

                            add_message("assistant", process_text_for_display(validated_response), avatar=avatar_char)
                        else:
                            print(f"WARNING: Could not map output_key '{output_key_in_delta}' to persona_key for UI display (Agent: {agent_author}).")
        
        # 진행 상황 확인 및 처리
        if len(processed_sub_agent_outputs) >= expected_sub_agent_output_count:
            print(f"DEBUG: All {expected_sub_agent_output_count} expected outputs processed: {processed_sub_agent_outputs}.")
            workflow_completed = True
        else:
            print(f"WARNING: Workflow incomplete. Expected {expected_sub_agent_output_count}, processed {len(processed_sub_agent_outputs)}: {list(processed_sub_agent_outputs)}")
            # 진행된 작업이 있으면 부분 결과로 처리
            if len(processed_sub_agent_outputs) > 0:
                await complete_with_partial_results()

        if any_response_processed_successfully or workflow_completed:
             st.session_state.need_rerun = True

        print(f"DEBUG: _run_phase1_analysis - Finished. WorkflowCompleted={workflow_completed}, AnyResponseProcessed={any_response_processed_successfully}")
        return workflow_completed and any_response_processed_successfully

    except Exception as e:
        print(f"ERROR in _run_phase1_analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # 에러 발생 시 부분 결과로 처리 시도
        try:
            partial_success = await complete_with_partial_results()
            if partial_success:
                print("Successfully completed with partial results after error.")
            st.session_state.need_rerun = True
        except Exception as nested_e:
            print(f"ERROR while trying to complete with partial results: {str(nested_e)}")
        
        return False

# --- 여기가 메인 분석 실행 및 UI 업데이트 함수 ---
def run_phase1_analysis_and_update_ui():
    try:
        orchestrator = AIdeaLabOrchestrator(model_name=st.session_state.selected_model)
        print(f"Created local orchestrator with model: {st.session_state.selected_model}")
        
        st.session_state.analysis_phase = "phase1_running"

        show_system_message("phase1_start")
        print("Phase 1 analysis initiated by user")
        
        idea_text = st.session_state.current_idea
        user_goal = st.session_state.get("user_goal", "")
        user_constraints = st.session_state.get("user_constraints", "")
        user_values = st.session_state.get("user_values", "")
        print(f"Analyzing idea: {idea_text}, Goal: {user_goal}, Constraints: {user_constraints}, Values: {user_values}")
        
        session_object, session_id_string = st.session_state.session_manager_instance.start_new_idea_session(
            idea_text,
            user_goal=user_goal,
            user_constraints=user_constraints,
            user_values=user_values
        )
        
        if not session_object or not session_id_string:
            print("ERROR: Failed to start new idea session in SessionManager.")
            st.session_state.analysis_phase = "phase1_error"
            show_system_message("phase1_error")
            st.session_state.need_rerun = True
            return

        st.session_state.adk_session_id = session_id_string
        print(f"New session started with ID: {session_id_string}, initial state verified in SessionManager.")
        
        phase1_workflow_agent = orchestrator.get_phase1_workflow()
        print(f"Successfully retrieved phase1_workflow_agent: {phase1_workflow_agent.name if hasattr(phase1_workflow_agent, 'name') else 'N/A'}")

        runner = Runner(
            agent=phase1_workflow_agent,
            app_name=APP_NAME,
            session_service=st.session_state.session_manager_instance.session_service 
        )
        print(f"Successfully initialized ADK Runner with agent: {phase1_workflow_agent.name if hasattr(phase1_workflow_agent, 'name') else 'N/A'}")
        
        content_parts = [types.Part(text=f"아이디어: {idea_text}")]
        if user_goal: content_parts.append(types.Part(text=f"\n목표: {user_goal}"))
        if user_constraints: content_parts.append(types.Part(text=f"\n제약조건: {user_constraints}"))
        if user_values: content_parts.append(types.Part(text=f"\n가치: {user_values}"))
        
        input_content_for_runner = types.Content(role="user", parts=content_parts)
        print(f"Prepared input_content_for_runner: {input_content_for_runner}")
        
        analysis_success = asyncio.run(_run_phase1_analysis(
            runner, 
            session_id_string, 
            input_content_for_runner, 
            orchestrator
        ))
        
        if analysis_success:
            print("Phase 1 analysis processing was successful according to _run_phase1_analysis.")
            show_system_message("phase1_complete") # 개별 메시지는 _run_phase1_analysis에서 추가, 여기선 완료 메시지만.
            st.session_state.analysis_phase = "phase1_complete"
        else:
            print("Phase 1 analysis processing FAILED according to _run_phase1_analysis.")
            # _run_phase1_analysis 내부에서 이미 에러 로그를 찍었을 것이므로, 여기서는 UI 상태만 업데이트
            current_phase = st.session_state.get("analysis_phase", "")
            if current_phase != "phase1_error": 
                show_system_message("phase1_error")
                st.session_state.analysis_phase = "phase1_error"
        
        st.session_state.analyzed_idea = idea_text

    except Exception as e:
        print(f"Critical error in run_phase1_analysis_and_update_ui: {str(e)}")
        import traceback
        traceback.print_exc()
        st.session_state.analysis_phase = "phase1_error"
        show_system_message("phase1_error")
    
    finally:
        st.session_state.need_rerun = True 
        print(f"run_phase1_analysis_and_update_ui finished. Phase: {st.session_state.get('analysis_phase', 'unknown')}, NeedRerun: {st.session_state.get('need_rerun', False)}")


def initialize_session_state():
    # SessionManager 객체를 Streamlit 세션 상태에 저장
    if 'session_manager_instance' not in st.session_state:
        print("Creating new SessionManager instance and storing in st.session_state")
        from src.session_manager import SessionManager
        st.session_state.session_manager_instance = SessionManager(APP_NAME, USER_ID)
    
    if 'session_counter' not in st.session_state: # 세션 지속 시간 또는 고유 ID 생성 등에 활용 가능
        st.session_state.session_counter = 0
    
    if 'selected_model' not in st.session_state:
        st.session_state.selected_model = DEFAULT_MODEL.value
    
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        try:
            welcome_message = SYSTEM_MESSAGES.get("welcome")
            add_message("assistant", welcome_message, avatar="🧠") # 아바타 일관성
        except Exception as e:
            print(f"Error adding welcome message: {str(e)}")
            add_message("assistant", "AIdea Lab에 오신 것을 환영합니다.", avatar="🧠")
    
    # 나머지 상태 초기화는 이전과 거의 동일하게 유지, .get으로 안전하게 접근
    if 'current_idea' not in st.session_state: st.session_state.current_idea = ""
    if 'analyzed_idea' not in st.session_state: st.session_state.analyzed_idea = ""
    if 'analysis_phase' not in st.session_state: st.session_state.analysis_phase = "idle"
    if 'adk_session_id' not in st.session_state: st.session_state.adk_session_id = None
    if 'user_goal' not in st.session_state: st.session_state.user_goal = ""
    if 'user_constraints' not in st.session_state: st.session_state.user_constraints = ""
    if 'user_values' not in st.session_state: st.session_state.user_values = ""
    if 'show_additional_info' not in st.session_state: st.session_state.show_additional_info = False
    if 'expander_state' not in st.session_state: st.session_state.expander_state = False # 기본적으로 닫혀있도록 변경 (선택)
    if 'need_rerun' not in st.session_state: st.session_state.need_rerun = False
    if 'proceed_to_phase2' not in st.session_state: st.session_state.proceed_to_phase2 = False
    
    # 2단계 토론 관련 상태 변수 추가
    if 'awaiting_user_input_phase2' not in st.session_state: st.session_state.awaiting_user_input_phase2 = False
    if 'phase2_user_prompt' not in st.session_state: st.session_state.phase2_user_prompt = ""
    if 'phase2_discussion_complete' not in st.session_state: st.session_state.phase2_discussion_complete = False
    if 'phase2_summary_complete' not in st.session_state: st.session_state.phase2_summary_complete = False


def update_setting(key, value): # 현재 직접 사용되지 않지만 유틸리티로 유지
    setattr(st.session_state, key, value)
    st.session_state.need_rerun = True

def restart_session(keep_messages=False):
    print("Restarting session...")
    messages_backup = list(st.session_state.get("messages", [])) # Get a copy

    # 필요한 핵심 상태만 초기화하고 나머지는 initialize_session_state에 맡김
    keys_to_reset_for_new_idea = [
        'current_idea', 'analyzed_idea', 'analysis_phase', 
        'adk_session_id', 'user_goal', 'user_constraints', 'user_values',
        'proceed_to_phase2', 'awaiting_user_input_phase2', 'phase2_user_prompt',
        'phase2_discussion_complete', 'phase2_summary_complete'
        # 'show_additional_info' 와 'expander_state'는 사용자의 선택을 유지할 수 있음
    ]
    for key in keys_to_reset_for_new_idea:
        if key in st.session_state:
            del st.session_state[key] 
            # 또는 st.session_state[key] = <초기값> 으로 설정

    # 기본 상태값 재설정 (messages 제외)
    initialize_session_state() # messages가 여기서 다시 초기화되지 않도록 주의 필요

    if keep_messages:
        st.session_state.messages = messages_backup
    else:
        st.session_state.messages = [] 
        try:
            welcome_message = SYSTEM_MESSAGES.get("welcome")
            add_message("assistant", welcome_message, avatar="🧠")
        except Exception as e:
            print(f"Error re-adding welcome message: {str(e)}")
            add_message("assistant", "AIdea Lab에 오신 것을 환영합니다.", avatar="🧠")
    
    print("Session restart logic completed.")
    st.session_state.need_rerun = True


def process_text_for_display(text_data):
    if not isinstance(text_data, str):
        text_data = str(text_data)
    # Markdown에서 자동 줄바꿈을 위해 줄 끝에 공백 두 개를 추가하거나, 
    # Streamlit이 CSS를 통해 white-space: pre-wrap 등을 지원하는지 확인.
    # 여기서는 명시적으로 HTML <br> 태그나 마크다운 공백2개를 사용할 수 있음.
    return text_data.replace("\n", "  \n")

def add_message(role, content, avatar=None):
    if content is None: # content가 None인 경우 추가하지 않음
        print(f"Skipping add_message for role {role} because content is None.")
        return

    print(f"Adding message - Role: {role}, Avatar: {avatar}, Content preview: {str(content)[:70]}...")
    
    # 메시지 객체 생성
    message_obj = {"role": role, "content": content, "avatar": avatar}
    
    # 현재 메시지 목록 가져오기 (없으면 새로 생성)
    if 'messages' not in st.session_state:
        st.session_state.messages = []
        
    # 시스템 메시지의 경우, 바로 이전 메시지와 내용 및 아바타가 동일하면 추가하지 않음 (연속 중복 방지)
    is_system_message_type = avatar == "ℹ️" # 시스템 메시지 아바타 기준
    if is_system_message_type and st.session_state.messages:
        last_message = st.session_state.messages[-1]
        if last_message.get("role") == role and \
           last_message.get("content") == content and \
           last_message.get("avatar") == avatar:
            print("Consecutive duplicate system message skipped.")
            return
            
    st.session_state.messages.append(message_obj)
    print(f"Message added. Total messages: {len(st.session_state.messages)}")

def show_system_message(message_key, rerun_immediately=False):
    message_content = SYSTEM_MESSAGES.get(message_key)
    if message_content:
        print(f"Showing system message for key '{message_key}': {message_content[:70]}...")
        add_message("system", message_content, avatar="ℹ️")
        if rerun_immediately:
            st.session_state.need_rerun = True
    else:
        print(f"WARNING: System message key '{message_key}' not defined in SYSTEM_MESSAGES.")

# 토론 히스토리 상태 업데이트를 위한 유틸리티 함수 (전역 함수로 이동)
def update_discussion_history(session_id_string, speaker, text):
    """
    토론 히스토리를 안정적으로 업데이트하는 유틸리티 함수
    
    Args:
        session_id_string (str): 세션 ID
        speaker (str): 발언자 (facilitator, marketer_agent, critic_agent, engineer_agent, user 등)
        text (str): 발언 내용
    """
    current_session = st.session_state.session_manager_instance.get_session(session_id_string)
    if not current_session:
        print(f"ERROR: Failed to get session with ID {session_id_string} in update_discussion_history.")
        return
        
    # 최신 상태의 토론 히스토리 가져오기
    discussion_history = current_session.state.get("discussion_history_phase2", [])
    
    # 새 발언 추가
    discussion_history.append({
        "speaker": speaker,
        "text": text
    })
    
    # EventActions를 사용하여 세션 상태 업데이트
    state_delta = {"discussion_history_phase2": discussion_history}
    event_actions = EventActions(state_delta=state_delta)
    event = Event(
        author=APP_NAME,
        actions=event_actions
    )
    
    # ADK 세션에 이벤트 추가
    st.session_state.session_manager_instance.session_service.append_event(
        session=current_session,
        event=event
    )
    
    print(f"DEBUG: Updated discussion_history_phase2 with {speaker}'s message. Total entries: {len(discussion_history)}")

# --- 2단계 토론 실행 및 UI 업데이트 함수 ---
async def _run_phase2_discussion(session_id_string, orchestrator):
    """
    2단계 토론 실행 함수
    
    토론 퍼실리테이터 및 페르소나 에이전트들 간의 대화를 조율하고 UI에 표시합니다.
    
    Args:
        session_id_string (str): 세션 ID
        orchestrator (AIdeaLabOrchestrator): 오케스트레이터 객체
    
    Returns:
        bool: 토론 진행 성공 여부
    """
    print(f"DEBUG: _run_phase2_discussion - Starting with session_id: {session_id_string}")
    
    try:
        session = st.session_state.session_manager_instance.get_session(session_id_string)
        if not session:
            print(f"ERROR: Failed to get session with ID {session_id_string} in _run_phase2_discussion.")
            return False

        # 각 에이전트의 응답을 표시할 때 사용할 아바타 매핑
        agent_to_avatar_map = {
            "facilitator": persona_avatars.get("facilitator", "🎯"),
            "marketer_agent": persona_avatars.get("marketer_phase2", "💡"),
            "critic_agent": persona_avatars.get("critic_phase2", "🔍"),
            "engineer_agent": persona_avatars.get("engineer_phase2", "⚙️"),
            "user": persona_avatars.get("user", "🧑‍💻"),
            "final_summary": persona_avatars.get("final_summary_phase2", "📊")
        }
        
        # 토론 퍼실리테이터 에이전트 가져오기
        facilitator_agent = orchestrator.get_phase2_discussion_facilitator()
        
        # 최대 토론 반복 횟수
        max_discussion_rounds = 15
        current_round = 0
        
        # 토론 루프 시작
        while current_round < max_discussion_rounds:
            current_round += 1
            print(f"DEBUG: Starting discussion round {current_round}/{max_discussion_rounds}")
            
            try:
                # 퍼실리테이터 에이전트 실행
                # 빈 메시지로 실행하여 세션 상태를 직접 참조하도록 함
                runner = Runner(
                    agent=facilitator_agent,
                    app_name=APP_NAME,
                    session_service=st.session_state.session_manager_instance.session_service
                )
                
                input_content = types.Content(role="user", parts=[types.Part(text="")])
                
                # 퍼실리테이터 에이전트의 응답 처리
                next_agent = None
                topic_for_next = ""
                
                event_stream = runner.run_async(
                    user_id=USER_ID,
                    session_id=session_id_string,
                    new_message=input_content
                )
                
                async for event in event_stream:
                    is_final_event = event.is_final_response() if hasattr(event, 'is_final_response') else False
                    event_actions = getattr(event, 'actions', None)
                    state_delta = getattr(event_actions, 'state_delta', None) if event_actions else None
                    
                    if is_final_event and state_delta:
                        # facilitator_response 키에서 응답 추출
                        facilitator_response = state_delta.get("facilitator_response", "")
                        if facilitator_response and isinstance(facilitator_response, str):
                            # 응답 전체를 로그로 출력 (디버깅용)
                            print(f"\n=== FACILITATOR RESPONSE (FULL) ===\n{facilitator_response}\n=== END FACILITATOR RESPONSE ===\n")
                            
                            # 퍼실리테이터 응답을 UI에 표시
                            show_system_message("facilitator_intro", rerun_immediately=False)
                            add_message("assistant", process_text_for_display(facilitator_response), avatar=agent_to_avatar_map["facilitator"])
                            
                            # facilitator_response에서 JSON 부분 추출
                            import re
                            import json
                            
                            # 더 정확한 JSON 추출을 위한 패턴 개선
                            # 마크다운 코드 블록 안의 JSON을 먼저 찾기
                            json_in_code_block = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', facilitator_response)
                            
                            # 그 다음 일반 텍스트에서 중괄호로 둘러싸인 부분 찾기
                            json_raw_pattern = r'({[\s\S]*?})'
                            json_matches = re.findall(json_raw_pattern, facilitator_response)
                            
                            parsed_successfully = False
                            json_data = None
                            parsing_error = None
                            json_str_attempted = None
                            
                            # 먼저 코드 블록 내 JSON 파싱 시도
                            if json_in_code_block:
                                json_str_attempted = json_in_code_block.group(1)
                                try:
                                    json_data = json.loads(json_str_attempted)
                                    parsed_successfully = True
                                    print(f"INFO: Successfully parsed JSON from code block")
                                except json.JSONDecodeError as e:
                                    parsing_error = str(e)
                                    print(f"WARNING: Failed to parse JSON from code block: {e}")
                            
                            # 실패한 경우 일반 텍스트에서 찾은 중괄호 블록 시도
                            if not parsed_successfully and json_matches:
                                for json_str in json_matches:
                                    json_str_attempted = json_str
                                    try:
                                        json_data = json.loads(json_str)
                                        parsed_successfully = True
                                        print(f"INFO: Successfully parsed JSON from regular text")
                                        break
                                    except json.JSONDecodeError:
                                        # 계속 다음 매치 시도
                                        continue
                            
                            # 마지막 시도: 응답 전체를 JSON으로 파싱
                            if not parsed_successfully:
                                json_str_attempted = facilitator_response
                                try:
                                    json_data = json.loads(facilitator_response)
                                    parsed_successfully = True
                                    print(f"INFO: Parsed entire response as JSON")
                                except json.JSONDecodeError as e:
                                    parsing_error = str(e)
                                    print(f"ERROR: Failed to parse any JSON from facilitator_response: {e}")
                                    print(f"Response is not valid JSON: {facilitator_response[:200]}...")
                            
                            if parsed_successfully and json_data:
                                next_agent = json_data.get("next_agent", "")
                                topic_for_next = json_data.get("message_to_next_agent_or_topic", "")
                                reasoning = json_data.get("reasoning", "")
                                
                                print(f"DEBUG: Extracted JSON data from facilitator_response:")
                                print(f"  - next_agent: {next_agent}")
                                print(f"  - topic: {topic_for_next[:50]}...")
                                print(f"  - reasoning: {reasoning[:50]}...")
                                
                                # 토론 히스토리에 퍼실리테이터 발언 추가
                                update_discussion_history(session_id_string, "facilitator", facilitator_response)
                            else:
                                # JSON 파싱 실패 시 오류 처리
                                print(f"ERROR: Could not extract valid JSON from facilitator_response")
                                if json_str_attempted:
                                    print(f"Last JSON string attempted to parse: {json_str_attempted[:200]}...")
                                
                                # 오류 발생 시 기본값 설정하여 계속 진행
                                next_agent = "FINAL_SUMMARY"  # 기본적으로 토론 종료
                                topic_for_next = "토론 진행 중 오류가 발생하여 최종 요약으로 진행합니다."
                                
                                # 오류 메시지를 대화에 추가
                                show_system_message("phase2_error", rerun_immediately=False)
                                
                            # UI 업데이트를 위해 필요
                            st.session_state.need_rerun = True
                
                # 다음 에이전트가 없거나 빈 문자열이면 종료
                if not next_agent:
                    print("WARNING: next_agent is None or empty, ending discussion loop")
                    break
                
                # 라우팅 처리
                if next_agent == "USER":
                    # 사용자 피드백 요청
                    show_system_message("user_prompt", rerun_immediately=False)
                    add_message("assistant", process_text_for_display(topic_for_next), avatar="ℹ️")
                    
                    # 사용자 입력을 기다리기 위한 상태 설정
                    st.session_state.awaiting_user_input_phase2 = True
                    st.session_state.phase2_user_prompt = topic_for_next
                    st.session_state.need_rerun = True
                    
                    # 사용자 입력을 기다리기 위해 루프를 빠져나감 (UI에서 입력 후 다시 호출)
                    return True
                
                elif next_agent == "FINAL_SUMMARY":
                    # 최종 요약으로 이동
                    print("DEBUG: Facilitator requested FINAL_SUMMARY, ending discussion loop")
                    st.session_state.phase2_discussion_complete = True
                    
                    # 토론 완료 메시지 표시
                    show_system_message("phase2_complete", rerun_immediately=False)
                    
                    # 최종 요약 에이전트 실행
                    final_summary_agent = orchestrator.get_phase2_final_summary_agent()
                    
                    runner = Runner(
                        agent=final_summary_agent,
                        app_name=APP_NAME,
                        session_service=st.session_state.session_manager_instance.session_service
                    )
                    
                    # 빈 메시지로 실행하여 세션 상태를 직접 참조하도록 함
                    input_content = types.Content(role="user", parts=[types.Part(text="")])
                    
                    # 최종 요약 에이전트 실행
                    event_stream = runner.run_async(
                        user_id=USER_ID,
                        session_id=session_id_string,
                        new_message=input_content
                    )
                    
                    # 최종 요약 처리
                    final_summary_processed = False
                    
                    async for event in event_stream:
                        is_final_event = event.is_final_response() if hasattr(event, 'is_final_response') else False
                        event_actions = getattr(event, 'actions', None)
                        state_delta = getattr(event_actions, 'state_delta', None) if event_actions else None
                        
                        if is_final_event and state_delta:
                            final_summary = state_delta.get("final_summary_report_phase2", "")
                            if final_summary and isinstance(final_summary, str):
                                # 최종 요약을 UI에 표시
                                show_system_message("final_summary_phase2_intro", rerun_immediately=False)
                                add_message("assistant", process_text_for_display(final_summary), avatar=agent_to_avatar_map["final_summary"])
                                
                                # 토론 히스토리에 최종 요약 추가
                                update_discussion_history(session_id_string, "final_summary", final_summary)
                                
                                final_summary_processed = True
                    
                    # 최종 요약 완료 상태 설정
                    st.session_state.phase2_summary_complete = final_summary_processed
                    st.session_state.need_rerun = True
                    
                    # 토론과 요약 모두 완료
                    return final_summary_processed
                
                else:
                    # 특정 페르소나 에이전트 실행
                    # 1. 먼저 facilitator_question_to_persona 세션 상태 설정
                    session.state["facilitator_question_to_persona"] = topic_for_next
                    
                    # 2. 해당 페르소나 에이전트 가져오기
                    persona_agent = None
                    persona_type_map = {
                        "marketer_agent": PersonaType.MARKETER,
                        "critic_agent": PersonaType.CRITIC,
                        "engineer_agent": PersonaType.ENGINEER
                    }
                    
                    # next_agent에 맞는 persona_type 가져오기
                    persona_type = persona_type_map.get(next_agent)
                    if not persona_type:
                        print(f"WARNING: Unknown persona type for next_agent: {next_agent}")
                        continue
                    
                    # 해당 페르소나 에이전트 가져오기
                    try:
                        persona_agent = orchestrator.get_phase2_persona_agent(persona_type)
                    except Exception as e:
                        print(f"ERROR: Failed to get persona agent for {persona_type}: {e}")
                        continue
                    
                    # 3. 페르소나 에이전트 실행
                    runner = Runner(
                        agent=persona_agent,
                        app_name=APP_NAME,
                        session_service=st.session_state.session_manager_instance.session_service
                    )
                    
                    # 빈 메시지로 실행하여 세션 상태를 직접 참조하도록 함
                    input_content = types.Content(role="user", parts=[types.Part(text="")])
                    
                    # 페르소나 에이전트 출력 키 매핑
                    persona_output_key_map = {
                        "marketer_agent": "marketer_response_phase2",
                        "critic_agent": "critic_response_phase2",
                        "engineer_agent": "engineer_response_phase2"
                    }
                    
                    # 페르소나 intro 메시지 키 매핑
                    persona_intro_msg_key_map = {
                        "marketer_agent": "marketer_phase2_intro",
                        "critic_agent": "critic_phase2_intro",
                        "engineer_agent": "engineer_phase2_intro"
                    }
                    
                    # 페르소나 에이전트 응답 처리
                    event_stream = runner.run_async(
                        user_id=USER_ID,
                        session_id=session_id_string,
                        new_message=input_content
                    )
                    
                    async for event in event_stream:
                        is_final_event = event.is_final_response() if hasattr(event, 'is_final_response') else False
                        event_actions = getattr(event, 'actions', None)
                        state_delta = getattr(event_actions, 'state_delta', None) if event_actions else None
                        
                        if is_final_event and state_delta:
                            output_key = persona_output_key_map.get(next_agent, "")
                            persona_response = state_delta.get(output_key, "")
                            
                            if persona_response and isinstance(persona_response, str):
                                # 해당 페르소나의 intro 메시지 표시
                                intro_msg_key = persona_intro_msg_key_map.get(next_agent, "")
                                if intro_msg_key:
                                    show_system_message(intro_msg_key, rerun_immediately=False)
                                
                                # 페르소나 응답을 UI에 표시
                                add_message("assistant", process_text_for_display(persona_response), avatar=agent_to_avatar_map[next_agent])
                                
                                # 토론 히스토리에 페르소나 발언 추가
                                update_discussion_history(session_id_string, next_agent, persona_response)
                                
                                # UI 업데이트를 위해 필요
                                st.session_state.need_rerun = True
            
            except Exception as e:
                print(f"ERROR in discussion round {current_round}: {e}")
                import traceback
                traceback.print_exc()
                # 오류가 있어도 토론을 계속 시도
        
        # 최대 라운드에 도달한 경우
        if current_round >= max_discussion_rounds:
            print(f"DEBUG: Reached maximum discussion rounds ({max_discussion_rounds})")
            show_system_message("phase2_complete", rerun_immediately=False)
            st.session_state.phase2_discussion_complete = True
            st.session_state.need_rerun = True
        
        return True  # 토론 진행 성공
    
    except Exception as e:
        print(f"Critical error in _run_phase2_discussion: {e}")
        import traceback
        traceback.print_exc()
        return False  # 토론 진행 실패

def handle_phase2_discussion():
    """
    2단계 토론 처리 함수
    
    사용자가 '2단계 토론 시작하기'를 선택하면 실행되는 함수로,
    토론 퍼실리테이터 에이전트와 페르소나 에이전트들 간의 대화를 조율합니다.
    """
    try:
        # 올바른 EventActions 임포트 경로
        from google.adk.events import Event, EventActions
        
        print("Starting Phase 2 discussion...")
        
        # 현재 세션 상태 확인
        if st.session_state.analysis_phase != "phase2_pending_start" and not st.session_state.awaiting_user_input_phase2:
            print(f"WARNING: Unexpected analysis phase '{st.session_state.analysis_phase}' for handle_phase2_discussion")
            return
        
        # 오케스트레이터 생성
        orchestrator = AIdeaLabOrchestrator(model_name=st.session_state.selected_model)
        print(f"Created local orchestrator with model: {st.session_state.selected_model}")
        
        # 세션 ID 가져오기
        session_id_string = st.session_state.adk_session_id
        if not session_id_string:
            print("ERROR: No session ID available for phase 2 discussion")
            st.session_state.analysis_phase = "phase2_error"
            show_system_message("phase2_error")
            st.session_state.need_rerun = True
            return
        
        # 세션 객체 가져오기
        session = st.session_state.session_manager_instance.get_session(session_id_string)
        if not session:
            print(f"ERROR: Failed to get session with ID {session_id_string}")
            st.session_state.analysis_phase = "phase2_error"
            show_system_message("phase2_error")
            st.session_state.need_rerun = True
            return
        
        # 사용자 입력을 기다리는 상태인 경우
        if st.session_state.awaiting_user_input_phase2:
            # 사용자 입력은 main() 함수에서 처리하고, 
            # 여기서는 사용자 입력이 있은 후에 호출됨
            
            # 1. discussion_history_phase2에 사용자 응답 추가
            user_response = st.session_state.get("phase2_user_response", "")
            if user_response:
                # update_discussion_history 함수 사용하여 사용자 응답 추가
                update_discussion_history(session_id_string, "user", user_response)
                
                # 사용자 입력 상태 초기화
                st.session_state.awaiting_user_input_phase2 = False
                st.session_state.phase2_user_prompt = ""
                st.session_state.phase2_user_response = ""
        else:
            # 최초 토론 시작 시 2단계로 전환
            if st.session_state.analysis_phase == "phase2_pending_start":
                # 환영 메시지 표시
                show_system_message("phase2_welcome")
                
                # 세션 상태를 phase2로 전환
                st.session_state.session_manager_instance.transition_to_phase2()
                
                # Streamlit 세션 상태 업데이트
                st.session_state.analysis_phase = "phase2_running"
        
        # 2단계 토론 실행
        with st.spinner("AI 페르소나들이 토론 중입니다... 이 작업은 최대 1-2분 소요될 수 있습니다."):
            discussion_success = asyncio.run(_run_phase2_discussion(
                session_id_string,
                orchestrator
            ))
        
        # 토론 결과에 따른 상태 업데이트
        if discussion_success:
            if st.session_state.phase2_discussion_complete and st.session_state.phase2_summary_complete:
                # 토론과 요약이 모두 완료된 경우
                st.session_state.analysis_phase = "phase2_complete"
            elif st.session_state.awaiting_user_input_phase2:
                # 사용자 입력을 기다리는 경우
                st.session_state.analysis_phase = "phase2_user_input"
            else:
                # 토론이 계속 진행 중인 경우
                st.session_state.analysis_phase = "phase2_running"
        else:
            # 토론 중 오류 발생
            st.session_state.analysis_phase = "phase2_error"
            show_system_message("phase2_error")
        
        # UI 업데이트를 위해 필요
        st.session_state.need_rerun = True
    
    except Exception as e:
        print(f"Critical error in handle_phase2_discussion: {e}")
        import traceback
        traceback.print_exc()
        st.session_state.analysis_phase = "phase2_error"
        show_system_message("phase2_error")
        st.session_state.need_rerun = True

def main():
    # 세션 상태 초기화
    initialize_session_state()
    
    # 로그 디렉토리 생성
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # 모델 성능 정보 가져오기
    model_recommendations = model_monitor.get_model_recommendations()
    best_model_info = model_monitor.get_best_model()
    
    # 사이드바 UI 구성
    with st.sidebar:
        st.title("⚙️ 설정")
        
        # 모델 선택 UI
        model_options = get_model_display_options()
        selected_display_name = st.selectbox(
            "모델 선택",
            options=list(model_options.keys()),
            index=list(model_options.values()).index(st.session_state.selected_model) if st.session_state.selected_model in model_options.values() else 0
        )
        
        # 선택된 모델의 내부 ID 가져오기
        selected_model_id = model_options[selected_display_name]
        
        # 모델 성능 정보 표시
        if selected_model_id in model_recommendations:
            recommendation = model_recommendations[selected_model_id]
            recommendation_color = {
                "highly_recommended": "green",
                "recommended": "blue",
                "not_recommended": "red",
                "insufficient_data": "gray"
            }.get(recommendation["recommendation"], "black")
            
            st.markdown(f"<span style='color:{recommendation_color}'>{recommendation['reason']}</span>", unsafe_allow_html=True)
            
            if recommendation["total_calls"] > 0:
                st.progress(recommendation["success_rate"], f"성공률: {recommendation['success_rate']:.1%}")
                st.text(f"평균 응답시간: {recommendation['avg_response_time']:.2f}초")
        
        # 최고 추천 모델 표시
        if best_model_info and best_model_info[0] != selected_model_id:
            best_model_name = MODEL_CONFIGS[ModelType(best_model_info[0])]["display_name"] if best_model_info[0] in [m.value for m in ModelType] else best_model_info[0]
            st.info(f"💡 추천 모델: {best_model_name} (성공률: {best_model_info[1]['success_rate']:.1%})")
        
        # 모델 변경 적용
        if st.session_state.selected_model != selected_model_id:
            st.session_state.selected_model = selected_model_id
            st.write(f"Model selection changed to: {selected_model_id}. Restarting session.")
            restart_session()
            st.rerun()
    
    # 나머지 main 함수 UI 코드는 그대로 유지
    initialize_session_state()
    
    # SessionManager 인스턴스 가져오기
    session_manager = st.session_state.session_manager_instance
    
    st.title("AIdea Lab - 아이디어 분석 워크숍")
    st.markdown("당신의 아이디어를 AI가 다양한 관점에서 분석해드립니다!")
    
    # 채팅 메시지 표시
    messages_container = st.container()
    with messages_container:
        if st.session_state.get('messages'):
            for idx, message in enumerate(st.session_state.messages): # Added enumerate for unique keys if needed
                role = message.get("role", "")
                msg_content = message.get("content", "")
                avatar = message.get("avatar", None)
                
                try:
                    if role == "user":
                        st.chat_message(role, avatar="🧑‍💻").write(msg_content)
                    elif role == "assistant":
                        st.chat_message(role, avatar=avatar).write(msg_content)
                    elif role == "system":
                        # 시스템 메시지를 info 박스 대신 일반 메시지처럼 보이게 처리
                        # st.info(msg_content) 
                        st.chat_message("assistant", avatar=avatar if avatar else "ℹ️").markdown(f"_{msg_content}_")
                except Exception as e:
                    print(f"Error rendering message (idx: {idx}): Role={role}, Avatar={avatar}, Exc={e}")
                    st.error(f"메시지 렌더링 중 오류 발생: {str(msg_content)[:30]}...")

    # 입력 UI 부분
    input_container = st.container()
    with input_container:
        current_analysis_phase = st.session_state.get("analysis_phase", "idle")

        if current_analysis_phase == "idle":
            # 추가 정보 입력 버튼 (토글 방식)
            additional_info_button_label = "아이디어 상세 정보 숨기기" if st.session_state.get("show_additional_info") else "아이디어 상세 정보 입력 (선택)"
            if st.button(additional_info_button_label, key="toggle_additional_info_button"):
                st.session_state.show_additional_info = not st.session_state.get("show_additional_info", False)
                if st.session_state.show_additional_info:
                     st.session_state.expander_state = True # 펼칠 때만 True
                st.session_state.need_rerun = True

            if st.session_state.get("show_additional_info"):
                with st.expander("아이디어 상세 정보", expanded=st.session_state.get("expander_state", True)):
                    st.text_area("아이디어의 핵심 목표 또는 해결하고자 하는 문제:", key="user_goal_input", value=st.session_state.get("user_goal",""))
                    st.text_area("주요 제약 조건 (예: 예산, 시간, 기술 등):", key="user_constraints_input", value=st.session_state.get("user_constraints",""))
                    st.text_area("중요하게 생각하는 가치 (예: 효율성, 창의성 등):", key="user_values_input", value=st.session_state.get("user_values",""))
                    if st.button("상세 정보 저장", key="save_additional_info"):
                        st.session_state.user_goal = st.session_state.user_goal_input
                        st.session_state.user_constraints = st.session_state.user_constraints_input
                        st.session_state.user_values = st.session_state.user_values_input
                        st.session_state.expander_state = False # 저장 후 닫기
                        st.session_state.show_additional_info = False # 저장 후 버튼 텍스트 변경 위해
                        st.success("상세 정보가 저장되었습니다.")
                        st.session_state.need_rerun = True
            
            user_input = st.chat_input("여기에 아이디어를 입력하고 Enter를 누르세요...")
            if user_input:
                if not st.session_state.get("user_goal"): # 상세정보가 입력되지 않았다면, 확장표시
                    st.session_state.show_additional_info = True
                    st.session_state.expander_state = True

                add_message("user", user_input)
                st.session_state.current_idea = user_input
                st.session_state.analysis_phase = "phase1_pending_start"
                st.session_state.need_rerun = True
        
        elif current_analysis_phase == "phase1_pending_start":
            if st.session_state.current_idea and st.session_state.current_idea != st.session_state.get("analyzed_idea"):
                with st.spinner("AI 페르소나가 아이디어를 분석 중입니다... 이 작업은 최대 1-2분 소요될 수 있습니다."):
                    # 상세 정보 저장 (만약 expanded 된 상태에서 아이디어만 바로 입력했을 경우 대비)
                    if st.session_state.get("show_additional_info"):
                         st.session_state.user_goal = st.session_state.get("user_goal_input", st.session_state.get("user_goal",""))
                         st.session_state.user_constraints = st.session_state.get("user_constraints_input", st.session_state.get("user_constraints",""))
                         st.session_state.user_values = st.session_state.get("user_values_input", st.session_state.get("user_values",""))
                    run_phase1_analysis_and_update_ui() # 여기서 분석 실행 및 상태 변경
            else: # 이미 분석된 아이디어거나 current_idea가 없는 경우 (보통 발생 안 함)
                st.session_state.analysis_phase = "idle" # 다시 idle로
                st.session_state.need_rerun = True


        elif current_analysis_phase == "phase1_complete":
            st.success("✔️ 1단계 아이디어 분석이 완료되었습니다.")
            
            col1, col2 = st.columns(2)
            with col1:
                if st.button("💬 2단계 토론 시작하기", key="start_phase2_button", use_container_width=True):
                    st.session_state.analysis_phase = "phase2_pending_start" 
                    st.session_state.proceed_to_phase2 = True
                    print("User selected to start Phase 2 discussion.")
                    st.session_state.need_rerun = True
            
            with col2:
                if st.button("✨ 새 아이디어 분석", key="new_idea_after_phase1_button", use_container_width=True):
                    restart_session(keep_messages=False)
                    print("User selected to analyze a new idea after Phase 1 completion.")

        elif current_analysis_phase == "phase1_error":
            # 오류 메시지는 show_system_message를 통해 이미 messages에 추가되었을 것임
            
            col_retry, col_restart_new = st.columns(2)
            with col_retry:
                if st.button("같은 아이디어로 재시도", key="retry_button_error", use_container_width=True):
                    st.session_state.analysis_phase = "phase1_pending_start" 
                    st.session_state.analyzed_idea = "" 
                    st.session_state.need_rerun = True
            with col_restart_new:
                if st.button("새 아이디어로 시작", key="restart_button_error", use_container_width=True):
                    restart_session(keep_messages=False)
        
        elif current_analysis_phase == "phase2_pending_start":
            # 2단계 토론 시작 처리
            with st.spinner("2단계 토론을 준비 중입니다..."):
                handle_phase2_discussion()
                
        elif current_analysis_phase == "phase2_running":
            # 토론 진행 중 표시
            st.info("AI 페르소나들이 토론 중입니다...")
            # 토론 진행이 이미 handle_phase2_discussion에서 처리되고 있으므로 별도 액션 불필요
            pass
            
        elif current_analysis_phase == "phase2_user_input":
            # 사용자 입력을 받아야 하는 상태
            if st.session_state.awaiting_user_input_phase2:
                st.info(f"토론에 참여해 주세요: {st.session_state.phase2_user_prompt}")
                user_response = st.chat_input("여기에 의견을 입력하고 Enter를 누르세요...")
                
                if user_response:
                    # 사용자 입력을 UI에 표시
                    add_message("user", user_response)
                    
                    # 입력값 저장 및 토론 계속 진행
                    st.session_state.phase2_user_response = user_response
                    st.session_state.analysis_phase = "phase2_running"
                    st.session_state.need_rerun = True
                    
                    # 토론 처리 함수 재호출
                    handle_phase2_discussion()
        
        elif current_analysis_phase == "phase2_complete":
            # 2단계 토론 완료 표시
            st.success("✔️ 2단계 토론과 최종 요약이 완료되었습니다.")
            
            if st.button("✨ 새 아이디어 분석", key="new_idea_after_phase2_button", use_container_width=True):
                restart_session(keep_messages=False)
                print("User selected to analyze a new idea after Phase 2 completion.")
                
        elif current_analysis_phase == "phase2_error":
            # 2단계 토론 중 오류 발생
            col_retry, col_restart_new = st.columns(2)
            with col_retry:
                if st.button("같은 아이디어로 재시도", key="retry_phase2_button_error", use_container_width=True):
                    st.session_state.analysis_phase = "phase2_pending_start" 
                    st.session_state.awaiting_user_input_phase2 = False
                    st.session_state.phase2_discussion_complete = False
                    st.session_state.phase2_summary_complete = False
                    st.session_state.need_rerun = True
            with col_restart_new:
                if st.button("새 아이디어로 시작", key="restart_phase2_button_error", use_container_width=True):
                    restart_session(keep_messages=False)
    
    if st.session_state.get("need_rerun", False):
        st.session_state.need_rerun = False
        st.rerun()

if __name__ == "__main__":
    main()