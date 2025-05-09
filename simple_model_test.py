# simple_model_test.py

import google.generativeai as genai
import os
from dotenv import load_dotenv
import traceback # 상세 오류 출력을 위해 추가

# --- 설정 부분 ---
# 1. 테스트할 "2.5 프로" 모델 ID를 정확하게 입력하세요.
#    (예: "gemini-2.5-pro-preview-05-06" 또는 config/models.py에 정의된 다른 2.5 프로 모델 ID)
MODEL_ID_TO_TEST = "gemini-2.5-pro-exp-03-25"  # <--- 여기에 테스트할 모델 ID 입력

# 2. (선택 사항) 테스트용 간단한 시스템 프롬프트
#    비워두거나 매우 간단하게 설정합니다.
SYSTEM_INSTRUCTION = "You are a helpful assistant."
# SYSTEM_INSTRUCTION = None # 시스템 프롬프트 없이 테스트하려면 이 줄의 주석을 해제하세요.

# 3. 테스트용 간단한 사용자 입력
USER_INPUT = '몰라요' # 이전 로그에서 문제가 발생했던 입력값 사용
# USER_INPUT = "Tell me a short joke about a cat." # 또는 다른 매우 간단한 입력으로 테스트

# 4. (선택 사항) 테스트용 간단한 생성 설정
#    기본값을 사용하거나, 문제가 의심되는 특정 설정을 테스트할 수 있습니다.
#    max_output_tokens는 응답 잘림 현상 확인을 위해 충분히 크게 설정하는 것이 좋습니다.
GENERATION_CONFIG = {
    "temperature": 0.7,
    "max_output_tokens": 2048, # 응답 잘림 방지를 위해 충분히 설정
    # "safety_settings": [...] # 필요한 경우 안전 설정 테스트 (이전 답변 참고)
}
# GENERATION_CONFIG = None # 기본 생성 설정을 사용하려면 이 줄의 주석을 해제하세요.
# --- 설정 부분 끝 ---

def run_direct_model_test():
    """
    지정된 모델 ID로 직접 API 호출을 수행하고 결과를 출력합니다.
    """
    print(f"--- 독립 테스트 스크립트 시작 ---")
    print(f"테스트 대상 모델 ID: {MODEL_ID_TO_TEST}")

    # .env 파일에서 API 키 로드 (스크립트와 같은 위치 또는 PYTHONPATH에 .env 파일이 있어야 함)
    load_dotenv()
    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key:
        print("🛑 중요: GOOGLE_API_KEY 환경 변수를 찾을 수 없습니다.")
        print("   .env 파일이 이 스크립트와 같은 위치에 있는지, 또는 환경 변수가 올바르게 설정되었는지 확인하세요.")
        return

    print(f"🔑 API 키 로드 확인 (앞 5자리): {api_key[:5]}...")
    genai.configure(api_key=api_key)

    try:
        print(f"\n🚀 모델 초기화 중: {MODEL_ID_TO_TEST}")
        model_args = {"model_name": MODEL_ID_TO_TEST}
        if SYSTEM_INSTRUCTION:
            model_args["system_instruction"] = SYSTEM_INSTRUCTION
        
        model = genai.GenerativeModel(**model_args)

        print(f"💬 사용자 입력: '{USER_INPUT}'")
        
        request_args = {}
        if GENERATION_CONFIG:
            print(f"⚙️ 생성 설정: {GENERATION_CONFIG}")
            # google-generativeai 0.5.0 이상 버전에서는 GenerationConfig 객체 직접 전달
            try:
                # types 모듈은 google.generativeai.types 로 접근 가능
                # 하지만 보통 GenerationConfig는 genai.types.GenerationConfig 로 직접 참조 가능
                # 또는 google.generativeai.types.GenerationConfig 로도 가능
                request_args["generation_config"] = genai.types.GenerationConfig(**GENERATION_CONFIG)
            except AttributeError: # 이전 버전 호환성 (genai.types.GenerationConfig가 없을 경우)
                request_args["generation_config"] = GENERATION_CONFIG
                print("참고: genai.types.GenerationConfig 를 찾을 수 없어 dict로 전달합니다. 라이브러리 버전이 낮을 수 있습니다.")

        response = model.generate_content(
            USER_INPUT,
            **request_args
        )

        print("\n--- 응답 결과 ---")
        if response.text:
            print(f"✅ 응답 텍스트:\n{response.text}")
        else:
            print("⚠️ LLM이 빈 텍스트를 반환했습니다.")

        # 상세 응답 정보 출력 (디버깅에 매우 중요)
        print("\n--- 상세 응답 정보 ---")
        if response.candidates:
            for i, candidate in enumerate(response.candidates):
                print(f"  후보 {i+1}:")
                if hasattr(candidate, 'finish_reason'): # finish_reason이 항상 있는지 확인
                    print(f"    종료 이유 (Finish Reason): {candidate.finish_reason}")
                    # finish_reason이 enum일 경우 .name으로 접근, 문자열일 경우 그대로 사용
                    finish_reason_name = candidate.finish_reason.name if hasattr(candidate.finish_reason, 'name') else str(candidate.finish_reason)
                    if finish_reason_name == "MAX_TOKENS":
                        print("    🚨 경고: max_output_tokens 제한에 도달하여 응답이 잘렸을 수 있습니다.")
                    elif finish_reason_name == "SAFETY":
                        print("    🚨 경고: 안전 필터에 의해 응답 생성이 중단되었거나 수정되었습니다.")
                else:
                    print("    종료 이유 (Finish Reason) 정보 없음.")
                
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    print(f"    안전 등급 (Safety Ratings):")
                    for rating in candidate.safety_ratings:
                        print(f"      - 카테고리: {rating.category}, 확률: {rating.probability}")
                else:
                    print("    안전 등급 정보 없음.")
        else:
            print("  응답에 후보(candidates) 정보가 없습니다.")

        if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
            print(f"\n  프롬프트 피드백 (Prompt Feedback):")
            if hasattr(response.prompt_feedback, 'block_reason'):
                print(f"    차단 이유 (Block Reason): {response.prompt_feedback.block_reason}")
            if hasattr(response.prompt_feedback, 'block_reason_message') and response.prompt_feedback.block_reason_message:
                 print(f"    차단 이유 메시지: {response.prompt_feedback.block_reason_message}")
            if hasattr(response.prompt_feedback, 'safety_ratings') and response.prompt_feedback.safety_ratings:
                print(f"    안전 등급 (Safety Ratings):")
                for rating in response.prompt_feedback.safety_ratings:
                    print(f"      - 카테고리: {rating.category}, 확률: {rating.probability}")
        else:
            print("\n  프롬프트 피드백 정보 없음.")
        
        # print(f"\n(참고용 전체 응답 객체: {response})") # 필요시 주석 해제

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {type(e).__name__} - {e}")
        traceback.print_exc() # 상세 오류 스택 출력
    finally:
        print("\n--- 독립 테스트 스크립트 종료 ---")

if __name__ == "__main__":
    run_direct_model_test()