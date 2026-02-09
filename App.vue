<template>
  <div class="app-layout">
    <aside class="sidebar">
      <div class="sidebar-header">
        <button class="new-chat-btn" @click="createNewSession" :disabled="isLoading">
          <i class="el-icon-plus"></i>
          <span>New Chat</span>
        </button>
      </div>

      <div class="session-list">
        <div v-if="sessions.length === 0" class="empty-tip">暂无历史记录</div>

        <div
            v-for="sess in sessions"
            :key="sess.session_id"
            class="session-item"
            :class="{ active: currentSessionId === sess.session_id }"
            @click="switchSession(sess.session_id)"
        >
          <i class="el-icon-chat-square icon"></i>

          <div class="title-wrapper" v-if="editingSessionId === sess.session_id">
            <input
                ref="renameInput"
                v-model="editTitle"
                class="rename-input"
                maxlength="20"
                placeholder="最多20字"
                @click.stop
                @blur="saveRename(sess)"
                @keyup.enter="saveRename(sess)"
                @keyup.esc="cancelRename"
            />
            <span class="char-count">{{ editTitle.length }}/20</span>
          </div>
          <span v-else class="title" :title="sess.title">
      {{ sess.title || '未命名会话' }}
    </span>

          <div class="actions">
            <i class="el-icon-edit edit-btn" @click.stop="startRename(sess)"></i>
            <i class="el-icon-delete delete-btn" @click.stop="deleteSession(sess.session_id)"></i>
          </div>
        </div>
      </div>

      <div class="user-profile">
        <div class="avatar">U</div>
        <div class="info">
          <span class="name">User Admin</span>
          <span class="status">Pro Plan</span>
        </div>
      </div>
    </aside>

    <main class="main-content">
      <header class="minimal-header">
        <div class="header-inner">
          <span class="model-name">Agent 问答助手 / Assistant</span>

          <div
              v-if="currentSessionId"
              class="id-badge"
              @click="copySessionId"
              title="点击复制 Session ID (用于运维追踪)"
          >
            <i class="el-icon-document-copy"></i>
            <span class="id-text"></span>
          </div>

          <span class="status-dot" :class="{ processing: isLoading }"></span>
        </div>
      </header>

      <div class="chat-viewport" ref="chatContainer">
        <div v-if="messageList.length === 0" class="empty-placeholder">
          <div class="logo-mark">✦</div>
          <h2>{{ greeting }}</h2>
          <p>我可以帮您询问版本的内容或答疑解惑。</p>
        </div>
        <div class="message-feed">
          <div
              v-for="(msg, index) in messageList"
              :key="index"
              class="message-group"
              :class="msg.role"
          >
            <div class="avatar-col">
              <div v-if="msg.role === 'ai'" class="ai-icon">✦</div>
              <div v-else class="user-icon">U</div>
            </div>

            <div class="content-col">
              <div v-if="msg.role === 'ai' && msg.toolName" class="tool-pill">
                <i class="el-icon-setting"></i>
                <span>Action: {{ msg.toolName }}</span>
              </div>

              <div v-if="msg.role === 'user'" class="user-text">{{ msg.content }}</div>
              <div v-else class="markdown-body minimal-markdown" v-html="renderMarkdown(msg.content)"></div>

              <span v-if="msg.role === 'ai' && msg.isStreaming" class="typing-cursor"></span>
            </div>
          </div>
        </div>
      </div>

      <footer class="input-area">
        <div class="input-card" :class="{ 'is-focus': isInputFocused }">
          <textarea
              v-model="inputQuery"
              placeholder="请输入您想问的问题..."
              @keydown.enter.prevent="handleSend"
              @focus="isInputFocused = true"
              @blur="isInputFocused = false"
              :disabled="isLoading"
              rows="1"
              ref="textarea"
              class="minimal-input"
          ></textarea>

          <button
              class="send-btn"
              @click="handleSend"
              :disabled="!inputQuery.trim() && !isLoading"
          >
            <i v-if="!isLoading" class="el-icon-top"></i>
            <i v-else class="el-icon-loading"></i>
          </button>
        </div>
        <div class="footer-note">AI can make mistakes. Please verify important information.</div>
      </footer>
    </main>
  </div>
</template>

<script>
import MarkdownIt from 'markdown-it';

// 定义后端地址
const API_BASE = 'http://127.0.0.1:8000/api';
const USER_ID = "admin_user_001"; // 模拟当前用户

