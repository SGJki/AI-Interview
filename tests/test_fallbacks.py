# tests/test_fallbacks.py

import pytest
from src.agent.fallbacks import get_fallback_question, get_fallback_feedback, FALLBACK_QUESTIONS

def test_get_fallback_question_warmup():
    """测试获取预热问题的 fallback"""
    result = get_fallback_question("warmup")
    assert result.content == "请简单介绍一下你自己"
    assert result.fallback_type == "warmup"

def test_get_fallback_question_unknown():
    """测试获取未知类型的 fallback"""
    result = get_fallback_question("unknown_type")
    assert result.content == "请谈谈你的项目经验"

def test_get_fallback_feedback_correction():
    """测试低偏差时获取纠正反馈"""
    result = get_fallback_feedback(0.2)
    assert result.fallback_type == "correction"

def test_get_fallback_feedback_guidance():
    """测试中等偏差时获取引导反馈"""
    result = get_fallback_feedback(0.5)
    assert result.fallback_type == "guidance"

def test_get_fallback_feedback_comment():
    """测试高偏差时获取评论反馈"""
    result = get_fallback_feedback(0.8)
    assert result.fallback_type == "comment"

def test_fallback_questions_all_types():
    """测试所有 fallback 问题类型都存在"""
    for key in ["warmup", "initial", "followup", "correction", "guidance", "comment"]:
        assert key in FALLBACK_QUESTIONS