# src/config.py

import os

# 把数据库路径定义在这里
# 使用绝对路径是个好习惯，防止在不同目录下运行脚本时找不到文件
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
METADATA_DB_PATH = os.path.join(BASE_DIR, "session_metadata.db")