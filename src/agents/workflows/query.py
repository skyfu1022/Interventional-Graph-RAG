"""
LangGraph 查询工作流模块。

该模块实现了基于图谱的智能查询路由和答案生成工作流。
支持查询复杂度分析、自适应检索、相关性评估和查询优化等功能。
"""

from typing import Literal, Optional, Any
from langgraph.graph import StateGraph, START, END
from langchain_core.language_models import BaseChatModel
from langgraph.types import RunnableConfig
from langgraph.graph.state import CompiledStateGraph

from src.agents.states import QueryState


def create_query_workflow(
    rag_adapter: Any,
    llm: Optional[BaseChatModel] = None,
    checkpointer: Optional[Any] = None,
) -> CompiledStateGraph:
    """创建查询工作流（支持检查点）。

    该工作流实现了智能查询路由机制，根据查询复杂度自动选择处理策略：
    - 简单查询：直接生成答案
    - 中等/复杂查询：执行检索增强生成（RAG）

    工作流支持：
    1. 查询复杂度自动分析
    2. 自适应上下文检索
    3. 文档相关性评估
    4. 查询优化和重试机制
    5. 状态持久化和恢复（通过 checkpointer）

    Args:
        rag_adapter: RAGAnythingAdapter 实例，用于检索和生成
        llm: LLM 实例（可选），用于复杂查询分析和答案生成
        checkpointer: 检查点存储器（可选），用于状态持久化
                     可以是 MemorySaver、SqliteSaver 等

    Returns:
        编译后的 StateGraph 工作流

    Example:
        >>> from src.core.adapters import RAGAnythingAdapter
        >>> from langchain_openai import ChatOpenAI
        >>> from langgraph.checkpoint.memory import MemorySaver
        >>>
        >>> adapter = RAGAnythingAdapter(...)
        >>> llm = ChatOpenAI(model="gpt-4")
        >>> memory = MemorySaver()
        >>> workflow = create_query_workflow(adapter, llm, checkpointer=memory)
        >>> config = {"configurable": {"thread_id": "query-123"}}
        >>> result = workflow.invoke({
        ...     "query": "什么是高血压？",
        ...     "graph_id": "medical_graph"
        ... }, config)
        >>>
        >>> # 从检查点恢复
        >>> restored = workflow.get_state(config)
    """
    # 创建状态图
    workflow = StateGraph(QueryState)

    # 添加节点
    workflow.add_node("analyze_query", analyze_query_node)
    workflow.add_node("retrieve", retrieve_node)
    workflow.add_node("grade_documents", grade_documents_node)
    workflow.add_node("generate_answer", generate_answer_node)
    workflow.add_node("refine_query", refine_query_node)

    # 设置入口点
    workflow.add_edge(START, "analyze_query")

    # 添加条件边：根据查询复杂度决定是否检索
    workflow.add_conditional_edges(
        "analyze_query",
        should_retrieve,
        {
            "simple": "generate_answer",
            "retrieve": "retrieve",
        },
    )

    # 添加条件边：根据检索结果评估相关性
    workflow.add_conditional_edges(
        "grade_documents",
        check_relevance,
        {
            "relevant": "generate_answer",
            "refine": "refine_query",
            "end": END,
        },
    )

    # 添加普通边
    workflow.add_edge("retrieve", "grade_documents")
    workflow.add_edge("refine_query", "retrieve")
    workflow.add_edge("generate_answer", END)

    # 编译工作流（添加检查点支持）
    app = workflow.compile(checkpointer=checkpointer)

    return app


# ==================== 节点函数 ====================


