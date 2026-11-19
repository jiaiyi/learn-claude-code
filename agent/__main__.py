"""REPL 入口：读用户输入 -> 跑 agent 循环 -> 打印最后一条回复。

运行：python -m agent
"""

from langchain_core.messages import AIMessage, HumanMessage

from .hooks import trigger_hooks
from .loop import agent_loop


def main():
    # 简单的交互式 REPL：读用户输入 -> 跑 agent 循环 -> 打印最后一条回复
    history = []
    while True:
        try:
            # \001/\002 tell Readline the ANSI escapes have zero display width.
            query = input("\001\033[36m\002agent >> \001\033[0m\002")
        except (EOFError, KeyboardInterrupt):
            break
        if not query.strip():
            continue
        if query.strip().lower() in ("q", "exit"):
            break

        # 触发 UserPromptSubmit hook（原来误写成 "Stop"）
        trigger_hooks("UserPromptSubmit", query)
        # 用 LangChain 消息类型记录用户输入
        history.append(HumanMessage(content=query))
        agent_loop(history)
        # 打印最后一条 AI 回复的文本内容
        last = history[-1]
        if isinstance(last, AIMessage) and last.content:
            print(last.content if isinstance(last.content, str)
                  else "\n".join(b.get("text", "") for b in last.content if isinstance(b, dict)))
        print()


if __name__ == "__main__":
    main()
