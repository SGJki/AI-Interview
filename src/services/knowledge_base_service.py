"""
Knowledge Base Service for AI Interview Agent

提供知识库的构建和管理功能
"""

import json
import logging
from typing import Optional

logger = logging.getLogger(__name__)

from langchain_core.documents import Document
from src.tools.rag_tools import (
    get_embeddings,
    get_vectorstore,
    add_to_knowledge_base,
)
from src.llm.client import invoke_llm
from src.llm.prompts import RESUME_EXTRACTION_PROMPT, SKILL_QUESTION_PROMPT


class KnowledgeBaseService:
    """
    知识库服务

    提供知识库构建、文档管理等功能
    """

    def __init__(self, persist_directory: str = "./data/vectorstore"):
        """
        初始化知识库服务

        Args:
            persist_directory: 向量数据库持久化路径
        """
        self.persist_directory = persist_directory

    async def build_from_resume(self, resume_content: str, resume_id: str) -> dict:
        """
        从简历构建知识库

        Args:
            resume_content: 简历文本内容
            resume_id: 简历ID

        Returns:
            构建结果，包含提取的信息和文档数量
        """
        try:
            # 使用 LLM 提取简历中的结构化信息
            prompt = RESUME_EXTRACTION_PROMPT.format(resume_content=resume_content)
            result_text = await invoke_llm(
                system_prompt="",
                user_prompt=prompt,
                temperature=0.3,
            )

            # 解析 JSON 结果
            resume_data = json.loads(result_text)

            # 构建文档列表
            documents = []

            # 0. 添加原始简历内容（用于后续检索）
            raw_doc = Document(
                page_content=f"原始简历内容: {resume_content}",
                metadata={"type": "raw_resume", "resume_id": resume_id}
            )
            documents.append(raw_doc)

            # 1. 添加技能文档
            skills = resume_data.get("skills", [])
            if skills:
                skill_doc = Document(
                    page_content=f"简历技能: {', '.join(skills)}",
                    metadata={"type": "skills", "resume_id": resume_id}
                )
                documents.append(skill_doc)

            # 2. 添加项目文档
            projects = resume_data.get("projects", [])
            for project in projects:
                project_text = f"项目: {project.get('name', '')}\n"
                project_text += f"描述: {project.get('description', '')}\n"
                project_text += f"技术栈: {', '.join(project.get('technologies', []))}\n"
                project_text += f"亮点: {', '.join(project.get('highlights', []))}"

                project_doc = Document(
                    page_content=project_text,
                    metadata={"type": "project", "resume_id": resume_id}
                )
                documents.append(project_doc)

            # 3. 添加经验文档
            experience = resume_data.get("experience", [])
            for exp in experience:
                exp_text = f"公司: {exp.get('company', '')}\n"
                exp_text += f"职位: {exp.get('position', '')}\n"
                exp_text += f"时间: {exp.get('duration', '')}\n"
                exp_text += f"亮点: {', '.join(exp.get('highlights', []))}"

                exp_doc = Document(
                    page_content=exp_text,
                    metadata={"type": "experience", "resume_id": resume_id}
                )
                documents.append(exp_doc)

            # 4. 添加职责文档 (responsibilities) - 这是面试针对性提问的关键
            responsibilities_count = 0
            for project in projects:
                project_name = project.get('name', '')
                responsibilities = project.get('responsibilities', [])
                # 调试日志：查看 LLM 提取的项目数据
                if responsibilities:
                    logger.debug(f"[build_from_resume] project='{project_name}', responsibilities count={len(responsibilities)}")
                    for idx, resp in enumerate(responsibilities):
                        logger.debug(f"[build_from_resume]   resp_{idx}: {resp[:50]}..." if len(resp) > 50 else f"[build_from_resume]   resp_{idx}: {resp}")
                for resp_idx, resp_text in enumerate(responsibilities):
                    if resp_text and resp_text.strip():
                        resp_doc = Document(
                            page_content=resp_text.strip(),
                            metadata={
                                "type": "responsibility",
                                "resume_id": resume_id,
                                "responsibility_id": resp_idx,
                                "project_name": project_name,
                            }
                        )
                        documents.append(resp_doc)
                        responsibilities_count += 1
            logger.debug(f"[build_from_resume] Total responsibilities to save: {responsibilities_count}")

            # 添加到向量数据库
            vectorstore = get_vectorstore(self.persist_directory)
            vectorstore.add_documents(documents)

            return {
                "status": "success",
                "resume_id": resume_id,
                "skills_count": len(skills),
                "projects_count": len(projects),
                "experience_count": len(experience),
                "responsibilities_count": responsibilities_count,
                "documents_added": len(documents),
            }

        except json.JSONDecodeError as e:
            return {
                "status": "error",
                "error": f"简历解析失败: {str(e)}",
            }
        except Exception as e:
            return {
                "status": "error",
                "error": f"知识库构建失败: {str(e)}",
            }

    async def build_preset_question_bank(self) -> dict:
        """
        构建预设面试题库

        常见面试问题按技能分类

        Returns:
            构建结果
        """
        skill_categories = [
            "Python编程",
            "数据库",
            "Redis缓存",
            "微服务架构",
            "系统设计",
            "项目经验",
            "团队协作",
            "问题解决",
        ]

        all_questions = []

        for skill in skill_categories:
            try:
                prompt = SKILL_QUESTION_PROMPT.format(skill_point=skill)
                result_text = await invoke_llm(
                    system_prompt="",
                    user_prompt=prompt,
                    temperature=0.7,
                )

                # 解析 JSON 数组
                questions = json.loads(result_text)
                all_questions.extend(questions)

                # 添加每个问题到知识库
                for q in questions:
                    doc = Document(
                        page_content=q,
                        metadata={"type": "question", "skill_point": skill}
                    )
                    await add_to_knowledge_base(
                        content=q,
                        metadata={"type": "question", "skill_point": skill},
                        persist_directory=self.persist_directory,
                    )

            except Exception:
                continue

        return {
            "status": "success",
            "category_count": len(skill_categories),
            "questions_added": len(all_questions),
        }

    async def build_standard_answer_kb(self) -> dict:
        """
        构建标准回答知识库

        为常见问题添加标准回答

        Returns:
            构建结果
        """
        # 常见问题-标准回答对
        qa_pairs = [
            {
                "question": "请介绍一下你最近做的项目",
                "answer": "我最近做了一个XXX项目，这是一个XXX类型的系统。项目使用了XX技术栈，我负责XX模块的开发。在项目中我遇到了XX挑战，通过XX方式解决了。项目最终达到了XX效果。"
            },
            {
                "question": "你最大的优点是什么",
                "answer": "我最大的优点是学习能力和问题解决能力。在工作中遇到新技术时，我能快速学习并应用到实际项目中。同时，我善于分析问题，会从多个角度思考解决方案。"
            },
            {
                "question": "你有什么缺点",
                "answer": "我的缺点是有时候对代码质量过于追求完美，可能会在细节上花费较多时间。不过我也在学习平衡质量和效率，确保在截止日期前交付可用的产品。"
            },
        ]

        count = 0
        for qa in qa_pairs:
            try:
                # 添加问题
                await add_to_knowledge_base(
                    content=qa["question"],
                    metadata={"type": "question"},
                    persist_directory=self.persist_directory,
                )

                # 添加标准回答
                await add_to_knowledge_base(
                    content=qa["answer"],
                    metadata={"type": "answer"},
                    persist_directory=self.persist_directory,
                )
                count += 1
            except Exception:
                continue

        return {
            "status": "success",
            "qa_pairs_added": count,
        }

    async def build_skill_point_kb(self, skill_points: list[str]) -> dict:
        """
        构建技能点知识库

        Args:
            skill_points: 技能点列表

        Returns:
            构建结果
        """
        count = 0
        for skill in skill_points:
            try:
                # 为每个技能点创建一个知识文档
                skill_doc = Document(
                    page_content=f"技能点: {skill}\n\n相关知识点:\n1. 基本概念\n2. 核心原理\n3. 实践应用\n4. 常见问题",
                    metadata={"type": "skill_point", "skill_point": skill}
                )

                await add_to_knowledge_base(
                    content=skill_doc.page_content,
                    metadata=skill_doc.metadata,
                    persist_directory=self.persist_directory,
                )
                count += 1
            except Exception:
                continue

        return {
            "status": "success",
            "skill_points_added": count,
        }

    async def add_document(
        self,
        content: str,
        metadata: dict,
    ) -> dict:
        """
        添加单个文档到知识库

        Args:
            content: 文档内容
            metadata: 元数据

        Returns:
            添加结果
        """
        try:
            await add_to_knowledge_base(
                content=content,
                metadata=metadata,
                persist_directory=self.persist_directory,
            )
            return {"status": "success", "content": content[:50]}
        except Exception as e:
            return {"status": "error", "error": str(e)}

    async def build_all(self) -> dict:
        """
        构建完整的知识库

        包括预设题库、标准回答等

        Returns:
            构建结果汇总
        """
        results = {}

        # 1. 构建预设题库
        results["question_bank"] = await self.build_preset_question_bank()

        # 2. 构建标准回答库
        results["standard_answers"] = await self.build_standard_answer_kb()

        return results
