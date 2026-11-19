"""计划管理（s05）：TodoManager + todo_write 工具。

TODO 是模块级单例，所以子 agent 的工具表里故意不给它 —— 否则会覆盖父 agent 的计划。
"""

import ast
import json

from langchain_core.tools import tool


class TodoManager:
    def __init__(self):
        self.items: list[dict] = []

    def update(self, todos: list | str) -> str:
        if isinstance(todos, str):
            try:
                todos = json.loads(todos)
            except json.JSONDecodeError:
                try:
                    todos = ast.literal_eval(todos)
                except (SyntaxError, ValueError):
                    raise ValueError("todos必须是一个列表或JSON数组字符串")
        if not isinstance(todos, list):
            raise ValueError("todos must be a list")
        if len(todos) > 20:
            raise ValueError("Max 20 todos allowed")

        # 替换当前列表前 进行解析和校验
        validated = []
        in_progress_count = 0
        for index, todo in enumerate(todos):
            if not isinstance(todo, dict):
                raise ValueError(f"todos[{index}] must be a object")
            content = str(todo.get("content", "")).strip()
            status = str(todo.get("status", "pending")).lower()
            if not content:
                raise ValueError(f"todos[{index}] requires content")
            if status not in ("pending", "in_progress", "completed"):
                raise ValueError(f"todos[{index}] has invalid status: {status}")
            if status == "in_progress":
                in_progress_count += 1
            validated.append({"content": content, "status": status})

        if in_progress_count > 1:
            raise ValueError("一次只能有一个待办事项在进行中")
        self.items = validated
        return self.render()

    def render(self) -> str:
        if not self.items:
            return "No todos"

        lines = []
        for todo in self.items:
            marker = {
                "pending": "[ ]",
                "in_progress": "[>]",
                "completed": "[x]",
            }[todo["status"]]
            lines.append(f"{marker} {todo['content']}")
        done = sum(todo["status"] == "completed" for todo in self.items)
        lines.append(f"\n({done}/{len(self.items)} completed)")
        return "\n".join(lines)


TODO = TodoManager()


@tool("todo_write")
def run_todo_write(todos: list | str) -> str:
    """Create and manage a task list for your current coding session."""
    try:
        output = TODO.update(todos)
    except ValueError as e:
        return f"Error: {e}"
    print(f"\n\033[33m## Current Tasks\033[0m\n{output}")
    return output
