import os
import re
import sqlite3
from typing import Optional, Literal

from langchain.agents import create_agent
from langchain.agents.middleware import before_model
from langgraph.checkpoint.memory import MemorySaver
from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.config import get_stream_writer
from pydantic import BaseModel, Field

from langchain_openai import ChatOpenAI
from langchain_core.tools import tool
from langchain_core.messages import SystemMessage, trim_messages
from langgraph.graph import StateGraph, MessagesState, START, END
from langgraph.prebuilt import ToolNode, tools_condition, create_react_agent
from dotenv import load_dotenv
load_dotenv()  # 自动寻找并加载项目根目录下的 .env 文件
# ==========================================
# 1. 定义实体枚举 (来自你的知识库)
# ==========================================
# 为了让 LLM 更精准，限制参数只能是这些值
ComponentsEnum = Literal[
    "libck", "ltrustee", "compiler_cpu", "vpp", "license", "dopra_ssp",
    "hisec_ict", "cmscbb", "bbuapp", "nse_egn", "EMRU", "ipclk",
    "airan", "iware", "visp", "rtos", "saie", "gmdb", "dopra_ddm",
    "hitss", "secure_c", "kmc", "rnt", "central_repo", "bts3920r"
]

ProductsEnum = Literal[
    "besa", "marp_ru", "rfa", "hert_mpe", "MRAT", "Atom_RRU", "bts",
    "ant_rcu", "gbts", "nodeb", "makelmt", "SMU", "mbts_cmc"
]


# ==========================================
# 2. 定义工具 (封装意图与参数校验)
# ==========================================
# --- 基础查询类 (意图 1-11) ---

@tool
def query_hert_node_on_rb(rb_name: str = Field(description="RB名称")):
    """[意图1] 查询RB上的hert节点信息"""
    return f"模拟数据：RB {rb_name} 上的 HERT 节点状态正常。"

@tool
def query_trunk_mirror_info():
    """[意图2] 查询主干配套的镜像信息"""
    return "模拟数据：当前主干镜像版本为 Image_20260125_V99。"

@tool
def query_bugfix_branch_info(branch_name: str = Field(description="Bugfix分支名称，通常包含 'bugfix' 字样")):
    """[意图3] bugfix分支信息查询"""
    return f"模拟数据：分支 {branch_name} 包含 3 个待合入补丁。"

@tool
def query_version_push_status(version_id: str):
    """[意图4] 版本推送情况查询"""
    return f"模拟数据：版本 {version_id} 推送成功，目标节点 10.20.30.40。"

@tool
def query_component_merge_status(
    component: ComponentsEnum,
    version_or_branch: str = Field(description="版本号或分支名")
):
    """[意图5] 三方组件合入情况查询"""
    return f"模拟数据：组件 {component} 在 {version_or_branch} 中已合入。"

@tool
def query_version_basic_info(version_id: str):
    """[意图6] 版本基本信息查询"""
    return f"模拟数据：版本 {version_id} 构建于 2026-01-24，负责人：WZH。"

@tool
def query_version_by_multimode(multimode_id: str):
    """[意图7] 版本基本信息查询(根据多模版本查询)"""
    return f"模拟数据：多模版本 {multimode_id} 对应的基线版本是 V500R001。"

@tool
def query_spc_commercial_status(spc_version: str = Field(description="SPC版本号，如 SPC100")):
    """[意图8] SPC版本商用情况查询"""
    return f"模拟数据：{spc_version} 已在 3 个局点商用。"

@tool
def query_merge_info_between_versions(start_version: str, end_version: str):
    """[意图9] 获取指定版本之间的合入情况"""
    return f"模拟数据：{start_version} 到 {end_version} 之间合入了 15 个 MR。"

@tool
def query_mr_info(mr_id: str = Field(description="MR编号，如 !12345 或 MR链接")):
    """[意图10] 查询指定MR情况"""
    return f"模拟数据：MR {mr_id} 状态：已合并，检视人：Admin。"

@tool
def check_trunk_build_status():
    """[意图11] 查看主干构建状态"""
    return "模拟数据：主干构建 🟢 成功 (Build #9527)。"

# 意图 12: 通过节点号查询三方组件配套信息
@tool
def query_component_by_node(
        node_id: str = Field(description="节点编号，通常是32位十六进制字符串或特定字母数字组合"),
        component_name: ComponentsEnum = Field(description="三方组件名称")
):
    """
    [意图12] 根据具体的构建节点号(Node ID)，查询指定三方组件的版本配套信息。
    """
    # 模拟 HTTP 请求
    print(f"\n📡 [系统调用] 正在查询节点 {node_id} 上的组件 {component_name}...")
    # 模拟校验逻辑（可根据 Excel 图片中的规则加强）
    if len(node_id) < 5:
        return "API错误: 节点号格式不正确，看起来太短了。"

    return {
        "intent_id": 12,
        "status": "success",
        "data": {
            "node": node_id,
            "component": component_name,
            "version": "v1.2.3-release",
            "merge_time": "2026-01-25 10:00:00"
        }
    }
@tool
def query_component_by_node(
    node_id: str = Field(description="节点编号(Node ID)，通常是32位Hash或字母数字组合"),
    component: ComponentsEnum = Field(description="三方组件名称")
):
    """[意图12] 通过节点号查询三方组件配套信息"""
    # 模拟HTTP请求逻辑
    print(f"📡 API Call: POST /api/query_match params={{node: {node_id}, type: 'component', name: {component}}}")
    return {"result": f"节点 {node_id} 配套的 {component} 版本是 v1.0.1"}

