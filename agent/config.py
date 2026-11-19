"""初始化与环境配置：加载 .env、创建 LLM 客户端、定位工作区。

对应 code_test.py 的 "1. 初始化" + "2. 基础配置"。
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from langchain.chat_models import init_chat_model

# 加载 .env 环境变量（verbose=True 会打印加载了哪些变量）
load_dotenv(verbose=True)

# 初始化聊天模型：从环境变量读取模型 ID / API Key / Base URL
llm = init_chat_model(
    model=os.getenv("MODEL_ID"),
    model_provider="openai",
    api_key=os.getenv("ANTHROPIC_API_KEY"),
    base_url=os.environ["ANTHROPIC_BASE_URL"].rstrip("/") + "/v1",
)

# 工作区根目录（当前工作目录），用于限制文件工具的访问范围
WORKDIR = Path.cwd()
# 技能目录相对工作区：从哪个目录启动，就在哪个目录下找 skills/
SKILLS_DIR = WORKDIR / "skills"

# 根据操作系统选择环境提示文案：Windows 下 bash 工具实际走 cmd.exe
ENVIRONMENT_PROMPT = (
    "Windows: the bash tool runs through cmd.exe; use cmd.exe syntax, not Unix "
    "Bash or PowerShell syntax, and prefer dedicated file tools for file operations"
    if os.name == "nt"
    else "Unix-like: the bash tool runs the system shell"
)
