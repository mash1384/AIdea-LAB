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

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from src.orchestrator.main_orchestrator import AIdeaLabOrchestrator
from src.session_manager import SessionManager
from config.personas import PERSONA_CONFIGS, PersonaType, ORCHESTRATOR_CONFIG, PERSONA_SEQUENCE
from config.models import get_model_display_options, MODEL_CONFIGS, ModelType, DEFAULT_MODEL

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit 페이지 설정
st.set_page_config(
    page_title="AIdea Lab - 아이디어 분석 워크숍",
    page_icon="🧠",
    layout="centered"
)

# 앱 정보
APP_NAME = "AIdea Lab"
USER_ID = "streamlit_user"

# 세션 관리자 초기화
session_manager = SessionManager(APP_NAME, USER_ID)

# 시스템 안내 메시지 템플릿 정의
SYSTEM_MESSAGES = {
    "welcome": "**AIdea Lab에 오신 것을 환영합니다.** 당신의 아이디어를 입력하시면 AI 페르소나들이 다양한 관점에서 분석해드립니다.",
    "phase1_start": "**분석을 시작합니다.** 각 AI 페르소나가 순차적으로 의견을 제시할 예정입니다.",
    "marketer_intro": "**💡 아이디어 마케팅 분석가의 의견:**",
    "critic_intro": "**🔍 비판적 분석가의 의견:**",
    "engineer_intro": "**⚙️ 현실주의 엔지니어의 의견:**",
    "summary_phase1_intro": "**📝 최종 요약 및 종합:**", # summary_phase1 키와 일치하도록 수정
    "phase1_complete": "**1단계 분석이 완료되었습니다.**",
    "phase1_error": "**분석 중 오류가 발생했습니다.** 다시 시도하거나 새로운 아이디어를 입력해주세요."
    # 2단계 관련 메시지 (추후 추가)
    # "phase2_welcome": "**2단계 심층 토론을 시작합니다.** 각 페르소나와 자유롭게 의견을 나눠보세요."
}

# 페르소나 아바타 정의
persona_avatars = {
    "marketer": "💡",
    "critic": "🔍",
    "engineer": "⚙️",
    "summary_phase1": "📝" # orchestrator.get_output_keys_phase1()의 키와 일치
}

print(f"Initialized persona avatars: {persona_avatars}")


# 텍스트를 단어 단위로 스트리밍하는 함수 (구현 계획서에 따라, 현재는 직접 사용되지 않음)
def stream_text_generator(text: str):
    words = text.split(' ')
    for word in words:
        yield word + " "
        time.sleep(0.05) # 단어 사이에 약간의 지연 추가