@tool
def query_component_by_branch(
    branch_name: str = Field(description="分支名称(Branch)，包含'/'符号或前缀如'hertbbu'"),
    component: ComponentsEnum = Field(description="三方组件名称")
):
    """[意图13] 通过分支名称查询三方组件配套信息"""
    writer = get_stream_writer()
    writer(f"正在查询天气信息....")

    return {"result": f"分支 {branch_name} 锁定的 {component} 版本是 v2.0"}

@tool
def query_component_by_hert_version(
    hert_version: str = Field(description="HERT版本号，必须以 'HERT BBU' 开头"),
    component: ComponentsEnum = Field(description="三方组件名称")
):
    """[意图14] 通过HERT版本号查询三方组件配套信息"""
    if not hert_version.startswith("HERT BBU"):
        return "错误：HERT版本号格式不正确，必须以 'HERT BBU' 开头。"
    return {"result": f"版本 {hert_version} 集成了 {component} v3.5"}

@tool
def query_product_by_node(
    node_id: str = Field(description="节点编号"),
    product: ProductsEnum = Field(description="产品/网元名称")
):
    """[意图15] 通过节点号查询产品配套版本"""
    return {"result": f"节点 {node_id} 对应的 {product} 版本是 V100R001"}

@tool
def query_product_by_branch(
    branch_name: str = Field(description="分支名称"),
    product: ProductsEnum = Field(description="产品/网元名称")
):
    """[意图16] 通过分支名称查询产品配套版本信息"""
    return {"result": f"分支 {branch_name} 对应的 {product} 版本是 V200R002"}

@tool
def query_product_by_hert_version(
    hert_version: str = Field(description="HERT版本号，必须以 'HERT BBU' 开头"),
    product: ProductsEnum = Field(description="产品/网元名称")
):
    """[意图17] 通过HERT版本号查询产品配套版本信息"""
    return {"result": f"版本 {hert_version} 对应的 {product} 配套包是 Package_A"}


# 定义一个“状态修改器”函数
# 这个函数会在每次调用 LLM 之前执行，负责把历史记录剪短

# 将工具放入列表
# 汇总所有工具


@before_model
def memory_trimming_middleware(state, runtime=None):
    """
    视图层中间件：只给模型看最近 10 条消息，节省 Token。
    """
    messages = state["messages"]

    # 智能修剪
    trimmed_messages = trim_messages(
        messages,
        strategy="last",
        token_counter=len,
        max_tokens=10,
        start_on="human",
        include_system=True,
        allow_partial=False,
    )

    # 兜底补充 System Prompt
    if not isinstance(trimmed_messages[0], SystemMessage):
        trimmed_messages = [SystemMessage(content=SYSTEM_PROMPT)] + trimmed_messages

    # 【重要】返回一个字典，代表对 State 的临时更新
    # 这样模型看到的 "messages" 就是剪裁过的版本
    return {"messages": trimmed_messages}

llm = ChatOpenAI(
    model="deepseek-chat",  # 或 gpt-4o
    api_key=os.getenv("DEEPSEEK_API_KEY"),
    base_url="https://api.deepseek.com",
    temperature=0  # 任务型 Agent 温度设为 0 以保证精准
)
tools_list = [
    query_hert_node_on_rb, query_trunk_mirror_info, query_bugfix_branch_info,
    query_version_push_status, query_component_merge_status, query_version_basic_info,
    query_version_by_multimode, query_spc_commercial_status, query_merge_info_between_versions,
    query_mr_info, check_trunk_build_status,
    query_component_by_node, query_component_by_branch, query_component_by_hert_version,
    query_product_by_node, query_product_by_branch, query_product_by_hert_version
]
# ==========================================
# 3. 配置 LLM 与 System Prompt
# ==========================================

# 你的原始 Prompt 核心逻辑，转化为 System Prompt
SYSTEM_PROMPT = """你是一个专业的 IT 运维意图识别专家 Agent。
你的任务是根据用户的输入，调用对应的工具来查询数据。

### 核心规则 (Entity & Logic)
1. **实体识别**：
   - 严格区分 **组件(Component)** (如 iware, rtos) 和 **产品(Product)** (如 nodeb, gbts)。
   - 参数 `component_name` 和 `product_name` 必须从预定义的列表中提取。

2. **参数特征识别**：
   - **分支 (Branch)**: 包含 "/" 或 "hert_bugfix" 等字样。特别注意："hert分支" 属于 Branch，而不是 HERT Version。
   - **HERT版本**: 必须以 "HERT BBU" 开头。
   - **节点号 (Node)**: 长字符串，通常是 Hash 值或 ID。

3. **交互原则**：
   - 如果用户只提供了查询对象（如“查一下iware”），但缺少查询条件（节点？分支？），**不要瞎编参数**。
   - 请礼貌地反问用户缺少的信息。例如：“您是想在哪个分支、节点，还是特定版本下查询 iware？”
   - 一旦收集齐参数，立即调用对应的工具。

### 映射矩阵参考
- Node + Component -> 调用 query_component_by_node
- Branch + Component -> 调用 query_component_by_branch
- HERT Version + Product -> 调用 query_product_by_hert_version
"""
db_path = "agent_chat_history.db" # 这会在你项目根目录生成一个文件
conn = sqlite3.connect(db_path, check_same_thread=False)

# 3. 初始化持久化存储器
memory = SqliteSaver(conn)
agent = create_agent(
    model=llm,
    tools=tools_list,
    system_prompt=SYSTEM_PROMPT,

    # 启用记忆持久化 (可选)
    # 把我们的修剪逻辑传给 state_modifier
    # 这样，虽然数据库里存了 100 条，但 LLM 每次只看到最近 10 条 + System Prompt

    checkpointer=memory,

    # LangChain 1.0 新特性：中间件 (Middleware)
    # 这里我们可以留空，或者添加用于日志、鉴权、限流的中间件
    # middleware=[memory_trimming_middleware],
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