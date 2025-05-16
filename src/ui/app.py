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

# 애플리케이션 상태 관리를 위한 클래스
class AppStateManager:
    """
    애플리케이션 상태를 관리하는 클래스
    Streamlit의 session_state를 캡슐화하여 상태 접근과 변경을 일관되게 처리합니다.
    """
    
    @staticmethod
    def initialize_session_state():
        """세션 상태 초기화"""
        # SessionManager 객체 초기화
        if 'session_manager_instance' not in st.session_state:
            print("Creating new SessionManager instance and storing in st.session_state")
            st.session_state.session_manager_instance = SessionManager(APP_NAME, USER_ID)
        
        # 기본 상태 변수 초기화
        default_states = {
            'session_counter': 0,
            'selected_model': DEFAULT_MODEL.value,
            'messages': [],
            'current_idea': "",
            'analyzed_idea': "",
            'analysis_phase': "idle",
            'adk_session_id': None,
            'user_goal': "",
            'user_constraints': "",
            'user_values': "",
            'show_additional_info': False,
            'expander_state': False,
            'proceed_to_phase2': False,
            'awaiting_user_input_phase2': False,
            'phase2_user_prompt': "",
            'phase2_discussion_complete': False,
            'phase2_summary_complete': False
        }
        
        # 없는 상태만 초기화
        for key, value in default_states.items():
            if key not in st.session_state:
                st.session_state[key] = value
        
        # 웰컴 메시지 추가 (messages 배열이 비어있을 때만)
        if not st.session_state.messages:
            try:
                welcome_message = SYSTEM_MESSAGES.get("welcome")
                AppStateManager.add_message("assistant", welcome_message, avatar="🧠")
            except Exception as e:
                print(f"Error adding welcome message: {str(e)}")
                AppStateManager.add_message("assistant", "AIdea Lab에 오신 것을 환영합니다.", avatar="🧠")
    
    @staticmethod
    def restart_session(keep_messages=False):
        """세션 재시작"""
        print("Restarting session...")
        
        # 현재 메시지 백업 (keep_messages가 True일 경우 사용)
        messages_backup = list(st.session_state.get("messages", [])) 
        
        # 재설정할 상태 키 목록
        keys_to_reset = [
            'current_idea', 'analyzed_idea', 'analysis_phase', 
            'adk_session_id', 'user_goal', 'user_constraints', 'user_values',
            'proceed_to_phase2', 'awaiting_user_input_phase2', 'phase2_user_prompt',
            'phase2_discussion_complete', 'phase2_summary_complete'
        ]
        
        # 상태 재설정
        for key in keys_to_reset:
            if key in st.session_state:
                del st.session_state[key]
        
        # 기본 상태 재초기화
        AppStateManager.initialize_session_state()
        
        # 메시지 처리
        if keep_messages:
            st.session_state.messages = messages_backup
        else:
            st.session_state.messages = []
            try:
                welcome_message = SYSTEM_MESSAGES.get("welcome")
                AppStateManager.add_message("assistant", welcome_message, avatar="🧠")
            except Exception as e:
                print(f"Error re-adding welcome message: {str(e)}")
                AppStateManager.add_message("assistant", "AIdea Lab에 오신 것을 환영합니다.", avatar="🧠")
        
        print("Session restart completed")
        # st.rerun()  # 세션 재시작 후 UI 갱신 - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def add_message(role, content, avatar=None):
        """메시지 추가"""
        if content is None:
            print(f"Skipping add_message for role {role} because content is None.")
            return
        
        print(f"Adding message - Role: {role}, Avatar: {avatar}, Content preview: {str(content)[:70]}...")
        
        # 메시지 객체 생성
        message_obj = {"role": role, "content": content, "avatar": avatar}
        
        # 현재 메시지 목록 가져오기
        if 'messages' not in st.session_state:
            st.session_state.messages = []
        
        # 연속 중복 시스템 메시지 방지
        is_system_message_type = avatar == "ℹ️"
        if is_system_message_type and st.session_state.messages:
            last_message = st.session_state.messages[-1]
            if (last_message.get("role") == role and 
                last_message.get("content") == content and 
                last_message.get("avatar") == avatar):
                print("Consecutive duplicate system message skipped.")
                return
        
        # 메시지 추가
        st.session_state.messages.append(message_obj)
        print(f"Message added. Total messages: {len(st.session_state.messages)}")
    
    @staticmethod
    def show_system_message(message_key):
        """시스템 메시지 표시"""
        message_content = SYSTEM_MESSAGES.get(message_key)
        if message_content:
            print(f"Showing system message for key '{message_key}': {message_content[:70]}...")
            AppStateManager.add_message("system", message_content, avatar="ℹ️")
        else:
            print(f"WARNING: System message key '{message_key}' not defined in SYSTEM_MESSAGES.")
    
    @staticmethod
    def get_state(key, default=None):
        """상태 값 가져오기"""
        return st.session_state.get(key, default)
    
    @staticmethod
    def set_state(key, value):
        """상태 값 설정"""
        st.session_state[key] = value
    
    @staticmethod
    def change_analysis_phase(new_phase):
        """분석 단계 변경"""
        print(f"Changing analysis phase from '{st.session_state.get('analysis_phase', 'unknown')}' to '{new_phase}'")
        st.session_state.analysis_phase = new_phase
    
    @staticmethod
    def process_text_for_display(text_data):
        """텍스트 표시용 처리"""
        if not isinstance(text_data, str):
            text_data = str(text_data)
        return text_data.replace("\n", "  \n")
    
    @staticmethod
    def toggle_additional_info():
        """추가 정보 표시 토글"""
        show_info = st.session_state.get("show_additional_info", False)
        st.session_state.show_additional_info = not show_info
        if not show_info:  # False에서 True로 변경될 때만 expander 펼치기
            st.session_state.expander_state = True
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def save_additional_info():
        """추가 정보 저장"""
        st.session_state.user_goal = st.session_state.user_goal_input
        st.session_state.user_constraints = st.session_state.user_constraints_input
        st.session_state.user_values = st.session_state.user_values_input
        st.session_state.expander_state = False
        st.session_state.show_additional_info = False
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def submit_idea(idea_text):
        """아이디어 제출"""
        if not idea_text:
            return
            
        # 상세정보가 입력되지 않았다면 확장 표시
        if not st.session_state.get("user_goal"):
            st.session_state.show_additional_info = True
            st.session_state.expander_state = True
        
        AppStateManager.add_message("user", idea_text)
        st.session_state.current_idea = idea_text
        AppStateManager.change_analysis_phase("phase1_pending_start")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def start_phase2_discussion():
        """2단계 토론 시작"""
        AppStateManager.change_analysis_phase("phase2_pending_start")
        st.session_state.proceed_to_phase2 = True
        print("User selected to start Phase 2 discussion.")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def submit_phase2_response(response_text):
        """2단계 사용자 응답 제출"""
        if not response_text:
            return
            
        AppStateManager.add_message("user", response_text)
        st.session_state.phase2_user_response = response_text
        AppStateManager.change_analysis_phase("phase2_running")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def retry_analysis():
        """동일 아이디어로 분석 재시도"""
        st.session_state.analysis_phase = "phase1_pending_start"
        st.session_state.analyzed_idea = ""
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def retry_phase2():
        """2단계 토론 재시도"""
        AppStateManager.change_analysis_phase("phase2_pending_start")
        st.session_state.awaiting_user_input_phase2 = False
        st.session_state.phase2_discussion_complete = False
        st.session_state.phase2_summary_complete = False
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def change_model(new_model_id):
        """모델 변경"""
        if st.session_state.selected_model != new_model_id:
            st.session_state.selected_model = new_model_id
            print(f"Model selection changed to: {new_model_id}")
            AppStateManager.restart_session()

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
    # 중간 요약 소개 메시지 추가
    "marketer_summary_intro": "**📄 마케터 보고서 요약:**",
    "critic_summary_intro": "**📄 비판적 분석가 보고서 요약:**",
    "engineer_summary_intro": "**📄 현실주의 엔지니어 보고서 요약:**",
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
    "final_summary_phase2": "📊",
    # 중간 요약 아바타 추가
    "marketer_summary": "📄",
    "critic_summary": "📄",
    "engineer_summary": "📄"
}

