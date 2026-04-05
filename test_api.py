"""API 服务验证脚本"""

import httpx
import asyncio


async def test_api():
    base_url = "http://127.0.0.1:8000"

    async with httpx.AsyncClient(timeout=10) as client:
        # 1. 测试健康检查
        print("1. 测试健康检查...")
        try:
            resp = await client.get(f"{base_url}/health")
            print(f"   状态码: {resp.status_code}")
            if resp.status_code == 200:
                print(f"   响应: {resp.json()}")
            else:
                print(f"   响应内容: {resp.text}")
        except Exception as e:
            print(f"   错误: {e}")

        # 2. 测试根路径
        print("\n2. 测试根路径...")
        try:
            resp = await client.get(f"{base_url}/")
            print(f"   状态码: {resp.status_code}")
            if resp.status_code == 200:
                print(f"   响应: {resp.json()}")
            else:
                print(f"   响应内容: {resp.text}")
        except Exception as e:
            print(f"   错误: {e}")

        # 3. 测试 LLM API 连通性
        print("\n3. 测试 LLM API 配置...")
        from src.config import get_llm_config
        cfg = get_llm_config()
        print(f"   API Key 设置: {'是' if cfg.api_key and not cfg.api_key.startswith('${') else '否'}")
        print(f"   Base URL: {cfg.base_url}")
        print(f"   Model: {cfg.model}")

        # 4. 测试 Embedding 配置
        print("\n4. 测试 Embedding 配置...")
        from src.config import get_embedding_config
        emb_cfg = get_embedding_config()
        print(f"   API Key 设置: {'是' if emb_cfg.api_key and not emb_cfg.api_key.startswith('${') else '否'}")
        print(f"   Base URL: {emb_cfg.base_url}")
        print(f"   Model: {emb_cfg.model}")
        print(f"   Dimensions: {emb_cfg.dimensions}")


if __name__ == "__main__":
    asyncio.run(test_api())
