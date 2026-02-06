import datetime
import os
import re
import sqlite3
from typing import Optional, Literal, Dict, Any, List

from langchain.agents import create_agent, AgentState
from langchain.agents.middleware import before_model, dynamic_prompt, ModelRequest
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.config import get_stream_writer
from langgraph.runtime import Runtime
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, trim_messages, BaseMessage
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from dotenv import load_dotenv

from chat.global_context import get_current_version
from chat.tools.PuoToolManager import PuoToolManager

load_dotenv()  # 自动寻找并加载项目根目录下的 .env 文件
# ==========================================
# 1. 定义实体枚举 (来自你的知识库)
# ==========================================
# 为了让 LLM 更精准，限制参数只能是这些值




llm = ChatOpenAI(
    model="deepseek-chat",  # 或 gpt-4o
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0  # 任务型 Agent 温度设为 0 以保证精准
)
tools_list = PuoToolManager.get_tools_list()
# ==========================================
# 3. 配置 LLM 与 System Prompt
# ==========================================

# 你的原始 Prompt 核心逻辑，转化为 System Prompt
COMPONENTS_LIST = [
    "tlbck", "ltrusteer", "compiler_cpu", "vpp", "license", "dopra_ssp",
    "hisec_ict", "cmscbb", "bbuapp", "nse_egn", "ERU", "ipclk",
    "airan", "iware", "visp", "rtos", "saie", "gndp", "dopra_dda",
    "hitss", "secure_c", "kme", "rnt", "central_repo", "bts3920"
]

PRODUCTS_LIST = [
    "besa", "marp_ru", "nfa", "hert_ue", "MRAT", "Atom_RRU", "bts",
    "ant_rcu", "gbts", "nodeb", "makelut", "SRU", "mbts_cmc"
]


# =================================================================
# 中间件 2: 调试日志打印 (只负责 Print)
# =================================================================
@before_model
def debug_print_prompt(state: AgentState, runtime: Runtime) -> None:
    """
    【调试中间件】负责将最终发给 LLM 的消息打印到控制台
    由于它排在 inject_environment_context 后面，所以它能看到更新后的 Prompt
    """
    messages: List[BaseMessage] = state["messages"]

    print("\n" + "🐛" * 20 + " [LLM Request Debug] " + "🐛" * 20)
    print(f"⏰ 触发时间: {datetime.datetime.now().strftime('%H:%M:%S')}")
    print(f"📦 消息总数: {len(messages)}")
    print("-" * 60)

    for i, msg in enumerate(messages):
        role = msg.type.upper()
        content = msg.content

        # 为了防止控制台刷屏，System Prompt 如果太长可以截断显示，或者完全显示
        preview = content
        if role == "SYSTEM" and len(content) > 100:
            # 这里只为了演示，实际调试你可能想看全
            # preview = content[:100] + "...(剩余略)..."
            pass

        print(f"[{i}] 【{role}】:")
        print(f"{preview}")
        print("-" * 30)

    print("🐛" * 45 + "\n")

    # 返回 None 表示不修改任何 state，只做副作用（打印）
    return None