print(f"Initialized persona avatars: {persona_avatars}")

# 모델 모니터링 인스턴스 생성
model_monitor = AIModelMonitor(log_file_path="logs/model_performance.json")

# monitor_model_performance 데코레이터 적용 (기존 함수 앞에 추가)
@monitor_model_performance(model_monitor)
async def _run_phase1_analysis(runner: Runner, session_id_string: str, content: types.Content, orchestrator: AIdeaLabOrchestrator):
    """
    1단계 분석을 실행하는 비동기 함수
    
    Args:
        runner: ADK Runner 인스턴스
        session_id_string: 세션 ID
        content: 입력 콘텐츠
        orchestrator: 오케스트레이터 인스턴스
    
    Returns:
        tuple: (성공 여부, 처리된 결과 키 목록)
    """
    print(f"DEBUG: _run_phase1_analysis - Starting with session_id: {session_id_string}")
    
    workflow_completed = False
    any_response_processed_successfully = False
    processed_sub_agent_outputs = set()
    
    # 응답 검증 및 대체 메커니즘 함수
    def validate_agent_response(response_text, agent_name, output_key):
        # 중간 요약 응답인지 확인
        is_summary_response = "_summary" in output_key
        
        # 기본 유효성 검사: 응답이 없거나 문자열이 아니거나 너무 짧은 경우
        if not response_text:
            print(f"DEBUG_VALIDATION: OutputKey '{output_key}', Reason: Response is empty or None.")
            basic_validation_failed = True
        elif not isinstance(response_text, str):
            print(f"DEBUG_VALIDATION: OutputKey '{output_key}', Reason: Response is not a string (type: {type(response_text)}).")
            basic_validation_failed = True
        elif len(response_text.strip()) < 20:
            print(f"DEBUG_VALIDATION: OutputKey '{output_key}', Reason: Response length ({len(response_text.strip())}) is less than 20.")
            basic_validation_failed = True
        else:
            basic_validation_failed = False
        
        # 중간 요약 응답에 대한 추가 유효성 검사
        if is_summary_response and not basic_validation_failed:
            # "핵심 포인트:"와 "종합 요약:" 문자열이 모두 포함되어 있는지 확인
            has_key_points = "핵심 포인트:" in response_text
            has_summary = "종합 요약:" in response_text
            
            # 각 필수 요소에 대한 검증 로그 추가
            if not has_key_points:
                print(f"DEBUG_VALIDATION: OutputKey '{output_key}', Reason: Missing '핵심 포인트:' in summary.")
            
            if not has_summary:
                print(f"DEBUG_VALIDATION: OutputKey '{output_key}', Reason: Missing '종합 요약:' in summary.")
            
            # 두 문자열이 모두 포함되어 있지 않으면 유효하지 않음
            if not (has_key_points and has_summary):
                print(f"WARNING: Summary response from {agent_name} for {output_key} is missing required format elements. Generating fallback response.")
                basic_validation_failed = True
        
        # 유효하지 않은 응답에 대한 대체 응답 생성
        if basic_validation_failed:
            print(f"WARNING: Invalid response from {agent_name} for {output_key}. Generating fallback response.")
            
            # 기본 대체 응답 생성
            fallback_response = f"[{agent_name}에서 유효한 응답을 받지 못했습니다. 이 메시지는 자동 생성된 대체 응답입니다.]"
            
            # 중간 요약 응답인 경우, 지정된 형식에 맞는 대체 응답 생성
            if is_summary_response:
                fallback_response = """**핵심 포인트:**
- 이 보고서는 요약 중 오류가 발생하여 자동 생성되었습니다.
- 원본 보고서의 내용을 참고해주세요.

**종합 요약:**
해당 페르소나의 원본 보고서에 대한 요약 생성에 실패했습니다. 원본 보고서를 직접 확인해주시기 바랍니다."""
            
            return fallback_response
            
        return response_text
    
    # 결과 저장 및 UI 메시지 생성 함수
    def process_response(output_key, response_text, agent_name, session_manager):
        # 응답 검증 및 필요 시 대체 응답 생성
        validated_response = validate_agent_response(response_text, agent_name, output_key)
        
        # 응답이 변경되었으면 세션 상태 업데이트
        if validated_response != response_text:
            try:
                session = session_manager.get_session(session_id_string)
                if session:
                    event_actions = EventActions(
                        state_delta={output_key: validated_response}
                    )
                    new_event = Event(
                        actions=event_actions,
                        author=f"{agent_name}_fallback"
                    )
                    session_manager.session_service.append_event(
                        session=session,
                        event=new_event
                    )
                    print(f"INFO: Successfully updated session with fallback response for {output_key}")
            except Exception as e:
                print(f"ERROR: Failed to update session with fallback response: {e}")
        
        # 결과 및 UI 메시지 반환
        return {
            "output_key": output_key,
            "response": validated_response,
            "agent_name": agent_name
        }
    
    try:
        output_keys_map = orchestrator.get_output_keys_phase1() 
        output_key_to_persona_key_map = {v: k for k, v in output_keys_map.items()}

        expected_sub_agent_output_count = len(output_keys_map)
        print(f"DEBUG: Expected sub-agent output count: {expected_sub_agent_output_count}")
        print(f"DEBUG: Output keys to track from orchestrator: {output_keys_map}")

        # 결과를 저장할 리스트
        processed_results = []

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
                        # 원본 페르소나 보고서인 경우 길이를 로그로 출력
                        if "report_phase1" in output_key_in_delta and "_summary" not in output_key_in_delta:
                            print(f"DEBUG_REPORT_LENGTH: Agent '{agent_author}', OutputKey: '{output_key_in_delta}', Length: {len(response_text)} chars")
                            
                        # 중간 요약 에이전트의 응답인 경우 원본 응답을 로그로 출력
                        if "report_phase1_summary" in output_key_in_delta:
                            print(f"DEBUG_LLM_RAW_RESPONSE: Agent '{agent_author}', OutputKey: '{output_key_in_delta}', RawResponse: '{response_text}'")
                        
                        print(f"DEBUG: Valid response text found for output_key '{output_key_in_delta}' from agent '{agent_author}'.")
                        
                        # 응답 처리 및 결과 저장
                        result = process_response(
                            output_key_in_delta, 
                            response_text, 
                            agent_author,
                            st.session_state.session_manager_instance
                        )
                        
                        processed_results.append(result)
                        processed_sub_agent_outputs.add(output_key_in_delta)
                        any_response_processed_successfully = True
        
        # 진행 상황 확인 및 처리
        if len(processed_sub_agent_outputs) >= expected_sub_agent_output_count:
            print(f"DEBUG: All {expected_sub_agent_output_count} expected outputs processed: {processed_sub_agent_outputs}.")
            workflow_completed = True
        else:
            print(f"WARNING: Workflow incomplete. Expected {expected_sub_agent_output_count}, processed {len(processed_sub_agent_outputs)}: {list(processed_sub_agent_outputs)}")

        print(f"DEBUG: _run_phase1_analysis - Finished. WorkflowCompleted={workflow_completed}, AnyResponseProcessed={any_response_processed_successfully}")
        return (workflow_completed and any_response_processed_successfully, processed_results, processed_sub_agent_outputs)

    except Exception as e:
        print(f"ERROR in _run_phase1_analysis: {str(e)}")
        import traceback
        traceback.print_exc()
        return (False, [], processed_sub_agent_outputs)


