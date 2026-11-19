"""agent 包：s01~s07 累积实现的模块化版本。

从项目根目录运行：

    python -m agent

原单文件版本保留在 s01_agent_loop/code_test.py，两个文件行为一致，
可以逐区块对照阅读。

# ===== 协议速查：本包是 OpenAI 写法（LangChain 封装），不是仓库原生的 Anthropic 写法 =====
# 1) 系统提示词：OpenAI 放 messages 第一条 -> SystemMessage；Anthropic 才是 create(system=...)
# 2) 工具定义：OpenAI 用 "parameters"；Anthropic 用 "input_schema"
# 3) 工具调用：OpenAI 在 ai.tool_calls（args 已是 dict）；Anthropic 在 content 的 {"type":"tool_use"}
# 4) 工具结果：OpenAI 每个结果一条 ToolMessage（role="tool"）；
#              Anthropic 是 user 消息里的 {"type":"tool_result", "tool_use_id": ...}
# 5) 提醒/续写：OpenAI 用独立的 HumanMessage；Anthropic 才能塞 {"type":"text"} 进 tool_result 数组
# 6) 结束原因：OpenAI "stop"/"tool_calls"；Anthropic "end_turn"/"tool_use"
# 抄 s01~s17 原生代码时，搜 "tool_use" / "tool_result" / "input_schema"，命中即需改成本包写法
"""
