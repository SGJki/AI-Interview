"""Tests for skill_point extraction."""
import pytest
from src.agent.skill_point_extractor import extract_skill_point


class TestExtractSkillPoint:
    """Test extract_skill_point function."""

    def test_extract_python(self):
        """Test Python extraction."""
        result = extract_skill_point("请谈谈Python编程的经验")
        assert result == "Python"

    def test_extract_redis(self):
        """Test Redis extraction."""
        result = extract_skill_point("Redis缓存优化方法")
        assert result == "Redis"

    def test_extract_microservice(self):
        """Test microservice extraction."""
        result = extract_skill_point("如何设计微服务架构")
        assert result == "微服务"

    def test_no_match(self):
        """Test no keyword match returns None."""
        result = extract_skill_point("介绍一下你自己和你的项目经验")
        assert result is None

    def test_case_insensitive(self):
        """Test case insensitive matching."""
        result = extract_skill_point("python programming")
        assert result == "python"  # lowercase match

    def test_empty_string(self):
        """Test empty string returns None."""
        result = extract_skill_point("")
        assert result is None

    def test_none_input(self):
        """Test None input returns None."""
        result = extract_skill_point(None)
        assert result is None

    def test_java(self):
        """Test Java extraction."""
        result = extract_skill_point("Java并发编程面试题")
        assert result == "Java"

    def test_docker(self):
        """Test Docker extraction."""
        result = extract_skill_point("Docker容器化部署")
        assert result == "Docker"

    def test_mysql(self):
        """Test MySQL extraction."""
        result = extract_skill_point("MySQL数据库优化")
        assert result == "MySQL"

    def test_kubernetes(self):
        """Test Kubernetes extraction."""
        result = extract_skill_point("Kubernetes集群管理")
        assert result == "Kubernetes"

    def test_api(self):
        """Test API extraction."""
        result = extract_skill_point("RESTful API设计")
        assert result == "API"

    def test_auth(self):
        """Test authentication extraction."""
        result = extract_skill_point("用户认证和授权机制")
        assert result == "认证"