def run_phase1_analysis_and_update_ui():
    """
    1단계 분석을 실행하고 UI를 업데이트하는 함수
    
    이 함수는 비동기 분석 작업을 호출하고, 결과를 UI에 반영합니다.
    """
    try:
        orchestrator = AIdeaLabOrchestrator(model_name=st.session_state.selected_model)
        print(f"Created local orchestrator with model: {st.session_state.selected_model}")
        
        # 분석 상태 업데이트
        AppStateManager.change_analysis_phase("phase1_running")
        AppStateManager.show_system_message("phase1_start")
        print("Phase 1 analysis initiated by user")
        
        # 사용자 입력 데이터 가져오기
        idea_text = st.session_state.current_idea
        user_goal = st.session_state.get("user_goal", "")
        user_constraints = st.session_state.get("user_constraints", "")
        user_values = st.session_state.get("user_values", "")
        print(f"Analyzing idea: {idea_text}, Goal: {user_goal}, Constraints: {user_constraints}, Values: {user_values}")
        
        # 새 세션 시작
        session_object, session_id_string = st.session_state.session_manager_instance.start_new_idea_session(
            idea_text,
            user_goal=user_goal,
            user_constraints=user_constraints,
            user_values=user_values
        )
        
        if not session_object or not session_id_string:
            print("ERROR: Failed to start new idea session in SessionManager.")
            AppStateManager.change_analysis_phase("phase1_error")
            AppStateManager.show_system_message("phase1_error")
            st.rerun()
            return

        st.session_state.adk_session_id = session_id_string
        print(f"New session started with ID: {session_id_string}, initial state verified in SessionManager.")
        
        # 1단계 워크플로우 에이전트 가져오기
        phase1_workflow_agent = orchestrator.get_phase1_workflow()
        print(f"Successfully retrieved phase1_workflow_agent: {phase1_workflow_agent.name if hasattr(phase1_workflow_agent, 'name') else 'N/A'}")

        # Runner 초기화
        runner = Runner(
            agent=phase1_workflow_agent,
            app_name=APP_NAME,
            session_service=st.session_state.session_manager_instance.session_service 
        )
        print(f"Successfully initialized ADK Runner with agent: {phase1_workflow_agent.name if hasattr(phase1_workflow_agent, 'name') else 'N/A'}")
        
        # 입력 내용 준비
        content_parts = [types.Part(text=f"아이디어: {idea_text}")]
        if user_goal: content_parts.append(types.Part(text=f"\n목표: {user_goal}"))
        if user_constraints: content_parts.append(types.Part(text=f"\n제약조건: {user_constraints}"))
        if user_values: content_parts.append(types.Part(text=f"\n가치: {user_values}"))
        
        input_content_for_runner = types.Content(role="user", parts=content_parts)
        print(f"Prepared input_content_for_runner: {input_content_for_runner}")
        
        # 분석 실행
        analysis_success, processed_results, processed_outputs = asyncio.run(_run_phase1_analysis(
            runner, 
            session_id_string, 
            input_content_for_runner, 
            orchestrator
        ))
        
        # UI에 결과 표시
        if processed_results:
            output_keys_map = orchestrator.get_output_keys_phase1()
            output_key_to_persona_key_map = {v: k for k, v in output_keys_map.items()}
            
            # 결과를 UI에 추가
            for result in processed_results:
                output_key = result["output_key"]
                response = result["response"]
                
                persona_key_for_display = output_key_to_persona_key_map.get(output_key)
                
                if persona_key_for_display:
                    # 페르소나 소개 메시지 표시
                    intro_message_key_base = persona_key_for_display
                    intro_message_key = f"{intro_message_key_base}_intro"
                    intro_content = SYSTEM_MESSAGES.get(intro_message_key)
                    avatar_char = persona_avatars.get(intro_message_key_base, "🤖")
                    
                    if intro_content:
                        AppStateManager.add_message("system", intro_content, avatar="ℹ️")
                        print(f"INFO: Adding intro message with key '{intro_message_key}' for persona '{persona_key_for_display}'")
                    else:
                        print(f"WARNING: Intro message content not found for key '{intro_message_key}' (Persona key: {persona_key_for_display})")
                    
                    # 페르소나 응답 표시
                    print(f"INFO: Using avatar '{avatar_char}' for persona '{persona_key_for_display}'")
                    AppStateManager.add_message("assistant", AppStateManager.process_text_for_display(response), avatar=avatar_char)
                else:
                    print(f"WARNING: Could not map output_key '{output_key}' to persona_key for UI display.")
        
        # 분석 완료 상태 업데이트
        if analysis_success:
            print("Phase 1 analysis processing was successful.")
            AppStateManager.show_system_message("phase1_complete")
            AppStateManager.change_analysis_phase("phase1_complete")
        else:
            print("Phase 1 analysis processing FAILED.")
            AppStateManager.change_analysis_phase("phase1_error")
            AppStateManager.show_system_message("phase1_error")
        
        st.session_state.analyzed_idea = idea_text
        st.rerun()  # UI 갱신
        
    except Exception as e:
        print(f"Critical error in run_phase1_analysis_and_update_ui: {str(e)}")
        import traceback
        traceback.print_exc()
        AppStateManager.change_analysis_phase("phase1_error")
        AppStateManager.show_system_message("phase1_error")
        st.rerun()  # UI 갱신

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
            AppStateManager.add_message("assistant", welcome_message, avatar="🧠") # 아바타 일관성
        except Exception as e:
            print(f"Error adding welcome message: {str(e)}")
            AppStateManager.add_message("assistant", "AIdea Lab에 오신 것을 환영합니다.", avatar="🧠")
    
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


