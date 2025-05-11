import os
import google.generativeai as genai
from dotenv import load_dotenv
import logging # 로깅 추가

# 로깅 기본 설정
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')

# .env 파일에서 환경 변수 로드
load_dotenv()
logging.info(".env 파일 로드 시도 완료.")

# 테스트에 사용할 모델
# 이전 테스트에서 gemini-2.0-flash가 성공했으므로 해당 모델 사용
TEST_MODEL_NAME = "gemini-2.0-flash"

def check_google_api_key():
    """
    GOOGLE_API_KEY를 사용하여 Gemini API에 간단한 요청을 보내 유효성을 검사하고,
    응답의 finish_reason 및 safety_ratings를 출력합니다.
    """
    logging.info("🔍 Google API 키 유효성 검사를 시작합니다...")

    api_key = os.getenv("GOOGLE_API_KEY")

    if not api_key or api_key == "YOUR_ACTUAL_API_KEY" or api_key == "YOUR_API_KEY":
        logging.error("❌ 오류: GOOGLE_API_KEY가 .env 파일에 설정되지 않았거나 유효하지 않은 값입니다.")
        logging.error("   '.env' 파일을 프로젝트 루트에 만들고 GOOGLE_API_KEY=\"실제API키\" 형식으로 입력해주세요.")
        return

    logging.info(f"🔑 API 키 로드됨 (일부만 표시): {api_key[:5]}...{api_key[-5:]}")

    try:
        # API 키 설정
        genai.configure(api_key=api_key)
        logging.info(f"✅ genai.configure(api_key=...) 성공.")

        # 사용 가능한 모델 목록 가져오기 (디버깅 시 주석 해제)
        # logging.info("\n🔄 사용 가능한 모델 목록을 가져오는 중...")
        # model_count = 0
        # models_found = []
        # for m in genai.list_models():
        #     if 'generateContent' in m.supported_generation_methods:
        #         logging.debug(f"  - 모델명: {m.name}, 지원 메서드: {m.supported_generation_methods}")
        #         models_found.append(m.name)
        #         model_count +=1
        # if model_count > 0:
        #     logging.info(f"✅ {model_count}개의 사용 가능한 (generateContent 지원) 모델 정보를 성공적으로 가져왔습니다.")
        #     logging.info(f"   사용 가능한 모델들: {models_found}")
        # else:
        #     logging.warning("⚠️ 사용 가능한 (generateContent 지원) 모델 정보를 가져오지 못했습니다.")


        # 테스트 모델 객체 생성
        logging.info(f"\n🔄 테스트 모델 '{TEST_MODEL_NAME}' 객체를 생성하는 중...")
        model = genai.GenerativeModel(TEST_MODEL_NAME)
        logging.info(f"✅ 모델 '{TEST_MODEL_NAME}' 객체 생성 성공.")

        # 간단한 텍스트 생성 요청 보내기
        prompt = "Hello! 영어로 매우 간단한 인사말 하나만 생성해주세요." # 프롬프트 간소화
        logging.info(f"\n📝 프롬프트: \"{prompt}\"")
        logging.info("⏳ LLM에 요청 중...")

        # 응답 생성
        response = model.generate_content(prompt)
        logging.info("✅ LLM 응답 수신 성공.")

        # 응답 텍스트 및 상세 정보 출력
        if response.text:
            print("\n🤖 LLM 응답 내용:") # print로 사용자에게 명확히 보여주기
            print(response.text)
            logging.info(f"   응답 텍스트: {response.text}") # 로그에도 남기기

            if response.candidates:
                candidate = response.candidates[0]
                logging.info(f"   Finish Reason: {candidate.finish_reason}")
                # safety_ratings는 없을 수도 있으므로 확인 후 출력
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    logging.info(f"   Safety Ratings: {candidate.safety_ratings}")
                else:
                    logging.info("   Safety Ratings: 정보 없음 또는 해당 없음")
            else:
                logging.warning("   응답에 candidates 정보가 없습니다.")

            print("\n🎉 API 키가 유효하고, LLM 호출이 성공적으로 완료되었습니다!") # print로 사용자에게 명확히 보여주기
            logging.info("🎉 API 키가 유효하고, LLM 호출이 성공적으로 완료되었습니다!")

        else:
            logging.error("\n❌ LLM으로부터 응답을 받았으나, 응답 내용(text)이 비어있습니다.")
            logging.error("   모델이 해당 프롬프트에 대해 응답을 생성하지 못했거나, 안전 필터 등에 의해 차단되었을 수 있습니다.")
            if hasattr(response, 'prompt_feedback') and response.prompt_feedback:
                logging.error(f"   프롬프트 피드백: {response.prompt_feedback}")
            if response.candidates:
                candidate = response.candidates[0]
                logging.error(f"   종료 이유 (text 없음): {candidate.finish_reason}")
                if hasattr(candidate, 'safety_ratings') and candidate.safety_ratings:
                    logging.error(f"   안전 등급 (text 없음): {candidate.safety_ratings}")
            else:
                logging.warning("   응답에 candidates 정보가 없습니다 (text 없음).")


    except Exception as e:
        logging.error(f"\n❌ API 키 유효성 검사 또는 LLM 호출 중 오류 발생: {type(e).__name__}", exc_info=True)
        logging.error("   API 키, Google Cloud 프로젝트 설정(API 활성화, 결제), 네트워크 연결, 모델 이름을 확인해주세요.")

if __name__ == "__main__":
    check_google_api_key()