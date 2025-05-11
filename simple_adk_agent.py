"""
AIdea Lab의 기본 Google ADK LlmAgent 예제 (테스트용으로 간소화)
Google ADK를 사용하여, API 키를 환경 변수에서 로드하고 Gemini를 사용하는 기본 에이전트 예제입니다.
LLM 호출 및 응답 수신, session.state 저장 기능을 테스트합니다.
(instruction에서 state 참조 제거, 로깅 추가, run_async 및 이벤트 로깅 사용)
"""

import os
import sys
import logging # 로깅 모듈 임포트
import asyncio # asyncio 임포트
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService, Session
from google.genai import types as genai_types

# --- 로깅 설정 ---
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(name)s - %(message)s')
# logging.getLogger('google.api_core').setLevel(logging.INFO) # 너무 많은 로그가 나올 수 있으니 주의

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

try:
    from config.models import DEFAULT_MODEL
    if hasattr(DEFAULT_MODEL, 'value'):
        DEFAULT_MODEL_VALUE = DEFAULT_MODEL.value
    else:
        DEFAULT_MODEL_VALUE = str(DEFAULT_MODEL)
    logging.info(f"config.models에서 DEFAULT_MODEL 로드 성공: {DEFAULT_MODEL_VALUE}")
except ImportError:
    logging.warning("WARNING: config.models 모듈을 찾을 수 없습니다. 기본 모델로 'gemini-1.5-flash-latest'를 사용합니다.")
    DEFAULT_MODEL_VALUE = "gemini-1.5-flash-latest" # 또는 테스트하려는 특정 모델

load_dotenv()
logging.info(".env 파일 로드 시도 완료.")

APP_NAME = "SimpleADKTestAsync" # 앱 이름 변경하여 이전 테스트와 구분
USER_ID = "test_user_simple_async"
SESSION_ID = "test_session_simple_async"
TEST_INITIAL_IDEA = "간단한 날씨 알림 앱 (이 값은 프롬프트에 직접 사용되지 않음)"

# Agent 정의: instruction에서 state 참조 제거
simple_test_agent = Agent(
    name="simple_test_agent_fixed_prompt_async",
    model=DEFAULT_MODEL_VALUE, # 이전 테스트에서 성공한 모델 사용 권장 (예: gemini-2.0-flash)
    description="Agent with a fixed prompt, using run_async.",
    instruction="Hello! 영어로 간단한 인사말을 생성해주세요. (상태 참조 없음)",
    output_key="simple_agent_response_fixed_async"
)
logging.info(f"Agent '{simple_test_agent.name}' 생성 완료. Model: {simple_test_agent.model}, Instruction: '{simple_test_agent.instruction}', Output Key: '{simple_test_agent.output_key}'")

