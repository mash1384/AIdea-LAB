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
    
    def create_session(self) -> Tuple[Session, str]:
        """
        새로운 세션을 생성합니다.
        
        Returns:
            Tuple[Session, str]: 생성된 세션 객체와 세션 ID
        """
        session_id = f"session_{uuid.uuid4().hex[:8]}"
        session = self.session_service.create_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id
        )
        self.active_sessions[self.user_id] = session_id
        return session, session_id
    
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
                return None
        
        return self.session_service.get_session(
            app_name=self.app_name,
            user_id=self.user_id,
            session_id=session_id
        )
    
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
    
    def update_session_state(self, state_updates: Dict[str, Any]) -> bool:
        """
        현재 활성화된 세션의 상태를 업데이트합니다.
        
        Args:
            state_updates (Dict[str, Any]): 업데이트할 상태 키-값 쌍
            
        Returns:
            bool: 업데이트 성공 여부
        """
        session = self.get_session()
        if session is None:
            return False
        
        for key, value in state_updates.items():
            session.state[key] = value
        
        return True
    
    def get_session_state_value(self, key: str, default: Any = None) -> Any:
        """
        현재 활성화된 세션 상태에서 값을 조회합니다.
        
        Args:
            key (str): 조회할 상태 키
            default (Any, optional): 키가 없을 때 반환할 기본값
            
        Returns:
            Any: 조회된 상태 값 또는 기본값
        """
        session = self.get_session()
        if session is None:
            return default
        
        return session.state.get(key, default)
    
    def start_new_idea_session(self, initial_idea: str, user_goal: str = "", 
                              user_constraints: str = "", user_values: str = "") -> Tuple[Session, str]:
        """
        새로운 아이디어 분석을 위한 세션을 시작합니다.
        
        Args:
            initial_idea (str): 사용자의 초기 아이디어
            user_goal (str, optional): 아이디어의 핵심 목표
            user_constraints (str, optional): 주요 제약 조건
            user_values (str, optional): 중요 가치
            
        Returns:
            Tuple[Session, str]: 생성된 세션 객체와 세션 ID
        """
        session, session_id = self.create_session()
        
        # 초기 상태 설정
        session.state["initial_idea"] = initial_idea
        session.state["current_phase"] = "phase1"  # Phase 1 시작
        
        # 추가 정보가 있으면 저장
        if user_goal:
            session.state["user_goal"] = user_goal
        if user_constraints:
            session.state["user_constraints"] = user_constraints
        if user_values:
            session.state["user_values"] = user_values
        
        return session, session_id
    
    def transition_to_phase2(self) -> bool:
        """
        현재 세션을 Phase 1에서 Phase 2로 전환합니다.
        
        Returns:
            bool: 전환 성공 여부
        """
        session = self.get_session()
        if session is None:
            return False
        
        session.state["current_phase"] = "phase2"
        session.state["discussion_history_phase2"] = []  # 2단계 토론 기록 초기화
        
        return True 