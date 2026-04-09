"""
Agent Prompt Templates

ReviewAgent 使用的 prompt 模板
"""

# =============================================================================
# ReviewAgent Prompts
# =============================================================================

REVIEW_EVALUATION_BASED_ON_QA = """判断以下评估是否基于实际的问答内容：

问题: {question}
回答: {user_answer}
评估: {evaluation}

评估是否基于问答内容而非外部信息？只回答 YES 或 NO。"""

REVIEW_STANDARD_ANSWER_FIT = """判断以下标准答案是否与问题相关：

问题: {question}
标准答案: {standard_answer}

标准答案是否适合作为该问题的参考？只回答 YES 或 NO。"""
