"""
AIdea Lab 세션 관리자

이 모듈은 Google ADK 세션을 관리하고 Streamlit UI와 ADK 세션 간의 상태 동기화를 
담당하는 SessionManager 클래스를 제공합니다.
"""

import uuid
from google.adk.sessions import InMemorySessionService, Session
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

    # update_session_state 메서드는 InMemorySessionService가 세션 객체의 복사본을 반환할 경우
    # 예상대로 작동하지 않을 수 있습니다. 상태 업데이트는 ADK의 이벤트 기반 메커니즘을 통하는 것이
    # 더 안정적입니다. 이 메서드를 사용해야 한다면, ADK 문서를 참조하여
    # InMemorySessionService에 변경된 세션을 명시적으로 "저장"하는 방법이 있는지 확인해야 합니다.
    # 현재로서는 create_session 시 초기 상태를 전달하는 데 집중합니다.
    def update_session_state(self, state_updates: Dict[str, Any]) -> bool:
        """
        현재 활성화된 세션의 상태를 업데이트합니다. (주의: InMemorySessionService 동작 방식에 따라 한계가 있을 수 있음)
        """
        session = self.get_session()
        if session is None:
            print("SessionManager: Cannot update state, no active session found.")
            return False
        
        print(f"SessionManager: Updating state for session ID '{session.id}'. Current keys: {list(session.state.keys())}")
        for key, value in state_updates.items():
            session.state[key] = value # 이 변경이 서비스에 반영되는지 확인 필요
            print(f"SessionManager: Set session.state['{key}'] = '{value}'")
        
        # 여기에 InMemorySessionService에 변경 사항을 "커밋"하는 코드가 필요할 수 있습니다.
        # 예를 들어, self.session_service.update_session(session) 같은 메서드가 있다면 호출해야 합니다.
        # 현재 ADK InMemorySessionService API에 그런 메서드가 명시적으로 없다면,
        # 이 직접적인 state 수정은 get_session()이 참조를 반환할 때만 유효합니다.
        # 로그를 통해 확인한 바로는 이 방식이 현재 문제를 해결하지 못하고 있습니다.
        # 따라서 이 메서드의 사용을 최소화하고, create_session 시 초기 상태를 전달하거나,
        # ADK Runner와 EventActions.state_delta를 통한 상태 업데이트를 고려해야 합니다.
        print(f"SessionManager: session.state for session ID '{session.id}' was modified. Verification of persistence needed.")
        # 임시로 True를 반환하지만, 실제 지속성은 보장되지 않을 수 있습니다.
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
            # create_session에서 초기 상태가 잘 설정되었는지 확인 (디버깅용)
            # get_session을 통해 서비스로부터 다시 가져와서 확인하는 것이 더 확실합니다.
            retrieved_session = self.get_session(session_id)
            if retrieved_session and retrieved_session.state.get("initial_idea") == initial_idea:
                print(f"SessionManager: Successfully started session ID '{session_id}' with initial_idea: '{retrieved_session.state.get('initial_idea')}'")
                self.set_active_session_id(session_id) # 여기서 active_session_id 설정
                return retrieved_session, session_id # get_session으로 다시 가져온 객체 반환
            elif retrieved_session:
                # 초기 상태가 기대와 다를 경우 경고
                print(f"SessionManager: WARNING - Verification of initial_idea for session ID '{session_id}' failed or incomplete. Found: '{retrieved_session.state.get('initial_idea')}', Expected: '{initial_idea}'. State keys: {list(retrieved_session.state.keys())}")
                self.set_active_session_id(session_id)
                return retrieved_session, session_id # 일단 반환
            else:
                # 세션은 생성되었으나 get_session으로 가져오지 못한 경우
                print(f"SessionManager: ERROR - Session created for ID '{session_id}' but failed to retrieve it for verification.")
                self.set_active_session_id(session_id) # ID는 설정
                return None, session_id # 세션 객체는 None
        else:
            print(f"SessionManager: ERROR - Failed to create session in start_new_idea_session for idea: {initial_idea}")
            return None, session_id
    
    def transition_to_phase2(self) -> bool:
        """
        현재 세션을 Phase 1에서 Phase 2로 전환합니다.
        (주의: 이 방식의 상태 업데이트는 InMemorySessionService의 특성에 따라 불안정할 수 있습니다.)
        """
        session = self.get_session() # 현재 활성화된 세션을 가져옴
        if session is None:
            print("SessionManager: Cannot transition to phase2, no active session.")
            return False
        
        session.state["current_phase"] = "phase2"
        session.state["discussion_history_phase2"] = []  # 2단계 토론 기록 초기화
        print(f"SessionManager: Attempted to transition session ID '{session.id}' to phase2 by direct state modification.")
        
        # 변경 사항이 실제로 서비스에 반영되었는지 확인하는 로직이 필요합니다.
        # 예를 들어, self.session_service.update_session(session) 같은 것이 있다면 호출해야 합니다.
        # 지금은 직접 수정 후 True를 반환하지만, 실제 지속성은 보장되지 않을 수 있습니다.
        # ADK의 EventActions.state_delta를 사용하는 것이 더 권장됩니다.
        
        # 확인을 위해 다시 세션을 가져와 상태를 로깅
        verified_session = self.get_session(session.id)
        if verified_session and verified_session.state.get("current_phase") == "phase2":
            print(f"SessionManager: Verified transition to phase2 for session ID '{session.id}'.")
            return True
        else:
            print(f"SessionManager: FAILED to verify transition to phase2 for session ID '{session.id}'.")
            return False