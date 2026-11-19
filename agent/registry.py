"""工具注册表：把各部分定义的工具汇总成父 agent 的 TOOLS / TOOL_MAP。

单独成文件是为了打断循环导入：tools.py 定义基础工具，subagent.py 要用它们，
而父 agent 的工具表又包含 subagent 里的 task。聚合放在这里，依赖方向才是单向的。
"""

from .config import llm
from .skills import run_load_skill
from .subagent import run_task
from .todo import run_todo_write
from .tools import BASE_TOOLS

# 父 agent 的工具：基础 5 个 + todo + task + load_skill
TOOLS = [*BASE_TOOLS, run_todo_write, run_task, run_load_skill]
TOOL_MAP = {t.name: t for t in TOOLS}
llm_with_tools = llm.bind_tools(TOOLS)
