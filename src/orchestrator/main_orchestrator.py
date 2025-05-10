"""
AIdea Lab 오케스트레이터

이 모듈은 다양한 AI 페르소나 에이전트들을 순차적으로 실행하고
그 결과를 조율하는 오케스트레이터 클래스를 구현합니다.
"""

import os
import sys
from typing import Dict, Any
from google.adk.agents import Agent, SequentialAgent
from google.adk.runners import Runner

from config.prompts import FINAL_SUMMARY_PROMPT
from config.personas import PersonaType, PERSONA_CONFIGS, PERSONA_SEQUENCE, ORCHESTRATOR_CONFIG
from config.models import DEFAULT_MODEL

from src.agents.marketer_agent import MarketerPersonaAgent
from src.agents.critic_agent import CriticPersonaAgent
from src.agents.engineer_agent import EngineerPersonaAgent

# .env 파일은 애플리케이션의 메인 진입점(app.py)에서 로드됨

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
        # generate_config = {
        #     "temperature": self.config["temperature"],
        #     "max_output_tokens": self.config["max_output_tokens"],
        #     "safety_settings": [
        #         {
        #             'category': 'HARM_CATEGORY_HARASSMENT',
        #             'threshold': 'BLOCK_NONE'
        #         },
        #         {
        #             'category': 'HARM_CATEGORY_HATE_SPEECH',
        #             'threshold': 'BLOCK_NONE'
        #         },
        #         {
        #             'category': 'HARM_CATEGORY_SEXUALLY_EXPLICIT',
        #             'threshold': 'BLOCK_NONE'
        #         },
        #         {
        #             'category': 'HARM_CATEGORY_DANGEROUS_CONTENT',
        #             'threshold': 'BLOCK_NONE'
        #         }
        #     ]
        # }
        
        self.summary_agent = Agent(
            name="summary_agent",
            model=self.model_name,
            description="최종 요약 생성 에이전트",
            instruction=FINAL_SUMMARY_PROMPT,
            output_key=self.config["summary_output_key"]
            # generate_content_config=generate_config
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
    
    def get_phase1_workflow(self):
        """
        1단계 분석용 워크플로우 에이전트를 반환합니다.
        
        1단계에서는 세 가지 페르소나 에이전트가 순차적으로 실행되고,
        마지막으로 최종 요약 에이전트가 실행됩니다.
        
        Returns:
            SequentialAgent: 1단계 워크플로우 에이전트
        """
        # 각 페르소나 에이전트의 1단계용 인스턴스 생성
        # (기존 에이전트는 self.agents에 이미 저장되어 있지만, phase1 전용 에이전트를 생성)
        phase1_agents = []
        
        # 마케터 에이전트 (1단계용)
        marketer_agent_phase1 = MarketerPersonaAgent(model_name=self.model_name)
        marketer_agent_phase1.get_agent().output_key = "marketer_report_phase1"  # 명확한 Phase 1 접미사 추가
        
        # 비판적 분석가 에이전트 (1단계용)
        critic_agent_phase1 = CriticPersonaAgent(model_name=self.model_name)
        critic_agent_phase1.get_agent().output_key = "critic_report_phase1"  # 명확한 Phase 1 접미사 추가
        
        # 현실적 엔지니어 에이전트 (1단계용)
        engineer_agent_phase1 = EngineerPersonaAgent(model_name=self.model_name)
        engineer_agent_phase1.get_agent().output_key = "engineer_report_phase1"  # 명확한 Phase 1 접미사 추가
        
        # 페르소나 순서에 따라 에이전트 추가
        for persona_type in PERSONA_SEQUENCE:
            if persona_type == PersonaType.MARKETER:
                phase1_agents.append(marketer_agent_phase1.get_agent())
            elif persona_type == PersonaType.CRITIC:
                phase1_agents.append(critic_agent_phase1.get_agent())
            elif persona_type == PersonaType.ENGINEER:
                phase1_agents.append(engineer_agent_phase1.get_agent())
        
        # 최종 요약 에이전트 (1단계용)
        summary_agent_phase1 = Agent(
            name="summary_agent_phase1",
            model=self.model_name,
            description="1단계 아이디어 분석 요약 에이전트",
            instruction=FINAL_SUMMARY_PROMPT,
            output_key="summary_report_phase1"  # 명확한 Phase 1 접미사 추가
        )
        
        # 1단계 전용 워크플로우 에이전트 생성
        phase1_workflow_agent = SequentialAgent(
            name="aidea_lab_phase1_workflow",
            description="AIdea Lab 1단계 워크숍 시퀀스",
            sub_agents=[*phase1_agents, summary_agent_phase1]
        )
        
        return phase1_workflow_agent
    
    def get_summary_agent(self):
        """요약 에이전트 반환"""
        return self.summary_agent
    
    def get_output_keys_phase1(self):
        """
        1단계 분석에 사용되는 모든 페르소나 에이전트의 출력 키 목록을 반환합니다.
        이 키들은 session.state에서 각 페르소나 보고서를 가져오는 데 사용됩니다.
        
        Returns:
            Dict[str, str]: 페르소나 이름과 해당 출력 키 매핑 딕셔너리
        """
        return {
            "marketer": "marketer_report_phase1",
            "critic": "critic_report_phase1",
            "engineer": "engineer_report_phase1",
            "summary_phase1": "summary_report_phase1"
        } 