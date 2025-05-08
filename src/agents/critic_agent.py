"""
비판적 분석가 페르소나 에이전트

이 모듈은 아이디어의 잠재적 문제점, 리스크, 논리적 허점을 분석하는 
비판적 분석가 페르소나 에이전트를 구현합니다.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from config.prompts import CRITIC_PROMPT
from config.personas import PersonaType, PERSONA_CONFIGS

# .env 파일에서 환경 변수 로드
load_dotenv()

class CriticPersonaAgent:
    """비판적 분석가 페르소나 에이전트 클래스"""
    
    def __init__(self):
        """에이전트 초기화"""
        # 페르소나 설정 가져오기
        persona_config = PERSONA_CONFIGS[PersonaType.CRITIC]
        
        # 생성 내용 설정 구성
        # temperature와 max_output_tokens는 generate_content_config에 설정
        generate_config = {
            "temperature": persona_config["temperature"],
            "max_output_tokens": persona_config["max_output_tokens"]
        }
        
        # 에이전트 생성
        self.agent = Agent(
            name="critic_agent",  # 영문자와 언더스코어만 사용
            model="gemini-2.0-flash",  # Gemini 모델 사용
            description=persona_config["description"],
            instruction=CRITIC_PROMPT,  # 비판적 분석가 시스템 프롬프트
            output_key=persona_config["output_key"],  # session.state에 저장될 키
            generate_content_config=generate_config  # 생성 설정
        )
    
    def get_agent(self):
        """Agent 객체 반환"""
        return self.agent
    
    def get_output_key(self):
        """에이전트 응답이 저장될 키 반환"""
        return PERSONA_CONFIGS[PersonaType.CRITIC]["output_key"] 