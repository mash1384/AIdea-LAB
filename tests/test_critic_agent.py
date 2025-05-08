"""
비판적 분석가 페르소나 에이전트 테스트
"""

import pytest
from src.agents.critic_agent import CriticPersonaAgent
from config.personas import PersonaType, PERSONA_CONFIGS
from config.prompts import CRITIC_PROMPT

def test_critic_agent_initialization():
    """비판적 분석가 에이전트 초기화 테스트"""
    # 에이전트 인스턴스 생성
    critic_agent = CriticPersonaAgent()
    
    # Agent 객체 가져오기
    agent = critic_agent.get_agent()
    
    # 페르소나 설정 가져오기
    persona_config = PERSONA_CONFIGS[PersonaType.CRITIC]
    
    # 기본 설정 검증
    assert agent.name == "critic_agent"  # 이름이 API 요구사항에 맞는지 확인
    assert agent.description == persona_config["description"]
    assert agent.instruction == CRITIC_PROMPT
    assert agent.output_key == persona_config["output_key"]
    
    # generate_content_config 설정 검증
    assert "temperature" in agent.generate_content_config
    assert agent.generate_content_config["temperature"] == persona_config["temperature"]
    assert "max_output_tokens" in agent.generate_content_config
    assert agent.generate_content_config["max_output_tokens"] == persona_config["max_output_tokens"]

def test_critic_agent_output_key():
    """출력 키 반환 메서드 테스트"""
    critic_agent = CriticPersonaAgent()
    expected_key = PERSONA_CONFIGS[PersonaType.CRITIC]["output_key"]
    
    assert critic_agent.get_output_key() == expected_key
    
if __name__ == "__main__":
    pytest.main(["-v", __file__]) 