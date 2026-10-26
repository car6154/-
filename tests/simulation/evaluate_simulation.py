# -*- coding: utf-8 -*-
"""
tests/simulation/evaluate_simulation.py
진짜 7대 대상 시뮬레이션 지표 산출 및 순위 평가
"""
import sys
import os

sys.path.insert(0, os.path.abspath("."))
from scratch.evaluate_7cars_simulation import evaluate_7cars

if __name__ == "__main__":
    evaluate_7cars()