def analyze_query_node(
    state: QueryState, config: Optional[RunnableConfig] = None
) -> dict:
    """分析查询复杂度节点。

    根据查询的长度、关键词数量、语义复杂度等特征，
    将查询分类为 simple、medium 或 complex。

    Args:
        state: 当前工作流状态
        config: 可选的配置信息（包含 rag_adapter 和 llm）

    Returns:
        更新后的状态字典，包含 query_complexity 字段
    """
    query = state.get("query", "")
    query_lower = query.lower()

    # 简单的启发式规则（实际应用中可使用 LLM 进行更复杂的分析）
    # 1. 检查查询长度（使用字符数，更适合中文）
    char_count = len(query)

    # 2. 检查复杂度指示词
    complex_indicators = [
        "比较",
        "对比",
        "分析",
        "关系",
        "影响",
        "原因",
        "为什么",
        "如何",
        "怎样",
        "机制",
        "原理",
        "区别",
        "相同",
        "不同",
        "优缺点",
        "风险",
        "评估",
        "探讨",
        "深入研究",
        "多种",
        "相互",
    ]

    has_complex_indicator = any(indicator in query for indicator in complex_indicators)
    complex_indicator_count = sum(
        1 for indicator in complex_indicators if indicator in query
    )

    # 3. 检查多实体查询
    entity_indicators = ["和", "与", "或", "以及", "还有"]
    entity_count = sum(query_lower.count(indicator) for indicator in entity_indicators)

    # 决定复杂度（调整后的逻辑，更适合中文）
    # simple: 短查询且无复杂指示词且单实体
    # medium: 中等长度或单复杂指示词或少实体
    # complex: 长查询或多复杂指示词或多实体
    if char_count <= 15 and not has_complex_indicator and entity_count == 0:
        complexity = "simple"
    elif char_count <= 50 or (complex_indicator_count <= 2 and entity_count <= 2):
        complexity = "medium"
    else:
        complexity = "complex"

    print(
        f"[分析查询] 复杂度: {complexity} (字符数: {char_count}, 复杂指示: {has_complex_indicator}({complex_indicator_count}), 实体数: {entity_count})"
    )

    return {
        "query_complexity": complexity,
        "retrieval_count": state.get("retrieval_count", 0),
        "max_retries": state.get("max_retries", 3),
    }


def retrieve_node(state: QueryState, config: Optional[RunnableConfig] = None) -> dict:
    """检索节点。

    调用 RAG-Anything 适配器从知识图谱中检索相关上下文。

    Args:
        state: 当前工作流状态
        config: 配置信息，应包含 rag_adapter

    Returns:
        更新后的状态字典，包含检索到的 context 和 sources
    """
    query = state.get("query", "")  # noqa: F841 - 保留用于日志记录和未来 RAG 调用
    graph_id = state.get("graph_id", "")  # noqa: F841 - 保留用于多图谱支持和未来扩展
    retrieval_count = state.get("retrieval_count", 0) + 1

    print(f"[检索上下文] 第 {retrieval_count} 次检索")

    # TODO: 实际实现时需要调用 RAGAnythingAdapter
    # 这里提供占位符实现
    context = []
    sources = []

    # 模拟检索结果（实际应用中替换为真实的 RAG 调用）
    # rag_adapter = config.get("rag_adapter") if config else None
    # if rag_adapter:
    #     result = rag_adapter.retrieve(query, graph_id=graph_id)
    #     context = result.get("context", [])
    #     sources = result.get("sources", [])

    print(f"[检索上下文] 检索到 {len(context)} 个相关上下文")

    return {
        "context": context,
        "sources": sources,
        "retrieval_count": retrieval_count,
    }


def grade_documents_node(
    state: QueryState, config: Optional[RunnableConfig] = None
) -> dict:
    """评估文档相关性节点。

    评估检索到的文档与查询的相关性，决定是否需要优化查询重试。

    Args:
        state: 当前工作流状态
        config: 配置信息，可能包含 llm 用于更精确的相关性评估

    Returns:
        更新后的状态字典，包含相关性评估结果
    """
    context = state.get("context", [])
    retrieval_count = state.get("retrieval_count", 0)
    max_retries = state.get("max_retries", 3)

    print(f"[评估相关性] 检索到 {len(context)} 个上下文")

    # 简单的启发式评估（实际应用中可使用 LLM 进行更精确的评估）
    if len(context) == 0:
        # 没有检索到任何上下文
        relevance = "refine"
        print("[评估相关性] 未检索到上下文，需要优化查询")
    elif len(context) < 3:
        # 检索结果较少，可能需要优化
        if retrieval_count >= max_retries:
            relevance = "end"
            print(f"[评估相关性] 达到最大重试次数 ({max_retries})，结束")
        else:
            relevance = "refine"
            print("[评估相关性] 上下文较少，尝试优化查询")
    else:
        # 检索结果充足
        relevance = "relevant"
        print("[评估相关性] 上下文充足，可以生成答案")

    return {
        "relevance": relevance,
    }


