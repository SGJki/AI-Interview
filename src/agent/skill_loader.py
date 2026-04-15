"""
Context-Aware Skill Loader for AI Interview Agents

按上下文动态加载 Skill，支持 phase/action/condition 三种触发条件。
"""

import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional
import yaml


@dataclass
class Skill:
    """Skill 元数据"""
    name: str
    description: str
    version: str = "1.0.0"
    agent: str = ""  # common 表示通用
    triggers: list[dict] = field(default_factory=list)
    content: str = ""


class ContextAwareSkillLoader:
    """按上下文动态加载 Skill"""

    def __init__(self, skills_dir: Optional[Path] = None):
        if skills_dir is None:
            # 默认使用 src/agent/skills 目录
            skills_dir = Path(__file__).parent / "skills"
        self.skills_dir = skills_dir
        self._skill_cache: dict[str, Skill] = {}

    def load_skill(self, agent: str, skill_path: str) -> Optional[Skill]:
        """加载指定 Skill"""
        skill_file = self.skills_dir / agent / skill_path / "SKILL.md"
        if not skill_file.exists():
            skill_file = self.skills_dir / agent / f"{skill_path}.md"
        if not skill_file.exists():
            return None
        return self._parse_skill(skill_file)

    def load_common_skill(self, skill_name: str) -> Optional[Skill]:
        """加载通用技能"""
        return self.load_skill("common", skill_name)

    def get_skills_for_context(
        self,
        agent: str,
        phase: str,
        action: Optional[str] = None,
        state: Optional[dict] = None,
    ) -> list[Skill]:
        """
        根据当前上下文获取匹配的 Skills

        1. 加载 Common Skills（始终可用）
        2. 加载 Agent 专属 Skills
        3. 根据 triggers 过滤
        """
        skills = []
        state = state or {}

        # 1. Common Skills - 按 triggers 匹配
        common_dir = self.skills_dir / "common"
        if common_dir.exists():
            skills.extend(self._load_matching_skills(common_dir, phase, action, state))

        # 2. Agent 专属 Skills
        agent_dir = self.skills_dir / agent
        if agent_dir.exists():
            skills.extend(self._load_matching_skills(agent_dir, phase, action, state))

        return skills

    def _load_matching_skills(
        self,
        skill_dir: Path,
        phase: str,
        action: Optional[str],
        state: dict,
    ) -> list[Skill]:
        """根据 triggers 匹配加载 Skills"""
        matched = []
        for skill_file in skill_dir.glob("**/SKILL.md"):
            skill = self._parse_skill(skill_file)
            if self._matches_triggers(skill, phase, action, state):
                matched.append(skill)
        return matched

    def _parse_skill(self, skill_file: Path) -> Skill:
        """解析 SKILL.md 文件"""
        cache_key = str(skill_file.absolute())
        if cache_key in self._skill_cache:
            return self._skill_cache[cache_key]

        content = skill_file.read_text(encoding="utf-8")
        skill = self._parse_skill_content(content, skill_file.parent.name)

        # 提取 relative path 作为 agent 标识
        relative = skill_file.parent.relative_to(self.skills_dir)
        skill.agent = str(relative.parent.name) if relative.parent != relative else "common"

        self._skill_cache[cache_key] = skill
        return skill

    def _parse_skill_content(self, content: str, default_agent: str = "") -> Skill:
        """解析 Skill 内容和 frontmatter"""
        # 解析 YAML frontmatter
        frontmatter = {}
        skill_content = content

        if content.startswith("---"):
            parts = content.split("---", 2)
            if len(parts) >= 3:
                try:
                    frontmatter = yaml.safe_load(parts[1]) or {}
                    skill_content = parts[2].strip()
                except yaml.YAMLError:
                    skill_content = content

        return Skill(
            name=frontmatter.get("name", "unnamed"),
            description=frontmatter.get("description", ""),
            version=frontmatter.get("version", "1.0.0"),
            agent=frontmatter.get("agent", default_agent),
            triggers=frontmatter.get("triggers", []),
            content=skill_content.strip(),
        )

    def _matches_triggers(self, skill: Skill, phase: str, action: str, state: dict) -> bool:
        """检查 Skill 是否匹配当前上下文"""
        if not skill.triggers:
            # 无 triggers 的 Skill 默认不匹配（需要显式指定）
            return False

        for trigger in skill.triggers:
            if "phase" in trigger and trigger["phase"] == phase:
                return True
            if "action" in trigger and trigger["action"] == action:
                return True
            if "condition" in trigger and self._eval_condition(trigger["condition"], state):
                return True

        return False

    def _eval_condition(self, condition: str, state: dict) -> bool:
        """评估条件表达式"""
        try:
            # 安全评估：只支持简单的比较操作
            # 支持的变量: state 中的所有键
            # 示例: "state.error_count > 0", "state.phase == 'init'"
            local_vars = {"state": state}
            # 替换 state.xxx 为 local_vars 中的值
            expr = condition
            for key, value in state.items():
                expr = expr.replace(f"state.{key}", repr(value))

            return eval(expr, {"__builtins__": {}}, local_vars)
        except Exception:
            return False

    def inject_skills_to_prompt(
        self,
        agent: str,
        phase: str,
        action: str,
        state: Optional[dict] = None,
        base_prompt: str = "",
    ) -> str:
        """将匹配的 Skills 注入到 prompt"""
        skills = self.get_skills_for_context(agent, phase, action, state)
        if not skills:
            return base_prompt

        skill_section = "\n\n## 参考方法论（按需使用）\n"
        for skill in skills:
            skill_section += f"\n### [{skill.agent}] {skill.name}\n{skill.content}\n"

        return base_prompt + skill_section

    def get_all_skills(self, agent: Optional[str] = None) -> list[Skill]:
        """获取所有 Skills 或指定 Agent 的 Skills"""
        skills = []
        search_dir = self.skills_dir / agent if agent else self.skills_dir

        if not search_dir.exists():
            return skills

        for skill_file in search_dir.glob("**/SKILL.md"):
            skills.append(self._parse_skill(skill_file))

        return skills

    def list_agents(self) -> list[str]:
        """列出所有有 Skills 的 Agent"""
        agents = []
        for item in self.skills_dir.iterdir():
            if item.is_dir() and item.name != "common":
                agents.append(item.name)
        return sorted(agents)


