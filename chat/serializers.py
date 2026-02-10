import json
from langchain_core.messages import HumanMessage, AIMessage, ToolMessage, SystemMessage

def serialize_message(message):
    """
    将 LangChain 的消息对象转换为简单的字典格式，
    专门用于运维界面展示完整的调用链路。
    """
    base_data = {
        "type": message.type,  # 'human', 'ai', 'tool'
        "content": message.content,
        "timestamp": None, # LangGraph 存储的消息通常没有自带时间戳，除非你自定义了
    }

    # 1. 处理 AI 的回复（可能包含工具调用请求）
    if isinstance(message, AIMessage):
        # 提取思维链/工具调用
        if hasattr(message, 'tool_calls') and message.tool_calls:
            base_data['tool_calls'] = [
                {
                    "name": tool_call['name'],
                    "args": tool_call['args'],
                    "id": tool_call['id']
                }
                for tool_call in message.tool_calls
            ]
        # 提取 Token 使用统计 (如果有)
        if hasattr(message, 'response_metadata'):
            base_data['metadata'] = message.response_metadata

    # 2. 处理工具的返回结果
    elif isinstance(message, ToolMessage):
        base_data['tool_call_id'] = message.tool_call_id
        base_data['status'] = "success" # 默认成功，你可以根据内容判断是否失败
        # 如果工具返回了 artifact (原始数据)，也可以提取出来
        if hasattr(message, 'artifact'):
             base_data['artifact'] = str(message.artifact)

    return base_data