async def main_async(): # 함수를 async로 정의
    logging.info("🤖 Simple ADK Agent Test (async)")
    logging.info(f"사용 중인 모델: {DEFAULT_MODEL_VALUE}")
    logging.info(f"테스트용 초기 아이디어 (세션에는 저장되나 프롬프트에는 미사용): '{TEST_INITIAL_IDEA}'")

    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "YOUR_ACTUAL_API_KEY" or api_key == "YOUR_API_KEY":
        logging.error("⚠️ 에러: GOOGLE_API_KEY가 .env 파일에 올바르게 설정되지 않았습니다.")
        return
    logging.info(f"GOOGLE_API_KEY 로드됨 (일부만 표시): {api_key[:5]}...{api_key[-5:]}")

    session_service = InMemorySessionService()
    logging.debug("InMemorySessionService 인스턴스 생성 완료.")
    initial_session_state = {"initial_idea": TEST_INITIAL_IDEA, "other_test_value": "이 값은 참조되지 않음"}

    try:
        logging.debug(f"세션 생성 시도: app_name='{APP_NAME}', user_id='{USER_ID}', session_id='{SESSION_ID}', state={initial_session_state}")
        session = session_service.create_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID,
            state=initial_session_state
        )
        if not session:
            logging.error("❌ 세션 생성에 실패했습니다 (session_service.create_session 반환값이 None).")
            return
        logging.info(f"✅ 세션이 성공적으로 생성되었습니다. ID: {session.id}")
        logging.info(f"   세션 생성 시 전달된 초기 상태: {initial_session_state}")

        retrieved_session_after_create = session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )
        if retrieved_session_after_create:
            logging.info(f"   서비스에서 가져온 세션의 초기 상태: {retrieved_session_after_create.state}")
        else:
            logging.warning("   ❌ 경고: 세션 생성 후 서비스에서 세션을 다시 가져오지 못했습니다.")

    except Exception as e:
        logging.error(f"❌ 세션 생성 또는 조회 중 오류 발생: {e}", exc_info=True)
        return

    runner = Runner(
        agent=simple_test_agent,
        app_name=APP_NAME,
        session_service=session_service
    )
    logging.info(f"Runner 생성 완료. Agent: {simple_test_agent.name}")

    user_input_text = "안녕, 오늘 날씨 어때? (이 입력은 에이전트 프롬프트에 직접 사용되지 않음)"

    try:
        logging.info(f"\n📝 사용자 입력 (new_message로 전달): '{user_input_text}'")
        logging.info("\n⏳ LLM에 요청 중 (Runner.run_async 실행)...")

        content_to_send = genai_types.Content(
            role="user",
            parts=[genai_types.Part(text=user_input_text)]
        )
        logging.debug(f"Runner.run_async() 호출 예정. user_id='{USER_ID}', session_id='{SESSION_ID}', new_message='{content_to_send}'")

        event_stream = runner.run_async( # run_async 사용
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=content_to_send
        )

        logging.info("\n🔄 이벤트 스트림 처리 시작:")
        final_event_content = None
        async for event in event_stream: # 이벤트 반복 처리
            logging.info(f"  - Event Received: Type={type(event).__name__}, Details={event}")
            # 이벤트 객체의 구체적인 속성은 ADK 버전에 따라 다를 수 있으므로, dir(event)나 vars(event)로 확인 가능
            # logging.debug(f"    Event dir: {dir(event)}")
            # logging.debug(f"    Event vars: {vars(event)}")

            if hasattr(event, 'agent_name'):
                logging.info(f"    Event Agent Name: {event.agent_name}")
            if hasattr(event, 'is_final_response') and event.is_final_response():
                logging.info(f"    Event Is Final Response: True")
                if hasattr(event, 'content') and event.content:
                    logging.info(f"    Event Final Content: {event.content}")
                    if event.content.parts:
                         final_event_content = event.content.parts[0].text # 마지막 최종 응답 텍스트 저장 시도
                else:
                    logging.info("    Event Final Content: 없음")
            # output_key에 저장되는 시점의 이벤트를 찾기 위한 추가적인 로깅 (ADK 내부 구조에 따라 다름)
            if hasattr(event, 'type') and 'state_update' in str(event.type).lower(): # 가상의 이벤트 타입
                logging.info(f"    State Update Event Detected: {event}")


        logging.info("\n✅ Runner.run_async() 및 이벤트 스트림 처리 완료.")
        if final_event_content:
            logging.info(f"   이벤트 스트림에서 마지막으로 확인된 최종 응답 텍스트: {final_event_content}")


        updated_session = session_service.get_session(
            app_name=APP_NAME, user_id=USER_ID, session_id=SESSION_ID
        )

        if updated_session:
            logging.info("\n📝 최종 세션 상태 (async 후):")
            for key, value in updated_session.state.items():
                logging.info(f"  - {key}: {value}")

            agent_response = updated_session.state.get(simple_test_agent.output_key)
            if agent_response:
                logging.info(f"\n🤖 에이전트 응답 ({simple_test_agent.output_key}):")
                print(f"LLM 응답: {agent_response}") # 실제 응답은 print로 명확히 보이도록
            else:
                logging.error(f"\n❌ '{simple_test_agent.output_key}' 키에 에이전트 응답이 저장되지 않았습니다. (async)")
                logging.error("   LLM 호출에 실패했거나, 응답이 비어있거나, output_key 저장 로직에 문제가 있을 수 있습니다.")
                if final_event_content:
                    logging.warning(f"   참고: 이벤트 스트림에서는 '{final_event_content}' 텍스트가 확인되었으나, output_key에는 저장되지 않았습니다.")
        else:
            logging.error("\n❌ 최종 세션 상태를 가져오지 못했습니다. (async)")


    except Exception as e:
        logging.error(f"\n❌ 에이전트 실행 중 오류 발생 (async): {e}", exc_info=True)
        logging.error("   API 키, 할당량, 모델 이름, 네트워크 연결 등을 확인해주세요.")

if __name__ == "__main__":
    # Python 3.7+ 에서는 asyncio.run()을 직접 사용
    asyncio.run(main_async())