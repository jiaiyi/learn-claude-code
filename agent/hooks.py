"""Hooks（s04）：生命周期事件注册表 + 本项目的 5 个回调。

事件顺序：
    UserPromptSubmit -> [循环: PreToolUse -> 执行工具 -> PostToolUse] -> Stop
"""

from langchain_core.messages import ToolMessage

from .config import WORKDIR
from .permissions import ask_rules, check_deny_list, check_rules

# 注册表，事件名映射到回调列表
HOOKS = {
    "UserPromptSubmit": [],  # 用户输入提交后、进入 LLM 前：输入验证、注入上下文
    "PreToolUse": [],        # 工具执行前：权限检查、日志记录
    "PostToolUse": [],       # 工具执行后：副作用（自动 git add 等）、输出检查
    "Stop": [],              # 循环即将退出时：收尾清理、决定是否继续循环
}


# 添加扩展
def register_hook(event: str, callback):
    HOOKS[event].append(callback)


# 调用扩展
def trigger_hooks(event: str, *args):
    for callback in HOOKS[event]:
        result = callback(*args)
        if result is not None:
            return result
    return None


# -- UserPromptSubmit --

def context_inject_hook(query: str) -> str | None:
    """在每个提示符中注入当前工作目录信息"""
    print(f"\033[90m[HOOK] UserPromptSubmit: working in {WORKDIR}\033[0m")
    return None  # return None = 不修改提示词，直接放行


# -- PreToolUse：权限 --

def permission_hook(tool_call: dict):
    """权限总入口：先过拒绝名单，再过规则表（需要时询问用户）。返回是否放行。
    LangChain 下 tool_call 是 dict：{"name", "args", "id"}"""
    # 第一关：bash 命令命中拒绝名单 -> 直接拦截
    if tool_call["name"] == "run_bash":
        reason = check_deny_list(tool_call["args"].get("command", ""))
        if reason:
            print(f"\033[31m[blocked] {reason}\033[0m")
            return "Permission denied by deny list"
    # 第二关：命中规则表 -> 询问用户
    reason = check_rules(tool_call["name"], tool_call["args"])
    if reason:
        decision = ask_rules(tool_call["name"], tool_call["args"], reason)
        # ask_rules 返回 "allow"/"deny"，与 s04_hooks 不同：这里是二次封装
        if decision == "deny":
            return "Permission denied by user"
    # 默认放行
    return None


# -- PreToolUse：日志 --

def log_hook(tool_call: dict):
    print(f"\033[90m[HOOK] {tool_call['name']}({str(list(tool_call['args'].values())[:2])[:60]})\033[0m")


# -- PostToolUse：大输出提醒 --

def large_output_hook(tool_call: dict, output):
    if len(str(output)) > 100000:
        print(f"\033[33m[HOOK] ⚠ Large output from {tool_call['name']}\033[0m")


# -- Stop：会话摘要 --

def summary_hook(messages: list) -> str | None:
    """统计本次会话的工具调用次数：LangChain 协议下每条工具结果是一条 ToolMessage。"""
    tool_count = sum(1 for m in messages if isinstance(m, ToolMessage))
    print(f"\033[90m[HOOK] Stop: session used {tool_count} tool calls\033[0m")
    return None  # return None = 允许终止, return string = 强制继续


register_hook("UserPromptSubmit", context_inject_hook)
register_hook("PreToolUse", permission_hook)
register_hook("PreToolUse", log_hook)
register_hook("PostToolUse", large_output_hook)
register_hook("Stop", summary_hook)
