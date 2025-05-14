"""
토론 퍼실리테이터 에이전트

이 모듈은 아이디어 토론을 촉진하고 조율하는 토론 퍼실리테이터 에이전트를 구현합니다.
퍼실리테이터는 다음 토론 참여자를 지정하고 토론 주제를 제시하는 역할을 담당합니다.
"""

import os
from google.adk.agents import Agent
from google.genai import types  # types 모듈 임포트 추가
from config.models import DEFAULT_MODEL

class DiscussionFacilitatorAgent:
    """토론 퍼실리테이터 에이전트 클래스
    
    이 클래스는 페르소나들 간의 토론을 조율하고 다음 발언자를 지정하는
    퍼실리테이터 역할을 수행합니다. 출력은 JSON 형식으로 다음 에이전트 및
    메시지를 포함합니다.
    """
    
    def __init__(self, model_name=None, instruction_provider=None):
        """
        에이전트 초기화
        
        Args:
            model_name (str, optional): 사용할 모델 이름. 기본값은 DEFAULT_MODEL.value
            instruction_provider (callable, optional): 동적 프롬프트 생성 함수
        """
        # 기본 모델 설정
        model_name = model_name or DEFAULT_MODEL.value
        
        # 온도 및 출력 토큰 설정
        generate_config = types.GenerationConfig(
            temperature=0.7,  # 다양한 방향의 토론 진행을 위해 약간 더 높은 온도 사용
            max_output_tokens=4096  # 충분한 토론 진행을 위한 토큰 수
        )

        # 에이전트 생성
        self.agent = Agent(
            name="facilitator_agent",  # 영문자와 언더스코어만 사용
            model=model_name,
            description="토론 촉진 및 조율을 담당하는 퍼실리테이터 에이전트",
            instruction=instruction_provider,  # 동적 프롬프트 생성 함수
            output_key="facilitator_response",  # session.state에 저장될 키
            generate_content_config=generate_config  # 생성 설정 명시적으로 전달
        )
    
    def get_agent(self):
        """Agent 객체 반환"""
        return self.agent
    
    def get_output_key(self):
        """에이전트 응답이 저장될 키 반환"""
        return "facilitator_response" 