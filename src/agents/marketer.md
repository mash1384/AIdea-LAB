<!--
# 문서 참고용 파일

이 파일은 실제 실행 코드가 아닌 문서 참고용 파일입니다.
실제 구현은 marketer_agent.py 파일을 참조하세요.
아래 코드는 참고용으로만 제공되며 실행되지 않습니다.
-->

"""
창의적 마케터 페르소나 에이전트

이 모듈은 아이디어의 창의적 가치와 시장 잠재력을 최대화하는
창의적 마케터 페르소나 에이전트를 구현합니다.
"""

import os
from dotenv import load_dotenv
from google.adk.agents import Agent
from config.prompts import MARKETER_PROMPT
from config.personas import PersonaType, PERSONA_CONFIGS
from config.models import DEFAULT_MODEL


# .env 파일에서 환경 변수 로드
load_dotenv()

class MarketerPersonaAgent:
    """창의적 마케터 페르소나 에이전트 클래스"""
    
    def __init__(self, model_name=None):
        """
        에이전트 초기화
        
        Args:
            model_name (str, optional): 사용할 모델 이름. 기본값은 DEFAULT_MODEL.value
        """
        # 기본 모델 설정
        model_name = model_name or DEFAULT_MODEL.value
        
        # 페르소나 설정 가져오기
        persona_config = PERSONA_CONFIGS[PersonaType.MARKETER]
        
        # 생성 내용 설정 구성
        # temperature와 max_output_tokens는 generate_content_config에 설정
        generate_config = {
            "temperature": persona_config["temperature"],
            "max_output_tokens": persona_config["max_output_tokens"]
        }
        
        # 에이전트 생성
        self.agent = Agent(
            name="marketer_agent",  # 영문자와 언더스코어만 사용
            model=model_name,  # 파라미터로 전달받은 모델 사용
            description=persona_config["description"],
            instruction=MARKETER_PROMPT,  # 창의적 마케터 시스템 프롬프트
            output_key=persona_config["output_key"],  # session.state에 저장될 키
            generate_content_config=generate_config  # 생성 설정
        )
    
    def get_agent(self):
        """Agent 객체 반환"""
        return self.agent
    
    def get_output_key(self):
        """에이전트 응답이 저장될 키 반환"""
        return PERSONA_CONFIGS[PersonaType.MARKETER]["output_key"] 