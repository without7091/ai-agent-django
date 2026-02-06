import json
import threading
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt

from .global_context import set_current_version
from .graph import graph
from .llm import generate_and_update_title
# 引入你的 graph 和 agent
# 确保 src/agent/graph.py 里用的是 SqliteSaver (同步版)

from .models import ChatSession


# 辅助函数：解析 JSON body
def parse_body(request):
    return json.loads(request.body.decode('utf-8'))


# ==========================================
# 1. 会话管理接口 (CRUD)
# ==========================================

@csrf_exempt
def create_session(request):
    if request.method == 'POST':
        data = parse_body(request)
        import uuid
        session_id = str(uuid.uuid4())

        ChatSession.objects.create(
            session_id=session_id,
            user_id=data.get('user_id'),
            title=data.get('title', '新对话')
        )
        return JsonResponse({"session_id": session_id, "title": data.get('title')})


def list_sessions(request):
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        # values() 返回的是 QuerySet，需要转成 list
        sessions = list(ChatSession.objects.filter(user_id=user_id).order_by('-created_at').values())
        return JsonResponse({"data": sessions})


@csrf_exempt
def rename_session(request):
    if request.method == 'POST':
        data = parse_body(request)
        try:
            session = ChatSession.objects.get(session_id=data['session_id'])
            session.title = data['title']
            session.save()
            return JsonResponse({"status": "success", "session_id": session.session_id, "title": session.title})
        except ChatSession.DoesNotExist:
            return JsonResponse({"error": "Session not found"}, status=404)


@csrf_exempt
def delete_session(request):
    if request.method == 'POST':
        data = parse_body(request)
        ChatSession.objects.filter(session_id=data['session_id']).delete()
        return JsonResponse({"status": "success"})


# ==========================================
# 2. 历史记录接口
# ==========================================

def get_history(request):
    session_id = request.GET.get('session_id')
    config = {"configurable": {"thread_id": session_id}}

    try:
        # 使用同步的 get_state，完美适配 SqliteSaver
        state = graph.get_state(config)
        if not state or not state.values:
            return JsonResponse({"messages": []})

        messages = state.values.get("messages", [])
        history_data = []
        for msg in messages:
            if hasattr(msg, "type") and msg.type in ["human", "ai"]:
                history_data.append({
                    "role": "user" if msg.type == "human" else "ai",
                    "content": msg.content
                })
        return JsonResponse({"messages": history_data})
    except Exception as e:
        print(f"Error getting history: {e}")
        return JsonResponse({"messages": []})


# ==========================================
# 3. 核心流式聊天接口 (同步版)
# ==========================================

# 辅助函数：在线程中运行，用于后台生成标题
def run_background_rename(session_id, query):
    # 这里需要处理一下 Django 的数据库连接上下文，但在简单的 sqlite 场景下直接调用通常没问题
    # 更好的做法是引入 asyncio.run 如果 generate_and_update_title 是 async 的
    # 这里假设 generate_and_update_title 内部已经处理好了 (参考之前的实现)
    import asyncio
    try:
        asyncio.run(generate_and_update_title(session_id, query))
    except Exception as e:
        print(f"后台改名任务失败: {e}")


@csrf_exempt
def chat_endpoint(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        query = data.get('query')
        session_id = data.get('session_id')

        # --- 后台改名逻辑 (使用线程) ---
        try:
            session = ChatSession.objects.get(session_id=session_id)
            if session.title in ["New Chat", "新对话", "未命名会话"]:
                # 启动一个新线程去跑 LLM 生成标题，不阻塞当前聊天
                t = threading.Thread(target=generate_and_update_title, args=(session_id, query))
                t.start()
        except ChatSession.DoesNotExist:
            pass
        set_current_version("29a")
        # --- 流式生成器 (同步) ---
        def event_stream():
            inputs = {
                "messages": [("user", query)]
            }
            config = {
                "configurable": {
                    "thread_id": session_id,
                    "user_context_version": "29a"
                },
                 #
            }

            # 【关键修改】使用 graph.stream (同步方法)
            # 这里的 stream_mode="messages" 配合 v0.2+ 的 LangGraph
            try:
                for chunk, metadata in graph.stream(inputs, config=config, stream_mode="messages"):

                    if chunk.type == "AIMessageChunk" and chunk.content:
                        payload = json.dumps({"type": "answer", "content": chunk.content}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"

                    elif chunk.type == "tool":
                        payload = json.dumps({"type": "tool", "content": chunk.name}, ensure_ascii=False)
                        yield f"data: {payload}\n\n"

                yield "data: [DONE]\n\n"
            except Exception as e:
                print(f"Stream Error: {e}")
                err_payload = json.dumps({"type": "error", "content": str(e)}, ensure_ascii=False)
                yield f"data: {err_payload}\n\n"

        # Django 的 StreamingHttpResponse 完全支持同步生成器
        # return StreamingHttpResponse(event_stream(), content_type='text/event-stream')
        # --- 【关键修改】添加响应头 ---
        response = StreamingHttpResponse(event_stream(), content_type='text/event-stream')

        # 1. 禁用缓存
        response['Cache-Control'] = 'no-cache'
        # 2. 告诉 Nginx/代理服务器不要缓冲 (X-Accel-Buffering)
        response['X-Accel-Buffering'] = 'no'

        return response