@before_model
def inject_environment_context(state: AgentState, runtime: Runtime) -> Dict[str, Any]:
    """
    每次调用模型前执行：
    1. 获取最新时间
    2. 获取 Config 参数
    3. 暴力替换/插入 SystemMessage
    """
    """
    动态生成 System Prompt
    该函数会在每次 LLM 调用前执行，用于注入时间及上下文版本
    """
    # --- A. 获取【绝对实时】的时间 ---
    # 因为这个函数每次对话都会运行，所以 now() 肯定是当前的
    now = datetime.datetime.now()
    current_time_str = now.strftime("%Y-%m-%d %H:%M:%S")

    # --- B. 获取 Django 传进来的 Context ---
    # 截图里 `@dynamic_prompt` 用的是 request.runtime.context
    # 这里直接有 runtime 对象，所以直接用 runtime.context
    # 加个防御性判断

    user_ver = get_current_version()

    # 打印日志（方便你后台看有没有刷新）
    print(f"⚡ [@before_model] 触发更新! 时间: {current_time_str}, 版本: {user_ver}")

    # --- C. 组装 Prompt ---
    components_str = ", ".join(COMPONENTS_LIST)
    products_str = ", ".join(PRODUCTS_LIST)
    # 3. 返回格式化后的完整 System Prompt 字符串
    SYSTEM_PROMPT = """你是一个专业的 IT 运维研发数据查询助手。
        你的核心任务是精准识别用户意图，并调用工具查询构建、版本、组件及产品配套信息。
        
        ### 全局数据字典 (Data Dictionary)
        注意：涉及 **组件/三方组件** 或 **产品(product)** 时，必须从以下列表中选择，严禁编造：
        * **支持的组件**: [{components_str}]
        * **支持的产品**: [{products_str}]

        ### 0. 环境感知 (Environment Context)
        * **当前系统时间**: {current_time}
        * **当前上下文版本**: {context_version}
          > **注意**: 如果用户在问题中没有明确指定版本号 (ver)，**请默认使用上述“当前上下文版本”**。只有当用户明确指定了新版本时，才覆盖此默认值。



        ### 核心规则（Entity & Logic）
        ### 1. 参数定义与格式规范 (Strict Format Rules)
        在提取参数调用工具前，必须严格进行格式校验。如果用户输入不符合规范，请礼貌反问，不要强行调用。

        * **ver (版本号)**:
            * 格式必须是 **2位数字 + 1个小写字母**。
            * ✅ 正确示例: `24a`, `24b`, `25c`


        * **search_key (通用查询凭证)**:
            用于组件或产品查询工具的 `search` 字段，模型需自动识别为以下三种类型之一：
            1.  **构建节点号 (Node ID)**: 长字符串，由字母和数字组成 (通常 40 位)。
                * 例: `36ff94e91b0ac3bc17513d9aa2a7799a6d771763`
            2.  **分支名 (Branch)**: 通常包含 `/` 或 `hert_bugfix` 前缀。
                * 例: `release/24a`, `hert_bugfix_abc`
                * 注意: 仅仅说 "hert分支" 属于此类，**不是** HERT版本。
            3.  **HERT版本号**: **必须**以 `HERT BBU` 开头。
                * 例: `HERT BBU V500R015C00SPC1508002`

        * **特定版本标识**:
            * **SPC版本**: 必须以 `SPC` 开头 (例: `SPC050`)。
            * **多模版本**: 必须以 `BTS3900` 开头。
            * **工程名/CM版本**: 以 `V` 开头 (例: `V500R015...`)。
        * **注意事项**:
            hert分支" 属于 分支，而不是 HERT Version。

        ### 2. 工具路由策略 (Routing Logic)
        请根据用户的意图和提取到的参数，选择最合适的工具：

        **场景 A：查询三方组件 (Component) 或 产品 (Product) 配套**
        * **判断依据**: 用户提到了具体的组件名 (如 `iware`, `rtos`) 或 产品名 (如 `nodeb`, `besa`)。
        * **操作**:
            1.  提取 **ver** (大版本)。
            2.  提取 **search_key** (节点、分支 或 HERT版本)。
            3.  如果是组件 -> 调用 `query_component_details`。
            4.  如果是产品 -> 调用 `query_product_details`。
        * **注意**: 组件名和产品名必须严格匹配枚举列表，不要臆造。

        **场景 B：查询版本基础信息 (Basic Info)**
        * **判断依据**: 用户提供了 SPC号、工程名(V开头)、CM版本 或 节点号，并询问“基本信息”或“构建详情”。
        * **操作**: 调用 `query_version_basic_info`。


        ### 3. 交互与记忆原则
        1.  **上下文补全**:
            * 如果用户只说了“查一下 iware”，但未提供 `ver` 或 `search_key`，请**先检查上下文历史**。
            * 如果上下文中有提到过 `ver` (如 "24a")，默认沿用该版本。
            * 如果上下文无相关信息，请追问：“请问您是在哪个版本（如 24a）、分支还是具体的节点号下查询？”
        2.  **拒绝瞎编**:
            * 严禁在没有工具返回结果的情况下编造数据。
            * 严禁使用枚举列表以外的单词作为 `component_name` 或 `product`。

        """

    filled_prompt = SYSTEM_PROMPT.format(
        current_time=current_time_str,
        context_version=user_ver,
        components_str=components_str,
        products_str=products_str
    )

    # --- D. 修改 Messages (核心逻辑) ---
    # Node-style 中间件要求返回一个 dict，用来更新 state
    # 我们取出旧的 messages，替换第一条
    messages = state["messages"]
    new_sys_msg = SystemMessage(content=filled_prompt)

    if messages and isinstance(messages[0], SystemMessage):
        # 如果第一条本来就是 SystemMessage，直接替换内容
        messages[0] = new_sys_msg
    else:
        # 否则插入到最前面
        messages.insert(0, new_sys_msg)

    # 返回更新后的 state
    return {"messages": messages}

db_path = "agent_chat_history.db" # 这会在你项目根目录生成一个文件
conn = sqlite3.connect(db_path, check_same_thread=False)


# 3. 初始化持久化存储器
memory = SqliteSaver(conn)
agent = create_agent(
    model=llm,
    tools=tools_list,
    # 启用记忆持久化 (可选)
    # 把我们的修剪逻辑传给 state_modifier
    # 这样，虽然数据库里存了 100 条，但 LLM 每次只看到最近 10 条 + System Prompt

    checkpointer=memory,

    # LangChain 1.0 新特性：中间件 (Middleware)
    # 这里我们可以留空，或者添加用于日志、鉴权、限流的中间件
    middleware=[inject_environment_context, debug_print_prompt],
)

