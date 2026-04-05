"""面试全流程测试脚本 - 增加超时时间"""

import httpx
import asyncio
import uuid


async def test_interview_flow():
    base_url = "http://127.0.0.1:8000"
    session_id = str(uuid.uuid4())

    # 简历内容
    resume_content = """
姓名：张三
工作年限：5年
技术栈：Python, Django, FastAPI, PostgreSQL, Redis, Docker
项目经验：
1. 电商平台后端开发
   - 使用 Django 构建 RESTful API
   - 使用 Redis 实现缓存
   - 使用 PostgreSQL 存储数据

2. 微服务架构改造
   - 使用 FastAPI 构建微服务
   - 使用 Docker 容器化部署
   - 使用 Kong 网关
"""

    async with httpx.AsyncClient(timeout=600) as client:  # 600秒超时（LLM慢）
        # 1. 测试健康检查
        print("1. 测试健康检查...")
        resp = await client.get(f"{base_url}/health")
        print(f"   状态码: {resp.status_code}, 响应: {resp.json()}")

        # 2. 先构建简历知识库
        print(f"\n2. 构建简历知识库 (session_id: {session_id[:8]}...)")
        resp = await client.post(f"{base_url}/knowledge/build", json={
            "knowledge_base_id": session_id,
            "source_type": "resume",
            "content": resume_content,
        })
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   响应: status={data.get('status')}, documents_count={data.get('documents_count')}")
        else:
            print(f"   错误: {resp.text}")

        # 3. 开始面试
        print(f"\n3. 开始面试...")
        resp = await client.post(f"{base_url}/interview/start", json={
            "session_id": session_id,
            "resume_id": session_id,
            "knowledge_base_id": session_id,
            "interview_mode": "free",
            "feedback_mode": "recorded",
            "max_series": 3,
        })
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   响应: session_id={data.get('session_id')}, status={data.get('status')}")
            if data.get('first_question'):
                q = data['first_question']
                print(f"   第一题: {q.get('content', '')[:80]}...")
        else:
            print(f"   错误: {resp.text}")
            return

        # 4. 提交答案
        print("\n4. 提交答案...")
        resp = await client.post(f"{base_url}/interview/answer", json={
            "session_id": session_id,
            "question_id": data.get('first_question', {}).get('question_id') or 'unknown',
            "user_answer": "我最近做了一个电商平台项目，使用 Django 框架构建后端 API，使用 Redis 做缓存，PostgreSQL 存数据。",
        })
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   反馈: {str(data.get('feedback', {}).get('content', ''))[:80] if data.get('feedback') else '无'}...")
            print(f"   下一题: {str(data.get('next_question_content', ''))[:80] if data.get('next_question_content') else '无'}...")
        else:
            print(f"   错误: {resp.text}")

        # 5. 结束面试
        print("\n5. 结束面试...")
        resp = await client.post(f"{base_url}/interview/end?session_id={session_id}")
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   状态: {data.get('status')}, 问题数: {data.get('total_questions')}")
            ff = data.get('final_feedback', {})
            if ff:
                print(f"   综合评分: {ff.get('overall_score', 'N/A')}")
        else:
            print(f"   错误: {resp.text}")


if __name__ == "__main__":
    asyncio.run(test_interview_flow())