def update_setting(key, value): # 현재 직접 사용되지 않지만 유틸리티로 유지
    setattr(st.session_state, key, value)

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
            AppStateManager.add_message("assistant", welcome_message, avatar="🧠")
        except Exception as e:
            print(f"Error re-adding welcome message: {str(e)}")
            AppStateManager.add_message("assistant", "AIdea Lab에 오신 것을 환영합니다.", avatar="🧠")
    
    print("Session restart logic completed.")


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

def show_system_message(message_key):
    """
    시스템 메시지 표시 (이전 방식, 제거 예정)
    
    AppStateManager.show_system_message()를 사용하도록 수정 중입니다.
    """
    message_content = SYSTEM_MESSAGES.get(message_key)
    if message_content:
        print(f"Showing system message for key '{message_key}': {message_content[:70]}...")
        AppStateManager.add_message("system", message_content, avatar="ℹ️")
    else:
        print(f"WARNING: System message key '{message_key}' not defined in SYSTEM_MESSAGES.")

# 토론 히스토리 상태 업데이트를 위한 유틸리티 함수
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


async def _run_phase2_discussion(session_id_string, orchestrator):
    """
    2단계 토론 실행 함수
    
    토론 퍼실리테이터 및 페르소나 에이전트들 간의 대화를 조율하고 결과를 구조화된 리스트로 반환합니다.
    UI를 직접 업데이트하거나 st.rerun()을 호출하지 않습니다.
    
    Args:
        session_id_string (str): 세션 ID
        orchestrator (AIdeaLabOrchestrator): 오케스트레이터 객체
    
    Returns:
        tuple: (토론 메시지 리스트, 상태 문자열, 사용자 질문(있는 경우))
              상태 문자열은 "진행 중", "완료", "사용자 입력 대기" 중 하나입니다.
    """
    print(f"DEBUG: _run_phase2_discussion - Starting with session_id: {session_id_string}")
    
    # 토론 메시지를 저장할 리스트 초기화
    discussion_messages = []
    
    # 페르소나의 첫 등장 여부를 추적
    persona_first_appearance = {
        "facilitator": True,
        "marketer_agent": True,
        "critic_agent": True,
        "engineer_agent": True,
        "final_summary": True
    }
    
    try:
        session = st.session_state.session_manager_instance.get_session(session_id_string)
        if not session:
            print(f"ERROR: Failed to get session with ID {session_id_string} in _run_phase2_discussion.")
            return discussion_messages, "오류", None

        # 각 에이전트의 응답을 표시할 때 사용할 아바타 매핑
        agent_to_avatar_map = {
            "facilitator": "🎯",
            "marketer_agent": "💡",
            "critic_agent": "🔍",
            "engineer_agent": "⚙️",
            "user": "🧑‍💻",
            "final_summary": "📊"
        }
        
        # 에이전트 이름 매핑
        agent_name_map = {
            "marketer_agent": "마케팅 분석가",
            "critic_agent": "비판적 분석가",
            "engineer_agent": "현실주의 엔지니어",
            "facilitator": "토론 진행자",
            "user": "사용자",
            "final_summary": "최종 요약"
        }
        
        # 페르소나 소개 메시지 키 매핑
        persona_intro_key_map = {
            "facilitator": "facilitator_intro",
            "marketer_agent": "marketer_phase2_intro",
            "critic_agent": "critic_phase2_intro",
            "engineer_agent": "engineer_phase2_intro",
            "final_summary": "final_summary_phase2_intro"
        }
        
        # 토론 퍼실리테이터 에이전트 가져오기
        facilitator_agent = orchestrator.get_phase2_discussion_facilitator()
        
        # 최대 토론 반복 횟수
        max_discussion_rounds = 15
        current_round = 0
        
        # 사용자 입력 대기 상태 확인
        if st.session_state.awaiting_user_input_phase2:
            # 사용자 입력이 있은 경우, 토론 히스토리에 추가
            user_response = st.session_state.get("phase2_user_response", "")
            if user_response:
                update_discussion_history(session_id_string, "user", user_response)
                
                # 사용자 응답을 토론 메시지에 추가
                discussion_messages.append({
                    "role": "user",
                    "content": user_response,
                    "avatar": agent_to_avatar_map["user"],
                    "speaker": "user",
                    "speaker_name": agent_name_map["user"]
                })
                
                # 사용자 입력 대기 상태 초기화
                st.session_state.awaiting_user_input_phase2 = False
                st.session_state.phase2_user_prompt = ""
        
        # 토론 루프 시작
        while current_round <= max_discussion_rounds:
            current_round += 1
            print(f"DEBUG: Starting discussion round {current_round}/{max_discussion_rounds}")
            
            try:
                # 퍼실리테이터 에이전트 실행
                runner = Runner(
                    agent=facilitator_agent,
                    app_name=APP_NAME,
                    session_service=st.session_state.session_manager_instance.session_service
                )
                
                input_content = types.Content(role="user", parts=[types.Part(text="")])
                
                # 퍼실리테이터 에이전트의 응답 처리
                next_agent = None
                topic_for_next = ""
                
                # 퍼실리테이터 사고 중 메시지는 생성하되 리스트에 추가하지 않음
                print("토론 퍼실리테이터가 다음 단계를 결정하고 있습니다...")
                
                event_stream = runner.run_async(
                    user_id=USER_ID,
                    session_id=session_id_string,
                    new_message=input_content
                )
                
                facilitator_response = None
                
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
                            
                            # 토론 히스토리에 퍼실리테이터 발언 추가
                            update_discussion_history(session_id_string, "facilitator", facilitator_response)
                            
                            # facilitator_response에서 JSON 부분 추출
                            import re
                            import json
                            
                            # 더 정확한 JSON 추출을 위한 패턴 개선
                            json_in_code_block = re.search(r'```(?:json)?\s*({[\s\S]*?})\s*```', facilitator_response)
                            json_matches = re.findall(r'({[\s\S]*?})', facilitator_response)
                            
                            parsed_successfully = False
                            json_data = None
                            json_str_attempted = None
                            
                            # 먼저 코드 블록 내 JSON 파싱 시도
                            if json_in_code_block:
                                json_str_attempted = json_in_code_block.group(1)
                                try:
                                    json_data = json.loads(json_str_attempted)
                                    parsed_successfully = True
                                    print(f"INFO: Successfully parsed JSON from code block")
                                except json.JSONDecodeError as e:
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
                                        continue
                            
                            # 마지막 시도: 응답 전체를 JSON으로 파싱
                            if not parsed_successfully:
                                json_str_attempted = facilitator_response
                                try:
                                    json_data = json.loads(facilitator_response)
                                    parsed_successfully = True
                                    print(f"INFO: Parsed entire response as JSON")
                                except json.JSONDecodeError as e:
                                    print(f"ERROR: Failed to parse any JSON from facilitator_response: {e}")
                                    print(f"Response is not valid JSON: {facilitator_response[:200]}...")
                            
                            if parsed_successfully and json_data:
                                next_agent = json_data.get("next_agent", "")
                                topic_for_next = json_data.get("message_to_next_agent_or_topic", "")
                                reasoning = json_data.get("reasoning", "")
                                
                                # 마지막 라운드에 도달했는데 FINAL_SUMMARY가 아니라면 강제로 FINAL_SUMMARY로 설정
                                if current_round >= max_discussion_rounds and next_agent != "FINAL_SUMMARY":
                                    print(f"INFO: Forcing transition to FINAL_SUMMARY at round {current_round}/{max_discussion_rounds}")
                                    next_agent = "FINAL_SUMMARY"
                                    topic_for_next = "최대 토론 라운드에 도달하여 최종 요약을 진행합니다."
                                
                                print(f"DEBUG: Extracted JSON data from facilitator_response:")
                                print(f"  - next_agent: {next_agent}")
                                print(f"  - topic: {topic_for_next[:50]}...")
                                print(f"  - reasoning: {reasoning[:50]}...")
                                
                                # 퍼실리테이터 첫 등장 시 소개 메시지 추가
                                if persona_first_appearance.get("facilitator", True):
                                    intro_key = persona_intro_key_map.get("facilitator")
                                    intro_content = SYSTEM_MESSAGES.get(intro_key)
                                    if intro_content:
                                        discussion_messages.append({
                                            "role": "system",
                                            "content": intro_content,
                                            "avatar": "ℹ️",
                                            "speaker": "system",
                                            "speaker_name": "시스템"
                                        })
                                    persona_first_appearance["facilitator"] = False
                                
                                # 퍼실리테이터 메시지를 사용자 친화적인 형태로 가공
                                facilitator_ui_message = ""
                                
                                # 다음 에이전트에 따라 메시지 형식 조정
                                if next_agent == "USER":
                                    # 사용자에게 질문 형태로 메시지 표시
                                    facilitator_ui_message = topic_for_next
                                elif next_agent == "FINAL_SUMMARY":
                                    # 최종 요약으로 전환 메시지
                                    facilitator_ui_message = "토론이 충분히 이루어졌습니다. 지금까지 논의된 내용을 최종 요약하겠습니다."
                                    if reasoning:
                                        facilitator_ui_message += f"\n\n이유: {reasoning}"
                                else:
                                    # 특정 페르소나 지목 시 메시지
                                    agent_display_name = agent_name_map.get(next_agent, next_agent)
                                    
                                    # 토픽과 이유를 결합하여 간결한 안내 메시지 생성
                                    facilitator_ui_message = f"다음은 {agent_display_name}에게 질문드립니다: {topic_for_next}"
                                    if reasoning:
                                        facilitator_ui_message += f" (이유: {reasoning})"
                                
                                # 가공된 퍼실리테이터 메시지를 리스트에 추가
                                discussion_messages.append({
                                    "role": "assistant",
                                    "content": facilitator_ui_message,
                                    "avatar": agent_to_avatar_map["facilitator"],
                                    "speaker": "facilitator",
                                    "speaker_name": agent_name_map["facilitator"]
                                })
                                
                            else:
                                # JSON 파싱 실패 시 오류 처리
                                print(f"ERROR: Could not extract valid JSON from facilitator_response")
                                if json_str_attempted:
                                    print(f"Last JSON string attempted to parse: {json_str_attempted[:200]}...")
                                
                                # 오류 발생 시 기본값 설정
                                next_agent = "FINAL_SUMMARY"
                                topic_for_next = "토론 진행 중 오류가 발생하여 최종 요약으로 진행합니다."
                                
                                # 오류 메시지를 리스트에 추가
                                discussion_messages.append({
                                    "role": "system",
                                    "content": "토론 진행 중 오류가 발생했습니다.",
                                    "avatar": "ℹ️",
                                    "speaker": "system",
                                    "speaker_name": "시스템"
                                })
                
                # 다음 에이전트가 없거나 빈 문자열이면 종료
                if not next_agent:
                    print("WARNING: next_agent is None or empty, ending discussion loop")
                    break
                
                # 라우팅 처리
                if next_agent == "USER":
                    # 사용자 질문 표시 메시지를 리스트에 추가
                    discussion_messages.append({
                        "role": "system",
                        "content": SYSTEM_MESSAGES.get("user_prompt", "사용자 의견이 필요합니다:"),
                        "avatar": "ℹ️",
                        "speaker": "system",
                        "speaker_name": "시스템"
                    })
                    
                    # 사용자 입력 대기 상태 설정
                    st.session_state.awaiting_user_input_phase2 = True
                    st.session_state.phase2_user_prompt = topic_for_next
                    
                    # 사용자 입력을 기다리기 위해 루프를 빠져나감
                    return discussion_messages, "사용자 입력 대기", topic_for_next
                
                elif next_agent == "FINAL_SUMMARY":
                    # 최종 요약으로 이동
                    print("DEBUG: Facilitator requested FINAL_SUMMARY, ending discussion loop")
                    st.session_state.phase2_discussion_complete = True
                    
                    # 토론 완료 메시지 추가
                    discussion_messages.append({
                        "role": "system",
                        "content": "토론이 완료되었습니다. 최종 요약을 생성합니다.",
                        "avatar": "ℹ️",
                        "speaker": "system",
                        "speaker_name": "시스템"
                    })
                    
                    # 최종 요약 에이전트 실행
                    final_summary_agent = orchestrator.get_phase2_final_summary_agent()
                    
                    runner = Runner(
                        agent=final_summary_agent,
                        app_name=APP_NAME,
                        session_service=st.session_state.session_manager_instance.session_service
                    )
                    
                    # 빈 메시지로 실행하여 세션 상태를 직접 참조하도록 함
                    input_content = types.Content(role="user", parts=[types.Part(text="")])
                    
                    # 최종 요약 생성 중 메시지
                    print("최종 요약을 생성하고 있습니다...")
                    
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
                                # 최종 요약 소개 메시지 추가
                                if persona_first_appearance.get("final_summary", True):
                                    intro_key = persona_intro_key_map.get("final_summary")
                                    intro_content = SYSTEM_MESSAGES.get(intro_key)
                                    if intro_content:
                                        discussion_messages.append({
                                            "role": "system",
                                            "content": intro_content,
                                            "avatar": "ℹ️",
                                            "speaker": "system",
                                            "speaker_name": "시스템"
                                        })
                                    persona_first_appearance["final_summary"] = False
                                
                                # 최종 요약 내용 리스트에 추가
                                discussion_messages.append({
                                    "role": "assistant",
                                    "content": final_summary,
                                    "avatar": agent_to_avatar_map["final_summary"],
                                    "speaker": "final_summary",
                                    "speaker_name": agent_name_map["final_summary"]
                                })
                                
                                # 토론 히스토리에 최종 요약 추가
                                update_discussion_history(session_id_string, "final_summary", final_summary)
                                
                                final_summary_processed = True
                    
                    # 최종 요약 완료 상태 설정
                    st.session_state.phase2_summary_complete = final_summary_processed
                    
                    # 토론과 요약 모두 완료
                    return discussion_messages, "완료", None
                
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
                    
                    # 페르소나 응답 생성 중 메시지
                    persona_display_name = agent_name_map.get(next_agent, next_agent)
                    print(f"{agent_to_avatar_map[next_agent]} {persona_display_name}가 응답을 생성하고 있습니다...")
                    
                    # 페르소나 첫 등장 시 소개 메시지 추가
                    if persona_first_appearance.get(next_agent, True):
                        intro_key = persona_intro_key_map.get(next_agent)
                        intro_content = SYSTEM_MESSAGES.get(intro_key)
                        if intro_content:
                            discussion_messages.append({
                                "role": "system",
                                "content": intro_content,
                                "avatar": "ℹ️",
                                "speaker": "system",
                                "speaker_name": "시스템"
                            })
                        persona_first_appearance[next_agent] = False
                    
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
                                # 페르소나 응답을 리스트에 추가
                                discussion_messages.append({
                                    "role": "assistant",
                                    "content": persona_response,
                                    "avatar": agent_to_avatar_map[next_agent],
                                    "speaker": next_agent,
                                    "speaker_name": agent_name_map.get(next_agent, next_agent)
                                })
                                
                                # 토론 히스토리에 페르소나 발언 추가
                                update_discussion_history(session_id_string, next_agent, persona_response)

            except Exception as e:
                print(f"ERROR in discussion round {current_round}: {e}")
                import traceback
                traceback.print_exc()
                
                # 오류 메시지를 리스트에 추가
                discussion_messages.append({
                    "role": "system",
                    "content": f"토론 라운드 {current_round} 중 오류가 발생했습니다. 다음 단계로 진행합니다.",
                    "avatar": "ℹ️",
                    "speaker": "system",
                    "speaker_name": "시스템"
                })
        
        # 최대 라운드에 도달한 경우
        if current_round > max_discussion_rounds and not st.session_state.get("phase2_summary_complete", False):
            print(f"DEBUG: Reached maximum discussion rounds ({max_discussion_rounds}) without completing summary")
            
            # 최대 라운드 도달 메시지 추가
            discussion_messages.append({
                "role": "system",
                "content": "최대 토론 라운드에 도달하여 최종 요약을 진행합니다.",
                "avatar": "ℹ️",
                "speaker": "system",
                "speaker_name": "시스템"
            })
            
            # 최종 요약 에이전트 실행
            final_summary_agent = orchestrator.get_phase2_final_summary_agent()
            
            runner = Runner(
                agent=final_summary_agent,
                app_name=APP_NAME,
                session_service=st.session_state.session_manager_instance.session_service
            )
            
            # 빈 메시지로 실행하여 세션 상태를 직접 참조하도록 함
            input_content = types.Content(role="user", parts=[types.Part(text="")])
            
            # 최종 요약 생성 중 메시지
            print("최종 요약을 생성하고 있습니다...")
            
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
                        # 최종 요약 소개 메시지 추가
                        if persona_first_appearance.get("final_summary", True):
                            intro_key = persona_intro_key_map.get("final_summary")
                            intro_content = SYSTEM_MESSAGES.get(intro_key)
                            if intro_content:
                                discussion_messages.append({
                                    "role": "system",
                                    "content": intro_content,
                                    "avatar": "ℹ️",
                                    "speaker": "system",
                                    "speaker_name": "시스템"
                                })
                            persona_first_appearance["final_summary"] = False
                        
                        # 최종 요약을 리스트에 추가
                        discussion_messages.append({
                            "role": "assistant",
                            "content": final_summary,
                            "avatar": agent_to_avatar_map["final_summary"],
                            "speaker": "final_summary",
                            "speaker_name": agent_name_map["final_summary"]
                        })
                        
                        # 토론 히스토리에 최종 요약 추가
                        update_discussion_history(session_id_string, "final_summary", final_summary)
                        
                        final_summary_processed = True
            
            # 최종 요약 완료 상태 설정
            st.session_state.phase2_summary_complete = final_summary_processed
        
        return discussion_messages, "완료", None  # 토론 진행 성공, 사용자 입력 대기 아님
    
    except Exception as e:
        print(f"Critical error in _run_phase2_discussion: {e}")
        import traceback
        traceback.print_exc()
        
        # 오류 메시지를 리스트에 추가
        discussion_messages.append({
            "role": "system",
            "content": f"토론 실행 중 심각한 오류가 발생했습니다: {str(e)}",
            "avatar": "ℹ️",
            "speaker": "system",
            "speaker_name": "시스템"
        })
        
        return discussion_messages, "오류", None

