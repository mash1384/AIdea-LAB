"""
ADK 연동 로직 캡슐화 모듈

이 모듈은 Google ADK와의 연동 로직을 캡슐화하여 UI 코드에서 ADK 실행의 세부사항을 분리합니다.
"""

import asyncio
import uuid
from typing import Optional, Tuple, List, Dict, Any
from google.adk.sessions import Session
from google.genai import types
from google.adk.runners import Runner
from google.adk.events import Event, EventActions

# 프로젝트 내부 임포트
from src.session_manager import SessionManager
from src.orchestrator.main_orchestrator import AIdeaLabOrchestrator


class AdkController:
    """
    ADK 연동 로직을 캡슐화하는 컨트롤러 클래스
    
    이 클래스는 Google ADK와의 모든 상호작용을 처리하며, UI 코드에서 ADK 실행의 
    세부사항을 숨깁니다.
    """
    
    def __init__(self, session_manager: SessionManager):
        """
        AdkController 초기화
        
        Args:
            session_manager (SessionManager): 세션 관리 인스턴스
        """
        self.session_manager = session_manager
        self.app_name = session_manager.app_name
        self.user_id = session_manager.user_id
    
    async def execute_phase1_workflow(self, session_id: str, input_content: types.Content, orchestrator: AIdeaLabOrchestrator) -> Tuple[bool, List[Dict], set]:
        """
        1단계 분석 워크플로우를 실행합니다.
        
        Args:
            session_id (str): 세션 ID
            input_content (types.Content): 입력 콘텐츠
            orchestrator (AIdeaLabOrchestrator): 오케스트레이터 인스턴스
            
        Returns:
            Tuple[bool, List[Dict], set]: (성공 여부, 처리된 결과 리스트, 처리된 출력 키 집합)
        """
        print(f"DEBUG: AdkController.execute_phase1_workflow - Starting with session_id: {session_id}")
        
        # SessionManager 인스턴스 검증 로그 추가
        print(f"DEBUG: AdkController SessionManager instance verification:")
        print(f"  - SessionManager ID: {id(self.session_manager)}")
        print(f"  - SessionManager.session_service ID: {id(self.session_manager.session_service)}")
        print(f"  - SessionManager app_name: '{self.app_name}'")
        print(f"  - SessionManager user_id: '{self.user_id}'")
        
        # SessionManager 디버깅 정보 출력
        debug_info = self.session_manager.debug_session_service_state()
        print(f"DEBUG: SessionManager debug info at Phase1 start:")
        for key, value in debug_info.items():
            print(f"  - {key}: {value}")
        
        workflow_completed = False
        any_response_processed_successfully = False
        processed_sub_agent_outputs = set()
        
        try:
            # 오케스트레이터에서 출력 키 정보 가져오기
            output_keys_map = orchestrator.get_output_keys_phase1()
            expected_sub_agent_output_count = len(output_keys_map)
            
            print(f"DEBUG: Expected sub-agent output count: {expected_sub_agent_output_count}")
            print(f"DEBUG: Output keys to track from orchestrator: {output_keys_map}")
            
            # 결과를 저장할 리스트
            processed_results = []
            
            # Runner 생성 및 실행
            runner = Runner(
                agent=orchestrator.get_phase1_workflow(),
                app_name=self.app_name,
                session_service=self.session_manager.session_service
            )
            
            event_stream = runner.run_async(
                user_id=self.user_id,
                session_id=session_id,
                new_message=input_content
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
                            result = self._process_response(
                                output_key_in_delta,
                                response_text,
                                agent_author
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
            
            print(f"DEBUG: AdkController.execute_phase1_workflow - Finished. WorkflowCompleted={workflow_completed}, AnyResponseProcessed={any_response_processed_successfully}")
            return (workflow_completed and any_response_processed_successfully, processed_results, processed_sub_agent_outputs)
        
        except Exception as e:
            print(f"ERROR in AdkController.execute_phase1_workflow: {str(e)}")
            import traceback
            traceback.print_exc()
            return (False, [], processed_sub_agent_outputs)
    
    async def execute_phase2_facilitator(self, session_id: str, facilitator_agent) -> Optional[Dict[str, Any]]:
        """
        2단계 토론 퍼실리테이터를 실행합니다.
        
        Args:
            session_id (str): 세션 ID
            facilitator_agent: 퍼실리테이터 에이전트
            
        Returns:
            Optional[Dict[str, Any]]: 퍼실리테이터 응답 데이터 또는 None (실패 시)
        """
        try:
            runner = Runner(
                agent=facilitator_agent,
                app_name=self.app_name,
                session_service=self.session_manager.session_service
            )
            
            input_content = types.Content(role="user", parts=[types.Part(text="")])
            
            event_stream = runner.run_async(
                user_id=self.user_id,
                session_id=session_id,
                new_message=input_content
            )
            
            facilitator_response = None
            
            async for event in event_stream:
                is_final_event = event.is_final_response() if hasattr(event, 'is_final_response') else False
                event_actions = getattr(event, 'actions', None)
                state_delta = getattr(event_actions, 'state_delta', None) if event_actions else None
                
                if is_final_event and state_delta:
                    facilitator_response = state_delta.get("facilitator_response", "")
                    if facilitator_response and isinstance(facilitator_response, str):
                        return {
                            "raw_response": facilitator_response,
                            "success": True
                        }
            
            return {
                "raw_response": "",
                "success": False,
                "error": "No valid facilitator response received"
            }
            
        except Exception as e:
            print(f"ERROR in AdkController.execute_phase2_facilitator: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "raw_response": "",
                "success": False,
                "error": str(e)
            }
    
    async def execute_phase2_persona(self, session_id: str, persona_agent, persona_name: str) -> Optional[Dict[str, Any]]:
        """
        2단계 토론 페르소나 에이전트를 실행합니다.
        
        Args:
            session_id (str): 세션 ID
            persona_agent: 페르소나 에이전트
            persona_name (str): 페르소나 이름
            
        Returns:
            Optional[Dict[str, Any]]: 페르소나 응답 데이터 또는 None (실패 시)
        """
        try:
            runner = Runner(
                agent=persona_agent,
                app_name=self.app_name,
                session_service=self.session_manager.session_service
            )
            
            input_content = types.Content(role="user", parts=[types.Part(text="")])
            
            event_stream = runner.run_async(
                user_id=self.user_id,
                session_id=session_id,
                new_message=input_content
            )
            
            async for event in event_stream:
                is_final_event = event.is_final_response() if hasattr(event, 'is_final_response') else False
                event_actions = getattr(event, 'actions', None)
                state_delta = getattr(event_actions, 'state_delta', None) if event_actions else None
                
                if is_final_event and state_delta:
                    # 페르소나별 응답 키를 동적으로 처리
                    for key, value in state_delta.items():
                        if persona_name.lower() in key.lower() or key in ["marketer_response", "critic_response", "engineer_response", "final_summary_response"]:
                            return {
                                "response_key": key,
                                "response_content": value,
                                "success": True
                            }
            
            return {
                "response_key": "",
                "response_content": "",
                "success": False,
                "error": f"No valid response received from {persona_name}"
            }
            
        except Exception as e:
            print(f"ERROR in AdkController.execute_phase2_persona for {persona_name}: {str(e)}")
            import traceback
            traceback.print_exc()
            return {
                "response_key": "",
                "response_content": "",
                "success": False,
                "error": str(e)
            }
    
    def _validate_agent_response(self, response_text: str, agent_name: str, output_key: str) -> str:
        """
        에이전트 응답을 검증하고 필요 시 대체 응답을 생성합니다.
        
        Args:
            response_text (str): 원본 응답 텍스트
            agent_name (str): 에이전트 이름
            output_key (str): 출력 키
            
        Returns:
            str: 검증된 응답 텍스트 (대체 응답 포함)
        """
        # 중간 요약 응답인지 확인
        is_summary_response = "_summary" in output_key
        
        # 기본 유효성 검사
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
            has_key_points = "핵심 포인트:" in response_text
            has_summary = "종합 요약:" in response_text
            
            if not has_key_points:
                print(f"DEBUG_VALIDATION: OutputKey '{output_key}', Reason: Missing '핵심 포인트:' in summary.")
            
            if not has_summary:
                print(f"DEBUG_VALIDATION: OutputKey '{output_key}', Reason: Missing '종합 요약:' in summary.")
            
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
    
    def _process_response(self, output_key: str, response_text: str, agent_name: str) -> Dict[str, Any]:
        """
        응답을 처리하고 검증된 결과를 반환합니다.
        
        Args:
            output_key (str): 출력 키
            response_text (str): 응답 텍스트
            agent_name (str): 에이전트 이름
            
        Returns:
            Dict[str, Any]: 처리된 응답 정보
        """
        # 응답 검증 및 필요 시 대체 응답 생성
        validated_response = self._validate_agent_response(response_text, agent_name, output_key)
        
        # 응답이 변경되었으면 세션 상태 업데이트
        if validated_response != response_text:
            try:
                session = self.session_manager.get_session()
                if session:
                    event_actions = EventActions(
                        state_delta={output_key: validated_response}
                    )
                    new_event = Event(
                        actions=event_actions,
                        author=f"{agent_name}_fallback"
                    )
                    self.session_manager.session_service.append_event(
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
    
    def handle_adk_error(self, error: Exception, context: str) -> str:
        """
        ADK 관련 오류를 처리하고 사용자 친화적인 메시지를 반환합니다.
        
        Args:
            error (Exception): 발생한 오류
            context (str): 오류 발생 컨텍스트
            
        Returns:
            str: 사용자에게 표시할 오류 메시지
        """
        error_message = str(error).lower()
        
        if "api" in error_message and "key" in error_message:
            return "API 키 설정에 문제가 있습니다. 환경 변수를 확인해주세요."
        elif "network" in error_message or "connection" in error_message:
            return "네트워크 연결에 문제가 있습니다. 인터넷 연결을 확인해주세요."
        elif "quota" in error_message or "limit" in error_message:
            return "API 사용량 한도에 도달했습니다. 잠시 후 다시 시도해주세요."
        elif "timeout" in error_message:
            return "요청 시간이 초과되었습니다. 다시 시도해주세요."
        else:
            print(f"ERROR in {context}: {str(error)}")
            import traceback
            traceback.print_exc()
            return f"처리 중 오류가 발생했습니다: {str(error)}" 