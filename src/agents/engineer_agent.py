"""
현실적 엔지니어 페르소나 에이전트

이 모듈은 아이디어의 기술적 실현 가능성을 검토하는
현실적 엔지니어 페르소나 에이전트를 구현합니다.
"""

import os
from google.adk.agents import Agent
from google.genai import types  # types 모듈 임포트 추가
from config.prompts import ENGINEER_PROMPT
from config.personas import PersonaType, PERSONA_CONFIGS
from config.models import DEFAULT_MODEL


# .env 파일은 애플리케이션의 메인 진입점(app.py)에서 로드됨

class EngineerPersonaAgent:
    """현실적 엔지니어 페르소나 에이전트 클래스"""
    
    def __init__(self, model_name=None):
        """
        에이전트 초기화
        
        Args:
            model_name (str, optional): 사용할 모델 이름. 기본값은 DEFAULT_MODEL.value
        """
        # 기본 모델 설정
        model_name = model_name or DEFAULT_MODEL.value
        
        # 페르소나 설정 가져오기
        persona_config = PERSONA_CONFIGS[PersonaType.ENGINEER]
        
        # GenerationConfig 객체 명시적 생성
        generate_config = types.GenerationConfig(
            temperature=persona_config["temperature"],
            max_output_tokens=persona_config["max_output_tokens"]
        )
        
        # 에이전트 생성
        self.agent = Agent(
            name="engineer_agent",  # 영문자와 언더스코어만 사용
            model=model_name,  # 파라미터로 전달받은 모델 사용
            description=persona_config["description"],
            instruction=ENGINEER_PROMPT,  # 현실적 엔지니어 시스템 프롬프트
            output_key=persona_config["output_key"],  # session.state에 저장될 키
            generate_content_config=generate_config  # 생성 설정 명시적으로 전달
        )
    
    def get_agent(self):
        """Agent 객체 반환"""
        return self.agent
    
    def get_output_key(self):
        """에이전트 응답이 저장될 키 반환"""
        return PERSONA_CONFIGS[PersonaType.ENGINEER]["output_key"] 