def handle_phase2_discussion():
    """
    2단계 토론 처리 함수
    
    사용자가 '2단계 토론 시작하기'를 선택하면 실행되는 함수로,
    토론 퍼실리테이터 에이전트와 페르소나 에이전트들 간의 대화를 조율합니다.
    """
    try:
        print("Starting Phase 2 discussion...")
        
        # 현재 세션 상태 확인
        if st.session_state.analysis_phase not in ["phase2_pending_start", "phase2_running", "phase2_user_input"]:
            if not st.session_state.awaiting_user_input_phase2:
                print(f"WARNING: Unexpected analysis phase '{st.session_state.analysis_phase}' for handle_phase2_discussion")
                return
        
        # 오케스트레이터 생성
        orchestrator = AIdeaLabOrchestrator(model_name=st.session_state.selected_model)
        print(f"Created local orchestrator with model: {st.session_state.selected_model}")
        
        # 세션 ID 가져오기
        session_id_string = st.session_state.adk_session_id
        if not session_id_string:
            print("ERROR: No session ID available for phase 2 discussion")
            AppStateManager.change_analysis_phase("phase2_error")
            AppStateManager.show_system_message("phase2_error")
            st.rerun()
            return
        
        # 세션 객체 가져오기
        session = st.session_state.session_manager_instance.get_session(session_id_string)
        if not session:
            print(f"ERROR: Failed to get session with ID {session_id_string}")
            AppStateManager.change_analysis_phase("phase2_error")
            AppStateManager.show_system_message("phase2_error")
            st.rerun()
            return
        
        # 최초 토론 시작 시 2단계로 전환
        if st.session_state.analysis_phase == "phase2_pending_start":
            # 환영 메시지 표시
            AppStateManager.show_system_message("phase2_welcome")
            
            # 세션 상태를 phase2로 전환
            st.session_state.session_manager_instance.transition_to_phase2()
            
            # Streamlit 세션 상태 업데이트
            AppStateManager.change_analysis_phase("phase2_running")
        
        # 2단계 토론 실행
        with st.spinner("토론을 진행 중입니다..."):
            discussion_messages, discussion_status, user_prompt = asyncio.run(_run_phase2_discussion(
                session_id_string,
                orchestrator
            ))
            
            # 각 메시지마다 새로 rerun할 필요 없이 한 번에 모든 메시지를 UI에 추가
            print(f"DEBUG: Received {len(discussion_messages)} messages from _run_phase2_discussion")
            print(f"DEBUG: Discussion status: {discussion_status}")
            
            # 받은 메시지 리스트의 모든 메시지를 UI에 추가
            for message in discussion_messages:
                AppStateManager.add_message(
                    role=message["role"],
                    content=message["content"],
                    avatar=message.get("avatar")
                )
        
        # 토론 상태에 따른 처리
        if discussion_status == "완료":
            # 토론이 완료된 경우
            AppStateManager.change_analysis_phase("phase2_complete")
            AppStateManager.show_system_message("phase2_complete")
            st.session_state.phase2_discussion_complete = True
            st.session_state.phase2_summary_complete = True
        elif discussion_status == "사용자 입력 대기":
            # 사용자 입력이 필요한 경우
            AppStateManager.change_analysis_phase("phase2_user_input")
            st.session_state.awaiting_user_input_phase2 = True
            st.session_state.phase2_user_prompt = user_prompt
        elif discussion_status == "오류":
            # 오류가 발생한 경우
            AppStateManager.change_analysis_phase("phase2_error")
            AppStateManager.show_system_message("phase2_error")
        else:
            # 토론이 계속 진행 중인 경우
            AppStateManager.change_analysis_phase("phase2_running")
        
        # UI 갱신 (모든 메시지 추가 후 한 번만 호출)
        st.rerun()
    
    except Exception as e:
        print(f"Critical error in handle_phase2_discussion: {e}")
        import traceback
        traceback.print_exc()
        AppStateManager.change_analysis_phase("phase2_error")
        AppStateManager.show_system_message("phase2_error")
        st.rerun()

