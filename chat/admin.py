from django.contrib import admin
from django.urls import path
from django.shortcuts import render
from django.utils.html import format_html
from .models import ChatSession

@admin.register(ChatSession)
class ChatSessionAdmin(admin.ModelAdmin):
    # 1. 列表页显示的字段
    list_display = ('session_id', 'title', 'user_id', 'created_at', 'ops_trace_link')
    # 2. 支持搜索的字段
    search_fields = ('session_id', 'user_id', 'title')
    # 3. 排序
    ordering = ('-created_at',)

    # --- 自定义按钮：全链路追踪 ---
    def ops_trace_link(self, obj):
        # 这里的 href 指向我们下面定义的 get_urls 中的 name
        return format_html(
            '<a class="button" href="trace/{}/">🔍 查看链路</a>',
            obj.session_id
        )
    ops_trace_link.short_description = "运维操作"
    ops_trace_link.allow_tags = True

    # --- 扩展 Admin 的 URL ---
    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('trace/<str:session_id>/', self.admin_site.admin_view(self.trace_view), name='session-trace'),
        ]
        return custom_urls + urls

    # --- 自定义视图：渲染上面的 HTML ---
    def trace_view(self, request, session_id):
        # 只要是能进 admin 的人，都是经过鉴权的
        context = {
            # 把 session_id 传给模板，模板里的 Vue 再拿去调 API
            'session_id': session_id,
            # 保持 Admin 的原有上下文（标题、导航栏等）
            **self.admin_site.each_context(request),
        }
        return render(request, 'admin/trace_detail.html', context)