# 全局单例
_global_loader: Optional[ContextAwareSkillLoader] = None


def get_skill_loader() -> ContextAwareSkillLoader:
    """获取全局 SkillLoader 单例"""
    global _global_loader
    if _global_loader is None:
        _global_loader = ContextAwareSkillLoader()
    return _global_loader


# ============================================================================
# Agent 集成助手
# ============================================================================

def skill_aware_prompt(
    agent: str,
    phase: str,
    action: str,
    base_prompt: str,
    state: Optional[dict] = None,
) -> str:
    """
    为 Agent 生成带 Skills 的增强 prompt

    用法:
        prompt = skill_aware_prompt(
            agent="question",
            phase=state.phase,
            action="generate_question",
            base_prompt=original_prompt,
            state=asdict(state),
        )
    """
    loader = get_skill_loader()
    return loader.inject_skills_to_prompt(
        agent=agent,
        phase=phase,
        action=action,
        state=state,
        base_prompt=base_prompt,
    )


class SkillContext:
    """
    Agent Skill 上下文管理器

    用法:
        with SkillContext("question", state) as ctx:
            prompt = ctx.enhance(base_prompt)
    """

    def __init__(self, agent: str, phase: str, action: str = ""):
        self.agent = agent
        self.phase = phase
        self.action = action
        self.state: dict = {}
        self._loader = get_skill_loader()

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def set_state(self, state: dict):
        """设置状态用于 condition 匹配"""
        self.state = state
        return self

    def enhance(self, prompt: str, action: Optional[str] = None) -> str:
        """增强 prompt，注入匹配的 Skills"""
        return self._loader.inject_skills_to_prompt(
            agent=self.agent,
            phase=self.phase,
            action=action or self.action,
            state=self.state,
            base_prompt=prompt,
        )
