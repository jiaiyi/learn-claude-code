"""主循环：调模型 -> 执行工具 -> 把结果喂回模型，直到模型不再调用工具。"""

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from .hooks import trigger_hooks
from .prompt import SYSTEM
from .registry import TOOL_MAP, llm_with_tools


def agent_loop(messages: list):
    """agent 主循环：调模型 -> 执行工具 -> 把结果喂回模型，直到模型不再调用工具。
    注意：LangChain(openai provider) 下工具调用在 ai.tool_calls，不在 content 块里。"""
    rounds_since_todo = 0
    while True:
        # 带上系统提示词和全部历史消息调用模型
        ai = llm_with_tools.invoke([SystemMessage(SYSTEM), *messages])
        # 调试行：stop_reason 藏在 response_metadata
        print(f"\033[90m[debug] stop_reason={ai.response_metadata.get('finish_reason')}, "
              f"tool_calls={getattr(ai, 'tool_calls', None)}\033[0m")

        # 关键：必须把 AIMessage 对象本身塞回历史，不能用 dict —— dict 会丢掉 tool_calls，
        # 下一轮模型就看不到"自己调过工具"，协议会直接报错
        messages.append(ai)

        # 模型没有再调用工具，说明任务完成，退出循环
        if not ai.tool_calls:
            force = trigger_hooks("Stop", messages)
            if force:
                messages.append(HumanMessage(content=force))
                continue
            return

        # OpenAI 协议：每个工具结果对应一条 ToolMessage（role="tool"），
        # 不能用 Anthropic 的 {"type": "tool_result"} 块
        used_todo = False
        for tool_call in ai.tool_calls:
            # tool_call 是 dict：{"name": ..., "args": {...}, "id": ...}
            # 黄色高亮打印本次工具调用
            print(f"\033[33m> {tool_call['name']} {tool_call['args']}\033[0m")

            # s04 改动：执行前先走 hook 权限流水线
            blocked = trigger_hooks("PreToolUse", tool_call)
            if blocked:
                messages.append(ToolMessage(str(blocked), tool_call_id=tool_call["id"],
                                            name=tool_call["name"]))
                continue

            # 按名字找到工具处理函数并执行
            handler = TOOL_MAP.get(tool_call["name"])
            output = handler.invoke(tool_call["args"]) if handler else f"Unknown: {tool_call['name']}"

            # 控制台只预览结果前 200 字符
            print(str(output)[:200])
            trigger_hooks("PostToolUse", tool_call, output)
            if tool_call["name"] == "todo_write":
                used_todo = True
            messages.append(ToolMessage(str(output), tool_call_id=tool_call["id"],
                                        name=tool_call["name"]))

        rounds_since_todo = 0 if used_todo else rounds_since_todo + 1
        if rounds_since_todo >= 3:
            messages.append(HumanMessage("<reminder>Update your todos.</reminder>"))
            rounds_since_todo = 0
