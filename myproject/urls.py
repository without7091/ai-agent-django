from django.urls import path
from chat import views

urlpatterns = [
    # 会话管理
    path('api/sessions/create', views.create_session),
    path('api/sessions/list', views.list_sessions),
    path('api/sessions/rename', views.rename_session),
    path('api/sessions/delete', views.delete_session),
    
    # 聊天功能
    path('api/history', views.get_history),
    path('api/chat', views.chat_endpoint),
]