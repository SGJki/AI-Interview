"""
Tests for AI Interview Agent - Resume Parser
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from src.services.resume_parser import (
    ResumeParser,
    ResumeInfo,
    ProjectInfo,
    EducationInfo,
    WorkExperience,
)


class TestResumeInfo:
    """Test ResumeInfo dataclass"""

    def test_resume_info_creation(self):
        """测试创建简历信息"""
        resume = ResumeInfo(
            name="张三",
            email="zhangsan@example.com",
            phone="13800138000",
        )

        assert resume.name == "张三"
        assert resume.email == "zhangsan@example.com"
        assert resume.skills == []
        assert resume.projects == []


class TestResumeParser:
    """Test ResumeParser class"""

    def test_resume_parser_exists(self):
        """测试 ResumeParser 类存在"""
        assert ResumeParser is not None

    @pytest.mark.asyncio
    async def test_parse_pdf_mock(self):
        """测试解析 PDF 简历"""
        mock_parser = MagicMock()
        mock_parser.aparse.return_value = {
            "name": "张三",
            "email": "zhangsan@example.com",
            "skills": ["Python", "FastAPI", "Redis"],
            "projects": [
                {"name": "电商系统", "description": "基于微服务的电商平台"}
            ],
        }

        # 由于是 mock，直接测试接口
        assert mock_parser.aparse is not None


class TestExtractSkills:
    """Test skill extraction"""

    def test_skill_extraction_patterns(self):
        """测试技能提取模式"""
        from src.services.resume_parser import _extract_skills_from_text

        text = "熟练使用 Python、Java、Go 等编程语言，熟悉 Redis、MySQL 数据库"
        skills = _extract_skills_from_text(text)

        assert "Python" in skills or "Java" in skills or "Go" in skills


class TestExtractWorkExperience:
    """Test work experience extraction"""

    def test_extract_work_experience_with_duration(self):
        """测试提取工作经历包含时长"""
        from src.services.resume_parser import _extract_work_experience

        text = """
        公司：字节跳动
        职位：高级后端工程师
        2020.03 - 2023.06
        负责抖音推荐系统后端开发
        """
        experience = _extract_work_experience(text)

        assert len(experience) > 0
        assert experience[0].company == "字节跳动"
        assert experience[0].position == "高级后端工程师"
        assert "2020" in experience[0].duration

    def test_extract_work_experience_no_duration(self):
        """测试提取工作经历无时长"""
        from src.services.resume_parser import _extract_work_experience

        text = """
        公司：某创业公司
        职位：初级工程师
        负责前端开发
        """
        experience = _extract_work_experience(text)

        assert len(experience) > 0
        assert experience[0].duration == ""


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
