"""
AIdea Lab 모델 성능 모니터링 시스템

이 모듈은 AI 모델의 성능을 모니터링하고 분석하는 클래스를 제공합니다.
응답 시간, 성공률, 오류 유형 등을 추적하여 최적의 모델을 추천합니다.
"""

import time
import asyncio
from typing import Dict, List, Any, Optional, Tuple
import json
import os
from datetime import datetime

class AIModelMonitor:
    """AI 모델 성능 모니터링 클래스"""
    
    def __init__(self, log_file_path: Optional[str] = None):
        """
        모니터링 시스템 초기화
        
        Args:
            log_file_path (str, optional): 로그 파일 경로. 기본값은 None.
        """
        self.response_times: Dict[str, List[float]] = {}
        self.success_rates: Dict[str, Dict[str, int]] = {}
        self.error_counts: Dict[str, Dict[str, int]] = {}
        self.log_file_path = log_file_path or "model_performance_logs.json"
        
        # 기존 로그 파일 로드 (있는 경우)
        self._load_logs()
    
    def _load_logs(self) -> None:
        """기존 로그 파일을 로드합니다."""
        if os.path.exists(self.log_file_path):
            try:
                with open(self.log_file_path, 'r') as f:
                    logs = json.load(f)
                    self.response_times = logs.get('response_times', {})
                    self.success_rates = logs.get('success_rates', {})
                    self.error_counts = logs.get('error_counts', {})
                print(f"Loaded existing model performance logs from {self.log_file_path}")
            except Exception as e:
                print(f"Error loading model performance logs: {e}")
    
    def _save_logs(self) -> None:
        """현재 로그를 파일에 저장합니다."""
        try:
            logs = {
                'response_times': self.response_times,
                'success_rates': self.success_rates,
                'error_counts': self.error_counts,
                'last_updated': datetime.now().isoformat()
            }
            with open(self.log_file_path, 'w') as f:
                json.dump(logs, f, indent=2)
        except Exception as e:
            print(f"Error saving model performance logs: {e}")
    
    def record_api_call(self, model_name: str, success: bool, response_time: float, error_type: Optional[str] = None) -> None:
        """
        모델 API 호출 결과를 기록합니다.
        
        Args:
            model_name (str): 모델 이름
            success (bool): 호출 성공 여부
            response_time (float): 응답 시간 (초)
            error_type (str, optional): 에러 유형 (실패 시)
        """
        # 모델 초기화 (첫 기록인 경우)
        if model_name not in self.response_times:
            self.response_times[model_name] = []
            self.success_rates[model_name] = {"success": 0, "total": 0}
            self.error_counts[model_name] = {}
        
        # 응답 시간 기록
        self.response_times[model_name].append(response_time)
        
        # 성공률 업데이트
        self.success_rates[model_name]["total"] += 1
        if success:
            self.success_rates[model_name]["success"] += 1
        # 에러 유형 카운트
        elif error_type:
            if error_type not in self.error_counts[model_name]:
                self.error_counts[model_name][error_type] = 0
            self.error_counts[model_name][error_type] += 1
        
        # 정기적으로 로그 저장
        if self.success_rates[model_name]["total"] % 10 == 0:
            self._save_logs()
    
    def get_model_performance(self, model_name: str) -> Dict[str, Any]:
        """
        특정 모델의 성능 지표를 반환합니다.
        
        Args:
            model_name (str): 모델 이름
            
        Returns:
            Dict[str, Any]: 성능 지표
        """
        if model_name not in self.response_times:
            return {"error": "Model not found in monitoring data"}
        
        total_calls = self.success_rates[model_name]["total"]
        success_calls = self.success_rates[model_name]["success"]
        
        performance = {
            "model_name": model_name,
            "total_calls": total_calls,
            "success_calls": success_calls,
            "success_rate": success_calls / total_calls if total_calls > 0 else 0,
            "avg_response_time": sum(self.response_times[model_name]) / len(self.response_times[model_name]) if self.response_times[model_name] else 0,
            "min_response_time": min(self.response_times[model_name]) if self.response_times[model_name] else 0,
            "max_response_time": max(self.response_times[model_name]) if self.response_times[model_name] else 0,
            "error_types": self.error_counts[model_name]
        }
        
        return performance
    
    def get_model_recommendations(self) -> Dict[str, Dict[str, Any]]:
        """
        성능 기반 모델 추천을 반환합니다.
        
        Returns:
            Dict[str, Dict[str, Any]]: 모델별 추천 정보
        """
        recommendations = {}
        
        for model, stats in self.success_rates.items():
            if stats["total"] < 5:
                # 충분한 데이터가 없는 경우
                recommendation = "insufficient_data"
                reason = f"모델 {model}에 대한 충분한 데이터가 없습니다 ({stats['total']} 호출)."
            else:
                success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
                avg_response_time = sum(self.response_times[model]) / len(self.response_times[model]) if self.response_times[model] else 0
                
                if success_rate < 0.7:
                    recommendation = "not_recommended"
                    reason = f"낮은 성공률 ({success_rate:.2%})"
                elif success_rate >= 0.9:
                    recommendation = "highly_recommended"
                    reason = f"높은 성공률 ({success_rate:.2%})"
                else:
                    recommendation = "recommended"
                    reason = f"보통 성공률 ({success_rate:.2%})"
            
            recommendations[model] = {
                "recommendation": recommendation,
                "reason": reason,
                "success_rate": stats["success"] / stats["total"] if stats["total"] > 0 else 0,
                "avg_response_time": sum(self.response_times[model]) / len(self.response_times[model]) if self.response_times[model] else 0,
                "total_calls": stats["total"]
            }
        
        return recommendations
    
    def get_best_model(self) -> Optional[Tuple[str, Dict[str, Any]]]:
        """
        가장 성능이 좋은 모델을 반환합니다.
        
        Returns:
            Optional[Tuple[str, Dict[str, Any]]]: (모델 이름, 성능 지표) 또는 None
        """
        if not self.success_rates:
            return None
        
        best_model = None
        best_score = -1
        
        for model, stats in self.success_rates.items():
            if stats["total"] < 5:
                continue  # 충분한 데이터가 없는 모델은 제외
            
            success_rate = stats["success"] / stats["total"] if stats["total"] > 0 else 0
            avg_response_time = sum(self.response_times[model]) / len(self.response_times[model]) if self.response_times[model] else 0
            
            # 성능 점수 계산 (성공률 80%, 응답 시간 20%)
            score = (success_rate * 0.8) - (min(avg_response_time, 10) / 10 * 0.2)
            
            if score > best_score:
                best_score = score
                best_model = model
        
        if best_model:
            return (best_model, self.get_model_performance(best_model))
        
        return None

