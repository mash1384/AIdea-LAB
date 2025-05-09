# test_single_critic.py (또는 src/poc/test_single_critic.py)

import os
import sys
import asyncio
from dotenv import load_dotenv
from google.adk.agents import Agent # LlmAgent로 변경해도 무방
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 프로젝트 루트 경로 추가 (파일 위치에 따라 경로 조정 필요)
# 만약 이 파일이 src/poc 안에 있다면:
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
# 만약 이 파일이 프로젝트 루트에 있다면:
# sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'src')))

# 필요한 모듈 임포트
from src.agents.critic_agent import CriticPersonaAgent
from config.models import DEFAULT_MODEL # 기본 모델 가져오기

# .env 파일 로드
load_dotenv()

# --- 테스트 설정 ---
APP_NAME = "SingleCriticTest"
USER_ID = "test_user_critic"
SESSION_ID = "test_session_critic"
TEST_IDEA = "반려동물과 대화할 수 있는 인공지능 목걸이"
# 사용할 모델 (기본 모델 또는 특정 모델 지정)
TEST_MODEL = DEFAULT_MODEL.value # 또는 "gemini-1.5-flash-latest" 등

async def run_single_agent_test():
    """단일 비판가 에이전트를 테스트하는 비동기 함수"""
    print(f"--- 단일 비판가 에이전트 테스트 시작 (모델: {TEST_MODEL}) ---")

    # API 키 확인
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY":
        print("⚠️ 에러: GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일을 확인하세요.")
        return

    # 세션 서비스 및 세션 생성
    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name=APP_NAME,
        user_id=USER_ID,
        session_id=SESSION_ID
    )

    # 초기 세션 상태 설정 (비판가 프롬프트가 참조할 값)
    session.state["initial_idea"] = TEST_IDEA
    # 비판가는 이전 페르소나 응답도 참조할 수 있으므로, 테스트를 위해 임의의 값을 넣어줄 수 있음
    # session.state["marketer_response"] = "시장 잠재력이 매우 높습니다! (테스트용 마케터 응답)"
    print(f"초기 세션 상태 설정: {session.state}")

    try:
        # 비판가 에이전트 인스턴스 생성 (테스트 모델 사용)
        critic_persona = CriticPersonaAgent(model_name=TEST_MODEL)
        adk_agent_to_run = critic_persona.get_agent()
        output_key = critic_persona.get_output_key() # 출력 키 가져오기

        print(f"\n에이전트 '{adk_agent_to_run.name}' 실행 준비 완료.")
        print(f"사용될 프롬프트 (instruction):\n---\n{adk_agent_to_run.instruction[:300]}...\n---") # 프롬프트 일부 확인

        # Runner 생성
        runner = Runner(
            agent=adk_agent_to_run,
            app_name=APP_NAME,
            session_service=session_service
        )

        # 에이전트 실행을 위한 입력 메시지 (간단한 트리거 역할)
        # 실제로는 instruction 내의 {state...} 참조가 중요
        trigger_message = types.Content(
            role="user",
            parts=[types.Part(text=f"아이디어 '{TEST_IDEA}'에 대한 비판적 분석을 시작해주세요.")]
        )

        print(f"\n📝 테스트 아이디어: '{TEST_IDEA}'")
        print("\n⏳ LLM에 요청 중...")

        # Runner를 통해 에이전트 실행
        events = runner.run(
            user_id=USER_ID,
            session_id=SESSION_ID,
            new_message=trigger_message
        )

        # 응답 처리
        response_text = None
        print("\n--- 실행 이벤트 로그 ---")
        for event in events:
            print(f"Event Type: {type(event)}, Is Final: {event.is_final_response()}")
            if event.is_final_response():
                 print(f"  Final Event Content: {event.content}")
                 if event.content and event.content.parts:
                     response_text = event.content.parts[0].text
                     print(f"  Extracted Text: {response_text}")
                 else:
                     print("  Final event has no content or parts.")
                 # break # 마지막 응답이어도 다른 이벤트가 있을 수 있으므로 break 제거하고 모두 출력

        print("--- 이벤트 로그 끝 ---")

        # 최종 세션 상태 확인
        updated_session = session_service.get_session(
            app_name=APP_NAME,
            user_id=USER_ID,
            session_id=SESSION_ID
        )
        print("\n📝 최종 세션 상태:")
        print(updated_session.state)

        # 결과 확인
        final_response = updated_session.state.get(output_key)

        if final_response:
            print("\n✅ 에이전트 응답 성공:")
            print(f"🤖 응답 ({output_key}):\n{final_response}")
        else:
            print(f"\n❌ '{output_key}' 키에 응답이 저장되지 않았습니다.")
            if response_text:
                 print(f"(참고: 마지막 이벤트에서 추출된 텍스트는 '{response_text}' 였습니다.)")

    except Exception as e:
        print(f"\n❌ 테스트 중 오류 발생: {str(e)}")
        import traceback
        traceback.print_exc() # 상세 오류 스택 출력

if __name__ == "__main__":
    asyncio.run(run_single_agent_test()) # 비동기 함수 실행