"""系统提示词：身份 + 环境 + 技能清单（只放名字和描述，不放正文）。"""

from .config import ENVIRONMENT_PROMPT, WORKDIR
from .skills import SKILL_LOADER


def build_system_prompt() -> str:
    """系统提示词 = 身份 + 环境 + 技能清单（只放名字和描述，不放正文）。"""
    return (
        f"You are a coding agent at {WORKDIR}. Environment: {ENVIRONMENT_PROMPT}. "
        "Use tools to solve tasks. "
        "Act, don't explain.\n\n"
        f"Skills available:\n{SKILL_LOADER.catalog()}\n\n"
        "Use load_skill to read the full instructions when a skill applies."
    )


SYSTEM = build_system_prompt()