graph = agent
#
# # 绑定工具
# llm_with_tools = llm.bind_tools(tools_list)
#
#
# # ==========================================
# # 4. 构建 LangGraph 图
# # ==========================================
#
# class State(MessagesState):
#     pass
#
#
# def chatbot_node(state: State):
#     messages = state["messages"]
#     # 确保 SystemMessage 在第一条
#     if not isinstance(messages[0], SystemMessage):
#         messages = [SystemMessage(content=SYSTEM_PROMPT)] + messages
#
#     response = llm_with_tools.invoke(messages)
#     return {"messages": [response]}
#
#
# workflow = StateGraph(State)
#
# # 添加节点
# workflow.add_node("chatbot", chatbot_node)
# workflow.add_node("tools", ToolNode(tools_list))  # LangGraph 内置的工具执行节点
#
# # 定义边
# workflow.add_edge(START, "chatbot")
#
# # 核心条件边：如果 LLM 返回 tool_calls -> 去 tools 节点；否则 -> 结束
# workflow.add_conditional_edges(
#     "chatbot",
#     tools_condition,
# )
#
# # 工具执行完，必须回到 chatbot 总结给用户
# workflow.add_edge("tools", "chatbot")
#
# graph = workflow.compile()

# ==========================================
# 5. 本地测试代码 (模拟 langgraph dev)
# ==========================================
# ==========================================
# 5. 本地测试代码
# ==========================================
# ==========================================
# 6. 本地集成测试 (Context & Memory)
# ==========================================
if __name__ == "__main__":
    # 定义一个固定的 Session ID，模拟同一个用户的连续对话
    # 如果你换成 "user_999"，对于 Agent 来说就是一个新用户，记忆会重置
    config = {"configurable": {"thread_id": "context_test_demo_v1"}}

    print(f"🚀 开始测试：多轮上下文记忆 (Thread ID: {config['configurable']['thread_id']})\n")

    # -----------------------------------------------------------
    # Round 1: 建立初始上下文 (Full Context)
    # 显式提供：[分支] hert_bugfix_2026, [组件] iware
    # -----------------------------------------------------------
    query_1 = "帮我查一下 hert_bugfix_2026 分支上 iware 的版本"
    print(f"👤 User (第1轮): {query_1}")

    inputs_1 = {"messages": [("user", query_1)]}
    for chunk, metadata in agent.stream(inputs_1, config=config, stream_mode="messages"):

        # 【核心逻辑】 只有当消息类型是 'ai' 且内容不为空时，才打印
        # chunk.type 可能的值：'ai', 'human', 'tool', 'system'

        # -------------------------------------------------
        # 情况 1: AI 的普通回复 (流式打印内容)
        # -------------------------------------------------
        print(chunk)
        if chunk.type == "AIMessageChunk" and chunk.content:
            print(chunk.content, end="", flush=True)

        # -------------------------------------------------
        # 情况 2: 工具执行的消息 (只打印工具名，不打印具体结果)
        # -------------------------------------------------
        elif chunk.type == "tool":
            # ToolMessage 对象有一个 .name 属性，存储了被调用工具的名字
            tool_name = chunk.name
            print(f"\n[🔧 系统调用了工具: {tool_name}]\n", end="")
            # 打印一个提示，比如 "[调用工具: search_api]"
            # 建议加个换行，防止和上面的 AI 回复粘在一起
        # print(chunk.type)
        # if chunk.type == "AIMessageChunk" and chunk.content:
        #     print(chunk.content, end="")
    # event["messages"][-1].pretty_print()
    # print("-" * 60)
    #
    # # -----------------------------------------------------------
    # # Round 2: 测试 "省略组件" (Implicit Component)
    # # 用户只换了[分支]：hert_feature_abc
    # # 期望 AI 自动继承上文的[组件]：iware
    # # -----------------------------------------------------------
    # query_2 = "那 hert_feature_abc 分支上呢？"
    # print(f"\n👤 User (第2轮): {query_2}  <-- 故意没说组件名，测试记忆")
    #
    # inputs_2 = {"messages": [("user", query_2)]}
    # for event in agent.stream(inputs_2, config=config, stream_mode="values"):
    #     pass
    # event["messages"][-1].pretty_print()
    # print("-" * 60)
    #
    # # -----------------------------------------------------------
    # # Round 3: 测试 "省略分支" (Implicit Branch)
    # # 用户只换了[组件]：rtos
    # # 期望 AI 自动继承"最新"的[分支]：hert_feature_abc (而不是第一轮的那个)
    # # -----------------------------------------------------------
    # query_3 = "rtos 这个组件呢？"
    # print(f"\n👤 User (第3轮): {query_3}  <-- 故意没说分支，测试是否继承了第2轮的分支")
    #
    # inputs_3 = {"messages": [("user", query_3)]}
    # for event in agent.stream(inputs_3, config=config, stream_mode="values"):
    #     pass
    # event["messages"][-1].pretty_print()
    # print("-" * 60)
    #
    # print("\n✅ 测试结束。如果第2、3轮都能正确调用工具，说明 Context Memory 工作正常！")