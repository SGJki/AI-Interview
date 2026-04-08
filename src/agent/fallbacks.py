# src/agent/fallbacks.py

from dataclasses import dataclass

FALLBACK_QUESTIONS = {
    "warmup": "请简单介绍一下你自己",
    "initial": "请谈谈你最近做的项目经验",
    "followup": "能详细说说这个项目中的具体实现吗？",
    "correction": "这个问题的答案需要结合具体场景来分析。",
    "guidance": "你的回答方向正确，能否更详细地说明一下？",
    "comment": "回答得很好！能否再深入一点？",
}

@dataclass
class FallbackResponse:
    content: str
    fallback_type: str

def get_fallback_question(question_type: str) -> FallbackResponse:
    """获取 fallback 问题"""
    content = FALLBACK_QUESTIONS.get(question_type, "请谈谈你的项目经验")
    return FallbackResponse(content=content, fallback_type=question_type)

def get_fallback_feedback(deviation_score: float) -> FallbackResponse:
    """根据偏差分数获取 fallback 反馈"""
    if deviation_score < 0.3:
        content = FALLBACK_QUESTIONS["correction"]
        fallback_type = "correction"
    elif deviation_score < 0.6:
        content = FALLBACK_QUESTIONS["guidance"]
        fallback_type = "guidance"
    else:
        content = FALLBACK_QUESTIONS["comment"]
        fallback_type = "comment"
    return FallbackResponse(content=content, fallback_type=fallback_type)