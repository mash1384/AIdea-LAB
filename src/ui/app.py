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

# state_manager 모듈에서 필요한 클래스와 함수들 import
from src.ui.state_manager import (
    AppStateManager, 
    SYSTEM_MESSAGES,
    initialize_session_state,
    restart_session,
    add_message,
    process_text_for_display,
    show_system_message
)

# ADK 컨트롤러 import 추가
from src.ui.adk_controller import AdkController

# views 모듈 import 추가
from src.ui.views import (
    render_idle_view,
    render_phase1_pending_view,
    render_phase1_complete_view,
    render_phase1_error_view,
    render_phase2_pending_view,
    render_phase2_running_view,
    render_phase2_user_input_view,
    render_phase2_complete_view,
    render_phase2_error_view,
    render_chat_messages,
    render_sidebar,
    render_app_header
)

# DiscussionController import 추가
from src.ui.discussion_controller import DiscussionController

# .env 파일에서 환경 변수 로드
load_dotenv()

# Streamlit 페이지 설정 (모든 import 후, 다른 Streamlit 명령어 이전에 배치)
st.set_page_config(
    page_title="AIdea Lab - 아이디어 분석 워크숍",
    page_icon="🧠",
    layout="wide"
)

# 앱 정보
# 주의: APP_NAME과 USER_ID는 AppStateManager.initialize_session_state()에서 
# SessionManager 초기화 시 중앙에서 관리됩니다. ("aidea-lab", "default-user")
# 모든 컨트롤러는 SessionManager 인스턴스에서 이 값들을 가져와 사용합니다.

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
def run_phase1_analysis_and_update_ui():
    """
    1단계 분석을 실행하고 UI를 업데이트하는 함수
    
    이 함수는 AdkController를 사용하여 비동기 분석 작업을 호출하고, 결과를 UI에 반영합니다.
    """
    try:
        orchestrator = AIdeaLabOrchestrator(model_name=AppStateManager.get_selected_model())
        print(f"Created local orchestrator with model: {AppStateManager.get_selected_model()}")
        
        # 분석 상태 업데이트
        AppStateManager.change_analysis_phase("phase1_running")
        AppStateManager.show_system_message("phase1_start")
        print("Phase 1 analysis initiated by user")
        
        # 사용자 입력 데이터 가져오기
        idea_text = AppStateManager.get_current_idea()
        user_goal = AppStateManager.get_user_goal()
        user_constraints = AppStateManager.get_user_constraints()
        user_values = AppStateManager.get_user_values()
        print(f"Analyzing idea: {idea_text}, Goal: {user_goal}, Constraints: {user_constraints}, Values: {user_values}")
        
        # 새 세션 시작
        session_object, session_id_string = AppStateManager.get_session_manager().start_new_idea_session(
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

        AppStateManager.set_adk_session_id(session_id_string)
        print(f"New session started with ID: {session_id_string}, initial state verified in SessionManager.")
        
        # AdkController 초기화
        adk_controller = AdkController(AppStateManager.get_session_manager())
        print("AdkController initialized successfully")
        
        # 입력 내용 준비
        content_parts = [types.Part(text=f"아이디어: {idea_text}")]
        if user_goal: content_parts.append(types.Part(text=f"\n목표: {user_goal}"))
        if user_constraints: content_parts.append(types.Part(text=f"\n제약조건: {user_constraints}"))
        if user_values: content_parts.append(types.Part(text=f"\n가치: {user_values}"))
        
        input_content_for_runner = types.Content(role="user", parts=content_parts)
        print(f"Prepared input_content_for_runner: {input_content_for_runner}")
        
        # AdkController를 사용하여 분석 실행
        with st.spinner("1단계 분석을 진행 중입니다..."):
            analysis_success, processed_results, processed_outputs = asyncio.run(
                adk_controller.execute_phase1_workflow(
                    session_id_string,
                    input_content_for_runner,
                    orchestrator
                )
            )
        
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
                    # 페르소나 소개 메시지 표시 (있는 경우에만)
                    intro_message_key_base = persona_key_for_display
                    intro_message_key = f"{intro_message_key_base}_intro"
                    intro_content = SYSTEM_MESSAGES.get(intro_message_key)
                    avatar_char = persona_avatars.get(intro_message_key_base, "🤖")
                    
                    if intro_content:
                        AppStateManager.add_message("system", intro_content, avatar="ℹ️")
                        print(f"INFO: Adding intro message with key '{intro_message_key}' for persona '{persona_key_for_display}'")
                    else:
                        print(f"INFO: No intro message for key '{intro_message_key}' (Persona key: {persona_key_for_display}) - proceeding without intro")
                    
                    # 페르소나 응답 표시 (intro 메시지가 있든 없든 항상 표시)
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
        
        AppStateManager.set_analyzed_idea(idea_text)
        st.rerun()  # UI 갱신
        
    except Exception as e:
        print(f"Critical error in run_phase1_analysis_and_update_ui: {str(e)}")
        import traceback
        traceback.print_exc()
        
        # AdkController의 오류 처리 기능 사용
        session_manager = AppStateManager.get_session_manager()
        if session_manager:
            adk_controller = AdkController(session_manager)
            user_friendly_error = adk_controller.handle_adk_error(e, "run_phase1_analysis_and_update_ui")
            AppStateManager.add_message("system", f"오류가 발생했습니다: {user_friendly_error}", avatar="⚠️")
        
        AppStateManager.change_analysis_phase("phase1_error")
        AppStateManager.show_system_message("phase1_error")
        st.rerun()  # UI 갱신

def handle_phase2_discussion():
    """
    2단계 토론 처리 함수
    
    사용자가 '2단계 토론 시작하기'를 선택하면 실행되는 함수로,
    토론 퍼실리테이터 에이전트와 페르소나 에이전트들 간의 대화를 조율합니다.
    """
    try:
        print("Starting Phase 2 discussion...")
        
        # 현재 세션 상태 확인
        if AppStateManager.get_analysis_phase() not in ["phase2_pending_start", "phase2_running", "phase2_user_input"]:
            if not AppStateManager.get_awaiting_user_input_phase2():
                print(f"WARNING: Unexpected analysis phase '{AppStateManager.get_analysis_phase()}' for handle_phase2_discussion")
                return
        
        # 오케스트레이터 생성
        orchestrator = AIdeaLabOrchestrator(model_name=AppStateManager.get_selected_model())
        print(f"Created local orchestrator with model: {AppStateManager.get_selected_model()}")
        
        # 세션 ID 가져오기
        session_id_string = AppStateManager.get_adk_session_id()
        if not session_id_string:
            print("ERROR: No session ID available for phase 2 discussion")
            AppStateManager.change_analysis_phase("phase2_error")
            AppStateManager.show_system_message("phase2_error")
            st.rerun()
            return
        
        # 세션 객체 가져오기
        session = AppStateManager.get_session_manager().get_session(session_id_string)
        if not session:
            print(f"ERROR: Failed to get session with ID {session_id_string}")
            AppStateManager.change_analysis_phase("phase2_error")
            AppStateManager.show_system_message("phase2_error")
            st.rerun()
            return
        
        # 최초 토론 시작 시 2단계로 전환
        if AppStateManager.get_analysis_phase() == "phase2_pending_start":
            # 환영 메시지 표시
            AppStateManager.show_system_message("phase2_welcome")
            
            # 세션 상태를 phase2로 전환
            AppStateManager.get_session_manager().transition_to_phase2()
            
            # Streamlit 세션 상태 업데이트
            AppStateManager.change_analysis_phase("phase2_running")
        
        # 2단계 토론 실행
        with st.spinner("토론을 진행 중입니다..."):
            # DiscussionController 인스턴스 생성
            session_manager = AppStateManager.get_session_manager()
            
            # SessionManager 인스턴스 검증 로그 추가
            print(f"DEBUG: handle_phase2_discussion - SessionManager instance verification:")
            print(f"  - SessionManager ID: {id(session_manager)}")
            print(f"  - SessionManager.session_service ID: {id(session_manager.session_service) if session_manager else 'None'}")
            print(f"  - SessionManager app_name: '{session_manager.app_name if session_manager else 'None'}'")
            print(f"  - SessionManager user_id: '{session_manager.user_id if session_manager else 'None'}'")
            print(f"  - Active sessions: {session_manager.active_sessions if session_manager else 'None'}")
            
            discussion_controller = DiscussionController(session_manager)
            
            discussion_messages, discussion_status, user_prompt = asyncio.run(discussion_controller.run_phase2_discussion(
                session_id_string,
                orchestrator
            ))
            
            # 각 메시지마다 새로 rerun할 필요 없이 한 번에 모든 메시지를 UI에 추가
            print(f"DEBUG: Received {len(discussion_messages)} messages from DiscussionController")
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
            AppStateManager.set_phase2_discussion_complete(True)
            AppStateManager.set_phase2_summary_complete(True)
        elif discussion_status == "사용자 입력 대기":
            # 사용자 입력이 필요한 경우
            AppStateManager.change_analysis_phase("phase2_user_input")
            AppStateManager.set_awaiting_user_input_phase2(True)
            AppStateManager.set_phase2_user_prompt(user_prompt)
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
    views.py의 렌더링 함수들을 조율하여 각 상태에 맞는 UI를 표시합니다.
    """
    # 세션 상태 초기화
    AppStateManager.initialize_session_state()
    
    # 로그 디렉토리 생성
    if not os.path.exists("logs"):
        os.makedirs("logs")
    
    # 사이드바 UI 렌더링
    render_sidebar()
    
    # 앱 헤더 렌더링
    render_app_header()
    
    # 채팅 메시지 렌더링
    messages_container = st.container()
    with messages_container:
        render_chat_messages()

    # 입력 UI 부분 - 현재 분석 상태에 따라 적절한 뷰 렌더링
    input_container = st.container()
    with input_container:
        current_analysis_phase = AppStateManager.get_analysis_phase()

        # 단계별 UI 처리
        if current_analysis_phase == "idle":
            render_idle_view()
        
        elif current_analysis_phase == "phase1_pending_start":
            result = render_phase1_pending_view()
            if result == "execute_analysis":
                    run_phase1_analysis_and_update_ui()  # 분석 실행

        elif current_analysis_phase == "phase1_complete":
            render_phase1_complete_view()

        elif current_analysis_phase == "phase1_error":
            render_phase1_error_view()
        
        elif current_analysis_phase == "phase2_pending_start":
            result = render_phase2_pending_view()
            if result == "execute_phase2":
                handle_phase2_discussion()
                
        elif current_analysis_phase == "phase2_running":
            result = render_phase2_running_view()
            if result == "execute_phase2":
                handle_phase2_discussion()
            
        elif current_analysis_phase == "phase2_user_input":
            render_phase2_user_input_view()
        
        elif current_analysis_phase == "phase2_complete":
            render_phase2_complete_view()
                
        elif current_analysis_phase == "phase2_error":
            render_phase2_error_view()

if __name__ == "__main__":
    main()