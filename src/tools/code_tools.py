"""
Code Parsing Tools for AI Interview Agent

用于解析简历中的项目源代码
"""

import os
import json
from pathlib import Path
from typing import Optional
from dataclasses import dataclass


# =============================================================================
# Data Classes
# =============================================================================

@dataclass
class ModuleInfo:
    """模块信息"""
    name: str
    path: str
    language: str
    functions: list[str]
    classes: list[str]
    dependencies: list[str]


@dataclass
class ProjectInfo:
    """项目信息"""
    name: str
    path: str
    language: str
    readme_content: Optional[str]
    architecture_files: list[str]
    modules: list[ModuleInfo]
    tech_stack: list[str]


@dataclass
class ArchitectureInfo:
    """架构信息"""
    description: str
    diagram_path: Optional[str]
    components: list[str]
    data_flow: str
    tech_choices: dict[str, str]  # 技术选型及理由


# =============================================================================
# File System Operations
# =============================================================================

def get_file_extension(path: str) -> str:
    """获取文件扩展名"""
    return Path(path).suffix.lower()


def is_text_file(path: str) -> bool:
    """判断是否为文本文件"""
    text_extensions = {
        ".py", ".java", ".js", ".ts", ".jsx", ".tsx",
        ".go", ".rs", ".c", ".cpp", ".h", ".hpp",
        ".cs", ".rb", ".php", ".swift", ".kt",
        ".md", ".txt", ".json", ".yaml", ".yml",
        ".xml", ".sql", ".sh", ".bash",
    }
    return get_file_extension(path) in text_extensions


def read_file_content(path: str, max_size: int = 1024 * 1024) -> Optional[str]:
    """
    读取文件内容

    Args:
        path: 文件路径
        max_size: 最大文件大小（字节）

    Returns:
        文件内容或 None
    """
    try:
        if not os.path.exists(path):
            return None

        file_size = os.path.getsize(path)
        if file_size > max_size:
            return None  # 文件过大

        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()
    except Exception:
        return None


# =============================================================================
# Code Parsing Functions
# =============================================================================

async def parse_source_code(
    code_path: str,
    language: Optional[str] = None
) -> list[ModuleInfo]:
    """
    解析源代码目录

    Args:
        code_path: 代码目录路径
        language: 编程语言（可选，自动检测）

    Returns:
        模块信息列表
    """
    if not os.path.exists(code_path) or not os.path.isdir(code_path):
        return []

    modules = []

    # 如果未指定语言，尝试从文件推断
    if not language:
        language = _detect_language(code_path)

    # 遍历目录
    for root, dirs, files in os.walk(code_path):
        # 跳过隐藏目录和常见非源码目录
        dirs[:] = [
            d for d in dirs
            if not d.startswith(".")
            and d not in {"node_modules", "__pycache__", "venv", ".venv", "target", "build"}
        ]

        for file in files:
            if not is_text_file(file):
                continue

            file_path = os.path.join(root, file)
            content = read_file_content(file_path)

            if not content:
                continue

            module_info = _parse_file(content, file_path, language)
            if module_info:
                modules.append(module_info)

    return modules


def _detect_language(code_path: str) -> str:
    """检测编程语言"""
    extensions = {}
    for root, _, files in os.walk(code_path):
        for file in files:
            ext = get_file_extension(file)
            if ext:
                extensions[ext] = extensions.get(ext, 0) + 1

    # 常见语言映射
    lang_map = {
        ".py": "Python",
        ".java": "Java",
        ".js": "JavaScript",
        ".ts": "TypeScript",
        ".go": "Go",
        ".rs": "Rust",
        ".cpp": "C++",
        ".c": "C",
        ".cs": "C#",
        ".rb": "Ruby",
        ".php": "PHP",
        ".swift": "Swift",
        ".kt": "Kotlin",
    }

    if not extensions:
        return "Unknown"

    # 返回出现最多的扩展名对应的语言
    most_common_ext = max(extensions.items(), key=lambda x: x[1])[0]
    return lang_map.get(most_common_ext, "Unknown")


def _parse_file(content: str, file_path: str, language: str) -> Optional[ModuleInfo]:
    """解析单个文件"""
    try:
        name = os.path.splitext(os.path.basename(file_path))[0]

        functions = _extract_functions(content, language)
        classes = _extract_classes(content, language)
        deps = _extract_dependencies(content, language)

        return ModuleInfo(
            name=name,
            path=file_path,
            language=language,
            functions=functions,
            classes=classes,
            dependencies=deps,
        )
    except Exception:
        return None