# --- run_phase1_analysis_and_update_ui 내부에서 호출될 비동기 함수 ---
async def _run_phase1_analysis(runner: Runner, session_id_string: str, content: types.Content, orchestrator: AIdeaLabOrchestrator):
    print(f"DEBUG: _run_phase1_analysis - Starting with session_id: {session_id_string}")
    
    workflow_completed = False
    any_response_processed_successfully = False
    
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
            # print(f"DEBUG_EVENT_DETAILS: Event ID={getattr(event,'id','N/A')}, Timestamp={getattr(event,'timestamp','N/A')}, Content={getattr(event,'content',None)}, Actions={event_actions}")

            if is_final_event and state_delta:
                for output_key_in_delta, response_text in state_delta.items():
                    if output_key_in_delta in output_keys_map.values() and output_key_in_delta not in processed_sub_agent_outputs:
                        if response_text and isinstance(response_text, str) and len(response_text.strip()) > 10:
                            print(f"DEBUG: Valid response text found for output_key '{output_key_in_delta}' from agent '{agent_author}'.")
                            
                            processed_sub_agent_outputs.add(output_key_in_delta)
                            any_response_processed_successfully = True

                            persona_key_for_display = output_key_to_persona_key_map.get(output_key_in_delta)
                            
                            if persona_key_for_display:
                                intro_message_key_base = persona_key_for_display
                                intro_message_key = f"{intro_message_key_base}_intro" 
                                # summary_phase1의 경우 intro_message_key는 "summary_phase1_intro"가 됨
                                intro_content = SYSTEM_MESSAGES.get(intro_message_key)
                                avatar_char = persona_avatars.get(intro_message_key_base, "🤖")

                                if intro_content:
                                    add_message("system", intro_content, avatar="ℹ️")
                                else: # intro 메시지를 찾지 못한 경우 로그 남기기 (특히 summary_phase1_intro 확인)
                                     print(f"WARNING: Intro message content not found for key '{intro_message_key}' (Persona key: {persona_key_for_display})")

                                add_message("assistant", process_text_for_display(response_text), avatar=avatar_char)
                            else:
                                print(f"WARNING: Could not map output_key '{output_key_in_delta}' to persona_key for UI display (Agent: {agent_author}).")
                        else:
                            print(f"WARNING: No/empty/short response for output_key '{output_key_in_delta}' from agent '{agent_author}'. Text: '{response_text}'")
        
        if len(processed_sub_agent_outputs) >= expected_sub_agent_output_count:
            print(f"DEBUG: All {expected_sub_agent_output_count} expected outputs processed: {processed_sub_agent_outputs}.")
            workflow_completed = True
        else:
            print(f"WARNING: Workflow incomplete. Expected {expected_sub_agent_output_count}, processed {len(processed_sub_agent_outputs)}: {list(processed_sub_agent_outputs)}")

        if any_response_processed_successfully or workflow_completed:
             st.session_state.need_rerun = True

        print(f"DEBUG: _run_phase1_analysis - Finished. WorkflowCompleted={workflow_completed}, AnyResponseProcessed={any_response_processed_successfully}")
        return workflow_completed and any_response_processed_successfully

    except Exception as e:
        print(f"ERROR in _run_phase1_analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        st.session_state.need_rerun = True 
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
        
        session_object, session_id_string = session_manager.start_new_idea_session(
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
            session_service=session_manager.session_service 
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
        'proceed_to_phase2' 
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

def main():
    initialize_session_state()
    
    st.title("AIdea Lab - 아이디어 분석 워크숍")
    st.markdown("당신의 아이디어를 AI가 다양한 관점에서 분석해드립니다!")
    
    # 모델 선택 UI
    model_options = [model.value for model in ModelType]
    default_model_value = st.session_state.get('selected_model', DEFAULT_MODEL.value)
    try:
        default_index = model_options.index(default_model_value)
    except ValueError:
        default_index = 0 # 기본값이 옵션에 없으면 첫번째 선택
        st.session_state.selected_model = model_options[0] if model_options else DEFAULT_MODEL.value

    selected_model_value_from_ui = st.selectbox(
        "AI 모델 선택",
        options=model_options,
        index=default_index,
        key="model_selector_widget"
    )
    if st.session_state.selected_model != selected_model_value_from_ui:
        st.session_state.selected_model = selected_model_value_from_ui
        print(f"Model selection changed to: {st.session_state.selected_model}. Restarting session.")
        restart_session(keep_messages=False) # 모델 변경 시 메시지 초기화하고 rerun
        # restart_session에서 need_rerun = True 설정되므로 여기서 추가 설정 불필요

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
                    # show_system_message("phase2_welcome") # 2단계 시작 메시지 (필요시)
                    print("User selected to start Phase 2 discussion.")
                    st.session_state.need_rerun = True
            
            with col2:
                if st.button("✨ 새 아이디어 분석", key="new_idea_after_phase1_button", use_container_width=True):
                    restart_session(keep_messages=False)
                    # analysis_phase는 restart_session 내부에서 idle로 설정됨 (initialize_session_state 호출)
                    print("User selected to analyze a new idea after Phase 1 completion.")
                    # st.session_state.need_rerun = True # restart_session 에서 이미 설정

        elif current_analysis_phase == "phase1_error":
            # 오류 메시지는 show_system_message를 통해 이미 messages에 추가되었을 것임
            # st.error("분석 중 문제가 발생했습니다.") # 중복될 수 있으므로 제거하거나 유지
            
            col_retry, col_restart_new = st.columns(2)
            with col_retry:
                if st.button("같은 아이디어로 재시도", key="retry_button_error", use_container_width=True):
                    # 메시지 기록에서 마지막 사용자 아이디어와 오류 관련 시스템 메시지 제거 (선택적)
                    # 예: st.session_state.messages = [m for m in st.session_state.messages if m.get("role") == "assistant" and "환영합니다" in m.get("content","")]
                    # 위와 같이 하거나, 그냥 메시지를 유지하고 재시도
                    st.session_state.analysis_phase = "phase1_pending_start" 
                    st.session_state.analyzed_idea = "" 
                    # 오류 관련 시스템 메시지를 한번 더 보여주는 것 방지 위해, 마지막 메시지 검사 후 추가
                    # show_system_message("phase1_start", rerun_immediately=True) # 이미 phase1_start 메시지는 있을 것임
                    st.session_state.need_rerun = True
            with col_restart_new:
                if st.button("새 아이디어로 시작", key="restart_button_error", use_container_width=True):
                    restart_session(keep_messages=False)
        
        elif current_analysis_phase == "phase2_pending_start":
            st.info("2단계 토론 기능은 현재 개발 중입니다. 곧 만나보실 수 있습니다! 😊")
            if st.button("돌아가기", key="back_to_phase1_complete"):
                st.session_state.analysis_phase = "phase1_complete" # 이전 상태로
                st.session_state.proceed_to_phase2 = False
                st.session_state.need_rerun = True
    
    if st.session_state.get("need_rerun", False):
        st.session_state.need_rerun = False
        st.rerun()

if __name__ == "__main__":
    main()