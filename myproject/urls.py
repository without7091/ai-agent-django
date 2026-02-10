from django.urls import path
from chat import views, ops_views
from django.contrib import admin  # ✅ 必须保留这一行
urlpatterns = [
# 1. Django 后台入口 (这就是你缺失的部分)
    path('admin/', admin.site.urls),
    # 会话管理
    path('api/sessions/create', views.create_session),
    path('api/sessions/list', views.list_sessions),
    path('api/sessions/rename', views.rename_session),
    path('api/sessions/delete', views.delete_session),
    
    # 聊天功能
    path('api/history', views.get_history),
    path('api/chat', views.chat_endpoint),

    # 1. 会话列表查询 (支持搜索用户)
    path('api/ops/sessions', ops_views.ops_session_list),

    # 2. 全链路追踪 (查看工具调用详情)
    path('api/ops/trace/<str:session_id>', ops_views.ops_session_trace),
]