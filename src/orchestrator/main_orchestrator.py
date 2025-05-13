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
from google.genai import types  # types 모듈 임포트 추가

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
        
        # 최종 요약 생성을 위한 에이전트의 GenerationConfig 설정
        generate_config = types.GenerationConfig(
            temperature=self.config["temperature"],
            max_output_tokens=self.config["max_output_tokens"]
        )
        
        self.summary_agent = Agent(
            name="summary_agent",
            model=self.model_name,
            description="최종 요약 생성 에이전트",
            instruction=FINAL_SUMMARY_PROMPT,
            output_key=self.config["summary_output_key"],
            generate_content_config=generate_config  # 생성 설정 명시적으로 전달
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
        # 직접 에이전트 객체를 가져와서 output_key 설정
        marketer_agent = marketer_agent_phase1.get_agent()
        marketer_agent.output_key = "marketer_report_phase1"  # 명확한 Phase 1 접미사 추가
        
        # 비판적 분석가 에이전트 (1단계용)
        critic_agent_phase1 = CriticPersonaAgent(model_name=self.model_name)
        # 직접 에이전트 객체를 가져와서 output_key 설정
        critic_agent = critic_agent_phase1.get_agent()
        critic_agent.output_key = "critic_report_phase1"  # 명확한 Phase 1 접미사 추가
        
        # 현실적 엔지니어 에이전트 (1단계용)
        engineer_agent_phase1 = EngineerPersonaAgent(model_name=self.model_name)
        # 직접 에이전트 객체를 가져와서 output_key 설정
        engineer_agent = engineer_agent_phase1.get_agent()
        engineer_agent.output_key = "engineer_report_phase1"  # 명확한 Phase 1 접미사 추가
        
        # 페르소나 순서에 따라 에이전트 추가
        for persona_type in PERSONA_SEQUENCE:
            if persona_type == PersonaType.MARKETER:
                phase1_agents.append(marketer_agent)
            elif persona_type == PersonaType.CRITIC:
                phase1_agents.append(critic_agent)
            elif persona_type == PersonaType.ENGINEER:
                phase1_agents.append(engineer_agent)
        
        # 최종 요약 에이전트 (1단계용)
        # 각 페르소나 에이전트의 output_key를 명시적으로 참조하는 수정된 프롬프트
        summary_prompt = FINAL_SUMMARY_PROMPT.replace("{state.marketer_response}", "{state.marketer_report_phase1}")
        summary_prompt = summary_prompt.replace("{state.critic_response}", "{state.critic_report_phase1}")
        summary_prompt = summary_prompt.replace("{state.engineer_response}", "{state.engineer_report_phase1}")
        
        # 요약 에이전트의 GenerationConfig 생성
        summary_generate_config = types.GenerationConfig(
            temperature=self.config["temperature"],
            max_output_tokens=self.config["max_output_tokens"]
        )
        
        summary_agent_phase1 = Agent(
            name="summary_agent_phase1",
            model=self.model_name,
            description="1단계 아이디어 분석 요약 에이전트",
            instruction=summary_prompt,
            output_key="summary_report_phase1",  # 명확한 Phase 1 접미사 추가
            generate_content_config=summary_generate_config  # 생성 설정 명시적으로 전달
        )
        
        # 디버깅 로그 출력
        print(f"Created phase1 agents - Marketer output_key: {marketer_agent.output_key}")
        print(f"Created phase1 agents - Critic output_key: {critic_agent.output_key}")
        print(f"Created phase1 agents - Engineer output_key: {engineer_agent.output_key}")
        print(f"Created phase1 agents - Summary output_key: {summary_agent_phase1.output_key}")
        
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
    
    def get_phase2_discussion_facilitator(self):
        """
        2단계 토론 촉진자 에이전트를 반환합니다.
        
        2단계 토론 촉진자는 페르소나들 간의 토론을 유도하고,
        다음에 어떤 페르소나가 발언할지, 어떤 주제에 대해 토론할지를 결정합니다.
        
        Returns:
            Agent: 토론 촉진자 에이전트
        """
        from src.agents.facilitator_agent import DiscussionFacilitatorAgent
        from config.prompts import FACILITATOR_PHASE2_PROMPT_PROVIDER
        
        # 2단계 토론 촉진자 에이전트 생성
        facilitator_agent = DiscussionFacilitatorAgent(
            model_name=self.model_name,
            instruction_provider=FACILITATOR_PHASE2_PROMPT_PROVIDER
        )
        
        # 디버깅 로그 출력
        print(f"Created phase2 facilitator agent with output_key: {facilitator_agent.get_output_key()}")
        
        return facilitator_agent.get_agent()
    
    def get_phase2_persona_agent(self, persona_type):
        """
        2단계 토론용 페르소나 에이전트를 반환합니다.
        
        특정 페르소나 유형의 에이전트를 2단계 토론용 프롬프트 제공자 함수와 함께 생성하여 반환합니다.
        
        Args:
            persona_type (PersonaType): 페르소나 유형 (MARKETER, CRITIC, ENGINEER)
            
        Returns:
            Agent: 해당 페르소나의 2단계 토론용 에이전트 객체
        """
        from config.prompts import (
            MARKETER_PHASE2_PROMPT_PROVIDER,
            CRITIC_PHASE2_PROMPT_PROVIDER,
            ENGINEER_PHASE2_PROMPT_PROVIDER
        )
        
        # 페르소나 유형에 따라 적절한 에이전트와 프롬프트 제공자 선택
        if persona_type == PersonaType.MARKETER:
            # 마케터 에이전트 생성 - 2단계 프롬프트 제공자 적용
            persona_config = PERSONA_CONFIGS[PersonaType.MARKETER]
            generate_config = types.GenerationConfig(
                temperature=persona_config["temperature"],
                max_output_tokens=persona_config["max_output_tokens"]
            )
            
            agent = Agent(
                name="marketer_agent_phase2",
                model=self.model_name,
                description="2단계 토론용 창의적 마케터 에이전트",
                instruction=MARKETER_PHASE2_PROMPT_PROVIDER,  # 동적 프롬프트 제공자 함수
                output_key="marketer_response_phase2",
                generate_content_config=generate_config
            )
            
        elif persona_type == PersonaType.CRITIC:
            # 비판적 분석가 에이전트 생성 - 2단계 프롬프트 제공자 적용
            persona_config = PERSONA_CONFIGS[PersonaType.CRITIC]
            generate_config = types.GenerationConfig(
                temperature=persona_config["temperature"],
                max_output_tokens=persona_config["max_output_tokens"]
            )
            
            agent = Agent(
                name="critic_agent_phase2",
                model=self.model_name,
                description="2단계 토론용 비판적 분석가 에이전트",
                instruction=CRITIC_PHASE2_PROMPT_PROVIDER,  # 동적 프롬프트 제공자 함수
                output_key="critic_response_phase2",
                generate_content_config=generate_config
            )
            
        elif persona_type == PersonaType.ENGINEER:
            # 현실적 엔지니어 에이전트 생성 - 2단계 프롬프트 제공자 적용
            persona_config = PERSONA_CONFIGS[PersonaType.ENGINEER]
            generate_config = types.GenerationConfig(
                temperature=persona_config["temperature"],
                max_output_tokens=persona_config["max_output_tokens"]
            )
            
            agent = Agent(
                name="engineer_agent_phase2",
                model=self.model_name,
                description="2단계 토론용 현실적 엔지니어 에이전트",
                instruction=ENGINEER_PHASE2_PROMPT_PROVIDER,  # 동적 프롬프트 제공자 함수
                output_key="engineer_response_phase2",
                generate_content_config=generate_config
            )
            
        else:
            raise ValueError(f"지원되지 않는 페르소나 유형입니다: {persona_type}")
        
        # 디버깅 로그 출력
        print(f"Created phase2 {persona_type.name} agent with output_key: {agent.output_key}")
        
        return agent
    
    def get_phase2_final_summary_agent(self):
        """
        2단계 토론 종료 후 최종 요약을 생성할 에이전트를 반환합니다.
        
        2단계 토론의 결과와 1단계 분석 결과를 종합하여 
        최종 발전된 아이디어 및 실행 계획 보고서를 생성합니다.
        
        Returns:
            Agent: 2단계 최종 요약 에이전트
        """
        from config.prompts import FINAL_SUMMARY_PHASE2_PROMPT_PROVIDER
        
        # 요약 에이전트의 GenerationConfig 생성
        summary_generate_config = types.GenerationConfig(
            temperature=0.3,  # 명확한 요약을 위해 낮은 온도 설정
            max_output_tokens=4096  # 충분한 요약 내용을 위한 토큰 수 증가
        )
        
        # 2단계 최종 요약 에이전트 생성
        final_summary_agent = Agent(
            name="final_summary_agent_phase2",
            model=self.model_name,
            description="2단계 토론 최종 요약 에이전트",
            instruction=FINAL_SUMMARY_PHASE2_PROMPT_PROVIDER,  # 동적 프롬프트 제공자 함수
            output_key="final_summary_report_phase2",
            generate_content_config=summary_generate_config
        )
        
        # 디버깅 로그 출력
        print(f"Created phase2 final summary agent with output_key: {final_summary_agent.output_key}")
        
        return final_summary_agent 