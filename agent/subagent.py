"""子 agent（s06）：一个全新的嵌套循环，只把最终文本交回父 agent。

上下文隔离的关键是 messages 从空开始 —— 父 agent 的历史一条都不带。
"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage
from langchain_core.tools import tool

from .config import ENVIRONMENT_PROMPT, WORKDIR, llm
from .hooks import trigger_hooks
from .tools import BASE_TOOLS

# 子 agent 的 system 更短：它只负责完成一件事并交回结论，不需要技能清单
SUB_SYSTEM = (
    f"You are a coding agent at {WORKDIR}. Environment: {ENVIRONMENT_PROMPT}. "
    "Complete the given task, then return a concise final answer."
)

# 子 agent 只给 5 个基础工具：
# - 不给 task：防止子 agent 再委派，无限递归
# - 不给 todo_write：TODO 是模块级单例，子 agent 会覆盖父 agent 的计划
SUB_TOOLS = list(BASE_TOOLS)
SUB_TOOL_MAP = {t.name: t for t in SUB_TOOLS}
sub_llm_with_tools = llm.bind_tools(SUB_TOOLS)


def run_subagent(prompt: str) -> str:
    """跑一个全新的嵌套循环：全新 messages，只有最终文本回到父循环。"""
    print("\n\033[35m[Subagent started]\033[0m")
    # 全新 messages：父 agent 的历史一条都不带，这是上下文隔离的关键
    messages: list = [HumanMessage(content=prompt)]

    # 最多 30 轮，防止子 agent 卡在循环里出不来
    for _ in range(30):
        ai = sub_llm_with_tools.invoke([SystemMessage(SUB_SYSTEM), *messages])
        messages.append(ai)

        if not ai.tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append(HumanMessage(content=force))
                continue
            # 没有工具调用 = 子任务结束，只把最终文本交回父 agent
            print("\033[35m[Subagent done]\033[0m")
            # OpenAI 下 content 通常是字符串，少数 provider 会给块列表，这里两种都兜住
            text = ai.content if isinstance(ai.content, str) else "\n".join(
                b.get("text", "") for b in ai.content if isinstance(b, dict))
            return text.strip() or "(no summary)"

        for tool_call in ai.tool_calls:
            # 子 agent 和父 agent 走同一套权限 / 生命周期 hooks
            blocked = trigger_hooks("PreToolUse", tool_call)
            if blocked:
                messages.append(ToolMessage(str(blocked), tool_call_id=tool_call["id"],
                                            name=tool_call["name"]))
                continue
            handler = SUB_TOOL_MAP.get(tool_call["name"])
            output = handler.invoke(tool_call["args"]) if handler else f"Unknown: {tool_call['name']}"
            print(f"  \033[90m[sub] {tool_call['name']}: {str(output)[:100]}\033[0m")
            trigger_hooks("PostToolUse", tool_call, output)
            messages.append(ToolMessage(str(output), tool_call_id=tool_call["id"],
                                        name=tool_call["name"]))

    print("\033[35m[Subagent stopped]\033[0m")
    return "Subagent stopped after 30 turns without a final answer."


# 父 agent 通过 task 委派；子 agent 的工具表里没有 task，所以不会无限递归
@tool("task")
def run_task(prompt: str) -> str:
    """Run a subagent with fresh conversation context and return its final text."""
    return run_subagent(prompt)
