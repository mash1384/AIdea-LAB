"""
AIdea Lab 오케스트레이터

이 모듈은 다양한 AI 페르소나 에이전트들을 순차적으로 실행하고
그 결과를 조율하는 오케스트레이터 클래스를 구현합니다.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent, SequentialAgent
from google.adk.runners import Runner
from google.genai import types

from config.prompts import FINAL_SUMMARY_PROMPT
from config.personas import PersonaType, PERSONA_CONFIGS, PERSONA_SEQUENCE, ORCHESTRATOR_CONFIG
from config.models import DEFAULT_MODEL

from src.agents.marketer_agent import MarketerPersonaAgent
from src.agents.critic_agent import CriticPersonaAgent
from src.agents.engineer_agent import EngineerPersonaAgent

# .env 파일에서 환경 변수 로드
load_dotenv()

class AIdeaLabOrchestrator:
    """아이디어 워크숍 오케스트레이터 클래스"""
    
    def __init__(self, model_name=None):
        """
        오케스트레이터 초기화
        
        Args:
            model_name (str, optional): 사용할 모델 이름. 기본값은 DEFAULT_MODEL.value
        """
        # 기본 모델 설정
        self.model_name = model_name or DEFAULT_MODEL.value
        
        # 오케스트레이터 설정 가져오기
        self.config = ORCHESTRATOR_CONFIG
        
        # 페르소나 에이전트들 생성 - model_name 전달
        self.marketer_agent = MarketerPersonaAgent(model_name=self.model_name)
        self.critic_agent = CriticPersonaAgent(model_name=self.model_name)
        self.engineer_agent = EngineerPersonaAgent(model_name=self.model_name)
        
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
            model=self.model_name,
            description="최종 요약 생성 에이전트",
            instruction=FINAL_SUMMARY_PROMPT,
            output_key=self.config["summary_output_key"],
            generate_content_config=generate_config
        )
        
        # SequentialAgent 생성하여 모든 페르소나 에이전트와 요약 에이전트를 포함
        self.workflow_agent = SequentialAgent(
            name="aidea_lab_workflow",
            description="AIdea Lab 워크숍 시퀀스",
            sub_agents=[*self.agents, self.summary_agent]
        )
    
    def get_workflow_agent(self):
        """워크플로우 에이전트(SequentialAgent) 반환"""
        return self.workflow_agent
    
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