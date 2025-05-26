"""
AIdea Lab 세션 관리자

이 모듈은 Google ADK 세션을 관리하고 Streamlit UI와 ADK 세션 간의 상태 동기화를 
담당하는 SessionManager 클래스를 제공합니다.
"""

import uuid
import logging
from google.adk.sessions import InMemorySessionService, Session
from google.adk.events import Event, EventActions # EventActions와 함께 Event도 임포트합니다.
from typing import Dict, Any, Optional, Tuple

# 모듈 레벨 로거 설정
logger = logging.getLogger(__name__)

class SessionManager:
    """
    ADK 세션을 일관되게 관리하고 Phase 1과 Phase 2에서 동일한 세션이 사용되도록 보장하는 
    세션 관리자 클래스
    """
    
    def __init__(self, app_name: str, user_id: str):
        """
        세션 관리자 초기화
        
        Args:
            app_name (str): 애플리케이션 이름
            user_id (str): 사용자 ID
        """
        self.app_name = app_name
        self.user_id = user_id
        self.session_service = InMemorySessionService()
        self.active_sessions: Dict[str, str] = {}  # 사용자별 active_session_id를 추적
    
    def create_session(self, initial_state: Optional[Dict[str, Any]] = None) -> Tuple[Optional[Session], str]: # initial_state 파라미터 추가
        """
        새로운 세션을 생성하고 서비스에 등록합니다. 초기 상태를 함께 전달할 수 있습니다.
        
        Returns:
            Tuple[Optional[Session], str]: 생성된 세션 객체와 세션 ID, 실패 시 세션 객체는 None
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        try:
            session = self.session_service.create_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id,
                state=initial_state if initial_state else {} # 초기 상태 전달
            )
            self.active_sessions[self.user_id] = session_id
            logger.info(f"SessionManager: Created session ID '{session_id}' with initial state: {initial_state}")
            return session, session_id
        except Exception as e:
            logger.error(f"SessionManager: Error creating session ID '{session_id}': {e}", exc_info=True)
            return None, session_id # 세션 생성 실패 시 객체는 None

    def get_session(self, session_id: Optional[str] = None) -> Optional[Session]:
        """
        세션 ID로 세션을 조회합니다. 세션 ID가 None이면 현재 활성화된 세션을 반환합니다.
        
        Args:
            session_id (str, optional): 조회할 세션 ID. 기본값은 None
            
        Returns:
            Optional[Session]: 조회된 세션 객체 또는 None (세션이 없는 경우)
        """
        if session_id is None:
            session_id = self.active_sessions.get(self.user_id)
            if session_id is None:
                logger.warning("SessionManager: No active session ID found for get_session.")
                return None
        
        logger.debug(f"SessionManager: Attempting to get session with ID '{session_id}'")
        session = self.session_service.get_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id
        )
        if session:
            logger.debug(f"SessionManager: Successfully retrieved session with ID '{session_id}'. State keys: {list(session.state.keys())}")
        else:
            logger.warning(f"SessionManager: Failed to retrieve session with ID '{session_id}'.")
        return session

    def get_active_session_id(self) -> Optional[str]:
        """
        현재 사용자의 활성화된 세션 ID를 반환합니다.
        
        Returns:
            Optional[str]: 활성화된 세션 ID 또는 None (활성 세션이 없는 경우)
        """
        return self.active_sessions.get(self.user_id)

    def set_active_session_id(self, session_id: str) -> None:
        """
        현재 사용자의 활성화된 세션 ID를 설정합니다.
        
        Args:
            session_id (str): 활성화할 세션 ID
        """
        self.active_sessions[self.user_id] = session_id
        logger.info(f"SessionManager: Set active session ID to '{session_id}'")

    def update_session_state(self, state_updates: Dict[str, Any]) -> bool:
        """
        현재 활성화된 세션의 상태를 업데이트합니다.
        ADK의 EventActions.state_delta를 사용하여 안정적인 상태 업데이트를 수행합니다.
        
        Args:
            state_updates (Dict[str, Any]): 업데이트할 상태 키-값 쌍
            
        Returns:
            bool: 상태 업데이트 성공 여부
        """
        # 현재 세션 ID 가져오기
        active_session_id = self.get_active_session_id()
        if active_session_id is None:
            logger.error("SessionManager: Cannot update state, no active session ID found.")
            return False
        
        # 현재 세션 객체 가져오기
        current_session = self.get_session(active_session_id)
        if current_session is None:
            logger.error(f"SessionManager: Cannot update state, failed to get session with ID '{active_session_id}'.")
            return False
        
        logger.info(f"SessionManager: Updating state for session ID '{current_session.id}' using event mechanism.")
        
        # EventActions 객체 생성
        event_actions = EventActions(state_delta=state_updates)
        
        # Event 객체 생성
        new_event = Event(
            author=self.app_name,  # 또는 "system_session_manager"
            actions=event_actions,
            # invocation_id는 기본값으로 자동 생성됨
            content=None
        )
        
        # 이벤트를 세션에 추가하여 상태 업데이트
        try:
            self.session_service.append_event(session=current_session, event=new_event)
            logger.info(f"SessionManager: Successfully updated state for session ID '{current_session.id}' with keys: {list(state_updates.keys())}")
            return True
        except Exception as e:
            logger.exception(f"SessionManager: Error updating state for session ID '{current_session.id}'")
            return False

    def get_session_state_value(self, key: str, default: Any = None) -> Any:
        """
        현재 활성화된 세션 상태에서 값을 조회합니다.
        """
        session = self.get_session()
        if session is None:
            return default
        
        return session.state.get(key, default)
    
    def start_new_idea_session(self, initial_idea: str, user_goal: str = "", 
                                 user_constraints: str = "", user_values: str = "") -> Tuple[Optional[Session], Optional[str]]:
        """
        새로운 아이디어 분석을 위한 세션을 시작하고, 초기 상태를 create_session에 전달합니다.
        
        Args:
            initial_idea (str): 사용자의 초기 아이디어
            user_goal (str, optional): 아이디어의 핵심 목표
            user_constraints (str, optional): 주요 제약 조건
            user_values (str, optional): 중요 가치
            
        Returns:
            Tuple[Optional[Session], Optional[str]]: 생성 및 업데이트된 세션 객체와 세션 ID, 실패 시 None
        """
        initial_state_payload = {
            "initial_idea": initial_idea,
            "current_phase": "phase1"  # Phase 1 시작
        }
        if user_goal:
            initial_state_payload["user_goal"] = user_goal
        if user_constraints:
            initial_state_payload["user_constraints"] = user_constraints
        if user_values:
            initial_state_payload["user_values"] = user_values
        
        logger.info(f"SessionManager: Preparing to create new session with initial state: {initial_state_payload}")
        # create_session 호출 시 initial_state 전달
        session, session_id = self.create_session(initial_state=initial_state_payload)

        if session:
            retrieved_session = self.get_session(session_id)
            if retrieved_session and retrieved_session.state.get("initial_idea") == initial_idea:
                logger.info(f"SessionManager: Successfully started session ID '{session_id}' with initial_idea: '{retrieved_session.state.get('initial_idea')}'")
                self.set_active_session_id(session_id) 
                return retrieved_session, session_id 
            elif retrieved_session:
                logger.warning(f"SessionManager: WARNING - Verification of initial_idea for session ID '{session_id}' failed or incomplete. Found: '{retrieved_session.state.get('initial_idea')}', Expected: '{initial_idea}'. State keys: {list(retrieved_session.state.keys())}")
                self.set_active_session_id(session_id)
                return retrieved_session, session_id 
            else:
                logger.error(f"SessionManager: ERROR - Session created for ID '{session_id}' but failed to retrieve it for verification.")
                self.set_active_session_id(session_id) 
                return None, session_id 
        else:
            logger.error(f"SessionManager: ERROR - Failed to create session in start_new_idea_session for idea: {initial_idea}")
            return None, session_id # session_id는 반환하되, session 객체는 None
    
    def transition_to_phase2(self) -> bool:
        """
        현재 세션을 Phase 1에서 Phase 2로 전환합니다.
        ADK의 EventActions.state_delta를 사용하여 안정적인 상태 업데이트를 보장합니다.
        """
        session = self.get_session() # 현재 활성화된 세션 (복사본일 수 있음)
        if session is None:
            logger.error("SessionManager: Cannot transition to phase2, no active session.")
            return False
        
        session_id_for_log = session.id # 로깅 및 검증용
        logger.info(f"SessionManager: Attempting to transition session ID '{session_id_for_log}' to phase2 using an event with state_delta.")
        
        # 1. 변경할 상태 정의
        state_changes = {
            "current_phase": "phase2",
            "discussion_history_phase2": []  # 2단계 토론 기록 초기화
        }

        # 2. EventActions 객체 생성
        event_actions = EventActions(state_delta=state_changes)
        
        # 3. Event 객체 생성
        #    author: 이 상태 변경의 주체. 시스템 레벨 변경이므로 "system_transition" 등으로 명명.
        #    invocation_id: ADK Runner의 특정 실행과 직접 연결되지 않는 시스템 이벤트의 경우,
        #                   Event 클래스의 기본값('')을 사용하거나, 세션 ID 등을 활용할 수 있습니다.
        #                   Event 객체 자체의 ID는 자동으로 생성됩니다.
        transition_event = Event(
            author="system_phase_manager", 
            actions=event_actions
            # invocation_id는 Event 클래스에서 ''로 기본 설정됨
        )

        # 4. session_service를 통해 이벤트 추가
        try:
            # self.session_service.append_event는 전달된 session 객체의 ID를 사용하여
            # 내부 저장소에 있는 실제 세션 객체를 찾아 이벤트를 추가하고 상태를 업데이트합니다.
            self.session_service.append_event(session=session, event=transition_event)
            logger.info(f"SessionManager: Successfully appended phase2 transition event for session ID '{session_id_for_log}'.")

            # 확인을 위해 다시 세션을 가져와 상태를 로깅
            verified_session = self.get_session(session_id_for_log) # 저장소에서 최신 세션 정보를 다시 가져옴
            if verified_session and verified_session.state.get("current_phase") == "phase2":
                logger.info(f"SessionManager: Verified transition to phase2 for session ID '{session_id_for_log}'. State: {verified_session.state}")
                return True
            else:
                current_phase_state = "N/A"
                full_state_for_log = {}
                if verified_session:
                    current_phase_state = verified_session.state.get("current_phase")
                    full_state_for_log = verified_session.state
                logger.error(f"SessionManager: FAILED to verify transition to phase2 for session ID '{session_id_for_log}' after appending event. Expected 'phase2', got '{current_phase_state}'.")
                logger.debug(f"SessionManager: Full state for session {session_id_for_log} after attempt: {full_state_for_log}")
                return False
        except Exception as e:
            logger.exception(f"SessionManager: Error appending phase2 transition event for session ID '{session_id_for_log}'")
            return False

    def debug_session_service_state(self) -> Dict[str, Any]:
        """
        디버깅을 위한 세션 서비스 상태 검사 메서드
        
        Returns:
            Dict[str, Any]: 세션 서비스의 현재 상태 정보
        """
        debug_info = {
            "session_service_type": type(self.session_service).__name__,
            "session_service_id": id(self.session_service),
            "app_name": self.app_name,
            "user_id": self.user_id,
            "active_sessions": self.active_sessions.copy(),
            "available_session_keys": []
        }
        
        try:
            # InMemorySessionService의 내부 세션 저장소 확인
            session_service = self.session_service
            
            if hasattr(session_service, 'sessions'):
                debug_info["available_session_keys"] = list(session_service.sessions.keys())
                debug_info["total_stored_sessions"] = len(session_service.sessions)
            elif hasattr(session_service, '_sessions'):
                debug_info["available_session_keys"] = list(session_service._sessions.keys())
                debug_info["total_stored_sessions"] = len(session_service._sessions)
            else:
                # 다른 가능한 속성들 탐색
                attrs = [attr for attr in dir(session_service) if not attr.startswith('__')]
                session_attrs = [attr for attr in attrs if 'session' in attr.lower()]
                debug_info["session_related_attributes"] = session_attrs
                
                for attr in session_attrs:
                    try:
                        attr_value = getattr(session_service, attr)
                        if hasattr(attr_value, 'keys'):
                            debug_info[f"{attr}_keys"] = list(attr_value.keys())
                        elif hasattr(attr_value, '__len__'):
                            debug_info[f"{attr}_length"] = len(attr_value)
                        else:
                            debug_info[f"{attr}_type"] = type(attr_value).__name__
                    except Exception as e:
                        debug_info[f"{attr}_error"] = str(e)
            
        except Exception as e:
            debug_info["debug_error"] = str(e)
        
        return debug_info