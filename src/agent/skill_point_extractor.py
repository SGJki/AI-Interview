"""Skill point extraction from question content."""
from typing import Optional


# Common technical keywords for skill points
SKILL_KEYWORDS = [
    # Programming languages
    "Python", "python", "Java", "Go", "Rust", "JavaScript", "TypeScript", "C++", "C#",
    # Databases
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
    # Infrastructure
    "Docker", "Kubernetes", "Git", "Linux", "Nginx",
    # Concepts
    "缓存", "队列", "微服务", "数据库", "架构", "认证", "授权", "OAuth",
    "Token", "JWT", "API", "REST", "GraphQL",
    # Chinese technical terms
    "Python", "Java", "Go", "Redis", "MySQL", "MongoDB",
    "缓存", "消息队列", "微服务", "容器", "DevOps",
]


def extract_skill_point(question_content: str) -> Optional[str]:
    """
    Extract skill_point from question content.

    Args:
        question_content: The question text

    Returns:
        The detected skill keyword or None if no match found
    """
    if not question_content:
        return None

    # Find first matching keyword
    for keyword in SKILL_KEYWORDS:
        if keyword in question_content:
            return keyword

    return None
