import pytest
import unittest.mock
import json


@pytest.mark.asyncio
async def test_extract_resume_info_success():
    """测试 extract_resume_info 成功解析简历"""
    from src.services.llm_service import InterviewLLMService

    service = InterviewLLMService()

    resume_text = """
    姓名: 张三
    技能: Python, FastAPI, PostgreSQL
    项目: 电商平台 - 负责 API 开发
    """

    # Mock the invoke_llm function at module level
    with unittest.mock.patch('src.services.llm_service.invoke_llm', new_callable=unittest.mock.AsyncMock) as mock:
        mock.return_value = '{"skills": ["Python"], "projects": [{"name": "Test", "responsibilities": ["开发 API"]}], "experience": []}'

        result = await service.extract_resume_info(resume_text)

        assert "skills" in result
        assert "projects" in result
        assert "experience" in result
        assert result["skills"] == ["Python"]
        assert result["projects"] == [{"name": "Test", "responsibilities": ["开发 API"]}]
        assert result["experience"] == []


@pytest.mark.asyncio
async def test_extract_resume_info_json_decode_error():
    """测试 extract_resume_info JSON 解析失败时返回空结构"""
    from src.services.llm_service import InterviewLLMService

    service = InterviewLLMService()

    with unittest.mock.patch('src.services.llm_service.invoke_llm', new_callable=unittest.mock.AsyncMock) as mock:
        mock.return_value = "invalid json {"

        result = await service.extract_resume_info("resume text")

        assert result == {"skills": [], "projects": [], "experience": []}


@pytest.mark.asyncio
async def test_extract_resume_info_non_dict_return():
    """测试 extract_resume_info 返回非字典时返回空结构"""
    from src.services.llm_service import InterviewLLMService

    service = InterviewLLMService()

    with unittest.mock.patch('src.services.llm_service.invoke_llm', new_callable=unittest.mock.AsyncMock) as mock:
        mock.return_value = '["not a dict"]'

        result = await service.extract_resume_info("resume text")

        assert result == {"skills": [], "projects": [], "experience": []}


@pytest.mark.asyncio
async def test_extract_resume_info_general_exception():
    """测试 extract_resume_info 通用异常时返回空结构"""
    from src.services.llm_service import InterviewLLMService

    service = InterviewLLMService()

    with unittest.mock.patch('src.services.llm_service.invoke_llm', new_callable=unittest.mock.AsyncMock) as mock:
        mock.side_effect = RuntimeError("LLM service unavailable")

        result = await service.extract_resume_info("resume text")

        assert result == {"skills": [], "projects": [], "experience": []}
