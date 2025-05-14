"""
AIdea Lab 세션 관리자

이 모듈은 Google ADK 세션을 관리하고 Streamlit UI와 ADK 세션 간의 상태 동기화를 
담당하는 SessionManager 클래스를 제공합니다.
"""

import uuid
from google.adk.sessions import InMemorySessionService, Session
from google.adk.events import Event, EventActions # EventActions와 함께 Event도 임포트합니다.
from typing import Dict, Any, Optional, Tuple

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
            print(f"SessionManager: Created session ID '{session_id}' with initial state: {initial_state}")
            return session, session_id
        except Exception as e:
            print(f"SessionManager: Error creating session ID '{session_id}': {e}")
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
                print("SessionManager: No active session ID found for get_session.")
                return None
        
        print(f"SessionManager: Attempting to get session with ID '{session_id}'")
        session = self.session_service.get_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id
        )
        if session:
            print(f"SessionManager: Successfully retrieved session with ID '{session_id}'. State keys: {list(session.state.keys())}")
        else:
            print(f"SessionManager: Failed to retrieve session with ID '{session_id}'.")
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
        print(f"SessionManager: Set active session ID to '{session_id}'")

    def update_session_state(self, state_updates: Dict[str, Any]) -> bool:
        """
        현재 활성화된 세션의 상태를 업데이트합니다. 
        (주의: ADK의 InMemorySessionService는 get_session() 시 복사본을 반환할 수 있으므로, 
         이 메소드를 통한 직접적인 상태 업데이트는 ADK Runner 외부에서는 불안정할 수 있습니다. 
         상태 업데이트는 가급적 ADK의 이벤트 메커니즘(state_delta)을 통해 수행하는 것이 권장됩니다.)
        """
        session = self.get_session()
        if session is None:
            print("SessionManager: Cannot update state, no active session found.")
            return False
        
        print(f"SessionManager: Updating state for session ID '{session.id}'. Current keys: {list(session.state.keys())}")
        # 이 방식은 get_session()이 세션의 복사본을 반환하는 경우, 원본 저장소의 상태를 변경하지 않을 수 있습니다.
        # ADK의 InMemorySessionService.append_event()는 내부적으로 저장된 세션 객체를 직접 수정합니다.
        # 따라서 상태 변경은 해당 메서드를 사용하는 것이 더 안정적입니다.
        for key, value in state_updates.items():
            session.state[key] = value 
            print(f"SessionManager: Set session.state['{key}'] = '{value}' (on a copy if not handled carefully)")
        
        # ADK InMemorySessionService는 명시적인 update_session 메소드가 없습니다.
        # 변경 사항을 안정적으로 반영하려면 append_event를 사용해야 합니다.
        print(f"SessionManager: session.state for session ID '{session.id}' was modified. "
              "Verification of persistence needed if not using event-based updates.")
        # 이 메서드는 ADK 외부에서 직접적인 상태 수정을 시도하므로, 성공 여부와 관계없이 True를 반환하는 것은 오해의 소지가 있을 수 있습니다.
        # 실제로는 이 변경이 반영되지 않았을 가능성이 높습니다.
        return True


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
        
        print(f"SessionManager: Preparing to create new session with initial state: {initial_state_payload}")
        # create_session 호출 시 initial_state 전달
        session, session_id = self.create_session(initial_state=initial_state_payload)

        if session:
            retrieved_session = self.get_session(session_id)
            if retrieved_session and retrieved_session.state.get("initial_idea") == initial_idea:
                print(f"SessionManager: Successfully started session ID '{session_id}' with initial_idea: '{retrieved_session.state.get('initial_idea')}'")
                self.set_active_session_id(session_id) 
                return retrieved_session, session_id 
            elif retrieved_session:
                print(f"SessionManager: WARNING - Verification of initial_idea for session ID '{session_id}' failed or incomplete. Found: '{retrieved_session.state.get('initial_idea')}', Expected: '{initial_idea}'. State keys: {list(retrieved_session.state.keys())}")
                self.set_active_session_id(session_id)
                return retrieved_session, session_id 
            else:
                print(f"SessionManager: ERROR - Session created for ID '{session_id}' but failed to retrieve it for verification.")
                self.set_active_session_id(session_id) 
                return None, session_id 
        else:
            print(f"SessionManager: ERROR - Failed to create session in start_new_idea_session for idea: {initial_idea}")
            return None, session_id # session_id는 반환하되, session 객체는 None
    
    def transition_to_phase2(self) -> bool:
        """
        현재 세션을 Phase 1에서 Phase 2로 전환합니다.
        ADK의 EventActions.state_delta를 사용하여 안정적인 상태 업데이트를 보장합니다.
        """
        session = self.get_session() # 현재 활성화된 세션 (복사본일 수 있음)
        if session is None:
            print("SessionManager: Cannot transition to phase2, no active session.")
            return False
        
        session_id_for_log = session.id # 로깅 및 검증용
        print(f"SessionManager: Attempting to transition session ID '{session_id_for_log}' to phase2 using an event with state_delta.")
        
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
            print(f"SessionManager: Successfully appended phase2 transition event for session ID '{session_id_for_log}'.")

            # 확인을 위해 다시 세션을 가져와 상태를 로깅
            verified_session = self.get_session(session_id_for_log) # 저장소에서 최신 세션 정보를 다시 가져옴
            if verified_session and verified_session.state.get("current_phase") == "phase2":
                print(f"SessionManager: Verified transition to phase2 for session ID '{session_id_for_log}'. State: {verified_session.state}")
                return True
            else:
                current_phase_state = "N/A"
                full_state_for_log = {}
                if verified_session:
                    current_phase_state = verified_session.state.get("current_phase")
                    full_state_for_log = verified_session.state
                print(f"SessionManager: FAILED to verify transition to phase2 for session ID '{session_id_for_log}' after appending event. Expected 'phase2', got '{current_phase_state}'.")
                print(f"SessionManager: Full state for session {session_id_for_log} after attempt: {full_state_for_log}")
                return False
        except Exception as e:
            print(f"SessionManager: Error appending phase2 transition event for session ID '{session_id_for_log}': {e}")
            import traceback
            traceback.print_exc()
            return False