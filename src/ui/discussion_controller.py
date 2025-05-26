"""
AIdea Lab Discussion Controller Module

이 모듈은 2단계 토론 로직을 담당합니다.
토론 퍼실리테이터와 페르소나 에이전트들 간의 대화를 조율하고 관리합니다.
"""

import asyncio
from google.adk.runners import Runner
from google.genai import types
from src.ui.state_manager import AppStateManager, SYSTEM_MESSAGES


class DiscussionController:
    """
    2단계 토론을 관리하는 컨트롤러 클래스
    """
    
    def __init__(self, session_manager):
        """
        DiscussionController 초기화
        
        Args:
            session_manager: SessionManager 인스턴스
        """
        self.session_manager = session_manager
        self.app_name = session_manager.app_name
        self.user_id = session_manager.user_id
        
        # 각 에이전트의 응답을 표시할 때 사용할 아바타 매핑
        self.agent_to_avatar_map = {
            "facilitator": "🎯",
            "marketer_agent": "💡",
            "critic_agent": "🔍",
            "engineer_agent": "⚙️",
            "user": "🧑‍💻",
            "final_summary": "📊"
        }
        
        # 에이전트 이름 매핑
        self.agent_name_map = {
            "marketer_agent": "마케팅 분석가",
            "critic_agent": "비판적 분석가",
            "engineer_agent": "현실주의 엔지니어",
            "facilitator": "토론 진행자",
            "user": "사용자",
            "final_summary": "최종 요약"
        }
        
        # 페르소나 소개 메시지 키 매핑
        self.persona_intro_key_map = {
            "facilitator": "facilitator_intro",
            "marketer_agent": "marketer_phase2_intro",
            "critic_agent": "critic_phase2_intro",
            "engineer_agent": "engineer_phase2_intro",
            "final_summary": "final_summary_phase2_intro"
        }
    
    def update_discussion_history(self, session_id: str, speaker: str, content: str):
        """
        토론 히스토리를 업데이트합니다.
        
        Args:
            session_id (str): 세션 ID
            speaker (str): 발화자
            content (str): 발화 내용
        """
        try:
            session = self.session_manager.get_session(session_id)
            if session:
                # discussion_history_phase2 가져오기
                discussion_history = session.state.get("discussion_history_phase2", [])
                
                # 새 항목 추가
                discussion_history.append({
                    "speaker": speaker,
                    "content": content
                })
                
                # 세션 상태 업데이트
                session.state["discussion_history_phase2"] = discussion_history
                print(f"DEBUG: Updated discussion history for session {session_id}, speaker: {speaker}")
            else:
                print(f"ERROR: Could not find session {session_id} for discussion history update")
        except Exception as e:
            print(f"ERROR: Failed to update discussion history: {e}")
    
    async def run_phase2_discussion(self, session_id_string: str, orchestrator):
        """
        2단계 토론 실행 함수
        
        토론 퍼실리테이터 및 페르소나 에이전트들 간의 대화를 조율하고 결과를 구조화된 리스트로 반환합니다.
        UI를 직접 업데이트하거나 st.rerun()을 호출하지 않습니다.
        
        Args:
            session_id_string (str): 세션 ID
            orchestrator: 오케스트레이터 객체
        
        Returns:
            tuple: (토론 메시지 리스트, 상태 문자열, 사용자 질문(있는 경우))
                  상태 문자열은 "진행 중", "완료", "사용자 입력 대기" 중 하나입니다.
        """
        print(f"DEBUG: DiscussionController.run_phase2_discussion - Starting with session_id: {session_id_string}")
        
        # 디버깅 로그 추가 - 인스턴스 및 세션 정보 출력
        print(f"DEBUG: DiscussionController instance verification:")
        print(f"  - session_id_string: '{session_id_string}'")
        print(f"  - self.app_name: '{self.app_name}'")
        print(f"  - self.user_id: '{self.user_id}'")
        print(f"  - SessionManager instance ID: {id(self.session_manager)}")
        print(f"  - SessionService instance ID: {id(self.session_manager.session_service)}")
        
        # 세션 서비스에서 직접 세션 조회 테스트
        try:
            direct_session_lookup = self.session_manager.session_service.get_session(
                app_name=self.app_name,
                user_id=self.user_id,
                session_id=session_id_string
            )
            if direct_session_lookup:
                print(f"DEBUG: Direct session lookup: FOUND")
                print(f"  - Session state keys: {list(direct_session_lookup.state.keys())}")
            else:
                print(f"DEBUG: Direct session lookup: NOT FOUND")
                
                # SessionManager의 디버깅 메서드를 활용하여 상세 정보 출력
                debug_info = self.session_manager.debug_session_service_state()
                print(f"DEBUG: SessionManager debug info:")
                for key, value in debug_info.items():
                    print(f"  - {key}: {value}")
                
                # 추가: 예상 세션 키 생성 및 비교
                expected_session_keys = []
                available_keys = debug_info.get("available_session_keys", [])
                
                # 현재 세션 ID와 유사한 키가 있는지 확인
                similar_keys = [key for key in available_keys if session_id_string in str(key)]
                if similar_keys:
                    print(f"  - Keys containing session_id '{session_id_string}': {similar_keys}")
                
                # app_name, user_id가 포함된 키 확인
                app_user_keys = [key for key in available_keys if self.app_name in str(key) or self.user_id in str(key)]
                if app_user_keys:
                    print(f"  - Keys containing app_name/user_id: {app_user_keys}")
                
                if not available_keys:
                    print(f"  - WARNING: No sessions found in session service storage!")
        
        except Exception as e:
            print(f"DEBUG: Error during direct session lookup: {e}")
            import traceback
            traceback.print_exc()
        
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
            session = self.session_manager.get_session(session_id_string)
            if not session:
                print(f"ERROR: Failed to get session with ID {session_id_string} in run_phase2_discussion.")
                # 세션 매니저의 활성 세션들 정보 출력
                print(f"DEBUG: Active sessions: {self.session_manager.active_sessions}")
                print(f"DEBUG: Session service status: {self.session_manager.session_service}")
                
                # 세션 복구 시도
                print("DEBUG: Attempting to recover session...")
                active_session_id = self.session_manager.get_active_session_id()
                if active_session_id:
                    print(f"DEBUG: Found active session ID: {active_session_id}")
                    if active_session_id != session_id_string:
                        print(f"DEBUG: Session ID mismatch - Expected: {session_id_string}, Active: {active_session_id}")
                        # 활성 세션 ID로 다시 시도
                        session = self.session_manager.get_session(active_session_id)
                        if session:
                            print(f"DEBUG: Successfully recovered session using active session ID")
                            session_id_string = active_session_id
                        else:
                            print(f"DEBUG: Failed to recover session even with active session ID")
                
                if not session:
                    return discussion_messages, "오류", None
            
            # 토론 퍼실리테이터 에이전트 가져오기
            facilitator_agent = orchestrator.get_phase2_discussion_facilitator()
            
            # 최대 토론 반복 횟수
            max_discussion_rounds = 15
            current_round = 0
            
            # 사용자 입력 대기 상태 확인
            if AppStateManager.is_awaiting_user_input_phase2():
                # 사용자 입력이 있은 경우, 토론 히스토리에 추가
                user_response = AppStateManager.get_phase2_user_response()
                if user_response:
                    self.update_discussion_history(session_id_string, "user", user_response)
                    
                    # 사용자 응답을 토론 메시지에 추가
                    discussion_messages.append({
                        "role": "user",
                        "content": user_response,
                        "avatar": self.agent_to_avatar_map["user"],
                        "speaker": "user",
                        "speaker_name": self.agent_name_map["user"]
                    })
                    
                    # 사용자 입력 대기 상태 초기화
                    AppStateManager.set_awaiting_user_input_phase2(False)
                    AppStateManager.set_phase2_user_prompt("")
            
            # 토론 루프 시작
            while current_round <= max_discussion_rounds:
                current_round += 1
                print(f"DEBUG: Starting discussion round {current_round}/{max_discussion_rounds}")
                
                try:
                    # 퍼실리테이터 에이전트 실행
                    runner = Runner(
                        agent=facilitator_agent,
                        app_name=self.app_name,
                        session_service=self.session_manager.session_service
                    )
                    
                    input_content = types.Content(role="user", parts=[types.Part(text="")])
                    
                    # 퍼실리테이터 에이전트의 응답 처리
                    next_agent = None
                    topic_for_next = ""
                    
                    # 퍼실리테이터 사고 중 메시지는 생성하되 리스트에 추가하지 않음
                    print("토론 퍼실리테이터가 다음 단계를 결정하고 있습니다...")
                    
                    event_stream = runner.run_async(
                        user_id=self.user_id,
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
                                self.update_discussion_history(session_id_string, "facilitator", facilitator_response)
                                
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
                                    
                                    print(f"DEBUG: ===== FACILITATOR JSON PARSING RESULT =====")
                                    print(f"DEBUG: Full JSON data: {json_data}")
                                    print(f"DEBUG: next_agent: '{next_agent}' (type: {type(next_agent)})")
                                    print(f"DEBUG: topic_for_next: '{topic_for_next}' (length: {len(topic_for_next)})")
                                    print(f"DEBUG: reasoning: '{reasoning}' (length: {len(reasoning)})")
                                    print(f"DEBUG: ===== END FACILITATOR JSON PARSING =====")
                                    
                                    # 마지막 라운드에 도달했는데 FINAL_SUMMARY가 아니라면 강제로 FINAL_SUMMARY로 설정
                                    if current_round >= max_discussion_rounds and next_agent != "FINAL_SUMMARY":
                                        print(f"INFO: Forcing transition to FINAL_SUMMARY at round {current_round}/{max_discussion_rounds}")
                                        next_agent = "FINAL_SUMMARY"
                                        topic_for_next = "최대 토론 라운드에 도달하여 최종 요약을 진행합니다."
                                    
                                    print(f"DEBUG: Extracted JSON data from facilitator_response:")
                                    print(f"  - next_agent: {next_agent}")
                                    print(f"  - topic: {topic_for_next[:50]}...")
                                    print(f"  - reasoning: {reasoning[:50]}...")
                                    
                                    # 다음 단계 라우팅 결정 로깅
                                    if next_agent in ["marketer_agent", "critic_agent", "engineer_agent"]:
                                        print(f"DEBUG: ✓ FACILITATOR REQUESTED PERSONA AGENT: {next_agent}")
                                    elif next_agent == "USER":
                                        print(f"DEBUG: ✓ FACILITATOR REQUESTED USER INPUT")
                                    elif next_agent == "FINAL_SUMMARY":
                                        print(f"DEBUG: ✓ FACILITATOR REQUESTED FINAL SUMMARY")
                                    else:
                                        print(f"DEBUG: ⚠️ UNKNOWN NEXT_AGENT VALUE: '{next_agent}'")
                                    
                                    # 퍼실리테이터 첫 등장 시 소개 메시지 추가
                                    if persona_first_appearance.get("facilitator", True):
                                        intro_key = self.persona_intro_key_map.get("facilitator")
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
                                        agent_display_name = self.agent_name_map.get(next_agent, next_agent)
                                        
                                        # 토픽과 이유를 결합하여 간결한 안내 메시지 생성
                                        facilitator_ui_message = f"다음은 {agent_display_name}에게 질문드립니다: {topic_for_next}"
                                        if reasoning:
                                            facilitator_ui_message += f" (이유: {reasoning})"
                                    
                                    # 가공된 퍼실리테이터 메시지를 리스트에 추가
                                    discussion_messages.append({
                                        "role": "assistant",
                                        "content": facilitator_ui_message,
                                        "avatar": self.agent_to_avatar_map["facilitator"],
                                        "speaker": "facilitator",
                                        "speaker_name": self.agent_name_map["facilitator"]
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
                        AppStateManager.set_awaiting_user_input_phase2(True)
                        AppStateManager.set_phase2_user_prompt(topic_for_next)
                        
                        # 사용자 입력을 기다리기 위해 루프를 빠져나감
                        return discussion_messages, "사용자 입력 대기", topic_for_next
                    
                    elif next_agent in ["marketer_agent", "critic_agent", "engineer_agent"]:
                        # 페르소나 에이전트 호출
                        try:
                            print(f"DEBUG: Calling persona agent: {next_agent}")
                            print(f"DEBUG: Topic for agent: {topic_for_next}")
                            
                            # 페르소나 타입 매핑
                            persona_type_map = {
                                "marketer_agent": "MARKETER",
                                "critic_agent": "CRITIC", 
                                "engineer_agent": "ENGINEER"
                            }
                            
                            persona_type = persona_type_map.get(next_agent)
                            if not persona_type:
                                print(f"ERROR: Unknown persona agent type: {next_agent}")
                                continue
                            
                            print(f"DEBUG: Mapped persona type: {persona_type}")
                            
                            # 퍼실리테이터의 질문을 세션에 저장
                            session = self.session_manager.get_session(session_id_string)
                            if session:
                                session.state["facilitator_question_to_persona"] = topic_for_next
                                print(f"DEBUG: Set facilitator_question_to_persona: {topic_for_next[:50]}...")
                            else:
                                print(f"ERROR: Failed to get session for setting facilitator question")
                            
                            # 페르소나 에이전트 생성 및 실행
                            print(f"DEBUG: Creating persona agent for type: {persona_type}")
                            persona_agent = orchestrator.get_phase2_persona_agent(persona_type)
                            print(f"DEBUG: Created persona agent: {persona_agent}")
                            
                            runner = Runner(
                                agent=persona_agent,
                                app_name=self.app_name,
                                session_service=self.session_manager.session_service
                            )
                            print(f"DEBUG: Created runner for persona agent")
                            
                            input_content = types.Content(role="user", parts=[types.Part(text="")])
                            
                            # 페르소나 사고 중 메시지
                            agent_display_name = self.agent_name_map.get(next_agent, next_agent)
                            print(f"{agent_display_name}가 응답을 준비하고 있습니다...")
                            
                            # 페르소나 에이전트 실행
                            print(f"DEBUG: Starting persona agent execution")
                            event_stream = runner.run_async(
                                user_id=self.user_id,
                                session_id=session_id_string,
                                new_message=input_content
                            )
                            print(f"DEBUG: Got event stream from persona agent")
                            
                            persona_response = None
                            event_count = 0
                            
                            async for event in event_stream:
                                event_count += 1
                                print(f"DEBUG: Processing event #{event_count} from persona agent")
                                
                                is_final_event = event.is_final_response() if hasattr(event, 'is_final_response') else False
                                event_actions = getattr(event, 'actions', None)
                                state_delta = getattr(event_actions, 'state_delta', None) if event_actions else None
                                
                                print(f"DEBUG: Event #{event_count} - is_final: {is_final_event}, has_actions: {event_actions is not None}, has_state_delta: {state_delta is not None}")
                                
                                if is_final_event and state_delta:
                                    print(f"DEBUG: Final event with state delta - keys: {list(state_delta.keys())}")
                                    
                                    # 페르소나별 응답 키 찾기
                                    response_key = f"{persona_type.lower()}_response_phase2"
                                    print(f"DEBUG: Looking for response key: {response_key}")
                                    persona_response = state_delta.get(response_key, "")
                                    
                                    if persona_response and isinstance(persona_response, str):
                                        print(f"DEBUG: Got {persona_type} response: {persona_response[:100]}...")
                                        
                                        # 페르소나 첫 등장 시 소개 메시지 추가
                                        if persona_first_appearance.get(next_agent, True):
                                            intro_key = self.persona_intro_key_map.get(next_agent)
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
                                        
                                        # 페르소나 응답을 리스트에 추가
                                        discussion_messages.append({
                                            "role": "assistant",
                                            "content": persona_response,
                                            "avatar": self.agent_to_avatar_map[next_agent],
                                            "speaker": next_agent,
                                            "speaker_name": agent_display_name
                                        })
                                        
                                        # 토론 히스토리에 페르소나 응답 추가
                                        self.update_discussion_history(session_id_string, next_agent, persona_response)
                                        
                                        break
                                    else:
                                        print(f"DEBUG: No valid response found for key {response_key}")
                                        print(f"DEBUG: Available state_delta keys: {list(state_delta.keys()) if state_delta else 'None'}")
                                        if state_delta:
                                            for key, value in state_delta.items():
                                                print(f"DEBUG: state_delta[{key}] = {type(value)} - {str(value)[:50]}...")
                            
                            print(f"DEBUG: Processed {event_count} events from persona agent")
                            
                            if not persona_response:
                                print(f"ERROR: No response received from {next_agent}")
                                # 에러 메시지 추가
                                discussion_messages.append({
                                    "role": "system",
                                    "content": f"{agent_display_name}의 응답을 받지 못했습니다.",
                                    "avatar": "ℹ️",
                                    "speaker": "system",
                                    "speaker_name": "시스템"
                                })
                        
                        except Exception as e:
                            print(f"ERROR calling persona agent {next_agent}: {e}")
                            import traceback
                            traceback.print_exc()
                            
                            # 에러 메시지 추가
                            discussion_messages.append({
                                "role": "system",
                                "content": f"페르소나 에이전트 호출 중 오류가 발생했습니다: {str(e)}",
                                "avatar": "ℹ️",
                                "speaker": "system",
                                "speaker_name": "시스템"
                            })
                    
                    elif next_agent == "FINAL_SUMMARY":
                        # 최종 요약으로 이동
                        print("DEBUG: Facilitator requested FINAL_SUMMARY, ending discussion loop")
                        AppStateManager.set_phase2_discussion_complete(True)
                        
                        # 토론 완료 메시지 추가
                        discussion_messages.append({
                            "role": "system",
                            "content": "토론이 완료되었습니다. 최종 요약을 생성합니다.",
                            "avatar": "ℹ️",
                            "speaker": "system",
                            "speaker_name": "시스템"
                        })
                        
                        # 최종 요약 실행
                        final_summary_messages = await self._execute_final_summary(
                            session_id_string, orchestrator, persona_first_appearance
                        )
                        discussion_messages.extend(final_summary_messages)
                        
                        # 토론과 요약 모두 완료
                        return discussion_messages, "완료", None
                
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
            if current_round > max_discussion_rounds and not AppStateManager.is_phase2_summary_complete():
                print(f"DEBUG: Reached maximum discussion rounds ({max_discussion_rounds}) without completing summary")
                
                # 최대 라운드 도달 메시지 추가
                discussion_messages.append({
                    "role": "system",
                    "content": "최대 토론 라운드에 도달하여 최종 요약을 진행합니다.",
                    "avatar": "ℹ️",
                    "speaker": "system",
                    "speaker_name": "시스템"
                })
                
                # 최종 요약 실행
                final_summary_messages = await self._execute_final_summary(
                    session_id_string, orchestrator, persona_first_appearance
                )
                discussion_messages.extend(final_summary_messages)
            
            return discussion_messages, "완료", None
        
        except Exception as e:
            print(f"Critical error in run_phase2_discussion: {e}")
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
    
    async def _execute_final_summary(self, session_id_string: str, orchestrator, persona_first_appearance: dict):
        """
        최종 요약을 실행하고 메시지 리스트를 반환합니다.
        
        Args:
            session_id_string (str): 세션 ID
            orchestrator: 오케스트레이터 객체
            persona_first_appearance (dict): 페르소나 첫 등장 여부 추적 딕셔너리
        
        Returns:
            list: 최종 요약 메시지 리스트
        """
        final_summary_messages = []
        
        try:
            # 최종 요약 에이전트 실행
            final_summary_agent = orchestrator.get_phase2_final_summary_agent()
            
            runner = Runner(
                agent=final_summary_agent,
                app_name=self.app_name,
                session_service=self.session_manager.session_service
            )
            
            # 빈 메시지로 실행하여 세션 상태를 직접 참조하도록 함
            input_content = types.Content(role="user", parts=[types.Part(text="")])
            
            # 최종 요약 생성 중 메시지
            print("최종 요약을 생성하고 있습니다...")
            
            # 최종 요약 에이전트 실행
            event_stream = runner.run_async(
                user_id=self.user_id,
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
                            intro_key = self.persona_intro_key_map.get("final_summary")
                            intro_content = SYSTEM_MESSAGES.get(intro_key)
                            if intro_content:
                                final_summary_messages.append({
                                    "role": "system",
                                    "content": intro_content,
                                    "avatar": "ℹ️",
                                    "speaker": "system",
                                    "speaker_name": "시스템"
                                })
                            persona_first_appearance["final_summary"] = False
                        
                        # 최종 요약 내용 리스트에 추가
                        final_summary_messages.append({
                            "role": "assistant",
                            "content": final_summary,
                            "avatar": self.agent_to_avatar_map["final_summary"],
                            "speaker": "final_summary",
                            "speaker_name": self.agent_name_map["final_summary"]
                        })
                        
                        # 토론 히스토리에 최종 요약 추가
                        self.update_discussion_history(session_id_string, "final_summary", final_summary)
                        
                        final_summary_processed = True
            
            # 최종 요약 완료 상태 설정
            AppStateManager.set_phase2_summary_complete(final_summary_processed)
            
        except Exception as e:
            print(f"ERROR in _execute_final_summary: {e}")
            final_summary_messages.append({
                "role": "system",
                "content": f"최종 요약 생성 중 오류가 발생했습니다: {str(e)}",
                "avatar": "ℹ️",
                "speaker": "system",
                "speaker_name": "시스템"
            })
        
        return final_summary_messages 