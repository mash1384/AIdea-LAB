"""
AIdea Lab 유틸리티 패키지

이 패키지는 AIdea Lab 애플리케이션에서 사용되는 다양한 유틸리티를 제공합니다.
"""

from .model_monitor import AIModelMonitor, monitor_model_performance

__all__ = ['AIModelMonitor', 'monitor_model_performance'] 