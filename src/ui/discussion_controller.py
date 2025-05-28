"""
AIdea Lab Discussion Controller Module

이 모듈은 2단계 토론 로직을 담당합니다.
토론 퍼실리테이터와 페르소나 에이전트들 간의 대화를 조율하고 관리합니다.
"""

import asyncio
import json
import re
import logging
from google.adk.runners import Runner
from google.genai import types
from src.ui.state_manager import AppStateManager, SYSTEM_MESSAGES
from config.personas import PersonaType
from datetime import datetime
import time


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
        Phase 2 토론 기록을 업데이트합니다.
        SessionManager의 update_session_state와 일관된 이벤트 기반 방식을 사용합니다.
        
        Args:
            session_id (str): 세션 ID
            speaker (str): 발화자
            content (str): 발화 내용
        """
        try:
            session = self.session_manager.get_session(session_id)
            if session:
                # 현재 토론 기록 가져오기
                current_discussion_history = session.state.get("discussion_history_phase2", [])
                
                # 새 항목 추가
                new_entry = {
                    "speaker": speaker,
                    "content": content,
                    "timestamp": datetime.now().isoformat()  # 타임스탬프 추가
                }
                updated_discussion_history = current_discussion_history + [new_entry]
                
                # SessionManager의 이벤트 기반 상태 업데이트 사용
                state_updates = {
                    "discussion_history_phase2": updated_discussion_history
                }
                
                success = self.session_manager.update_session_state(state_updates)
                if success:
                    logging.info(f"DiscussionController: Successfully updated discussion history for session {session_id}, speaker: {speaker}")
                else:
                    logging.error(f"DiscussionController: Failed to update discussion history for session {session_id}")
            else:
                logging.error(f"DiscussionController: Could not find session {session_id} for discussion history update")
        except Exception as e:
            logging.exception(f"DiscussionController: Failed to update discussion history: {e}")
    
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
        
        discussion_messages = []
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
            
            facilitator_agent = orchestrator.get_phase2_discussion_facilitator()
            max_discussion_rounds = 15
            current_round = 0
            
            if AppStateManager.is_awaiting_user_input_phase2():
                user_response = AppStateManager.get_phase2_user_response()
                if user_response:
                    self.update_discussion_history(session_id_string, "user", user_response)
                    discussion_messages.append({
                        "role": "user", "content": user_response,
                        "avatar": self.agent_to_avatar_map["user"], "speaker": "user",
                        "speaker_name": self.agent_name_map["user"]
                    })
                    AppStateManager.set_awaiting_user_input_phase2(False)
                    AppStateManager.set_phase2_user_prompt("")
            
            while current_round <= max_discussion_rounds:
                current_round += 1
                print(f"DEBUG: Starting discussion round {current_round}/{max_discussion_rounds}")
                
                next_agent_str = None
                topic_for_next = ""
                
                try:
                    runner = Runner(
                        agent=facilitator_agent,
                        app_name=self.app_name,
                        session_service=self.session_manager.session_service
                    )
                    input_content = types.Content(role="user", parts=[types.Part(text="")])
                    print("토론 퍼실리테이터가 다음 단계를 결정하고 있습니다...")
                    
                    event_stream = runner.run_async(
                        user_id=self.user_id,
                        session_id=session_id_string,
                        new_message=input_content
                    )
                    
                    facilitator_response_content_full = ""
                    parsed_facilitator_json = None
                    max_retries = 3
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            async for event in event_stream:
                                event_actions = getattr(event, 'actions', None)
                                
                                # 스트리밍 텍스트 처리
                                if (event_actions and 
                                    hasattr(event_actions, 'content_delta') and 
                                    event_actions.content_delta and 
                                    hasattr(event_actions.content_delta, 'parts')):
                                    delta_content = event_actions.content_delta
                                    if delta_content.parts and hasattr(delta_content.parts[0], 'text'):
                                        facilitator_response_content_full += delta_content.parts[0].text
                                        print(f"DEBUG: Facilitator streaming: {delta_content.parts[0].text}")
                                
                                # 최종 응답 처리
                                if event.is_final_response() if hasattr(event, 'is_final_response') else False:
                                    if event_actions and hasattr(event_actions, 'state_delta'):
                                        state_delta = event_actions.state_delta
                                        if state_delta and hasattr(facilitator_agent, 'output_key'):
                                            final_response = state_delta.get(facilitator_agent.output_key)
                                            if final_response:
                                                facilitator_response_content_full = final_response
                                    
                                    if facilitator_response_content_full:
                                        try:
                                            parsed_facilitator_json = self._parse_facilitator_response(facilitator_response_content_full)
                                            next_agent_str = parsed_facilitator_json.get("next_agent")
                                            topic_for_next = parsed_facilitator_json.get("message_to_next_agent_or_topic", "")
                                            facilitator_thinking_process = parsed_facilitator_json.get("reasoning", "")
                                            print(f"DEBUG: Parsed facilitator response - next_agent: {next_agent_str}, topic_for_next: {topic_for_next}")
                                            
                                            facilitator_display_content = f"{facilitator_thinking_process}\n\n다음 토론 주제: {topic_for_next}\n다음 발언자: {self.agent_name_map.get(next_agent_str, next_agent_str)}"
                                            facilitator_message = {
                                                "role": "assistant", "content": facilitator_display_content,
                                                "avatar": self.agent_to_avatar_map["facilitator"], "speaker": "facilitator",
                                                "speaker_name": self.agent_name_map["facilitator"]
                                            }
                                            if persona_first_appearance["facilitator"]:
                                                intro_message = SYSTEM_MESSAGES.get(self.persona_intro_key_map["facilitator"], "")
                                                discussion_messages.append({
                                                    "role": "system", "content": intro_message,
                                                    "avatar": self.agent_to_avatar_map["facilitator"], "speaker": "facilitator",
                                                    "speaker_name": self.agent_name_map["facilitator"]
                                                })
                                                persona_first_appearance["facilitator"] = False
                                            discussion_messages.append(facilitator_message)
                                            self.update_discussion_history(session_id_string, "facilitator", facilitator_display_content)
                                            break
                                            
                                        except ValueError as ve:
                                            print(f"ERROR: Facilitator response is not valid JSON or parsing failed: {ve}")
                                            print(f"Facilitator raw response: {facilitator_response_content_full}")
                                            
                                            # JSON 파싱 실패 시 재시도 로직
                                            if retry_count < max_retries - 1:
                                                print(f"Retrying with JSON format correction... (Attempt {retry_count + 1}/{max_retries})")
                                                
                                                # 오류 상세 정보와 함께 재시도를 위한 새로운 프롬프트 생성
                                                retry_prompt = self._create_json_retry_prompt(facilitator_response_content_full, str(ve))
                                                
                                                # 새로운 Runner와 이벤트 스트림 생성
                                                retry_runner = Runner(
                                                    agent=facilitator_agent,
                                                    app_name=self.app_name,
                                                    session_service=self.session_manager.session_service
                                                )
                                                retry_input = types.Content(role="user", parts=[types.Part(text=retry_prompt)])
                                                event_stream = retry_runner.run_async(
                                                    user_id=self.user_id,
                                                    session_id=session_id_string,
                                                    new_message=retry_input
                                                )
                                                
                                                # 응답 내용 초기화 후 재시도
                                                facilitator_response_content_full = ""
                                                retry_count += 1
                                                await asyncio.sleep(1)
                                                break  # 내부 루프 탈출하여 다시 이벤트 스트림 처리
                                            else:
                                                # 최대 재시도 횟수 초과
                                                error_message = SYSTEM_MESSAGES.get("facilitator_json_error", 
                                                    f"토론 진행자의 응답을 처리하는 중 오류가 발생했습니다. ({max_retries}회 재시도 후 실패)")
                                                discussion_messages.append({
                                                    "role": "system", "content": error_message, "avatar": "⚠️",
                                                    "speaker": "system", "speaker_name": "시스템"
                                                })
                                                self.update_discussion_history(session_id_string, "system", error_message)
                                                return discussion_messages, "오류", None
                            
                            if facilitator_response_content_full and parsed_facilitator_json:
                                break
                            
                            # 완전한 응답을 받지 못한 경우에도 재시도
                            if retry_count < max_retries - 1:
                                print(f"WARNING: No complete response received, retrying... (Attempt {retry_count + 1}/{max_retries})")
                                retry_count += 1
                                await asyncio.sleep(2)
                            else:
                                break
                            
                        except Exception as e:
                            print(f"ERROR during facilitator response processing: {e}")
                            retry_count += 1
                            if retry_count < max_retries:
                                print(f"Retrying due to error... (Attempt {retry_count + 1}/{max_retries})")
                                await asyncio.sleep(2)
                            else:
                                raise
                    
                    if not facilitator_response_content_full or not parsed_facilitator_json:
                        raise ValueError("No valid facilitator response received after maximum retries")
                
                except Exception as e:
                    print(f"ERROR: Error during facilitator agent execution: {e}")
                    import traceback
                    traceback.print_exc()
                    error_message = SYSTEM_MESSAGES.get("facilitator_execution_error", "토론 진행자 실행 중 오류가 발생했습니다.")
                    discussion_messages.append({
                        "role": "system", "content": error_message, "avatar": "⚠️",
                        "speaker": "system", "speaker_name": "시스템"
                    })
                    self.update_discussion_history(session_id_string, "system", error_message)
                    continue
                
                if not next_agent_str:
                    print("INFO: Facilitator did not specify a next agent. Ending discussion or awaiting user input.")
                    AppStateManager.set_awaiting_user_input_phase2(True)
                    AppStateManager.set_phase2_user_prompt(SYSTEM_MESSAGES.get("user_input_prompt_facilitator_choice", "진행자가 다음 토론자를 지정하지 않았습니다. 직접 토론을 이어가시겠습니까, 아니면 다른 주제로 넘어갈까요?"))
                    return discussion_messages, "사용자 입력 대기", AppStateManager.get_phase2_user_prompt()
                
                if next_agent_str.upper() == "USER":
                    print("INFO: Facilitator requests user input.")
                    AppStateManager.set_awaiting_user_input_phase2(True)
                    user_prompt = topic_for_next if topic_for_next else SYSTEM_MESSAGES.get("user_input_prompt_general", "다음 의견을 말씀해주십시오.")
                    AppStateManager.set_phase2_user_prompt(user_prompt)
                    return discussion_messages, "사용자 입력 대기", user_prompt
                
                if next_agent_str.upper() == "FINAL_SUMMARY":
                    print("INFO: Facilitator requests final summary.")
                    final_summary_message = await self._execute_final_summary(session_id_string, orchestrator, persona_first_appearance)
                    if final_summary_message:
                        discussion_messages.extend(final_summary_message)
                    return discussion_messages, "완료", None

                persona_type_to_call = None
                if next_agent_str == "marketer_agent":
                    persona_type_to_call = PersonaType.MARKETER
                elif next_agent_str == "critic_agent":
                    persona_type_to_call = PersonaType.CRITIC
                elif next_agent_str == "engineer_agent":
                    persona_type_to_call = PersonaType.ENGINEER
                else:
                    print(f"WARNING: Unknown next_agent string '{next_agent_str}'. Skipping persona call.")
                    warning_message = SYSTEM_MESSAGES.get("unknown_agent_warning", f"알 수 없는 다음 토론자({next_agent_str})가 지정되어 해당 순서를 건너니다.")
                    discussion_messages.append({
                        "role": "system", "content": warning_message, "avatar": "⚠️",
                        "speaker": "system", "speaker_name": "시스템"
                    })
                    self.update_discussion_history(session_id_string, "system", warning_message)
                    continue

                print(f"DEBUG: Mapped next_agent_str '{next_agent_str}' to PersonaType '{persona_type_to_call}'")
                
                try:
                    persona_agent = orchestrator.get_phase2_persona_agent(persona_type_to_call)
                    print(f"DEBUG: Successfully retrieved persona agent: {type(persona_agent).__name__} for PersonaType {persona_type_to_call}")

                    runner_persona = Runner(
                        agent=persona_agent,
                        app_name=self.app_name,
                        session_service=self.session_manager.session_service
                    )
                    input_for_persona = types.Content(role="user", parts=[types.Part(text=topic_for_next)])
                    
                    print(f"{self.agent_name_map.get(next_agent_str, next_agent_str)}가 응답을 준비하고 있습니다...")

                    event_stream_persona = runner_persona.run_async(
                        user_id=self.user_id, session_id=session_id_string, new_message=input_for_persona
                    )
                    
                    persona_response_content_full = ""
                    max_retries = 3
                    retry_count = 0
                    
                    while retry_count < max_retries:
                        try:
                            async for event_persona in event_stream_persona:
                                event_actions = getattr(event_persona, 'actions', None)
                                
                                # 스트리밍 텍스트 처리
                                if (event_actions and 
                                    hasattr(event_actions, 'content_delta') and 
                                    event_actions.content_delta and 
                                    hasattr(event_actions.content_delta, 'parts')):
                                    delta_content = event_actions.content_delta
                                    if delta_content.parts and hasattr(delta_content.parts[0], 'text'):
                                        persona_response_content_full += delta_content.parts[0].text
                                        print(f"DEBUG: Persona agent ({next_agent_str}) streaming: {delta_content.parts[0].text}")
                                
                                # 최종 응답 처리
                                if event_persona.is_final_response() if hasattr(event_persona, 'is_final_response') else False:
                                    if event_actions and hasattr(event_actions, 'state_delta'):
                                        state_delta = event_actions.state_delta
                                        if state_delta and hasattr(persona_agent, 'output_key'):
                                            final_response = state_delta.get(persona_agent.output_key)
                                            if final_response:
                                                persona_response_content_full = final_response
                                                print(f"DEBUG: Found response for key: {persona_agent.output_key}")
                                    
                                    if persona_response_content_full:
                                        print(f"DEBUG: Persona agent ({next_agent_str}) final response: {persona_response_content_full}")
                                        
                                        persona_message = {
                                            "role": "assistant", "content": persona_response_content_full,
                                            "avatar": self.agent_to_avatar_map[next_agent_str],
                                            "speaker": next_agent_str,
                                            "speaker_name": self.agent_name_map[next_agent_str]
                                        }
                                        if persona_first_appearance[next_agent_str]:
                                            intro_key = self.persona_intro_key_map.get(next_agent_str)
                                            if intro_key:
                                                intro_message = SYSTEM_MESSAGES.get(intro_key, "")
                                                discussion_messages.append({
                                                    "role": "system", "content": intro_message,
                                                    "avatar": self.agent_to_avatar_map[next_agent_str], "speaker": next_agent_str,
                                                    "speaker_name": self.agent_name_map[next_agent_str]
                                                })
                                            persona_first_appearance[next_agent_str] = False
                                        discussion_messages.append(persona_message)
                                        self.update_discussion_history(session_id_string, next_agent_str, persona_response_content_full)
                                        break
                            
                            if persona_response_content_full:
                                break
                            
                            retry_count += 1
                            if retry_count < max_retries:
                                print(f"WARNING: No response received from persona agent ({next_agent_str}), retrying... (Attempt {retry_count + 1}/{max_retries})")
                                await asyncio.sleep(2)
                            
                        except ConnectionError as ce:
                            print(f"ERROR: Network connection error for persona agent ({next_agent_str}): {ce}")
                            retry_count += 1
                            if retry_count < max_retries:
                                print(f"Retrying due to network error... (Attempt {retry_count + 1}/{max_retries})")
                                await asyncio.sleep(3)  # 네트워크 오류 시 더 긴 대기
                            else:
                                network_error_message = SYSTEM_MESSAGES.get("network_error", 
                                    f"네트워크 연결 문제로 {self.agent_name_map.get(next_agent_str, next_agent_str)}의 응답을 받을 수 없습니다. 잠시 후 다시 시도해주세요.")
                                discussion_messages.append({
                                    "role": "system", "content": network_error_message, "avatar": "🌐",
                                    "speaker": "system", "speaker_name": "시스템"
                                })
                                self.update_discussion_history(session_id_string, "system", network_error_message)
                                return discussion_messages, "네트워크 오류", None
                        
                        except Exception as e:
                            print(f"ERROR during persona agent ({next_agent_str}) response processing: {e}")
                            
                            # HTTP 500 등 서버 오류 처리
                            if "500" in str(e) or "Internal Server Error" in str(e):
                                print(f"WARNING: Server error detected for persona agent ({next_agent_str}): {e}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    print(f"Retrying due to server error... (Attempt {retry_count + 1}/{max_retries})")
                                    await asyncio.sleep(5)  # 서버 오류 시 더 긴 대기
                                else:
                                    server_error_message = SYSTEM_MESSAGES.get("server_error", 
                                        f"서버 문제로 {self.agent_name_map.get(next_agent_str, next_agent_str)}의 응답을 받을 수 없습니다. 잠시 후 다시 시도해주세요.")
                                    discussion_messages.append({
                                        "role": "system", "content": server_error_message, "avatar": "⚠️",
                                        "speaker": "system", "speaker_name": "시스템"
                                    })
                                    self.update_discussion_history(session_id_string, "system", server_error_message)
                                    return discussion_messages, "서버 오류", None
                            
                            # API 레이트 리미트 오류 처리
                            elif "rate limit" in str(e).lower() or "quota" in str(e).lower():
                                print(f"WARNING: Rate limit error detected for persona agent ({next_agent_str}): {e}")
                                retry_count += 1
                                if retry_count < max_retries:
                                    print(f"Retrying due to rate limit... (Attempt {retry_count + 1}/{max_retries})")
                                    await asyncio.sleep(10)  # 레이트 리미트 시 더 긴 대기
                                else:
                                    rate_limit_message = SYSTEM_MESSAGES.get("rate_limit_error", 
                                        f"API 사용량 한도로 인해 {self.agent_name_map.get(next_agent_str, next_agent_str)}의 응답을 받을 수 없습니다. 잠시 후 다시 시도해주세요.")
                                    discussion_messages.append({
                                        "role": "system", "content": rate_limit_message, "avatar": "⏳",
                                        "speaker": "system", "speaker_name": "시스템"
                                    })
                                    self.update_discussion_history(session_id_string, "system", rate_limit_message)
                                    return discussion_messages, "API 한도 초과", None
                            
                            # 기타 일반적인 오류 처리
                            else:
                                retry_count += 1
                                if retry_count < max_retries:
                                    print(f"Retrying due to generic error... (Attempt {retry_count + 1}/{max_retries})")
                                    await asyncio.sleep(2)
                                else:
                                    raise
                    
                    if not persona_response_content_full:
                        print(f"WARNING: Persona agent ({next_agent_str}) did not provide a response after {max_retries} attempts.")
                        no_response_message = SYSTEM_MESSAGES.get("persona_no_response_warning", f"{self.agent_name_map.get(next_agent_str, next_agent_str)}로부터 응답을 받지 못했습니다.")
                        discussion_messages.append({
                            "role": "system", "content": no_response_message, "avatar": "⚠️",
                            "speaker": "system", "speaker_name": "시스템"
                        })
                        self.update_discussion_history(session_id_string, "system", no_response_message)
                        
                        # 대응 방안: 다른 페르소나로 토론 계속하기
                        available_agents = ["marketer_agent", "critic_agent", "engineer_agent"]
                        available_agents.remove(next_agent_str)  # 실패한 에이전트 제외
                        
                        if available_agents:
                            fallback_message = f"토론을 계속 진행하기 위해 다른 관점에서 의견을 들어보겠습니다."
                            discussion_messages.append({
                                "role": "system", "content": fallback_message, "avatar": "🔄",
                                "speaker": "system", "speaker_name": "시스템"
                            })
                            self.update_discussion_history(session_id_string, "system", fallback_message)
                            # 현재 라운드는 실패했지만 토론 계속 진행
                            continue
                        else:
                            # 모든 페르소나가 실패한 경우 토론 종료
                            critical_error_message = "모든 페르소나가 응답할 수 없는 상태입니다. 토론을 안전하게 종료합니다."
                            discussion_messages.append({
                                "role": "system", "content": critical_error_message, "avatar": "🛑",
                                "speaker": "system", "speaker_name": "시스템"
                            })
                            self.update_discussion_history(session_id_string, "system", critical_error_message)
                            return discussion_messages, "시스템 오류로 종료", None
                
                except ValueError as ve:
                    print(f"ERROR: Could not get persona agent for type {persona_type_to_call}. Error: {ve}")
                    error_message = SYSTEM_MESSAGES.get("persona_get_agent_error", f"{persona_type_to_call} 유형의 토론자를 가져오는 중 오류가 발생했습니다: {ve}")
                    discussion_messages.append({
                        "role": "system", "content": error_message, "avatar": "⚠️",
                        "speaker": "system", "speaker_name": "시스템"
                    })
                    self.update_discussion_history(session_id_string, "system", error_message)
                    continue
                
                except Exception as e:
                    print(f"ERROR: Error during persona agent ({next_agent_str}) execution: {e}")
                    import traceback
                    traceback.print_exc()
                    error_message = SYSTEM_MESSAGES.get("persona_execution_error", f"{self.agent_name_map.get(next_agent_str, next_agent_str)} 실행 중 오류가 발생했습니다.")
                    discussion_messages.append({
                        "role": "system", "content": error_message, "avatar": "⚠️",
                        "speaker": "system", "speaker_name": "시스템"
                    })
                    self.update_discussion_history(session_id_string, "system", error_message)
                    continue
            
            if current_round > max_discussion_rounds:
                print(f"INFO: Max discussion rounds ({max_discussion_rounds}) reached.")
                return discussion_messages, "완료", None
        
        except Exception as e:
            print(f"CRITICAL ERROR in run_phase2_discussion: {e}")
            return discussion_messages, "오류", None
        
        return discussion_messages, "완료", None

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
                    # final_summary_candidate를 통해 상세 로깅
                    final_summary_candidate = state_delta.get("final_summary_report_phase2", "KEY_NOT_FOUND")
                    print(f"DEBUG_SUMMARY: final_summary_candidate: {final_summary_candidate}")
                    print(f"DEBUG_SUMMARY: type(final_summary_candidate): {type(final_summary_candidate)}")
                    
                    # 유효한 문자열인지 확인
                    if (final_summary_candidate != "KEY_NOT_FOUND" and 
                        final_summary_candidate is not None and 
                        isinstance(final_summary_candidate, str) and 
                        final_summary_candidate.strip()):
                        
                        final_summary = final_summary_candidate
                        
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
                    else:
                        # 유효하지 않은 응답인 경우 로그 및 시스템 메시지 추가
                        print(f"ERROR_SUMMARY: Invalid final_summary_candidate received: value={final_summary_candidate}, type={type(final_summary_candidate)}")
                        final_summary_messages.append({
                            "role": "system",
                            "content": "최종 요약 내용을 가져오는 데 실패했습니다.",
                            "avatar": "⚠️",
                            "speaker": "system",
                            "speaker_name": "시스템"
                        })
            
            # 최종 요약 완료 상태 설정
            AppStateManager.set_phase2_summary_complete(final_summary_processed)
            
            # final_summary_processed가 False로 남아있는 경우 오류 메시지 추가
            if not final_summary_processed:
                final_summary_messages.append({
                    "role": "system",
                    "content": "최종 요약 생성에 실패했습니다. 에이전트로부터 유효한 응답을 받지 못했습니다.",
                    "avatar": "⚠️",
                    "speaker": "system",
                    "speaker_name": "시스템"
                })
            
        except Exception as e:
            print(f"ERROR in _execute_final_summary: {e}")
            final_summary_processed = False
            final_summary_messages.append({
                "role": "system",
                "content": "최종 요약 생성 중 오류가 발생했습니다. 관리자에게 문의하세요.",
                "avatar": "⚠️",
                "speaker": "system",
                "speaker_name": "시스템"
            })
        
        return final_summary_messages

    def _parse_facilitator_response(self, response_text: str) -> dict:
        """
        퍼실리테이터의 응답을 파싱하여 JSON 객체로 변환합니다.
        다양한 LLM 응답 변형에 대응할 수 있도록 방어 로직을 포함합니다.
        
        Args:
            response_text (str): 파싱할 JSON 문자열
            
        Returns:
            dict: 파싱된 JSON 객체
            
        Raises:
            ValueError: JSON 파싱에 실패한 경우
        """
        if not response_text or not response_text.strip():
            raise ValueError("응답 텍스트가 비어있습니다.")
        
        # 원본 텍스트 로깅
        print(f"DEBUG: Raw facilitator response: {response_text}")
        
        # 1. 먼저 전체 텍스트에서 JSON 객체 추출 시도
        json_candidates = []
        
        # 방법 1: 중괄호로 감싸진 영역 찾기 (가장 바깥쪽부터)
        brace_count = 0
        start_idx = -1
        for i, char in enumerate(response_text):
            if char == '{':
                if brace_count == 0:
                    start_idx = i
                brace_count += 1
            elif char == '}':
                brace_count -= 1
                if brace_count == 0 and start_idx != -1:
                    json_candidates.append(response_text[start_idx:i+1])
                    start_idx = -1
        
        # 방법 2: 정규식으로 JSON 패턴 찾기
        json_pattern = r'\{[^{}]*(?:\{[^{}]*\}[^{}]*)*\}'
        regex_matches = re.findall(json_pattern, response_text, re.DOTALL)
        json_candidates.extend(regex_matches)
        
        # 방법 3: 마크다운 코드 블록 내부 검사
        code_block_patterns = [
            r'```json\s*(\{.*?\})\s*```',
            r'```\s*(\{.*?\})\s*```',
            r'`(\{.*?\})`'
        ]
        for pattern in code_block_patterns:
            matches = re.findall(pattern, response_text, re.DOTALL)
            json_candidates.extend(matches)
        
        # 방법 4: 단순히 첫 번째 { 부터 마지막 } 까지 (기존 방식)
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}')
        if start_idx != -1 and end_idx != -1 and start_idx <= end_idx:
            json_candidates.append(response_text[start_idx:end_idx + 1])
        
        # 후보들을 중복 제거하고 정리
        unique_candidates = []
        for candidate in json_candidates:
            candidate = candidate.strip()
            if candidate and candidate not in unique_candidates:
                unique_candidates.append(candidate)
        
        print(f"DEBUG: Found {len(unique_candidates)} JSON candidates")
        
        # 각 후보에 대해 파싱 시도
        parsing_errors = []
        for i, candidate in enumerate(unique_candidates):
            try:
                # 텍스트 정리
                cleaned_candidate = self._clean_json_text(candidate)
                print(f"DEBUG: Trying candidate {i+1}: {cleaned_candidate[:100]}...")
                
                parsed_json = json.loads(cleaned_candidate)
                
                # 기본 구조 검증
                if not isinstance(parsed_json, dict):
                    raise ValueError("JSON이 객체(dict) 형태가 아닙니다.")
                
                # 필수 필드 검증
                if "next_agent" not in parsed_json:
                    raise ValueError("next_agent 필드가 없습니다.")
                
                # 유효한 next_agent 값인지 확인
                valid_agents = ["marketer_agent", "critic_agent", "engineer_agent", "USER", "FINAL_SUMMARY", "final_summary"]
                if parsed_json["next_agent"] not in valid_agents:
                    raise ValueError(f"next_agent 값이 유효하지 않습니다: {parsed_json['next_agent']}")
                
                # message_to_next_agent_or_topic 필드가 없으면 빈 문자열로 설정
                if "message_to_next_agent_or_topic" not in parsed_json:
                    parsed_json["message_to_next_agent_or_topic"] = ""
                
                # reasoning 필드가 없으면 빈 문자열로 설정
                if "reasoning" not in parsed_json:
                    parsed_json["reasoning"] = ""
                
                print(f"DEBUG: Successfully parsed JSON with candidate {i+1}")
                return parsed_json
                
            except json.JSONDecodeError as e:
                error_msg = f"Candidate {i+1} JSON 파싱 실패: {str(e)}"
                parsing_errors.append(error_msg)
                print(f"DEBUG: {error_msg}")
                continue
            except ValueError as e:
                error_msg = f"Candidate {i+1} 검증 실패: {str(e)}"
                parsing_errors.append(error_msg)
                print(f"DEBUG: {error_msg}")
                continue
            except Exception as e:
                error_msg = f"Candidate {i+1} 예상치 못한 오류: {str(e)}"
                parsing_errors.append(error_msg)
                print(f"DEBUG: {error_msg}")
                continue
        
        # 모든 후보가 실패한 경우
        all_errors = "; ".join(parsing_errors)
        raise ValueError(f"JSON 형식의 응답을 찾을 수 없습니다. 시도한 후보들의 오류: {all_errors}")
    
    def _clean_json_text(self, json_text: str) -> str:
        """
        JSON 텍스트를 정리하여 파싱 가능하도록 만듭니다.
        
        Args:
            json_text (str): 정리할 JSON 텍스트
            
        Returns:
            str: 정리된 JSON 텍스트
        """
        # 앞뒤 공백 제거
        cleaned = json_text.strip()
        
        # 마크다운 코드 블록 표시 제거
        cleaned = re.sub(r'^```json\s*', '', cleaned)
        cleaned = re.sub(r'^```\s*', '', cleaned)
        cleaned = re.sub(r'\s*```$', '', cleaned)
        
        # 백틱 제거
        cleaned = cleaned.strip('`')
        
        # 다시 앞뒤 공백 제거
        cleaned = cleaned.strip()
        
        # 제어 문자 제거 (개행, 탭 등은 유지)
        cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', cleaned)
        
        return cleaned
    
    def _create_json_retry_prompt(self, failed_response: str, error_message: str) -> str:
        """
        JSON 파싱 실패 시 재시도를 위한 프롬프트를 생성합니다.
        
        Args:
            failed_response (str): 파싱에 실패한 원본 응답
            error_message (str): 파싱 실패 오류 메시지
            
        Returns:
            str: 재시도를 위한 프롬프트
        """
        return f"""이전 응답이 올바른 JSON 형식이 아니어서 파싱에 실패했습니다.

오류 내용: {error_message}

이전 응답: {failed_response[:500]}{"..." if len(failed_response) > 500 else ""}

다시 응답해주세요. 반드시 다음 요구사항을 정확히 준수해야 합니다:

1. 순수한 JSON 객체만 응답하세요 (다른 텍스트 절대 금지)
2. 다음 정확한 형식을 사용하세요:
{{"next_agent":"값","message_to_next_agent_or_topic":"값","reasoning":"값"}}

3. next_agent는 다음 중 하나만 사용: marketer_agent, critic_agent, engineer_agent, USER, FINAL_SUMMARY

4. 마크다운 코드 블록(```) 사용 금지
5. 설명이나 인사말 추가 금지

올바른 예시: {{"next_agent":"marketer_agent","message_to_next_agent_or_topic":"시장 분석을 부탁드립니다","reasoning":"마케팅 관점이 필요함"}}""" 