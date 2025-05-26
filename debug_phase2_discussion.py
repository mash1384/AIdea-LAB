#!/usr/bin/env python3
"""
AIdea Lab 2차 토론 디버깅 스크립트

이 스크립트는 2차 토론에서 페르소나 에이전트들이 응답하지 않는 문제를 진단하기 위해 작성되었습니다.
"""

import os
import sys
import asyncio
from pathlib import Path

# 프로젝트 루트 디렉토리를 Python 경로에 추가
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# 환경 변수 설정
os.environ['PYTHONPATH'] = str(project_root)

# Google API 키 설정 (환경 변수에서)
if 'GOOGLE_API_KEY' not in os.environ:
    print("WARNING: GOOGLE_API_KEY environment variable not set")

# 의존성 임포트
try:
    from src.session_manager import SessionManager
    from src.orchestrator.main_orchestrator import AIdeaLabOrchestrator
    from src.ui.discussion_controller import DiscussionController
    from config.models import DEFAULT_MODEL
    print("✓ All imports successful")
except ImportError as e:
    print(f"❌ Import error: {e}")
    sys.exit(1)

async def debug_phase2_discussion():
    """
    2차 토론 디버깅 함수 - 실제 문제 재현 시도
    """
    print("=== 2차 토론 디버깅 시작 ===")
    
    try:
        # 1. 세션 매니저 초기화
        print("\n1. SessionManager 초기화 중...")
        session_manager = SessionManager(
            app_name="aidea-lab",
            user_id="debug-user"
        )
        print(f"✓ SessionManager 생성: {id(session_manager)}")
        
        # 2. 오케스트레이터 초기화 (model_name 파라미터 포함)
        print("\n2. Orchestrator 초기화 중...")
        orchestrator = AIdeaLabOrchestrator(model_name=DEFAULT_MODEL.value)
        print(f"✓ Orchestrator 생성: 모델={orchestrator.model_name}")
        
        # 3. 세션 생성
        print("\n3. 세션 생성 중...")
        session_id, session = session_manager.create_session(
            initial_idea="빈티지 인스타라방 - 희소성 있는 빈티지 아이템을 인스타그램 라이브로 판매하는 커머스 플랫폼"
        )
        print(f"✓ 세션 생성됨: session_id={session_id}")
        
        # 4. 1단계 분석 결과를 가짜로 채우기 (2차 토론을 위해 필요)
        print("\n4. 가짜 1단계 분석 결과 추가 중...")
        session.state.update({
            "marketer_report_phase1": "마케터 분석: 시장 잠재력 높음",
            "marketer_report_phase1_summary": "핵심: 높은 시장 잠재력",
            "critic_report_phase1": "비판적 분석: 운영상 난제 존재",
            "critic_report_phase1_summary": "핵심: 구조적 한계 분석",
            "engineer_report_phase1": "엔지니어 분석: 기술적 구현 가능",
            "engineer_report_phase1_summary": "핵심: 기술적 실현 가능성 중간",
            "summary_report_phase1": "종합: 아이디어는 매력적이나 실행 과제 존재",
            "discussion_history_phase2": []  # 빈 토론 히스토리로 시작
        })
        print("✓ 가짜 1단계 결과 추가 완료")
        
        # 5. DiscussionController 초기화
        print("\n5. DiscussionController 초기화 중...")
        discussion_controller = DiscussionController(session_manager)
        print(f"✓ DiscussionController 생성")
        
        # 6. 2차 토론 실행 (최대 3라운드로 제한하여 빠른 테스트)
        print("\n6. 2차 토론 실행 시작...")
        print("=" * 50)
        
        # discussion_controller의 max_discussion_rounds를 임시로 3으로 제한
        original_max_rounds = 15
        # 클래스 내 상수를 직접 수정하는 대신 메소드 호출 시 파라미터로 제한
        
        messages, status, user_question = await discussion_controller.run_phase2_discussion(
            session_id_string=session_id,
            orchestrator=orchestrator
        )
        
        print("=" * 50)
        print(f"\n7. 2차 토론 결과:")
        print(f"   - 상태: {status}")
        print(f"   - 메시지 수: {len(messages)}")
        print(f"   - 사용자 질문: {user_question}")
        
        # 8. 메시지 내용 분석
        print(f"\n8. 메시지 분석:")
        facilitator_count = 0
        persona_count = 0
        system_count = 0
        
        for i, msg in enumerate(messages):
            speaker = msg.get('speaker', 'unknown')
            content_preview = msg.get('content', '')[:50].replace('\n', ' ')
            
            print(f"   [{i+1}] {speaker}: {content_preview}...")
            
            if speaker == 'facilitator':
                facilitator_count += 1
            elif speaker in ['marketer_agent', 'critic_agent', 'engineer_agent']:
                persona_count += 1
            elif speaker == 'system':
                system_count += 1
        
        print(f"\n9. 통계:")
        print(f"   - 퍼실리테이터 메시지: {facilitator_count}")
        print(f"   - 페르소나 메시지: {persona_count}")
        print(f"   - 시스템 메시지: {system_count}")
        
        # 10. 문제 진단
        print(f"\n10. 문제 진단:")
        if persona_count == 0:
            print("❌ 문제 확인: 페르소나 에이전트가 전혀 발언하지 않음")
            print("   가능한 원인:")
            print("   - 퍼실리테이터가 잘못된 next_agent 값 선택")
            print("   - JSON 파싱 실패")
            print("   - 페르소나 에이전트 호출 오류")
        elif persona_count < 3:
            print(f"⚠️ 부분적 문제: 페르소나 에이전트 발언 수가 적음 ({persona_count}개)")
        else:
            print("✓ 페르소나 에이전트들이 정상적으로 발언함")
        
        if facilitator_count > persona_count * 2:
            print("⚠️ 퍼실리테이터가 과도하게 많이 발언함")
        
        # 11. 세션 상태 확인
        print(f"\n11. 최종 세션 상태:")
        discussion_history = session.state.get("discussion_history_phase2", [])
        print(f"   - 토론 히스토리 길이: {len(discussion_history)}")
        
        if discussion_history:
            print("   - 토론 참여자:")
            speakers = set(entry.get('speaker', 'unknown') for entry in discussion_history)
            for speaker in speakers:
                count = sum(1 for entry in discussion_history if entry.get('speaker') == speaker)
                print(f"     * {speaker}: {count}회 발언")
        
        print("\n=== 디버깅 완료 ===")
        
    except Exception as e:
        print(f"\n❌ 디버깅 중 오류 발생: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # 환경 변수 확인
    if 'GOOGLE_API_KEY' not in os.environ:
        print("GOOGLE_API_KEY 환경 변수를 설정해주세요.")
        print("export GOOGLE_API_KEY='your-api-key'")
        sys.exit(1)
    
    # 비동기 실행
    asyncio.run(debug_phase2_discussion()) 