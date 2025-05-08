"""
AIdea Lab 오케스트레이터

이 모듈은 다양한 AI 페르소나 에이전트들을 순차적으로 실행하고
그 결과를 조율하는 오케스트레이터 클래스를 구현합니다.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import Session
from google.genai import types

from config.prompts import ORCHESTRATOR_PROMPT, FINAL_SUMMARY_PROMPT
from config.personas import PersonaType, PERSONA_CONFIGS, PERSONA_SEQUENCE, ORCHESTRATOR_CONFIG

from src.agents.marketer_agent import MarketerPersonaAgent
from src.agents.critic_agent import CriticPersonaAgent
from src.agents.engineer_agent import EngineerPersonaAgent

# .env 파일에서 환경 변수 로드
load_dotenv()

class AIdeaLabOrchestrator:
    """아이디어 워크숍 오케스트레이터 클래스"""
    
    def __init__(self):
        """오케스트레이터 초기화"""
        # 오케스트레이터 설정 가져오기
        self.config = ORCHESTRATOR_CONFIG
        
        # 페르소나 에이전트들 생성
        self.marketer_agent = MarketerPersonaAgent()
        self.critic_agent = CriticPersonaAgent()
        self.engineer_agent = EngineerPersonaAgent()
        
        # 순차적으로 실행할 에이전트들의 순서 설정
        self.agents = []
        for persona_type in PERSONA_SEQUENCE:
            if persona_type == PersonaType.MARKETER:
                self.agents.append(self.marketer_agent.get_agent())
            elif persona_type == PersonaType.CRITIC:
                self.agents.append(self.critic_agent.get_agent())
            elif persona_type == PersonaType.ENGINEER:
                self.agents.append(self.engineer_agent.get_agent())
        
        # 최종 요약 생성을 위한 에이전트
        generate_config = {
            "temperature": self.config["temperature"],
            "max_output_tokens": self.config["max_output_tokens"]
        }
        
        self.summary_agent = Agent(
            name="summary_agent",
            model="gemini-2.0-flash",
            description="최종 요약 생성 에이전트",
            instruction=FINAL_SUMMARY_PROMPT,
            output_key=self.config["summary_output_key"],
            generate_content_config=generate_config
        )
        
        # 커스텀 에이전트로 대체하여 에이전트들을 직접 관리
        self.orchestrator_agent = Agent(
            name="aidea_lab_orchestrator",
            model="gemini-2.0-flash",
            description="AIdea Lab 워크숍 오케스트레이터",
            instruction=ORCHESTRATOR_PROMPT
        )
    
    def get_sequential_agent(self):
        """오케스트레이터 에이전트 반환"""
        return self.orchestrator_agent
    
    def get_summary_agent(self):
        """요약 에이전트 반환"""
        return self.summary_agent
    
    def get_output_keys(self):
        """모든 페르소나 에이전트의 출력 키 목록 반환"""
        return {
            "marketer": self.marketer_agent.get_output_key(),
            "critic": self.critic_agent.get_output_key(),
            "engineer": self.engineer_agent.get_output_key(),
            "summary": self.config["summary_output_key"]
        }
        
    async def run_all_personas_sequentially(self, session_service, app_name, user_id, session_id, idea_text):
        """
        페르소나 에이전트들을 순차적으로 실행하는 함수
        """
        session = session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
        
        # 아이디어가 세션 상태에 있는지 확인하고 없으면 저장
        if "initial_idea" not in session.state:
            session.state["initial_idea"] = idea_text
            
        # 각 페르소나를 순서대로 실행
        for i, agent in enumerate(self.agents):
            persona_type = PERSONA_SEQUENCE[i]
            content = types.Content(
                role="user",
                parts=[types.Part(text=f"다음 아이디어를 분석해주세요: {idea_text}")]
            )
            
            # Runner 생성 및 실행
            runner = Runner(
                agent=agent,
                app_name=app_name,
                session_service=session_service
            )
            
            # 에이전트 실행
            events = runner.run(
                user_id=user_id,
                session_id=session_id,
                new_message=content
            )
            
            # 이벤트 처리
            for event in events:
                if event.is_final_response():
                    break
        
        # 업데이트된 세션 반환
        return session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id) 