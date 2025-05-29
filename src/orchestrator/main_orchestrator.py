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
    
    def create_intermediate_summarizer_agent(self, original_report_key: str, summary_output_key: str):
        """
        각 페르소나의 상세 보고서를 짧게 요약하는 중간 요약 에이전트를 생성합니다.
        
        Args:
            original_report_key (str): 원본 보고서의 상태 키 (예: "marketer_report_phase1")
            summary_output_key (str): 요약 결과를 저장할 상태 키 (예: "marketer_report_phase1_summary")
            
        Returns:
            Agent: 중간 요약 에이전트 객체
        """
        # 모델별 컨텍스트 제한 설정
        MODEL_CONTEXT_LIMITS = {
            "gemini-2.5-flash-preview-04-17": 12000,  # 프리뷰 모델은 더 짧은 컨텍스트
            "gemini-2.0-flash": 12000,
            "gemini-2.5-pro-exp-03-25": 16000,
            "gemini-2.5-pro-preview-05-06": 16000
        }
        
        # 현재 모델의 컨텍스트 제한 (기본값: 8000)
        current_model_limit = MODEL_CONTEXT_LIMITS.get(self.model_name, 8000)
        
        # 동적 프롬프트 제공자 함수 생성
        def intermediate_summary_prompt_provider(ctx):
            """
            중간 요약을 위한 동적 프롬프트 생성 함수
            
            Args:
                ctx: 세션 상태 컨텍스트
                
            Returns:
                str: 현재 세션 상태에 맞게 생성된 중간 요약 프롬프트
            """
            # 원본 보고서 내용 가져오기
            original_report_content = ctx.state.get(original_report_key, "")
            
            # marketer_report_phase1에 대한 상세 로깅
            if original_report_key == "marketer_report_phase1":
                print(f"DEBUG_MARKETER_STATE: Original report key: '{original_report_key}'")
                print(f"DEBUG_MARKETER_STATE: Report content type: {type(original_report_content)}")
                print(f"DEBUG_MARKETER_STATE: Report content length: {len(original_report_content) if original_report_content else 0} chars")
                if original_report_content:
                    # 처음 500자와 마지막 500자 로깅
                    first_500 = original_report_content[:500] if len(original_report_content) > 500 else original_report_content
                    last_500 = original_report_content[-500:] if len(original_report_content) > 500 else ""
                    print(f"DEBUG_MARKETER_STATE: First 500 chars: '{first_500}'")
                    if last_500:
                        print(f"DEBUG_MARKETER_STATE: Last 500 chars: '{last_500}'")
                else:
                    print(f"DEBUG_MARKETER_STATE: WARNING - Original report content is empty or None!")
            
            # 기본 요약 프롬프트 생성
            prompt = f"""
당신은 아이디어 워크숍의 페르소나 보고서를 요약하는 전문가입니다.

아래 텍스트는 워크숍 과정에서 특정 페르소나가 작성한 상세한 보고서입니다.
이 보고서를 다른 AI 에이전트들이 활용할 수 있도록 간결하고 핵심적인 내용만 담아 요약해주세요.

요약은 다음 형식을 준수해주세요:
1. "**핵심 포인트:**" 제목 아래에 불릿 포인트로 5개 이내의 핵심 요점을 나열하세요.
2. "**종합 요약:**" 제목 아래에 전체 내용을 2-3문장으로 요약하세요.

간결하게 요약해주세요.

분석할 텍스트:
{original_report_content}
"""
            
            return prompt
        
        # 중간 요약 에이전트의 GenerationConfig 설정 (max_output_tokens 증가)
        generate_config = types.GenerationConfig(
            temperature=0.1,  # 요약은 매우 명확하고 사실적이어야 하므로 낮은 온도 설정
            max_output_tokens=4096,  # 요약 생성을 위한 충분한 토큰 수로 증가
            top_p=0.8,  # 더 결정적인 응답을 위해 조정
            top_k=40,  # 더 결정적인 응답을 위해 조정
            candidate_count=1,  # 단일 응답만 필요
            stop_sequences=[]  # 특별한 중단 시퀀스 없음
        )
        
        # 페르소나 이름 추출 (예: marketer_report_phase1 -> marketer)
        persona_name = original_report_key.split("_")[0] if "_" in original_report_key else "unknown"
        
        # marketer_summary_agent 생성 시 상세 로깅 추가
        if original_report_key == "marketer_report_phase1":
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Creating intermediate summarizer agent")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Original report key: '{original_report_key}'")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Summary output key: '{summary_output_key}'")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Persona name: '{persona_name}'")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Model name: '{self.model_name}'")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Generate config:")
            print(f"  - temperature: {generate_config.temperature}")
            print(f"  - max_output_tokens: {generate_config.max_output_tokens}")
            print(f"  - top_p: {generate_config.top_p}")
            print(f"  - top_k: {generate_config.top_k}")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Using dynamic prompt provider for runtime state access")
        
        # 중간 요약 에이전트 생성 (동적 프롬프트 제공자 사용)
        intermediate_summary_agent = Agent(
            name=f"{persona_name}_summary_agent",
            model=self.model_name,
            description=f"{persona_name.capitalize()} 페르소나의 상세 보고서 중간 요약 에이전트",
            instruction=intermediate_summary_prompt_provider,  # 동적 프롬프트 제공자 사용
            output_key=summary_output_key,
            generate_content_config=generate_config
        )
        
        # 디버깅 로그 출력
        print(f"Created intermediate summary agent for {persona_name} with output_key: {summary_output_key}")
        print(f"Using dynamic prompt provider for runtime state access")
        
        if original_report_key == "marketer_report_phase1":
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Successfully created marketer_summary_agent")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Agent name: '{intermediate_summary_agent.name}'")
            print(f"DEBUG_MARKETER_ORCHESTRATOR: Agent output_key: '{intermediate_summary_agent.output_key}'")
        
        return intermediate_summary_agent
    
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
        
        # 각 페르소나 에이전트 실행 후 중간 요약 에이전트 추가
        # 마케터 중간 요약 에이전트
        marketer_summary_agent = self.create_intermediate_summarizer_agent(
            original_report_key="marketer_report_phase1",
            summary_output_key="marketer_report_phase1_summary"
        )
        
        # 비판적 분석가 중간 요약 에이전트
        critic_summary_agent = self.create_intermediate_summarizer_agent(
            original_report_key="critic_report_phase1",
            summary_output_key="critic_report_phase1_summary"
        )
        
        # 현실적 엔지니어 중간 요약 에이전트
        engineer_summary_agent = self.create_intermediate_summarizer_agent(
            original_report_key="engineer_report_phase1",
            summary_output_key="engineer_report_phase1_summary"
        )
        
        # 페르소나와 각각의 중간 요약 에이전트를 명확한 순서로 배치
        # 명시적으로 순서를 지정하여 예측 가능한 워크플로우 생성
        interleaved_agents = []
        
        # PERSONA_SEQUENCE 순서에 따라 페르소나와 해당 요약 에이전트를 순차적으로 추가
        for persona_type in PERSONA_SEQUENCE:
            if persona_type == PersonaType.MARKETER:
                # 먼저 마케터 페르소나 에이전트 추가
                interleaved_agents.append(marketer_agent)
                print(f"Added marketer_agent to workflow at position {len(interleaved_agents)}")
                # 그 다음 마케터 요약 에이전트 추가
                interleaved_agents.append(marketer_summary_agent)
                print(f"Added marketer_summary_agent to workflow at position {len(interleaved_agents)}")
            elif persona_type == PersonaType.CRITIC:
                # 먼저 비평가 페르소나 에이전트 추가
                interleaved_agents.append(critic_agent)
                print(f"Added critic_agent to workflow at position {len(interleaved_agents)}")
                # 그 다음 비평가 요약 에이전트 추가
                interleaved_agents.append(critic_summary_agent)
                print(f"Added critic_summary_agent to workflow at position {len(interleaved_agents)}")
            elif persona_type == PersonaType.ENGINEER:
                # 먼저 엔지니어 페르소나 에이전트 추가
                interleaved_agents.append(engineer_agent)
                print(f"Added engineer_agent to workflow at position {len(interleaved_agents)}")
                # 그 다음 엔지니어 요약 에이전트 추가
                interleaved_agents.append(engineer_summary_agent)
                print(f"Added engineer_summary_agent to workflow at position {len(interleaved_agents)}")
        
        # 워크플로우 에이전트 구성 로깅
        print(f"Total agents in interleaved workflow: {len(interleaved_agents)}")
        for i, agent in enumerate(interleaved_agents):
            print(f"Workflow position {i+1}: {agent.name} with output_key: {agent.output_key}")
        
        # 최종 요약 에이전트 (1단계용)
        # 각 페르소나 에이전트의 output_key와 중간 요약 output_key를 모두 참조하는 수정된 프롬프트
        summary_prompt = FINAL_SUMMARY_PROMPT.replace("{state.marketer_response}", "{state.marketer_report_phase1}")
        summary_prompt = summary_prompt.replace("{state.critic_response}", "{state.critic_report_phase1}")
        summary_prompt = summary_prompt.replace("{state.engineer_response}", "{state.engineer_report_phase1}")
        
        # 추가로 중간 요약 출력도 참조할 수 있도록 프롬프트 수정
        summary_prompt += """
        
        각 페르소나의 보고서 요약:
        
        [마케터 요약]
        {state.marketer_report_phase1_summary}
        
        [비판적 분석가 요약]
        {state.critic_report_phase1_summary}
        
        [현실적 엔지니어 요약]
        {state.engineer_report_phase1_summary}
        """
        
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
        
        # 1단계 전용 워크플로우 에이전트 생성 - 중간 요약 에이전트를 포함하도록 수정
        phase1_workflow_agent = SequentialAgent(
            name="aidea_lab_phase1_workflow",
            description="AIdea Lab 1단계 워크숍 시퀀스",
            sub_agents=[*interleaved_agents, summary_agent_phase1]  # 페르소나와 중간요약이 번갈아가며 실행되는 에이전트 목록 사용
        )
        
        # 디버깅 로그 출력
        print(f"Created phase1 agents - Marketer output_key: {marketer_agent.output_key}")
        print(f"Created phase1 agents - Critic output_key: {critic_agent.output_key}")
        print(f"Created phase1 agents - Engineer output_key: {engineer_agent.output_key}")
        print(f"Created phase1 agents - Summary output_key: {summary_agent_phase1.output_key}")
        print(f"Final workflow configuration: {len(phase1_workflow_agent.sub_agents)} agents in sequence")
        print(f"Expected output keys: {self.get_output_keys_phase1().values()}")
        
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
            "marketer_summary": "marketer_report_phase1_summary",  # 중간 요약 키 추가
            "critic": "critic_report_phase1",
            "critic_summary": "critic_report_phase1_summary",  # 중간 요약 키 추가
            "engineer": "engineer_report_phase1",
            "engineer_summary": "engineer_report_phase1_summary",  # 중간 요약 키 추가
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
            max_output_tokens=11000  # 충분한 요약 내용을 위한 토큰 수 증가
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