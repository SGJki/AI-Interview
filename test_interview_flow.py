"""面试全流程测试脚本"""

import httpx
import asyncio
import uuid


async def test_interview_flow():
    base_url = "http://127.0.0.1:8000"
    session_id = str(uuid.uuid4())

    async with httpx.AsyncClient(timeout=30) as client:
        # 1. 测试健康检查
        print("1. 测试健康检查...")
        resp = await client.get(f"{base_url}/health")
        print(f"   状态码: {resp.status_code}, 响应: {resp.json()}")

        # 2. 开始面试
        print(f"\n2. 开始面试 (session_id: {session_id[:8]}...)")
        resp = await client.post(f"{base_url}/interview/start", json={
            "session_id": session_id,
            "resume_id": session_id,
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

        # 3. 提交答案
        print("\n3. 提交答案...")
        resp = await client.post(f"{base_url}/interview/answer", json={
            "session_id": session_id,
            "question_id": data.get('first_question', {}).get('question_id') or 'unknown',
            "user_answer": "这是一个测试回答，用于验证API是否正常工作。",
        })
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   响应: question_id={data.get('question_id')}")
            print(f"   反馈: {str(data.get('feedback', {}).get('content', ''))[:80] if data.get('feedback') else '无'}...")
            print(f"   下一题: {str(data.get('next_question_content', ''))[:80] if data.get('next_question_content') else '无'}...")
            print(f"   继续: {data.get('should_continue')}, 状态: {data.get('interview_status')}")
        else:
            print(f"   错误: {resp.text}")

        # 4. 结束面试
        print("\n4. 结束面试...")
        resp = await client.post(f"{base_url}/interview/end?session_id={session_id}")
        print(f"   状态码: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            print(f"   响应: session_id={data.get('session_id')}, status={data.get('status')}")
            print(f"   问题数: {data.get('total_questions')}, 系列数: {data.get('total_series')}")
            ff = data.get('final_feedback', {})
            if ff:
                print(f"   综合评分: {ff.get('overall_score', 'N/A')}")
                print(f"   优点: {ff.get('strengths', [])[:2] if ff.get('strengths') else '无'}")
                print(f"   待改进: {ff.get('weaknesses', [])[:2] if ff.get('weaknesses') else '无'}")
        else:
            print(f"   错误: {resp.text}")


if __name__ == "__main__":
    asyncio.run(test_interview_flow())