# 모니터링 측정 데코레이터
def monitor_model_performance(monitor: AIModelMonitor):
    """
    모델 성능을 모니터링하는 데코레이터
    
    Args:
        monitor (AIModelMonitor): 모니터링 인스턴스
    """
    def decorator(func):
        # 비동기 함수인지 확인
        if asyncio.iscoroutinefunction(func):
            # 비동기 함수를 위한 래퍼
            async def wrapper(*args, **kwargs):
                # kwargs에서 model_name 추출, 없으면 'unknown'을 사용
                model_name = kwargs.get('model_name', 'unknown')
                # orchestrator 객체에서 model_name 추출 시도
                if model_name == 'unknown' and args and hasattr(args[0], 'model_name'):
                    model_name = args[0].model_name
                
                start_time = time.time()
                success = True
                error_type = None
                
                try:
                    # 비동기 함수 호출 시 await 사용
                    result = await func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_type = type(e).__name__
                    raise
                finally:
                    response_time = time.time() - start_time
                    monitor.record_api_call(model_name, success, response_time, error_type)
            
            return wrapper
        else:
            # 동기 함수를 위한 기존 래퍼
            def wrapper(*args, **kwargs):
                # kwargs에서 model_name 추출, 없으면 'unknown'을 사용
                model_name = kwargs.get('model_name', 'unknown')
                # orchestrator 객체에서 model_name 추출 시도
                if model_name == 'unknown' and args and hasattr(args[0], 'model_name'):
                    model_name = args[0].model_name
                
                start_time = time.time()
                success = True
                error_type = None
                
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    success = False
                    error_type = type(e).__name__
                    raise
                finally:
                    response_time = time.time() - start_time
                    monitor.record_api_call(model_name, success, response_time, error_type)
            
            return wrapper
    
    return decorator 