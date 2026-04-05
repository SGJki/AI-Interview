"""
Resume Parser Service for AI Interview Agent

简历解析服务：解析 PDF 简历，提取结构化信息
"""

import re
from dataclasses import dataclass, field
from typing import Optional
from pypdf import PdfReader
from io import BytesIO


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ProjectInfo:
    """项目信息"""
    name: str
    description: str
    technologies: list[str] = field(default_factory=list)
    role: Optional[str] = None
    duration: Optional[str] = None
    highlights: list[str] = field(default_factory=list)


@dataclass
class EducationInfo:
    """教育经历"""
    school: str
    degree: str
    major: str
    duration: Optional[str] = None
    gpa: Optional[str] = None


@dataclass
class WorkExperience:
    """工作经历"""
    company: str
    position: str
    duration: str
    description: str
    achievements: list[str] = field(default_factory=list)


@dataclass
class ResumeInfo:
    """简历信息"""
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    location: Optional[str] = None

    # 技能
    skills: list[str] = field(default_factory=list)
    skill_categories: dict[str, list[str]] = field(default_factory=dict)

    # 项目
    projects: list[ProjectInfo] = field(default_factory=list)

    # 教育
    education: list[EducationInfo] = field(default_factory=list)

    # 工作经历
    work_experience: list[WorkExperience] = field(default_factory=list)

    # 原始文本
    raw_text: str = ""

    # 元数据
    file_path: Optional[str] = None
    parsed_at: Optional[str] = None


# =============================================================================
# Skill Patterns
# =============================================================================

SKILL_PATTERNS = {
    "programming_languages": [
        "Python", "Java", "JavaScript", "TypeScript", "Go", "Rust", "C++",
        "C#", "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R",
    ],
    "frameworks": [
        "Spring", "Django", "Flask", "FastAPI", "React", "Vue", "Angular",
        "Node.js", "Express", "NestJS", "Next.js", "Nuxt",
    ],
    "databases": [
        "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch",
        "Oracle", "SQL Server", "SQLite", "Cassandra", "DynamoDB",
    ],
    "tools": [
        "Git", "Docker", "Kubernetes", "Jenkins", "CI/CD", "Linux",
        "Nginx", "Apache", "Maven", "Gradle", "Webpack",
    ],
    "cloud": [
        "AWS", "Azure", "GCP", "Alibaba Cloud", "Tencent Cloud",
        "ECS", "S3", "Lambda", "K8s",
    ],
    "ml_ai": [
        "Machine Learning", "Deep Learning", "NLP", "TensorFlow",
        "PyTorch", "Scikit-learn", "LangChain", "LangGraph",
    ],
}


# =============================================================================
# Helper Functions
# =============================================================================

def _extract_skills_from_text(text: str) -> list[str]:
    """从文本中提取技能"""
    found_skills = []
    text_upper = text.upper()

    for category, skills in SKILL_PATTERNS.items():
        for skill in skills:
            if skill.upper() in text_upper:
                if skill not in found_skills:
                    found_skills.append(skill)

    return found_skills


def _categorize_skills(skills: list[str]) -> dict[str, list[str]]:
    """对技能进行分类"""
    categories = {}

    for category, category_skills in SKILL_PATTERNS.items():
        matched = [s for s in skills if s in category_skills]
        if matched:
            categories[category] = matched

    return categories


def _extract_projects(text: str) -> list[ProjectInfo]:
    """从文本中提取项目信息"""
    projects = []

    # 项目名称模式
    project_pattern = r"项目[：:]\s*([^\n]+)"
    project_matches = re.finditer(project_pattern, text)

    for match in project_matches:
        project_name = match.group(1).strip()
        start_pos = match.start()

        # 尝试获取项目描述（接下来的几行）
        end_pos = min(start_pos + 500, len(text))
        project_text = text[start_pos:end_pos]

        # 提取技术栈
        technologies = _extract_skills_from_text(project_text)

        # 提取项目亮点
        highlight_pattern = r"[•\-\*]\s*([^\n]+)"
        highlights = re.findall(highlight_pattern, project_text)

        projects.append(ProjectInfo(
            name=project_name,
            description=project_text[:200],  # 截取前200字符
            technologies=technologies,
            highlights=highlights[:3],  # 最多3个亮点
        ))

    return projects


def _extract_education(text: str) -> list[EducationInfo]:
    """从文本中提取教育经历"""
    education = []

    # 教育模式
    education_pattern = r"(?:学校|大学|学院)[：:]\s*([^\n]+)"
    matches = re.finditer(education_pattern, text)

    for match in matches:
        school_text = match.group(1).strip()

        # 尝试提取学历和专业
        degree_major_pattern = r"(本科|硕士|博士|研究生)[^\n]*([^\n]+)"
        degree_match = re.search(degree_major_pattern, school_text + text[match.end():match.end()+200])

        if degree_match:
            degree = degree_match.group(1)
            major = degree_match.group(2).strip() if degree_match.group(2) else "未知专业"
        else:
            degree = "未知学历"
            major = "未知专业"

        education.append(EducationInfo(
            school=school_text[:50],
            degree=degree,
            major=major,
        ))

    return education