def main():
    """
    메인 UI 렌더링 함수
    
    Streamlit 앱의 전체 UI를 구성하고 사용자 상호작용을 처리합니다.
    """
    # 세션 상태 초기화
    AppStateManager.initialize_session_state()
    
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
            index=list(model_options.values()).index(st.session_state.selected_model) if st.session_state.selected_model in model_options.values() else 0,
            key="model_selector",
            on_change=lambda: AppStateManager.change_model(model_options[st.session_state.model_selector])
        )
        
        # 선택된 모델의 내부 ID
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
    
    # 앱 제목 및 소개
    st.title("AIdea Lab - 아이디어 분석 워크숍")
    st.markdown("당신의 아이디어를 AI가 다양한 관점에서 분석해드립니다!")
    
    # 채팅 메시지 표시
    messages_container = st.container()
    with messages_container:
        if st.session_state.get('messages'):
            for idx, message in enumerate(st.session_state.messages):
                role = message.get("role", "")
                msg_content = message.get("content", "")
                avatar = message.get("avatar", None)
                
                try:
                    if role == "user":
                        st.chat_message(role, avatar="🧑‍💻").write(msg_content)
                    elif role == "assistant":
                        st.chat_message(role, avatar=avatar).write(msg_content)
                    elif role == "system":
                        # 시스템 메시지를 chat_message로 표시
                        st.chat_message("assistant", avatar=avatar if avatar else "ℹ️").markdown(f"_{msg_content}_")
                except Exception as e:
                    print(f"Error rendering message (idx: {idx}): Role={role}, Avatar={avatar}, Exc={e}")
                    st.error(f"메시지 렌더링 중 오류 발생: {str(msg_content)[:30]}...")

    # 입력 UI 부분
    input_container = st.container()
    with input_container:
        current_analysis_phase = st.session_state.get("analysis_phase", "idle")

        # 단계별 UI 처리
        if current_analysis_phase == "idle":
            # 추가 정보 입력 버튼
            additional_info_button_label = "아이디어 상세 정보 숨기기" if st.session_state.get("show_additional_info") else "아이디어 상세 정보 입력 (선택)"
            st.button(
                additional_info_button_label, 
                key="toggle_additional_info_button", 
                on_click=AppStateManager.toggle_additional_info
            )

            if st.session_state.get("show_additional_info"):
                with st.expander("아이디어 상세 정보", expanded=st.session_state.get("expander_state", True)):
                    st.text_area("아이디어의 핵심 목표 또는 해결하고자 하는 문제:", key="user_goal_input", value=st.session_state.get("user_goal",""))
                    st.text_area("주요 제약 조건 (예: 예산, 시간, 기술 등):", key="user_constraints_input", value=st.session_state.get("user_constraints",""))
                    st.text_area("중요하게 생각하는 가치 (예: 효율성, 창의성 등):", key="user_values_input", value=st.session_state.get("user_values",""))
                    st.button(
                        "상세 정보 저장", 
                        key="save_additional_info", 
                        on_click=AppStateManager.save_additional_info
                    )
            
            # 아이디어 입력 필드
            st.chat_input(
                "여기에 아이디어를 입력하고 Enter를 누르세요...",
                key="idea_input",
                on_submit=lambda: AppStateManager.submit_idea(st.session_state.idea_input)
            )
        
        elif current_analysis_phase == "phase1_pending_start":
            if st.session_state.current_idea and st.session_state.current_idea != st.session_state.get("analyzed_idea"):
                with st.spinner("AI 페르소나가 아이디어를 분석 중입니다... 이 작업은 최대 1-2분 소요될 수 있습니다."):
                    # 상세 정보 저장 (만약 expanded 된 상태에서 아이디어만 바로 입력했을 경우 대비)
                    if st.session_state.get("show_additional_info"):
                         st.session_state.user_goal = st.session_state.get("user_goal_input", st.session_state.get("user_goal",""))
                         st.session_state.user_constraints = st.session_state.get("user_constraints_input", st.session_state.get("user_constraints",""))
                         st.session_state.user_values = st.session_state.get("user_values_input", st.session_state.get("user_values",""))
                    run_phase1_analysis_and_update_ui()  # 분석 실행
            else:
                AppStateManager.change_analysis_phase("idle")
                st.rerun()

        elif current_analysis_phase == "phase1_complete":
            st.success("✔️ 1단계 아이디어 분석이 완료되었습니다.")
            
            col1, col2 = st.columns(2)
            with col1:
                st.button(
                    "💬 2단계 토론 시작하기", 
                    key="start_phase2_button", 
                    use_container_width=True,
                    on_click=AppStateManager.start_phase2_discussion
                )
            
            with col2:
                st.button(
                    "✨ 새 아이디어 분석", 
                    key="new_idea_after_phase1_button", 
                    use_container_width=True,
                    on_click=lambda: AppStateManager.restart_session(keep_messages=False)
                )

        elif current_analysis_phase == "phase1_error":
            col_retry, col_restart_new = st.columns(2)
            with col_retry:
                st.button(
                    "같은 아이디어로 재시도", 
                    key="retry_button_error", 
                    use_container_width=True,
                    on_click=AppStateManager.retry_analysis
                )
            with col_restart_new:
                st.button(
                    "새 아이디어로 시작", 
                    key="restart_button_error", 
                    use_container_width=True,
                    on_click=lambda: AppStateManager.restart_session(keep_messages=False)
                )
        
        elif current_analysis_phase == "phase2_pending_start":
            # 2단계 토론 시작 처리
            with st.spinner("2단계 토론을 준비 중입니다..."):
                handle_phase2_discussion()
                
        elif current_analysis_phase == "phase2_running":
            # 토론 진행 중 표시
            st.info("AI 페르소나들이 토론 중입니다...")
            handle_phase2_discussion()
            
        elif current_analysis_phase == "phase2_user_input":
            # 사용자 입력을 받아야 하는 상태
            if st.session_state.awaiting_user_input_phase2:
                # 사용자 질문을 더 명확하게 표시
                st.info("💬 **토론에 참여해 주세요**")
                with st.container(border=True):
                    st.markdown(f"**질문:** {st.session_state.phase2_user_prompt}")
                
                # 사용자 입력 필드
                st.chat_input(
                    "여기에 의견을 입력하고 Enter를 누르세요...",
                    key="phase2_response_input",
                    on_submit=lambda: AppStateManager.submit_phase2_response(st.session_state.phase2_response_input)
                )
        
        elif current_analysis_phase == "phase2_complete":
            # 2단계 토론 완료 표시
            st.success("✔️ 2단계 토론과 최종 요약이 완료되었습니다.")
            
            st.button(
                "✨ 새 아이디어 분석", 
                key="new_idea_after_phase2_button", 
                use_container_width=True,
                on_click=lambda: AppStateManager.restart_session(keep_messages=False)
            )
                
        elif current_analysis_phase == "phase2_error":
            # 2단계 토론 중 오류 발생
            col_retry, col_restart_new = st.columns(2)
            with col_retry:
                st.button(
                    "같은 아이디어로 재시도", 
                    key="retry_phase2_button_error", 
                    use_container_width=True,
                    on_click=AppStateManager.retry_phase2
                )
            with col_restart_new:
                st.button(
                    "새 아이디어로 시작", 
                    key="restart_phase2_button_error", 
                    use_container_width=True,
                    on_click=lambda: AppStateManager.restart_session(keep_messages=False)
                )


