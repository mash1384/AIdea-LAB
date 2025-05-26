import streamlit as st
from config.models import DEFAULT_MODEL

# 시스템 안내 메시지 템플릿 정의
SYSTEM_MESSAGES = {
    "welcome": "**AIdea Lab에 오신 것을 환영합니다.** 당신의 아이디어를 입력하시면 AI 페르소나들이 다양한 관점에서 분석해드립니다.",
    "phase1_start": "**분석을 시작합니다.** 각 AI 페르소나가 순차적으로 의견을 제시할 예정입니다.",
    "marketer_intro": "**💡 아이디어 마케팅 분석가의 의견:**",
    "critic_intro": "**🔍 비판적 분석가의 의견:**",
    "engineer_intro": "**⚙️ 현실주의 엔지니어의 의견:**",
    "summary_phase1_intro": "**📝 최종 요약 및 종합:**",
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

# 애플리케이션 상태 관리를 위한 클래스
class AppStateManager:
    """
    애플리케이션 상태를 관리하는 클래스
    Streamlit의 session_state를 캡슐화하여 상태 접근과 변경을 일관되게 처리합니다.
    """
    
    @staticmethod
    def initialize_session_state():
        """세션 상태 초기화"""
        # SessionManager 관련 import는 사용하는 곳에서 처리
        from src.session_manager import SessionManager
        
        # 애플리케이션 상수들
        APP_NAME = "aidea-lab"
        USER_ID = "default-user"
        
        # SessionManager 객체 초기화
        if 'session_manager_instance' not in st.session_state:
            print("Creating new SessionManager instance and storing in st.session_state")
            new_session_manager = SessionManager(APP_NAME, USER_ID)
            st.session_state.session_manager_instance = new_session_manager
            print(f"SessionManager instance created with ID: {id(new_session_manager)}")
            print(f"SessionManager.session_service ID: {id(new_session_manager.session_service)}")
            print(f"SessionManager app_name: '{new_session_manager.app_name}', user_id: '{new_session_manager.user_id}'")
        else:
            existing_session_manager = st.session_state.session_manager_instance
            print(f"Reusing existing SessionManager instance with ID: {id(existing_session_manager)}")
            print(f"Existing SessionManager.session_service ID: {id(existing_session_manager.session_service)}")
            print(f"Existing SessionManager app_name: '{existing_session_manager.app_name}', user_id: '{existing_session_manager.user_id}'")
            # 기존 SessionManager의 활성 세션 정보 출력
            if hasattr(existing_session_manager, 'active_sessions'):
                print(f"Active sessions in SessionManager: {existing_session_manager.active_sessions}")
            else:
                print("WARNING: SessionManager has no active_sessions attribute")
        
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
        AppStateManager.set_user_goal(AppStateManager.get_input_value('user_goal_input'))
        AppStateManager.set_user_constraints(AppStateManager.get_input_value('user_constraints_input'))
        AppStateManager.set_user_values(AppStateManager.get_input_value('user_values_input'))
        AppStateManager.set_state('expander_state', False)
        AppStateManager.set_state('show_additional_info', False)
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def submit_idea(idea_text):
        """아이디어 제출"""
        if not idea_text:
            return
            
        # 상세정보가 입력되지 않았다면 확장 표시
        if not AppStateManager.get_user_goal():
            AppStateManager.set_state('show_additional_info', True)
            AppStateManager.set_state('expander_state', True)
        
        AppStateManager.add_message("user", idea_text)
        AppStateManager.set_current_idea(idea_text)
        AppStateManager.change_analysis_phase("phase1_pending_start")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def start_phase2_discussion():
        """2단계 토론 시작"""
        AppStateManager.change_analysis_phase("phase2_pending_start")
        AppStateManager.set_state('proceed_to_phase2', True)
        print("User selected to start Phase 2 discussion.")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def submit_phase2_response(response_text):
        """2단계 사용자 응답 제출"""
        if not response_text:
            return
        
        print(f"User submitted Phase 2 response: {response_text[:50]}...")
        AppStateManager.add_message("user", response_text)
        
        # 사용자 응답을 session_state에 저장하고 대기 상태 해제
        AppStateManager.set_phase2_user_response(response_text)
        AppStateManager.set_awaiting_user_input_phase2(False)
        
        # 토론 재개를 위해 단계 변경
        AppStateManager.change_analysis_phase("phase2_running")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def retry_analysis():
        """분석 재시도"""
        AppStateManager.change_analysis_phase("phase1_pending_start")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def retry_phase2():
        """2단계 재시도"""
        AppStateManager.change_analysis_phase("phase2_pending_start")
        # st.rerun() - 콜백 내에서는 작동하지 않음
    
    @staticmethod
    def change_model(new_model_id):
        """모델 변경"""
        # config.personas 모듈의 SELECTED_MODEL 변수 업데이트
        try:
            import config.personas as personas_module
            personas_module.SELECTED_MODEL = new_model_id
            print(f"Model changed to: {new_model_id}")
        except Exception as e:
            print(f"Error updating SELECTED_MODEL in config.personas: {e}")
        
        # Streamlit 세션 상태에도 저장
        AppStateManager.set_state('selected_model', new_model_id)
        
        # 성공 메시지 표시
        try:
            from config.models import MODEL_CONFIGS
            model_name = MODEL_CONFIGS.get(new_model_id, {}).get("display_name", new_model_id)
            st.success(f"모델이 '{model_name}'로 변경되었습니다.")
        except Exception as e:
            print(f"Error showing model change success message: {e}")
            st.success(f"모델이 '{new_model_id}'로 변경되었습니다.")

    # 1.2단계: st.session_state 접근 일원화를 위한 추가 메서드들
    
    @staticmethod
    def get_session_manager():
        """SessionManager 인스턴스 가져오기"""
        return st.session_state.get('session_manager_instance')
    
    @staticmethod
    def get_selected_model():
        """선택된 모델 가져오기"""
        return st.session_state.get('selected_model')
    
    @staticmethod
    def get_current_idea():
        """현재 아이디어 가져오기"""
        return st.session_state.get('current_idea', '')
    
    @staticmethod
    def set_current_idea(idea):
        """현재 아이디어 설정"""
        st.session_state.current_idea = idea
    
    @staticmethod
    def get_analyzed_idea():
        """분석된 아이디어 가져오기"""
        return st.session_state.get('analyzed_idea', '')
    
    @staticmethod
    def set_analyzed_idea(idea):
        """분석된 아이디어 설정"""
        st.session_state.analyzed_idea = idea
    
    @staticmethod
    def get_analysis_phase():
        """현재 분석 단계 가져오기"""
        return st.session_state.get('analysis_phase', 'idle')
    
    @staticmethod
    def get_adk_session_id():
        """ADK 세션 ID 가져오기"""
        return st.session_state.get('adk_session_id')
    
    @staticmethod
    def set_adk_session_id(session_id):
        """ADK 세션 ID 설정"""
        st.session_state.adk_session_id = session_id
    
    @staticmethod
    def get_user_goal():
        """사용자 목표 가져오기"""
        return st.session_state.get('user_goal', '')
    
    @staticmethod
    def set_user_goal(goal):
        """사용자 목표 설정"""
        st.session_state.user_goal = goal
    
    @staticmethod
    def get_user_constraints():
        """사용자 제약조건 가져오기"""
        return st.session_state.get('user_constraints', '')
    
    @staticmethod
    def set_user_constraints(constraints):
        """사용자 제약조건 설정"""
        st.session_state.user_constraints = constraints
    
    @staticmethod
    def get_user_values():
        """사용자 가치 가져오기"""
        return st.session_state.get('user_values', '')
    
    @staticmethod
    def set_user_values(values):
        """사용자 가치 설정"""
        st.session_state.user_values = values
    
    @staticmethod
    def get_messages():
        """메시지 목록 가져오기"""
        return st.session_state.get('messages', [])
    
    @staticmethod
    def get_show_additional_info():
        """추가 정보 표시 여부 가져오기"""
        return st.session_state.get('show_additional_info', False)
    
    @staticmethod
    def get_expander_state():
        """확장기 상태 가져오기"""
        return st.session_state.get('expander_state', True)
    
    @staticmethod
    def is_awaiting_user_input_phase2():
        """2단계 사용자 입력 대기 여부 확인"""
        return st.session_state.get('awaiting_user_input_phase2', False)
    
    @staticmethod
    def set_awaiting_user_input_phase2(waiting):
        """2단계 사용자 입력 대기 상태 설정"""
        st.session_state.awaiting_user_input_phase2 = waiting
    
    @staticmethod
    def get_phase2_user_prompt():
        """2단계 사용자 프롬프트 가져오기"""
        return st.session_state.get('phase2_user_prompt', '')
    
    @staticmethod
    def set_phase2_user_prompt(prompt):
        """2단계 사용자 프롬프트 설정"""
        st.session_state.phase2_user_prompt = prompt
    
    @staticmethod
    def get_phase2_user_response():
        """2단계 사용자 응답 가져오기"""
        return st.session_state.get('phase2_user_response', '')
    
    @staticmethod
    def set_phase2_user_response(response):
        """2단계 사용자 응답 설정"""
        st.session_state.phase2_user_response = response
    
    @staticmethod
    def is_phase2_discussion_complete():
        """2단계 토론 완료 여부 확인"""
        return st.session_state.get('phase2_discussion_complete', False)
    
    @staticmethod
    def set_phase2_discussion_complete(complete):
        """2단계 토론 완료 상태 설정"""
        st.session_state.phase2_discussion_complete = complete
    
    @staticmethod
    def is_phase2_summary_complete():
        """2단계 요약 완료 여부 확인"""
        return st.session_state.get('phase2_summary_complete', False)
    
    @staticmethod
    def set_phase2_summary_complete(complete):
        """2단계 요약 완료 상태 설정"""
        st.session_state.phase2_summary_complete = complete
    
    @staticmethod
    def get_input_value(key, default=''):
        """입력 필드 값 가져오기 (Streamlit 위젯 값)"""
        return st.session_state.get(key, default)


# 전역 함수들 (호환성을 위해 유지, AppStateManager 메서드를 호출)
def initialize_session_state():
    """
    세션 상태 초기화 (이전 방식, 호환성을 위해 유지)
    """
    AppStateManager.initialize_session_state()


def restart_session(keep_messages=False):
    """
    세션 재시작 (이전 방식, 호환성을 위해 유지)
    """
    AppStateManager.restart_session(keep_messages=keep_messages)


def add_message(role, content, avatar=None):
    """
    메시지 추가 (이전 방식, 호환성을 위해 유지)
    """
    AppStateManager.add_message(role, content, avatar)


def process_text_for_display(text_data):
    """
    텍스트 표시용 처리 (이전 방식, 호환성을 위해 유지)
    """
    return AppStateManager.process_text_for_display(text_data)


def show_system_message(message_key):
    """
    시스템 메시지 표시 (이전 방식, 호환성을 위해 유지)
    """
    AppStateManager.show_system_message(message_key) 