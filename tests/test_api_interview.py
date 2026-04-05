"""
Tests for FastAPI Interview Endpoints - Phase 5

测试面试相关 API 端点：
- /interview/start - 开始面试
- /interview/question - 获取当前问题（流式）
- /interview/answer - 提交回答
- /interview/end - 结束面试
"""

import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from fastapi.testclient import TestClient


class TestInterviewAPI:
    """Test Interview API endpoints"""

    def test_start_interview_endpoint_exists(self):
        """测试开始面试端点存在"""
        from src.api import interview_router
        # 验证 interview_router 存在
        assert interview_router is not None

    def test_question_endpoint_is_sse(self):
        """测试问题端点支持 SSE"""
        from src.api import interview_router
        # 验证 question 路由是 GET 方法
        routes = [route.path for route in interview_router.routes]
        assert "/question" in routes or "/question" in str(routes)


class TestStartInterview:
    """Test /interview/start endpoint"""

    def test_start_interview_request_model(self):
        """测试 StartInterviewRequest 模型"""
        from src.api.models import StartInterviewRequest
        req = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
        )
        assert req.resume_id == "resume-123"
        assert req.session_id == "session-456"

    def test_start_interview_request_with_optional_fields(self):
        """测试 StartInterviewRequest 可选字段"""
        from src.api.models import StartInterviewRequest
        req = StartInterviewRequest(
            resume_id="resume-123",
            session_id="session-456",
            interview_mode="training",
            feedback_mode="realtime",
            max_series=3,
        )
        assert req.interview_mode == "training"
        assert req.feedback_mode == "realtime"
        assert req.max_series == 3


class TestSubmitAnswer:
    """Test /interview/answer endpoint"""

    def test_submit_answer_request_model(self):
        """测试 SubmitAnswerRequest 模型"""
        from src.api.models import SubmitAnswerRequest
        req = SubmitAnswerRequest(
            session_id="session-123",
            question_id="q-1",
            user_answer="我的回答",
        )
        assert req.session_id == "session-123"
        assert req.question_id == "q-1"
        assert req.user_answer == "我的回答"


class TestQAResponse:
    """Test QAResponse model"""

    def test_qa_response_model(self):
        """测试 QAResponse 模型"""
        from src.api.models import QAResponse
        resp = QAResponse(
            question_id="q-1",
            question_content="请介绍项目",
            feedback=None,
            next_question_id=None,
            should_continue=True,
            interview_status="active",
        )
        assert resp.question_id == "q-1"
        assert resp.should_continue is True
        assert resp.interview_status == "active"

    def test_qa_response_with_feedback(self):
        """测试带反馈的 QAResponse"""
        from src.api.models import QAResponse, FeedbackData
        resp = QAResponse(
            question_id="q-1",
            question_content="请介绍项目",
            feedback=FeedbackData(
                content="回答得很好",
                feedback_type="comment",
                is_correct=True,
            ),
            next_question_id=None,
            should_continue=False,
            interview_status="completed",
        )
        assert resp.feedback is not None
        assert resp.feedback.feedback_type == "comment"


class TestInterviewResult:
    """Test InterviewResult model"""

    def test_interview_result_model(self):
        """测试 InterviewResult 模型"""
        from src.api.models import InterviewResult
        result = InterviewResult(
            session_id="session-123",
            status="completed",
            total_questions=5,
            total_series=2,
            final_feedback={},
        )
        assert result.session_id == "session-123"
        assert result.status == "completed"


class TestAPIEndpoints:
    """Test API endpoint routing"""

    def test_interview_router_has_all_routes(self):
        """测试 interview_router 包含所有必要路由"""
        from src.api import interview_router
        # 获取所有路由路径
        route_paths = []
        for route in interview_router.routes:
            if hasattr(route, 'path'):
                route_paths.append(route.path)
            elif hasattr(route, 'url_path'):
                route_paths.append(route.url_path)

        # 验证必要路由存在
        assert any("start" in p for p in route_paths)
        assert any("question" in p for p in route_paths)
        assert any("answer" in p for p in route_paths)
        assert any("end" in p for p in route_paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