export default {
  name: "ModernChat",
  data() {
    return {
      sessions: [], // 会话列表
      currentSessionId: null, // 当前选中的会话
      messageList: [], // 当前会话的消息
      inputQuery: "",
      isLoading: false,
      isInputFocused: false,
      abortController: null,
      editingSessionId: null, // 当前正在重命名的会话ID
      editTitle: "",          // 正在输入的临时标题
      md: new MarkdownIt({ html: true, linkify: true, breaks: true })
    };
  },
  watch: {
    inputQuery() {
      this.$nextTick(() => {
        const el = this.$refs.textarea;
        if (el) {
          el.style.height = 'auto';
          el.style.height = Math.min(el.scrollHeight, 150) + 'px'; // 限制最大高度
        }
      });
    }
  },
  mounted() {
    this.loadSessionList();
  },
  computed: {
    // 1. 动态问候语逻辑
    greeting() {
      const hour = new Date().getHours();

      if (hour < 12) {
        return "Good Morning";
      } else if (hour < 18) {
        return "Good Afternoon";
      } else {
        return "Good Evening";
      }
    },

    // ... 如果你之前有其他 computed (比如 currentSessionTitle)，保留它们 ...
  },
  methods: {
    renderMarkdown(text) {
      return this.md.render(text || '');
    },

    // --- 1. 会话管理逻辑 ---
    copySessionId() {
      if (!this.currentSessionId) return;

      navigator.clipboard.writeText(this.currentSessionId)
          .then(() => {
            // 如果你安装了 ElementUI，用 this.$message
            // 如果没有，可以用 alert 或者 console.log
            if (this.$message) {
              this.$message.success({
                message: `ID 已复制: ${this.currentSessionId}`,
                duration: 2000
              });
            } else {
              alert("ID 已复制");
            }
          })
          .catch(err => {
            console.error('复制失败', err);
            this.$message.error("复制失败，请手动复制");
          });
    },
    async loadSessionList(isSilent = false) {
      try {
        const res = await fetch(`${API_BASE}/sessions/list?user_id=${USER_ID}`);
        const data = await res.json();

        this.sessions = data.data || [];

        // 只有在非静默模式（比如刚打开页面）且没有选中会话时，才自动选中第一个
        if (!isSilent) {
          if (this.sessions.length > 0 && !this.currentSessionId) {
            this.switchSession(this.sessions[0].session_id);
          } else if (this.sessions.length === 0) {
            this.createNewSession();
          }
        }
      } catch (e) {
        console.error("加载会话失败", e);
      }
    },

    async createNewSession() {
      // 1. 【新增逻辑】防抖检查
      // 如果当前还有会话（sessions.length > 0）
      // 且当前会话的消息列表是空的（messageList.length === 0）
      // 说明当前这就已经是一个“新会话”了，不需要再建一个
      if (this.sessions.length > 0 && this.messageList.length === 0) {
        this.$message.warning("当前已经是新会话，请先开始提问");
        return; // 直接结束，不发请求
      }

      try {
        const res = await fetch(`${API_BASE}/sessions/create`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ user_id: USER_ID, title: 'New Chat' })
        });
        const data = await res.json();

        await this.loadSessionList();

        // 切换到新建的会话
        this.switchSession(data.session_id);

        // 自动聚焦输入框，提升体验
        this.$nextTick(() => {
          if (this.$refs.textarea) this.$refs.textarea.focus();
        });

      } catch (e) {
        this.$message.error("创建失败");
      }
    },
    async switchSession(sessionId) {
      if (this.currentSessionId === sessionId) return;
      this.currentSessionId = sessionId;
      this.messageList = []; // 清屏
      this.isLoading = false;
      if (this.abortController) this.abortController.abort(); // 中断之前的请求

      await this.fetchHistory(sessionId);
    },

    async deleteSession(sessionId) {
      if(!confirm("确定删除此会话吗？")) return;
      try {
        await fetch(`${API_BASE}/sessions/delete`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ session_id: sessionId })
        });
        // 如果删除的是当前会话，清空当前ID
        if (this.currentSessionId === sessionId) {
          this.currentSessionId = null;
          this.messageList = [];
        }
        await this.loadSessionList();
      } catch (e) {
        this.$message.error("删除失败");
      }
    },

    async fetchHistory(sessionId) {
      try {
        const res = await fetch(`${API_BASE}/history?session_id=${sessionId}`);
        const data = await res.json();
        if (data.messages) {
          this.messageList = data.messages;
          this.scrollToBottom();
        }
      } catch (e) {
        console.error("加载历史失败", e);
      }
    },

    // --- 2. 聊天发送逻辑 ---

    async handleSend() {
      if (this.isLoading) {
        // 如果正在生成，点击按钮则是停止生成
        if (this.abortController) this.abortController.abort();
        this.isLoading = false;
        return;
      }
      if (!this.inputQuery.trim()) return;

      const query = this.inputQuery;
      this.inputQuery = "";
      if (this.$refs.textarea) this.$refs.textarea.style.height = 'auto';

      this.messageList.push({ role: 'user', content: query });
      this.scrollToBottom();

      await this.requestBackend(query);
    },

    async requestBackend(query) {
      this.isLoading = true;
      this.abortController = new AbortController();

      // 预先占位 AI 消息
      const aiMsgIndex = this.messageList.push({
        role: 'ai',
        content: '',
        toolName: '',
        isStreaming: true
      }) - 1;

      try {
        const response = await fetch(`${API_BASE}/chat`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            query: query,
            session_id: this.currentSessionId,
            user_id: USER_ID
          }),
          signal: this.abortController.signal
        });

        if (!response.ok) throw new Error(`Status: ${response.status}`);

        const reader = response.body.getReader();
        const decoder = new TextDecoder('utf-8');
        let buffer = '';

        // eslint-disable-next-line no-constant-condition
        while (true) {
          const { done, value } = await reader.read();
          if (done) break;

          const chunk = decoder.decode(value, { stream: true });
          buffer += chunk;
          const lines = buffer.split('\n');
          buffer = lines.pop();

          for (const line of lines) {
            const trimmed = line.trim();
            if (trimmed.startsWith('data: ')) {
              const jsonStr = trimmed.substring(6);
              if (jsonStr === '[DONE]') continue;

              try {
                const data = JSON.parse(jsonStr);
                const currentMsg = this.messageList[aiMsgIndex];

                if (data.type === 'answer') {
                  currentMsg.toolName = '';
                  currentMsg.content += data.content;
                } else if (data.type === 'tool') {
                  currentMsg.toolName = data.content;
                }

                // 强制更新视图
                this.$set(this.messageList, aiMsgIndex, currentMsg);
                this.scrollToBottom();
              } catch (e) {console.log(e)}
            }
          }

        }
      } catch (error) {
        if (error.name !== 'AbortError') {
          const currentMsg = this.messageList[aiMsgIndex];
          currentMsg.content += "\n\n*(网络请求失败)*";
          this.$set(this.messageList, aiMsgIndex, currentMsg);
        }
      } finally {
        this.isLoading = false;
        this.abortController = null;
        const currentMsg = this.messageList[aiMsgIndex];
        if (currentMsg) {
          currentMsg.isStreaming = false;
          this.$set(this.messageList, aiMsgIndex, currentMsg);
        }
        await this.loadSessionList(true); // 传入 true 表示静默刷新
      }

    },
