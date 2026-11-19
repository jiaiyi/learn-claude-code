"""基础工具（s02）：bash + 文件读写改查。

这一层只负责"怎么执行"，不做权限判断 —— 权限在 hooks 层的 PreToolUse 里。
"""

import os
import subprocess
from pathlib import Path

from langchain_core.tools import tool

from .config import WORKDIR


# -- bash --

@tool
def run_bash(command: str) -> str:
    """执行一条 shell 命令。"""
    # 简单的危险命令黑名单，命中直接拦截
    dangerous = ["rm -rf /", "sudo", "shutdown", "reboot", "> /dev/"]
    if any(d in command for d in dangerous):
        return "Error: Dangerous command blocked"
    try:
        # shell=True 交给系统 shell 执行；捕获 stdout/stderr；超时 120 秒
        r = subprocess.run(command, shell=True, cwd=os.getcwd(),
                           capture_output=True, text=True, errors="replace", timeout=120)
        # 合并 stdout 和 stderr，去掉首尾空白；空输出给占位提示
        out = (r.stdout + r.stderr).strip()
        return out[:50000] if out else "(no output)"
    except subprocess.TimeoutExpired:
        return "Error: Timeout (120s)"
    except (FileNotFoundError, OSError) as e:
        return f"Error: {e}"


# -- 文件工具（s02） --

def safe_path(p: str) -> Path:
    """把相对路径解析到工作区内，并校验不会越界逃出工作区。"""
    path = (WORKDIR / p).resolve()
    if not path.is_relative_to(WORKDIR):
        raise ValueError(f"Path escapes workspace: {p}")
    return path


@tool
def run_read(path: str, limit: int | None = None) -> str:
    """读取文本文件。读源码文件时优先用这个工具而不是 bash。"""
    try:
        # 按行读入整个文件
        lines = safe_path(path).read_text(encoding="utf-8").splitlines()
        # limit 只保留前 N 行，并提示剩余行数
        if limit and limit < len(lines):
            lines = lines[:limit] + [f"... ({len(lines) - limit} more lines)"]
        return "\n".join(lines)
    except Exception as e:
        return f"Error: {e}"


@tool
def run_write(path: str, content: str) -> str:
    """用给定内容覆盖写入文件。会自动创建父目录。"""
    try:
        file_path = safe_path(path)
        # 逐级创建父目录（已存在则跳过）
        file_path.parent.mkdir(parents=True, exist_ok=True)
        file_path.write_text(content, encoding="utf-8")
        return f"Wrote {len(content)} bytes to {path}"
    except Exception as e:
        return f"Error: {e}"


@tool
def run_edit(path: str, old_text: str, new_text: str) -> str:
    """把文件中第一处完全匹配的 old_text 替换为 new_text。小改动优先用这个而不是整文件覆写。"""
    try:
        file_path = safe_path(path)
        text = file_path.read_text(encoding="utf-8")
        # 找不到目标文本就报错，不做任何修改
        if old_text not in text:
            return f"Error: text not found in {path}"
        # 只替换第一处出现（count=1）
        file_path.write_text(text.replace(old_text, new_text, 1), encoding="utf-8")
        return f"Edited {path}"
    except Exception as e:
        return f"Error: {e}"


@tool
def run_glob(pattern: str) -> str:
    """按 glob 模式查找文件；** 表示递归匹配子目录。"""
    import glob as g
    try:
        # 在工作区内递归匹配，并再次过滤确保结果不越出工作区
        matches = sorted({
            match for match in g.glob(
                pattern, root_dir=WORKDIR, recursive=True)
            if (WORKDIR / match).resolve().is_relative_to(WORKDIR)
        })
        # 最多返回 200 条，超出则提示缩小匹配范围
        shown = matches[:200]
        if len(matches) > 200:
            shown.append("... (more matches omitted; narrow the pattern)")
        return "\n".join(shown) if shown else "(no matches)"
    except Exception as e:
        return f"Error: {e}"


# 子 agent 和父 agent 共用的基础工具表（不含 todo / task / load_skill）
BASE_TOOLS = [run_bash, run_read, run_write, run_glob, run_edit]
