"""
AIdea Lab의 기본 Google ADK LlmAgent 예제
Google ADK를 사용하여, API 키를 환경 변수에서 로드하고 Gemini를 사용하는 기본 에이전트 예제입니다.
"""

import os
import sys
from dotenv import load_dotenv
from google.adk.agents import Agent
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 프로젝트 루트 디렉토리를 sys.path에 추가
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))
from config.personas import SELECTED_MODEL

# .env 파일에서 환경 변수 로드
load_dotenv()

# 기본 에이전트 정의
basic_agent = Agent(
    name="basic_hello_agent",
    model=SELECTED_MODEL,  # 선택된 제미니 모델 사용
    description="A simple agent that responds to basic greetings and questions.",
    instruction="You are a helpful assistant that provides concise responses to user queries.",
)

# 메인 실행 코드
def main():
    print("🤖 AIdea Lab Basic ADK Agent Test")
    print("환경 변수에서 API 키를 로드하여 Google ADK와 Gemini 모델을 연결합니다.")
    print("간단한 프롬프트로 LLM 기본 응답을 테스트합니다.")
    print(f"사용 중인 모델: {SELECTED_MODEL}")
    
    # 환경 변수 확인
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key or api_key == "YOUR_API_KEY":
        print("⚠️ 에러: GOOGLE_API_KEY가 설정되지 않았습니다. .env 파일에 API 키를 설정해주세요.")
        return

    # 세션 서비스 및 런너 설정
    app_name = "AIdea Lab Test"
    user_id = "test_user"
    session_id = "test_session"
    
    session_service = InMemorySessionService()
    session = session_service.create_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    
    # Runner 생성
    runner = Runner(
        agent=basic_agent,
        app_name=app_name,
        session_service=session_service
    )

    # 테스트 프롬프트
    test_prompt = "안녕하세요, 당신은 누구인가요?"

    try:
        print(f"\n📝 테스트 프롬프트: '{test_prompt}'")
        print("\n⏳ LLM에 요청 중...")
        
        # Content 객체 생성
        content = types.Content(
            role="user",
            parts=[types.Part(text=test_prompt)]
        )
        
        # Runner를 통해 에이전트 실행
        events = runner.run(
            user_id=user_id,
            session_id=session_id, 
            new_message=content
        )
        
        # 응답 처리
        response_text = None
        for event in events:
            if event.is_final_response() and event.content and event.content.parts:
                response_text = event.content.parts[0].text
                break
        
        if response_text:
            print("\n✅ LLM 응답 성공:")
            print(f"🤖 응답: {response_text}")
        else:
            print("\n❌ 응답을 받지 못했습니다.")
        
    except Exception as e:
        print(f"\n❌ 오류 발생: {str(e)}")
        print("API 키가 올바른지, 네트워크 연결이 정상인지 확인해주세요.")

if __name__ == "__main__":
    main() 