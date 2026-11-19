"""权限判断（s03）：拒绝名单 + 规则表 + 终端询问。

这里只有"判断逻辑"，真正的调用时机在 hooks.py 的 PreToolUse 里。
"""

import re

from .config import WORKDIR

# 第一关：硬拒绝名单 —— 命中即直接禁止，不询问
DENY_LIST = ["rm -rf /", "sudo", "shutdown", "reboot", "mkfs", "dd if=", "> /dev/sda"]


def check_deny_list(command: str) -> str | None:
    """检查命令是否命中拒绝名单；命中返回拦截原因，否则返回 None。"""
    for pattern in DENY_LIST:
        if pattern in command:
            return f"Blocked: '{pattern}' is on the deny list"
    return None


# 危险命令词正则：匹配作为独立命令出现的 rm / del（前面是开头或分隔符）
DESTRUCTIVE_COMMAND_WORD = re.compile(
    r"(?i)(?:^|[;&|()\n])\s*(?:rm|del)(?=\s|$|[;&|()])"
)


def contains_destructive_command(command: str) -> bool:
    """判断命令里是否包含独立的删除类命令（rm / del）。"""
    return bool(DESTRUCTIVE_COMMAND_WORD.search(command))


# 规则表：针对特定工具的检查函数，命中则要求用户确认
# 注意：工具名必须和 registry.TOOLS 里注册的一致（run_bash / run_read / ...）
PERMISSION_RULES = [
    # 文件写入类工具：路径越出工作区就要求确认
    {"tools": ["run_read", "run_write", "run_edit"],
     "check": lambda args: not (WORKDIR / args.get("path", "")).resolve().is_relative_to(WORKDIR),
     "message": "Writing outside workspace"},
    # bash 工具：包含删除命令或危险关键词就要求确认
    {"tools": ["run_bash"],
     "check": lambda args: contains_destructive_command(args.get("command", "")) or
     any(kw in args.get("command", "") for kw in ["rm ", "> /etc/", "chmod 777"]),
     "message": "Potentially destructive command"},
]


def check_rules(tool_name: str, args: dict) -> str | None:
    """按规则表逐条检查；命中返回该规则的提示信息，否则返回 None。"""
    for rule in PERMISSION_RULES:
        if tool_name in rule["tools"] and rule["check"](args):
            return rule["message"]
    return None


def ask_rules(tool_name: str, args: dict, reason: str) -> str:
    """第二关：在终端询问用户是否放行，返回 'allow' 或 'deny'。"""
    # 黄色高亮打印拦截原因和工具调用详情
    print(f"\n\033[33m[permission] {reason}\033[0m")
    print(f"   Tool: {tool_name}({args})")
    choice = input("   Allow? [y/N] ").strip().lower()
    return "allow" if choice in ("y", "yes") else "deny"
