"""
AIdea Lab 제미니 모델 설정
사용 가능한 제미니 모델과 기본 모델을 정의합니다.
"""

from enum import Enum

# 모델 유형 정의
class ModelType(Enum):
    GEMINI_2_5_FLASH_PREVIEW_0417 = "gemini-2.5-flash-preview-04-17"
    GEMINI_2_5_PRO_PREVIEW_0506 = "gemini-2.5-pro-preview-05-06"

# 모델 정보 설정
MODEL_CONFIGS = {
    ModelType.GEMINI_2_5_FLASH_PREVIEW_0417: {
        "name": "Gemini 2.5 Flash Preview 04-17",
        "description": "제미니 2.5 플래시 Preview 04-17 버전 - 개선된 성능의 빠른 응답 모델",
        "display_name": "제미니 2.5 플래시 Preview 04-17",
    },
    ModelType.GEMINI_2_5_PRO_PREVIEW_0506: {
        "name": "Gemini 2.5 Pro Preview 05-06",
        "description": "제미니 2.5 프로 Preview 05-06 버전 - 최신 기능이 적용된 모델",
        "display_name": "제미니 2.5 프로 Preview 05-06",
    }
}

# 기본 모델 설정
DEFAULT_MODEL = ModelType.GEMINI_2_5_FLASH_PREVIEW_0417

# 모델 목록을 표시 이름과 함께 반환하는 함수
def get_model_display_options():
    """
    모델 선택 드롭다운용 표시 옵션을 반환합니다.
    
    Returns:
        dict: 키는 표시 이름, 값은 모델 ID
    """
    options = {}
    for model_type in ModelType:
        options[MODEL_CONFIGS[model_type]["display_name"]] = model_type.value
    return options 