# 남아있는 전역 함수들을 리팩토링
def show_system_message(message_key):
    """
    시스템 메시지 표시 (이전 방식, 제거 예정)
    
    AppStateManager.show_system_message()를 사용하도록 수정 중입니다.
    """
    message_content = SYSTEM_MESSAGES.get(message_key)
    if message_content:
        print(f"Showing system message for key '{message_key}': {message_content[:70]}...")
        AppStateManager.add_message("system", message_content, avatar="ℹ️")
    else:
        print(f"WARNING: System message key '{message_key}' not defined in SYSTEM_MESSAGES.")


def initialize_session_state():
    """
    세션 상태 초기화 (이전 방식, 제거 예정)
    
    AppStateManager.initialize_session_state()를 사용하도록 수정 중입니다.
    """
    AppStateManager.initialize_session_state()


def process_text_for_display(text_data):
    """
    텍스트 표시용 처리 (이전 방식, 제거 예정)
    
    AppStateManager.process_text_for_display()를 사용하도록 수정 중입니다.
    """
    return AppStateManager.process_text_for_display(text_data)


def add_message(role, content, avatar=None):
    """
    메시지 추가 (이전 방식, 제거 예정)
    
    AppStateManager.add_message()를 사용하도록 수정 중입니다.
    """
    AppStateManager.add_message(role, content, avatar)


def restart_session(keep_messages=False):
    """
    세션 재시작 (이전 방식, 제거 예정)
    
    AppStateManager.restart_session()를 사용하도록 수정 중입니다.
    """
    AppStateManager.restart_session(keep_messages=keep_messages)


if __name__ == "__main__":
    main()