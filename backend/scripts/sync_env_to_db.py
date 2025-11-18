"""将 .env 文件中的配置同步到数据库。

此脚本读取 .env 文件中的环境变量，并将 LLM 配置写入数据库。
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from backend.database import init_db, upsert_config
from backend.config import Config as AppConfig


def sync_env_to_db() -> None:
    """从 .env 文件读取配置并写入数据库。"""
    # 确保数据库已初始化
    init_db()
    
    # 从环境变量读取配置（.env 文件已在 config.py 中加载）
    api_key = AppConfig.get_api_key()
    base_url = AppConfig.get_base_url()
    model_name = AppConfig.get_model_name()
    temperature = AppConfig.get_temperature()
    
    # 写入数据库
    config = upsert_config(
        api_key=api_key,
        base_url=base_url,
        model_name=model_name,
        temperature=temperature,
    )
    
    print(f"配置已同步到数据库：")
    print(f"  - API Key: {'已设置' if config.api_key else '未设置'}")
    print(f"  - Base URL: {config.base_url}")
    print(f"  - Model Name: {config.model_name}")
    print(f"  - Temperature: {config.temperature}")


if __name__ == "__main__":
    try:
        sync_env_to_db()
    except Exception as e:
        print(f"错误: {e}", file=sys.stderr)
        sys.exit(1)

