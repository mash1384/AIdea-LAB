"""
AIdea Lab Discussion Controller Module

이 모듈은 2단계 토론 로직을 담당합니다.
토론 퍼실리테이터와 페르소나 에이전트들 간의 대화를 조율하고 관리합니다.
"""

import asyncio
from google.adk.runners import Runner
from google.genai import types
from src.ui.state_manager import AppStateManager, SYSTEM_MESSAGES
from config.personas import PersonaType


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
                        user_id=self.user_id, session_id=session_id_string, new_message=input_content
                    )
                    
                    facilitator_response_content_full = ""
                    async for event in event_stream:
                        if event.is_final_response() if hasattr(event, 'is_final_response') else False:
                            facilitator_response_content = event.parts[0].text.strip()
                            facilitator_response_content_full += facilitator_response_content
                            print(f"DEBUG: Facilitator final response part: {facilitator_response_content}")
                            try:
                                facilitator_response_json = orchestrator.parse_facilitator_response(facilitator_response_content_full)
                                next_agent_str = facilitator_response_json.get("next_agent")
                                topic_for_next = facilitator_response_json.get("topic_for_next", "")
                                facilitator_thinking_process = facilitator_response_json.get("thinking_process", "")
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
                                
                            except ValueError as ve:
                                print(f"ERROR: Facilitator response is not valid JSON or parsing failed: {ve}")
                                print(f"Facilitator raw response: {facilitator_response_content_full}")
                                error_message = SYSTEM_MESSAGES.get("facilitator_json_error", "토론 진행자의 응답을 처리하는 중 오류가 발생했습니다.")
                                discussion_messages.append({
                                    "role": "system", "content": error_message, "avatar": "⚠️",
                                    "speaker": "system", "speaker_name": "시스템"
                                })
                                self.update_discussion_history(session_id_string, "system", error_message)
                                continue
                            
                            break
                        
                        elif event.parts:
                            facilitator_response_content_part = event.parts[0].text
                            facilitator_response_content_full += facilitator_response_content_part
                            print(f"DEBUG: Facilitator streaming: {facilitator_response_content_part}")

                    if not next_agent_str:
                        print("ERROR: Facilitator did not provide a response or next agent after stream.")
                        error_message = SYSTEM_MESSAGES.get("facilitator_no_response_error", "토론 진행자로부터 응답을 받지 못했습니다.")
                        discussion_messages.append({
                            "role": "system", "content": error_message, "avatar": "⚠️",
                            "speaker": "system", "speaker_name": "시스템"
                        })
                        self.update_discussion_history(session_id_string, "system", error_message)
                        continue
                
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
                
                if next_agent_str == "user":
                    print("INFO: Facilitator requests user input.")
                    AppStateManager.set_awaiting_user_input_phase2(True)
                    user_prompt = topic_for_next if topic_for_next else SYSTEM_MESSAGES.get("user_input_prompt_general", "다음 의견을 말씀해주십시오.")
                    AppStateManager.set_phase2_user_prompt(user_prompt)
                    return discussion_messages, "사용자 입력 대기", user_prompt
                
                if next_agent_str == "final_summary":
                    print("INFO: Facilitator requests final summary.")
                    final_summary_message = await self._execute_final_summary(session_id_string, orchestrator, persona_first_appearance)
                    if final_summary_message:
                        discussion_messages.append(final_summary_message)
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
                    async for event_persona in event_stream_persona:
                        if event_persona.is_final_response() if hasattr(event_persona, 'is_final_response') else False:
                            persona_response_content = event_persona.parts[0].text.strip()
                            persona_response_content_full += persona_response_content
                            print(f"DEBUG: Persona agent ({next_agent_str}) final response part: {persona_response_content}")
                            
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
                        
                        elif event_persona.parts:
                            persona_response_content_part = event_persona.parts[0].text
                            persona_response_content_full += persona_response_content_part
                            print(f"DEBUG: Persona agent ({next_agent_str}) streaming: {persona_response_content_part}")
                    
                    if not persona_response_content_full:
                        print(f"WARNING: Persona agent ({next_agent_str}) did not provide a response.")
                        no_response_message = SYSTEM_MESSAGES.get("persona_no_response_warning", f"{self.agent_name_map.get(next_agent_str, next_agent_str)}로부터 응답을 받지 못했습니다.")
                        discussion_messages.append({
                            "role": "system", "content": no_response_message, "avatar": "⚠️",
                            "speaker": "system", "speaker_name": "시스템"
                        })
                        self.update_discussion_history(session_id_string, "system", no_response_message)
                
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