def _extract_work_experience(text: str) -> list[WorkExperience]:
    """从文本中提取工作经历"""
    experience = []

    # 公司模式
    company_pattern = r"(?:公司|企业)[：:]\s*([^\n]+)"
    matches = re.finditer(company_pattern, text)

    for match in matches:
        company_text = match.group(1).strip()
        start_pos = match.start()

        # 尝试获取职位和描述
        end_pos = min(start_pos + 300, len(text))
        exp_text = text[start_pos:end_pos]

        # 提取职位
        position_pattern = r"(?:职位|岗位)[：:]\s*([^\n]+)"
        position_match = re.search(position_pattern, exp_text)
        position = position_match.group(1).strip() if position_match else "未知职位"

        experience.append(WorkExperience(
            company=company_text[:50],
            position=position,
            duration="",  # TODO: 提取时长
            description=exp_text[:200],
        ))

    return experience


# =============================================================================
# Resume Parser
# =============================================================================

class ResumeParser:
    """
    简历解析器

    支持 PDF 格式简历的解析
    """

    def __init__(self):
        """初始化解析器"""
        pass

    async def aparse(self, file_path: str) -> ResumeInfo:
        """
        异步解析简历

        Args:
            file_path: 简历文件路径

        Returns:
            解析后的简历信息
        """
        # 读取 PDF
        text = await self._read_pdf(file_path)

        # 解析各个部分
        resume_info = ResumeInfo(
            raw_text=text,
            file_path=file_path,
        )

        # 提取基本信息
        resume_info.name = self._extract_name(text)
        resume_info.email = self._extract_email(text)
        resume_info.phone = self._extract_phone(text)

        # 提取技能
        resume_info.skills = _extract_skills_from_text(text)
        resume_info.skill_categories = _categorize_skills(resume_info.skills)

        # 提取项目
        resume_info.projects = _extract_projects(text)

        # 提取教育
        resume_info.education = _extract_education(text)

        # 提取工作经历
        resume_info.work_experience = _extract_work_experience(text)

        return resume_info

    async def _read_pdf(self, file_path: str) -> str:
        """
        读取 PDF 文件

        Args:
            file_path: PDF 文件路径

        Returns:
            提取的文本内容
        """
        try:
            reader = PdfReader(file_path)
            text_parts = []

            for page in reader.pages:
                text_parts.append(page.extract_text())

            return "\n".join(text_parts)
        except Exception as e:
            # TODO: 添加日志
            return ""

    async def _read_pdf_bytes(self, pdf_bytes: bytes) -> str:
        """
        从字节流读取 PDF

        Args:
            pdf_bytes: PDF 文件字节

        Returns:
            提取的文本内容
        """
        try:
            reader = PdfReader(BytesIO(pdf_bytes))
            text_parts = []

            for page in reader.pages:
                text_parts.append(page.extract_text())

            return "\n".join(text_parts)
        except Exception:
            return ""

    def _extract_name(self, text: str) -> Optional[str]:
        """提取姓名"""
        # 常见模式：姓名的下一行通常是联系方式
        lines = text.split("\n")
        for i, line in enumerate(lines):
            if any(x in line for x in ["姓名", "名字", "Name"]):
                if i + 1 < len(lines):
                    return lines[i + 1].strip()[:20]

        # 假设第一行是姓名
        if lines and lines[0].strip():
            return lines[0].strip()[:20]

        return None

    def _extract_email(self, text: str) -> Optional[str]:
        """提取邮箱"""
        email_pattern = r"[\w\.-]+@[\w\.-]+\.\w+"
        match = re.search(email_pattern, text)
        return match.group(0) if match else None

    def _extract_phone(self, text: str) -> Optional[str]:
        """提取电话号码"""
        phone_pattern = r"1[3-9]\d{9}"
        match = re.search(phone_pattern, text)
        return match.group(0) if match else None


# =============================================================================
# LLM Enhanced Parser (Optional)
# =============================================================================

class LLMEnhancedResumeParser(ResumeParser):
    """
    LLM 增强的简历解析器

    使用大模型进一步理解和结构化简历信息
    """

    def __init__(self, llm):
        """
        初始化

        Args:
            llm: LangChain LLM 实例
        """
        super().__init__()
        self.llm = llm

    async def enhance_parse(self, resume_info: ResumeInfo) -> ResumeInfo:
        """
        使用 LLM 增强解析

        Args:
            resume_info: 基础解析结果

        Returns:
            增强后的简历信息
        """
        # TODO: 使用 LLM 进一步解析和完善简历信息
        # prompt = f"请分析和结构化以下简历信息：\n{resume_info.raw_text}"
        # response = await self.llm.ainvoke(prompt)

        return resume_info
