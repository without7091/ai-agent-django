from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt

from .graph import graph
from .models import ChatSession
from .serializers import serialize_message

# 引入你编译好的 graph 对象
# 必须确保这个 graph 初始化的 checkpointer 指向的是 'agent_chat_history.db'



@csrf_exempt
def ops_session_list(request):
    """
    运维接口：获取所有会话列表（带详细元数据）
    支持分页和按用户ID搜索
    """
    if request.method == 'GET':
        user_id = request.GET.get('user_id')
        page = int(request.GET.get('page', 1))
        page_size = int(request.GET.get('page_size', 20))

        # 1. 查询 Django 数据库中的元数据
        queryset = ChatSession.objects.all().order_by('-created_at')

        if user_id:
            queryset = queryset.filter(user_id__contains=user_id)

        total = queryset.count()

        # 分页切片
        start = (page - 1) * page_size
        sessions = queryset[start: start + page_size]

        data = []
        for s in sessions:
            data.append({
                "session_id": s.session_id,
                "user_id": s.user_id,
                "title": s.title,
                "created_at": s.created_at.strftime("%Y-%m-%d %H:%M:%S"),
            })

        return JsonResponse({
            "code": 200,
            "data": {
                "list": data,
                "total": total,
                "page": page,
                "page_size": page_size
            }
        })


@csrf_exempt
def ops_session_trace(request, session_id):
    """
    运维接口：获取某个会话的【全链路追踪】
    从 LangGraph 的 SQLite Checkpoint 中读取完整历史
    """
    if request.method == 'GET':
        try:
            # 1. 构造 LangGraph 配置
            config = {"configurable": {"thread_id": session_id}}

            # 2. 从 Checkpointer 获取状态快照
            # graph.get_state 会去读取 agent_chat_history.db
            state = graph.get_state(config)

            if not state or not state.values:
                return JsonResponse({"code": 404, "msg": "未找到该会话的 Graph 状态", "trace": []})

            # 3. 提取 messages
            messages = state.values.get("messages", [])

            # 4. 序列化为前端可视化的格式
            trace_log = [serialize_message(msg) for msg in messages]

            return JsonResponse({
                "code": 200,
                "session_id": session_id,
                "step_count": len(trace_log),
                "trace": trace_log
            })

        except Exception as e:
            return JsonResponse({"code": 500, "msg": str(e)})