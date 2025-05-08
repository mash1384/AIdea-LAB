import pytest
from src.agents.critic_agent import CriticPersonaAgent
from config.personas import PersonaType, PERSONA_CONFIGS, SELECTED_MODEL
from config.prompts import CRITIC_PROMPT
from google.genai.types import GenerateContentConfig # GenerateContentConfig 타입을 확인하기 위해 필요할 수 있음

def test_critic_agent_initialization():
    """비판적 분석가 에이전트 초기화 테스트"""
    critic_agent = CriticPersonaAgent()
    agent = critic_agent.get_agent()
    persona_config = PERSONA_CONFIGS[PersonaType.CRITIC]

    assert agent.name == "critic_agent"
    assert agent.description == persona_config["description"]
    assert agent.instruction == CRITIC_PROMPT
    assert agent.output_key == persona_config["output_key"]
    assert agent.model == SELECTED_MODEL  # 선택된 모델 검증

    # generate_content_config 설정 검증
    assert isinstance(agent.generate_content_config, GenerateContentConfig) # 타입 확인
    assert hasattr(agent.generate_content_config, "temperature") # 속성 존재 여부 확인
    assert agent.generate_content_config.temperature == persona_config["temperature"]
    assert hasattr(agent.generate_content_config, "max_output_tokens") # 속성 존재 여부 확인
    assert agent.generate_content_config.max_output_tokens == persona_config["max_output_tokens"]

def test_critic_agent_output_key():
    """출력 키 반환 메서드 테스트"""
    critic_agent = CriticPersonaAgent()
    expected_key = PERSONA_CONFIGS[PersonaType.CRITIC]["output_key"]
    assert critic_agent.get_output_key() == expected_key

# if __name__ == "__main__": # 테스트 파일에서 이 부분은 일반적으로 제거합니다.
#     pytest.main(["-v", __file__])