def generate_answer_node(
    state: QueryState, config: Optional[RunnableConfig] = None
) -> dict:
    """生成答案节点。

    基于查询和检索到的上下文生成最终答案。

    Args:
        state: 当前工作流状态
        config: 配置信息，应包含 llm 用于生成答案

    Returns:
        更新后的状态字典，包含生成的 answer
    """
    query = state.get("query", "")
    context = state.get("context", [])
    query_complexity = state.get("query_complexity", "simple")

    print(f"[生成答案] 复杂度: {query_complexity}, 上下文数: {len(context)}")

    # TODO: 实际实现时需要使用 LLM 生成答案
    # 这里提供占位符实现
    if query_complexity == "simple" and not context:
        # 简单查询且无上下文，使用通用知识
        answer = f"关于问题「{query}」的回答：这是一个简单的查询。"
    else:
        # 使用检索到的上下文生成答案
        context_str = "\n".join(context[:3])  # 使用前3个上下文
        answer = f"关于问题「{query}」的回答：\n\n基于知识图谱的检索结果，{context_str}"

    print("[生成答案] 已生成答案")

    return {
        "answer": answer,
    }


def refine_query_node(
    state: QueryState, config: Optional[RunnableConfig] = None
) -> dict:
    """优化查询节点。

    当检索结果不理想时，优化查询表达式以便重新检索。

    Args:
        state: 当前工作流状态
        config: 配置信息，可能包含 llm 用于查询优化

    Returns:
        更新后的状态字典，包含优化后的 query
    """
    original_query = state.get("query", "")
    retrieval_count = state.get("retrieval_count", 0)

    print(f"[优化查询] 第 {retrieval_count} 次优化")

    # TODO: 实际实现时可以使用 LLM 优化查询
    # 这里提供简单的占位符实现
    # 策略1: 添加上下文扩展词
    # 策略2: 提取关键实体
    # 策略3: 重述查询

    # 简单实现：保持原查询（实际应用中应使用 LLM 优化）
    refined_query = original_query

    # 示例优化策略（可选实现）
    # if retrieval_count == 1:
    #     # 第一次优化：添加相关上下文词
    #     refined_query = f"{original_query} 详细说明"
    # elif retrieval_count == 2:
    #     # 第二次优化：更具体的查询
    #     refined_query = f"{original_query} 临床表现 诊断 治疗"

    print("[优化查询] 保持原查询（实际应用中应使用 LLM 优化）")

    return {
        "query": refined_query,
    }


# ==================== 条件边函数 ====================


def should_retrieve(state: QueryState) -> Literal["simple", "retrieve"]:
    """判断是否需要检索。

    根据查询复杂度决定执行路径：
    - simple: 直接生成答案，跳过检索
    - retrieve: 执行检索增强生成

    Args:
        state: 当前工作流状态

    Returns:
        "simple" 或 "retrieve"
    """
    complexity = state.get("query_complexity", "simple")

    if complexity == "simple":
        print("[路由决策] 简单查询，直接生成答案")
        return "simple"
    else:
        print(f"[路由决策] 复杂查询({complexity})，执行检索")
        return "retrieve"


def check_relevance(state: QueryState) -> Literal["relevant", "refine", "end"]:
    """检查检索相关性并决定下一步。

    根据相关性评估结果决定：
    - relevant: 检索结果相关，生成答案
    - refine: 检索结果不相关，优化查询后重试
    - end: 达到最大重试次数，结束流程

    Args:
        state: 当前工作流状态

    Returns:
        "relevant"、"refine" 或 "end"
    """
    relevance = state.get("relevance", "relevant")
    retrieval_count = state.get("retrieval_count", 0)
    max_retries = state.get("max_retries", 3)

    if relevance == "relevant":
        print("[相关性检查] 检索结果相关，生成答案")
        return "relevant"
    elif retrieval_count >= max_retries:
        print("[相关性检查] 达到最大重试次数，结束流程")
        return "end"
    else:
        print(f"[相关性检查] 优化查询后重试 (当前: {retrieval_count}/{max_retries})")
        return "refine"
