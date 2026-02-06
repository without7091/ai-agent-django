# chat/global_context.py
import contextvars

# 1. 定义一个 ContextVar (上下文变量)
# default="无..." 是默认值，类似你之前写的兜底逻辑
# 这个变量是“线程隔离”的，不用担心并发冲突
_user_version_store = contextvars.ContextVar("user_context_version", default="无 (需询问用户)")

def set_current_version(version: str):
    """设置当前请求的上下文版本"""
    _user_version_store.set(version)

def get_current_version() -> str:
    """获取当前上下文版本 (像读取时间一样简单)"""
    return _user_version_store.get()