def _extract_functions(content: str, language: str) -> list[str]:
    """提取函数名"""
    functions = []

    if language == "Python":
        import re
        pattern = r"^def\s+(\w+)\s*\("
        for line in content.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                functions.append(match.group(1))

    elif language in ("Java", "JavaScript", "TypeScript", "C#"):
        import re
        pattern = r"(?:public|private|protected)?\s*(?:static)?\s*\w+\s+(\w+)\s*\("
        for line in content.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                functions.append(match.group(1))

    return functions


def _extract_classes(content: str, language: str) -> list[str]:
    """提取类名"""
    classes = []

    if language == "Python":
        import re
        pattern = r"^class\s+(\w+)"
        for line in content.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                classes.append(match.group(1))

    elif language in ("Java", "JavaScript", "TypeScript", "C#"):
        import re
        pattern = r"class\s+(\w+)"
        for match in re.finditer(pattern, content):
            classes.append(match.group(1))

    return classes


def _extract_dependencies(content: str, language: str) -> list[str]:
    """提取依赖"""
    deps = []

    if language == "Python":
        import re
        # import xxx 或 from xxx import
        pattern = r"^(?:import\s+|from\s+)(\w+)"
        for line in content.split("\n"):
            match = re.match(pattern, line.strip())
            if match:
                deps.append(match.group(1))

    elif language in ("Java", "JavaScript", "TypeScript"):
        # 简单的 import 语句提取
        import re
        pattern = r"import\s+.*?(\w+);"
        for match in re.finditer(pattern, content):
            deps.append(match.group(1))

    return list(set(deps))  # 去重


# =============================================================================
# Project Level Parsing
# =============================================================================

async def extract_project_info(
    project_path: str,
    project_name: str
) -> ProjectInfo:
    """
    提取项目级信息

    Args:
        project_path: 项目路径
        project_name: 项目名称

    Returns:
        项目信息
    """
    # 读取 README
    readme_content = None
    for readme_name in ["README.md", "README.txt", "readme.md"]:
        readme_path = os.path.join(project_path, readme_name)
        readme_content = read_file_content(readme_path)
        if readme_content:
            break

    # 查找架构文件
    architecture_files = []
    for root, _, files in os.walk(project_path):
        for file in files:
            if any(x in file.lower() for x in ["architecture", "diagram", "schema"]):
                architecture_files.append(os.path.join(root, file))

    # 解析模块
    modules = await parse_source_code(project_path)

    # 检测技术栈
    tech_stack = _detect_tech_stack(project_path)

    return ProjectInfo(
        name=project_name,
        path=project_path,
        language=_detect_language(project_path),
        readme_content=readme_content,
        architecture_files=architecture_files,
        modules=modules,
        tech_stack=tech_stack,
    )


def _detect_tech_stack(project_path: str) -> list[str]:
    """检测技术栈"""
    tech_stack = []

    # 检测配置文件
    config_files = {
        "requirements.txt": "Python",
        "package.json": "Node.js",
        "pom.xml": "Java (Maven)",
        "build.gradle": "Java (Gradle)",
        "go.mod": "Go",
        "Cargo.toml": "Rust",
        "composer.json": "PHP",
    }

    for file, tech in config_files.items():
        if os.path.exists(os.path.join(project_path, file)):
            tech_stack.append(tech)

    return tech_stack


async def extract_architecture(
    project_path: str
) -> ArchitectureInfo:
    """
    提取架构信息

    Args:
        project_path: 项目路径

    Returns:
        架构信息
    """
    # 查找架构文档
    arch_doc = None
    arch_path = None
    for root, _, files in os.walk(project_path):
        for file in files:
            if "architecture" in file.lower() or "design" in file.lower():
                if file.endswith((".md", ".txt", ".drawio", ".png")):
                    arch_path = os.path.join(root, file)
                    arch_doc = read_file_content(arch_path)
                    break

    # TODO: 解析架构图
    # 目前只返回基本描述

    return ArchitectureInfo(
        description=arch_doc or "未找到架构文档",
        diagram_path=arch_path,
        components=[],  # TODO: 从架构文档解析
        data_flow="",   # TODO: 从架构文档解析
        tech_choices={},  # TODO: 从架构文档解析
    )


# =============================================================================
# Module Structure Extraction
# =============================================================================

async def extract_module_structure(
    project_path: str
) -> dict:
    """
    提取模块结构

    Args:
        project_path: 项目路径

    Returns:
        模块结构字典
    """
    modules = await parse_source_code(project_path)

    structure = {
        "modules": [],
        "total_functions": 0,
        "total_classes": 0,
    }

    for module in modules:
        structure["modules"].append({
            "name": module.name,
            "path": module.path,
            "functions": module.functions,
            "classes": module.classes,
            "dependencies": module.dependencies,
        })
        structure["total_functions"] += len(module.functions)
        structure["total_classes"] += len(module.classes)

    return structure
