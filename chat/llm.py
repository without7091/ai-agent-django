import time
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser

from chat.graph import llm
# 引入 Django 模型 (注意：需要在 django setup 之后才能引入，通常在 views 调用时没问题)
# 如果报 AppRegistryNotReady，请确保只在函数内部 import，或者确保 Django 已启动
from chat.models import ChatSession

# 单独初始化一个轻量级 LLM (保持你之前的逻辑)



# 【重点修改】去掉 async，改为普通函数
def generate_and_update_title(session_id: str, user_query: str):
    """
    后台任务：同步版，适合在 threading.Thread 中运行
    """
    print(f"🚀 [后台任务启动] 正在为会话 {session_id} 生成标题...")

    try:
        # 1. 定义 Prompt
        prompt = ChatPromptTemplate.from_template(
            "请根据用户的输入生成一个非常简短的对话标题（不超过10个字），不要包含任何标点符号，直接输出标题内容。\n\n用户输入: {query}"
        )
        chain = prompt | llm | StrOutputParser()

        # 2. 调用 LLM (同步 invoke)
        # 线程会阻塞在这里等待 HTTP 请求返回，但这不影响主线程的流式输出
        new_title = chain.invoke({"query": user_query})
        new_title = new_title.strip().replace('"', '')

        print(f"✅ [生成成功] 新标题: {new_title}")

        # 3. 使用 Django ORM 更新数据库 (比 raw sql 更安全)
        # filter().update() 是直接在数据库层面执行 SQL update，效率高
        rows = ChatSession.objects.filter(session_id=session_id).update(title=new_title)

        if rows == 0:
            print(f"⚠️ [更新警告] 未找到会话 ID: {session_id}")
        else:
            print(f"💾 [数据库更新] 会话标题已保存")

    except Exception as e:
        print(f"❌ 自动生成标题失败: {e}")