// 1. 开始重命名
    startRename(session) {
      this.editingSessionId = session.session_id;
      this.editTitle = session.title || '未命名会话';

      // 等待 DOM 更新后让输入框自动聚焦
      this.$nextTick(() => {
        // 因为是 v-for 里的 ref，所以 this.$refs.renameInput 是一个数组
        if (this.$refs.renameInput && this.$refs.renameInput[0]) {
          this.$refs.renameInput[0].focus();
        }
      });
    },

    // 2. 取消重命名 (按 ESC)
    cancelRename() {
      this.editingSessionId = null;
      this.editTitle = "";
    },

    // 3. 保存重命名 (按回车或失去焦点)
    async saveRename(session) {
      // 如果没有处于编辑状态（防止 blur 和 enter 冲突重复触发），直接返回
      if (this.editingSessionId !== session.session_id) return;

      const newTitle = this.editTitle.trim();

      // 如果标题没变或者为空，直接取消
      if (!newTitle || newTitle === session.title) {
        this.cancelRename();
        return;
      }
      const oldTitle = session.title;
      try {
        // 乐观更新：先在界面上改了，让用户觉得快
        session.title = newTitle;
        this.editingSessionId = null; // 退出编辑模式

        // 发送后端请求
        await fetch(`${API_BASE}/sessions/rename`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            session_id: session.session_id,
            title: newTitle
          })
        });

      } catch (e) {
        this.$message.error("重命名失败");
        session.title = oldTitle; // 回滚
      }
    },
    scrollToBottom() {
      this.$nextTick(() => {
        const container = this.$refs.chatContainer;
        if (container) {
          container.scrollTo({ top: container.scrollHeight, behavior: 'smooth' });
        }
      });
    }
  }
};
</script>

<style scoped>
/* =========================================
   Modern Layout (Side + Main)
   ========================================= */
