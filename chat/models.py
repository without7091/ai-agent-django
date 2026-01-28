from django.db import models

class ChatSession(models.Model):
    # 对应你原来的 session_id
    session_id = models.CharField(max_length=100, primary_key=True)
    # 对应 user_id
    user_id = models.CharField(max_length=100)
    # 对应 title
    title = models.CharField(max_length=200, default="New Chat")
    # 对应 created_at
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'sessions'  #以此名在数据库中创建表
        ordering = ['-created_at']