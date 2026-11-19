"""技能加载（s07）：扫描 skills/*/SKILL.md，按需加载正文。

技能采用"渐进式加载"：启动时只把 name/description 放进系统提示词，
模型需要时再调 load_skill 取完整 SKILL.md，避免一开始就把上下文占满。
"""

from pathlib import Path

import yaml
from langchain_core.tools import tool

from .config import SKILLS_DIR


class SkillLoader:
    """扫描 skills/*/SKILL.md，启动时只缓存元信息，正文等模型按需加载。"""

    def __init__(self, skills_dir: Path):
        self.skills_dir = skills_dir
        self.skills: dict[str, dict[str, str]] = {}
        self.scan()

    @staticmethod
    def parse_frontmatter(text: str) -> tuple[dict, str]:
        """把 SKILL.md 拆成 frontmatter(YAML 元信息) 和 body(正文)。

        没写 frontmatter 或格式不对时返回 ({}, 原文)，由调用方兜底。
        """
        lines = text.splitlines(keepends=True)
        if not lines or lines[0].rstrip("\r\n") != "---":
            return {}, text
        closing_index = next(
            (index for index, line in enumerate(lines[1:], start=1) if line.rstrip("\r\n") == "---"),
            None,
        )
        if closing_index is None:
            return {}, text

        frontmatter = "".join(lines[1:closing_index])
        body = "".join(lines[closing_index + 1:]).strip()
        try:
            metadata = yaml.safe_load(frontmatter) or {}
        except yaml.YAMLError:
            metadata = {}
        if not isinstance(metadata, dict):
            metadata = {}
        return metadata, body

    def scan(self):
        """清空并重建索引：key 是技能名，value 存 name/description/content。"""
        self.skills.clear()
        if not self.skills_dir.exists():
            return

        skills_root = self.skills_dir.resolve()
        for manifest in sorted(self.skills_dir.glob("*/SKILL.md")):
            if not manifest.is_file() or not manifest.resolve().is_relative_to(skills_root):
                continue
            content = manifest.read_text(encoding="utf-8")
            metadata, body = self.parse_frontmatter(content)
            raw_name = metadata.get("name")
            name = raw_name.strip() if isinstance(raw_name, str) else ""
            name = name or manifest.parent.name
            raw_description = metadata.get("description")
            description = raw_description if isinstance(raw_description, str) else ""
            description = description or body.split("\n", 1)[0]
            description = " ".join(str(description).lstrip("# ").split())
            self.skills[name] = {
                "name": name,
                "description": description,
                "content": content,
            }

    def catalog(self) -> str:
        """给系统提示词用的清单：只有名字和简介，不含正文。"""
        if not self.skills:
            return "(no skills found)"
        return "\n".join(
            f"- {skill['name']}: {skill['description']}" for skill in self.skills.values()
        )

    def load(self, name: str) -> str:
        """按名字取完整 SKILL.md；找不到时返回错误和可选项，方便模型自我纠正。"""
        skill = self.skills.get(name)
        if skill:
            return skill["content"]
        available = ", ".join(self.skills) or "none"
        return f"Error: Unknown skill '{name}'. Available: {available}"


# 导入时扫描一次；之后新增的技能要重启进程才会出现在清单里
SKILL_LOADER = SkillLoader(SKILLS_DIR)


# -- 技能工具（s07） --

@tool("load_skill")
def run_load_skill(name: str) -> str:
    """Load the full SKILL.md content by skill name."""
    return SKILL_LOADER.load(name)