.app-layout {
  display: flex;
  height: 100vh;
  width: 100%;
  background-color: #ffffff;
  font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
  color: #1a1a1a;
}

/* --- Left Sidebar --- */
.sidebar {
  width: 260px;
  background-color: #f9f9f9;
  border-right: 1px solid #eaeaea;
  display: flex;
  flex-direction: column;
  flex-shrink: 0;
  transition: all 0.3s ease;
}

.sidebar-header {
  padding: 20px;
}

.new-chat-btn {
  width: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 10px 16px;
  background: #ffffff;
  border: 1px solid #e5e5e5;
  border-radius: 8px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 500;
  color: #333;
  transition: all 0.2s;
  box-shadow: 0 1px 2px rgba(0,0,0,0.05);
}
.new-chat-btn:hover {
  background: #f0f0f0;
  border-color: #dcdcdc;
}

.session-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px;
}

.empty-tip {
  padding: 20px;
  text-align: center;
  color: #999;
  font-size: 13px;
}

.session-item {
  display: flex;
  align-items: center;
  padding: 10px 12px;
  margin-bottom: 4px;
  border-radius: 6px;
  cursor: pointer;
  font-size: 14px;
  color: #555;
  transition: background 0.2s;
  position: relative;
}
.session-item:hover {
  background-color: #ececec;
}
.session-item.active {
  background-color: #e6e6e6;
  color: #000;
  font-weight: 500;
}
.session-item .icon {
  margin-right: 10px;
  font-size: 14px;
  color: #888;
}
.session-item .title {
  flex: 1;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.actions {
  display: none;
}
.session-item:hover .actions {
  display: block;
}
.delete-btn {
  color: #999;
  padding: 4px;
}
.delete-btn:hover {
  color: #ff4d4f;
}

.user-profile {
  padding: 16px;
  border-top: 1px solid #eaeaea;
  display: flex;
  align-items: center;
  gap: 12px;
}
.user-profile .avatar {
  width: 32px;
  height: 32px;
  background: #333;
  color: #fff;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: bold;
  font-size: 12px;
}
.user-profile .info {
  display: flex;
  flex-direction: column;
}
.user-profile .name {
  font-size: 14px;
  font-weight: 600;
}
.user-profile .status {
  font-size: 12px;
  color: #888;
}

/* --- Right Main Content --- */
.main-content {
  flex: 1;
  display: flex;
  flex-direction: column;
  position: relative;
  background-color: #fff;
}

.minimal-header {
  height: 50px;
  display: flex;
  align-items: center;
  justify-content: center;
  /* border-bottom: 1px solid #f5f5f5; 取消底边框让界面更干净 */
  z-index: 10;
}
.header-inner {
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 14px;
  font-weight: 500;
  color: #666;
  cursor: pointer;
  padding: 6px 12px;
  border-radius: 6px;
}
.header-inner:hover { background: #f5f5f5; }
.status-dot { width: 6px; height: 6px; background: #ddd; border-radius: 50%; }
.status-dot.processing { background: #10a37f; box-shadow: 0 0 4px rgba(16,163,127,0.4); }

/* Chat Viewport */
.chat-viewport {
  flex: 1;
  overflow-y: auto;
  padding: 0 0 120px 0; /* 底部预留输入框空间 */
}

/* Empty State */
.empty-placeholder {
  height: 80%;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  color: #1a1a1a;
}
.logo-mark {
  font-size: 32px;
  margin-bottom: 20px;
  width: 50px; height: 50px;
  background: #f9f9f9;
  border-radius: 50%;
  display: flex; align-items: center; justify-content: center;
}
.empty-placeholder h2 { font-weight: 600; font-size: 24px; margin-bottom: 8px; }
.empty-placeholder p { color: #888; }

/* Message Feed */
.message-feed {
  max-width: 800px; /* 类似 ChatGPT 的阅读宽度 */
  margin: 0 auto;
  padding-top: 20px;
}

.message-group {
  display: flex;
  gap: 20px;
  padding: 24px 20px;
  /* border-bottom: 1px solid #fbfbfb; 可选的分隔线 */
}

.avatar-col {
  width: 30px;
  flex-shrink: 0;
}
.ai-icon, .user-icon {
  width: 30px; height: 30px;
  border-radius: 6px;
  display: flex; align-items: center; justify-content: center;
  font-size: 14px;
}
.ai-icon { background: #000; color: #fff; }
.user-icon { background: #f0f0f0; color: #555; }

.content-col {
  flex: 1;
  min-width: 0;
}

.user-text {
  font-size: 16px;
  line-height: 1.6;
  color: #1a1a1a;
  white-space: pre-wrap;
}

/* Tool Pill */
.tool-pill {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  color: #666;
  background: #f5f5f5;
  padding: 4px 10px;
  border-radius: 4px;
  margin-bottom: 12px;
  font-family: monospace;
}

/* Markdown Styles (Minimal) */
.minimal-markdown {
  font-size: 16px;
  line-height: 1.7;
  color: #242424;
}
.minimal-markdown >>> p { margin-bottom: 16px; }
.minimal-markdown >>> pre {
  background: #f7f7f7;
  padding: 16px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 16px 0;
}
.minimal-markdown >>> code {
  font-family: monospace;
  background: rgba(0,0,0,0.05);
  padding: 2px 4px;
  border-radius: 4px;
  font-size: 0.9em;
}

/* Typing Cursor */
.typing-cursor {
  display: inline-block;
  width: 8px; height: 16px;
  background: #000;
  vertical-align: middle;
  animation: blink 1s step-end infinite;
}
@keyframes blink { 50% { opacity: 0; } }

/* Input Area */
.input-area {
  position: absolute;
  bottom: 0; left: 0; right: 0;
  padding: 24px;
  background: linear-gradient(to top, rgba(255,255,255,1) 70%, rgba(255,255,255,0));
  display: flex;
  flex-direction: column;
  align-items: center;
}

.input-card {
  width: 100%;
  max-width: 800px;
  background: #fff;
  border: 1px solid #e5e5e5;
  border-radius: 12px;
  box-shadow: 0 4px 12px rgba(0,0,0,0.05);
  padding: 10px 12px;
  display: flex;
  align-items: flex-end;
  transition: border-color 0.2s, box-shadow 0.2s;
}

.input-card.is-focus {
  border-color: #999;
  box-shadow: 0 4px 16px rgba(0,0,0,0.08);
}

.minimal-input {
  flex: 1;
  border: none;
  background: transparent;
  padding: 8px;
  font-size: 16px;
  font-family: inherit;
  resize: none;
  max-height: 200px;
  outline: none;
  line-height: 1.5;
}

.send-btn {
  width: 32px; height: 32px;
  border-radius: 6px;
  border: none;
  background: #1a1a1a;
  color: #fff;
  cursor: pointer;
  display: flex; align-items: center; justify-content: center;
  transition: opacity 0.2s;
  margin-bottom: 2px;
}
.send-btn:disabled {
  background: #e5e5e5;
  cursor: default;
}
.send-btn:hover:not(:disabled) {
  opacity: 0.8;
}

.footer-note {
  font-size: 11px;
  color: #aaa;
  margin-top: 10px;
}
/* 修改 .title-wrapper */
.title-wrapper {
  flex: 1;
  display: flex;
  align-items: center; /* 垂直居中 */
  overflow: hidden;
  position: relative; /* 为字数统计定位 */
}

.rename-input {
  width: 100%;
  border: 1px solid #3b82f6;
  border-radius: 4px;
  padding: 2px 24px 2px 4px; /* 右侧留出空间给数字 */
  font-size: 14px;
  font-family: inherit;
  outline: none;
  background: #fff;
  color: #333;
}

/* 新增字数统计样式 */
.char-count {
  position: absolute;
  right: 6px;
  font-size: 10px;
  color: #ccc;
  pointer-events: none; /* 防止遮挡点击 */
}

/* 【新增】顶部 ID 复制按钮样式 */
.id-badge {
  display: flex;
  align-items: center;
  gap: 4px;
  background-color: #f0f2f5;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 11px;
  color: #909399;
  cursor: pointer;
  margin-left: 8px; /* 稍微离标题远一点 */
  margin-right: 8px;
  transition: all 0.2s;
  border: 1px solid transparent;
}

.id-badge:hover {
  background-color: #e6f7ff;
  color: #1890ff;
  border-color: #bae7ff;
}

.id-badge i {
  font-size: 12px;
}

.id-badge .id-text {
  font-weight: 600;
  font-family: monospace; /* 看起来更像技术参数 */
}

/* 微调原有的 header-inner，让内容对齐更好看 */
.header-inner {
  display: flex;
  align-items: center;
  /* gap: 8px;  <-- 这行可以去掉或保留，我们上面用了 margin */
  font-size: 14px;
  font-weight: 500;
  color: #666;
  /* padding: 6px 12px; <--- 建议去掉这个 hover 背景，因为我们现在有了可点击的子元素 */
}
</style>