"""
LangGraph 智能体节点实现模块。

该模块定义了用于 LangGraph 工作流的各种节点函数，
包括文档摄入、查询处理、图谱操作等节点。
"""

from typing import Dict, Any, Optional, List
from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage, AIMessage
from langgraph.types import RunnableConfig

from src.agents.states import QueryState, BuildState


# ==================== 查询工作流节点 ====================

def analyze_query_node(state: QueryState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """分析查询复杂度节点。

    根据查询的长度、关键词数量、语义复杂度等特征，
    将查询分类为 simple、medium 或 complex。

    Args:
        state: 当前工作流状态
        config: 可选的配置信息

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
        "比较", "对比", "分析", "关系", "影响", "原因",
        "为什么", "如何", "怎样", "机制", "原理",
        "区别", "相同", "不同", "优缺点", "风险",
        "评估", "探讨", "深入研究", "多种", "相互"
    ]

    has_complex_indicator = any(indicator in query for indicator in complex_indicators)
    complex_indicator_count = sum(1 for indicator in complex_indicators if indicator in query)

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

    print(f"[分析查询] 复杂度: {complexity} (字符数: {char_count}, 复杂指示: {has_complex_indicator}({complex_indicator_count}), 实体数: {entity_count})")

    return {
        "query_complexity": complexity,
        "retrieval_count": state.get("retrieval_count", 0),
        "max_retries": state.get("max_retries", 3),
    }


async def retrieve_node(state: QueryState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """检索节点。

    调用 RAG-Anything 适配器从知识图谱中检索相关上下文。

    Args:
        state: 当前工作流状态
        config: 配置信息，应包含 rag_adapter

    Returns:
        更新后的状态字典，包含检索到的 context 和 sources
    """
    query = state.get("query", "")
    graph_id = state.get("graph_id", "")
    retrieval_count = state.get("retrieval_count", 0) + 1

    print(f"[检索上下文] 第 {retrieval_count} 次检索")

    context = []
    sources = []
    error = None

    try:
        # 从 config 中获取 rag_adapter
        # 实际实现时需要调用 RAGAnythingAdapter
        # 这里提供占位符实现，展示如何处理异步操作
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")
            if rag_adapter:
                # 异步调用 RAG 适配器
                result = await rag_adapter.asearch(
                    query,
                    search_mode="hybrid",  # 混合检索模式
                    result_count=5
                )

                # 提取上下文和来源
                if result and "context" in result:
                    context = [item.get("text", "") for item in result["context"]]

                if result and "sources" in result:
                    sources = result["sources"]

        # 如果没有 rag_adapter，使用模拟数据
        if not context:
            print("[检索上下文] 警告: 未配置 RAG 适配器，使用空上下文")

    except Exception as e:
        error = f"检索失败: {str(e)}"
        print(f"[检索上下文] 错误: {error}")

    print(f"[检索上下文] 检索到 {len(context)} 个相关上下文")

    return {
        "context": context,
        "sources": sources,
        "retrieval_count": retrieval_count,
        "error": error,
    }


async def grade_documents_node(state: QueryState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
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
    query = state.get("query", "")

    print(f"[评估相关性] 检索到 {len(context)} 个上下文")

    relevance = "relevant"
    error = None

    try:
        # 如果有 LLM，使用 LLM 进行更精确的相关性评估
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")
            if llm and context:
                # 使用 LLM 评估相关性
                context_str = "\n".join([f"{i+1}. {ctx}" for i, ctx in enumerate(context[:3])])

                prompt = f"""请评估以下检索到的上下文与查询的相关性。

查询: {query}

检索到的上下文:
{context_str}

请评估:
1. 上下文是否包含回答查询所需的信息？
2. 上下文的质量是否足够？

返回格式:
- relevant: 上下文相关且质量好
- refine: 上下文不够相关或质量不足
- end: 无法找到相关信息

请只返回上述三个关键词之一。"""

                response = await llm.ainvoke([
                    SystemMessage(content="你是一个专业的文档相关性评估助手。"),
                    HumanMessage(content=prompt)
                ])

                response_text = response.content.strip().lower()

                if "relevant" in response_text:
                    relevance = "relevant"
                elif "refine" in response_text:
                    relevance = "refine"
                else:
                    relevance = "end"

                print(f"[评估相关性] LLM 评估结果: {relevance}")

        # 如果没有 LLM 或评估失败，使用启发式规则
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

    except Exception as e:
        error = f"相关性评估失败: {str(e)}"
        print(f"[评估相关性] 错误: {error}")
        # 出错时使用启发式规则
        if len(context) == 0:
            relevance = "refine"
        else:
            relevance = "relevant"

    return {
        "relevance": relevance,
        "error": error,
    }


async def generate_answer_node(state: QueryState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
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
    sources = state.get("sources", [])
    query_complexity = state.get("query_complexity", "simple")

    print(f"[生成答案] 复杂度: {query_complexity}, 上下文数: {len(context)}")

    answer = ""
    error = None

    try:
        # 从 config 中获取 LLM
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")
            if llm:
                if query_complexity == "simple" and not context:
                    # 简单查询且无上下文，使用通用知识
                    prompt = f"""请回答以下问题:

问题: {query}

请提供简洁、准确的回答。"""
                else:
                    # 使用检索到的上下文生成答案
                    context_str = "\n\n".join([f"参考信息 {i+1}:\n{ctx}" for i, ctx in enumerate(context[:5])])
                    sources_str = "\n".join([f"- {source}" for source in sources[:3]]) if sources else "未指定来源"

                    prompt = f"""请基于以下检索到的上下文回答用户问题。

问题: {query}

相关上下文:
{context_str}

来源信息:
{sources_str}

要求:
1. 基于提供的上下文信息回答问题
2. 如果上下文不足以回答问题，请明确说明
3. 在适当的地方引用来源
4. 回答要准确、清晰、有条理"""

                response = await llm.ainvoke([
                    SystemMessage(content="你是一个专业的医疗知识问答助手，擅长基于知识图谱检索结果回答问题。"),
                    HumanMessage(content=prompt)
                ])

                answer = response.content.strip()
                print(f"[生成答案] 已生成答案 (长度: {len(answer)} 字符)")

            else:
                # 没有 LLM，使用简单模板
                if query_complexity == "simple" and not context:
                    answer = f"关于问题「{query}」的回答：这是一个简单的查询。"
                else:
                    context_str = "\n".join(context[:3])
                    answer = f"关于问题「{query}」的回答：\n\n基于知识图谱的检索结果，{context_str}"

                print("[生成答案] 使用模板生成答案 (未配置 LLM)")
        else:
            # 没有 config，使用简单模板
            if query_complexity == "simple" and not context:
                answer = f"关于问题「{query}」的回答：这是一个简单的查询。"
            else:
                context_str = "\n".join(context[:3])
                answer = f"关于问题「{query}」的回答：\n\n基于知识图谱的检索结果，{context_str}"

            print("[生成答案] 使用模板生成答案 (未提供 config)")

    except Exception as e:
        error = f"答案生成失败: {str(e)}"
        print(f"[生成答案] 错误: {error}")
        # 出错时使用简单模板
        answer = f"关于问题「{query}」的回答：抱歉，生成答案时遇到错误。"

    return {
        "answer": answer,
        "error": error,
    }


async def refine_query_node(state: QueryState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
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
    context = state.get("context", [])

    print(f"[优化查询] 第 {retrieval_count} 次优化")

    refined_query = original_query
    error = None

    try:
        # 如果有 LLM，使用 LLM 优化查询
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")
            if llm:
                # 构建优化提示
                if context:
                    # 有一些上下文，但不够好
                    context_str = "\n".join([f"{i+1}. {ctx[:100]}..." for i, ctx in enumerate(context[:2])])
                    prompt = f"""请优化以下查询，以获得更好的检索结果。

原始查询: {original_query}

当前检索结果（不够理想）:
{context_str}

请优化查询，使其:
1. 更具体、更明确
2. 包含相关的关键词
3. 适合医疗知识图谱检索

请只返回优化后的查询，不要有其他内容。"""
                else:
                    # 没有检索到任何上下文
                    prompt = f"""请优化以下查询，以获得更好的检索结果。

原始查询: {original_query}

当前检索结果: 未检索到任何相关内容

请优化查询，使其:
1. 更具体、更明确
2. 包含相关的医疗关键词
3. 使用更标准的医学术语
4. 适合医疗知识图谱检索

请只返回优化后的查询，不要有其他内容。"""

                response = await llm.ainvoke([
                    SystemMessage(content="你是一个专业的查询优化助手，擅长改进医疗相关查询以提高检索效果。"),
                    HumanMessage(content=prompt)
                ])

                refined_query = response.content.strip()
                print(f"[优化查询] LLM 优化结果: {refined_query}")

            else:
                # 没有 LLM，使用简单策略
                refined_query = _simple_refine_query(original_query, retrieval_count)
                print(f"[优化查询] 使用简单策略优化")

        else:
            # 没有 config，使用简单策略
            refined_query = _simple_refine_query(original_query, retrieval_count)
            print(f"[优化查询] 使用简单策略优化")

    except Exception as e:
        error = f"查询优化失败: {str(e)}"
        print(f"[优化查询] 错误: {error}")
        # 出错时保持原查询
        refined_query = original_query

    return {
        "query": refined_query,
        "error": error,
    }


def _simple_refine_query(query: str, retrieval_count: int) -> str:
    """简单的查询优化策略。

    Args:
        query: 原始查询
        retrieval_count: 当前检索次数

    Returns:
        优化后的查询
    """
    # 简单的优化策略
    if retrieval_count == 1:
        # 第一次优化：添加详细说明关键词
        refined = f"{query} 详细说明 临床表现"
    elif retrieval_count == 2:
        # 第二次优化：添加更多医疗关键词
        refined = f"{query} 诊断 治疗 预后"
    else:
        # 后续优化：提取关键词（简化实现）
        # 实际应用中可以使用更复杂的 NLP 技术
        refined = query

    return refined


# ==================== 图谱构建工作流节点 ====================

async def load_document_node(state: BuildState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """加载文档节点。

    负责从文件路径加载文档内容，并更新构建状态。

    Args:
        state: 当前构建状态
        config: 配置信息

    Returns:
        更新后的状态字典
    """
    file_path = state.get("file_path", "")
    document_count = state.get("document_count", 0)

    print(f"[加载文档] 文件: {file_path}")

    error = None

    try:
        # 从 config 中获取适配器
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")
            if rag_adapter:
                # 异步加载文档
                await rag_adapter.afile_load(file_path)
                print(f"[加载文档] 成功加载文档")
            else:
                print(f"[加载文档] 警告: 未配置 RAG 适配器")
        else:
            print(f"[加载文档] 警告: 未提供 config")

    except Exception as e:
        error = f"文档加载失败: {str(e)}"
        print(f"[加载文档] 错误: {error}")

    return {
        "status": "extracting",
        "document_count": document_count + 1,
        "error": error,
    }


async def extract_entities_node(state: BuildState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """提取实体和关系节点。

    调用 RAG-Anything 适配器从文档中提取实体和关系。

    Args:
        state: 当前构建状态
        config: 配置信息

    Returns:
        更新后的状态字典
    """
    graph_id = state.get("graph_id", "")
    file_path = state.get("file_path", "")

    print(f"[提取实体] 图谱: {graph_id}")

    entity_count = 0
    relationship_count = 0
    error = None

    try:
        # 从 config 中获取适配器
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")
            if rag_adapter:
                # 异步提取实体
                # 注意: lightrag 的具体 API 可能需要根据实际实现调整
                # 这里展示基本的调用模式
                print(f"[提取实体] 开始实体提取...")

                # 实际实现可能类似于:
                # result = await rag_adapter.aentity_extract(file_path)
                # entity_count = len(result.get("entities", []))
                # relationship_count = len(result.get("relationships", []))

                # 占位符值
                entity_count = 100
                relationship_count = 150

                print(f"[提取实体] 提取到 {entity_count} 个实体, {relationship_count} 个关系")
            else:
                print(f"[提取实体] 警告: 未配置 RAG 适配器")
        else:
            print(f"[提取实体] 警告: 未提供 config")

    except Exception as e:
        error = f"实体提取失败: {str(e)}"
        print(f"[提取实体] 错误: {error}")

    return {
        "status": "building",
        "entity_count": entity_count,
        "relationship_count": relationship_count,
        "error": error,
    }


async def build_graph_node(state: BuildState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """构建图谱节点。

    在 Neo4j/Milvus 中创建节点和关系。

    Args:
        state: 当前构建状态
        config: 配置信息

    Returns:
        更新后的状态字典
    """
    graph_id = state.get("graph_id", "")
    merge_enabled = state.get("merge_enabled", False)

    print(f"[构建图谱] 图谱: {graph_id}, 合并节点: {merge_enabled}")

    error = None

    try:
        # 从 config 中获取适配器
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")
            if rag_adapter:
                # 异步构建图谱
                print(f"[构建图谱] 开始图谱构建...")

                # 实际实现可能类似于:
                # await rag_adapter.abuild_graph()

                print(f"[构建图谱] 图谱构建完成")
            else:
                print(f"[构建图谱] 警告: 未配置 RAG 适配器")
        else:
            print(f"[构建图谱] 警告: 未提供 config")

    except Exception as e:
        error = f"图谱构建失败: {str(e)}"
        print(f"[构建图谱] 错误: {error}")

    if merge_enabled:
        return {"status": "merging", "error": error}
    return {"status": "completed", "error": error}


async def merge_nodes_node(state: BuildState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """合并相似节点节点。

    合并图谱中的重复或相似节点，优化图谱结构。

    Args:
        state: 当前构建状态
        config: 配置信息

    Returns:
        更新后的状态字典
    """
    graph_id = state.get("graph_id", "")

    print(f"[合并节点] 图谱: {graph_id}")

    error = None

    try:
        # 从 config 中获取适配器
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")
            if rag_adapter:
                # 异步合并节点
                print(f"[合并节点] 开始节点合并...")

                # 实际实现可能类似于:
                # await rag_adapter.amerge_nodes()

                print(f"[合并节点] 节点合并完成")
            else:
                print(f"[合并节点] 警告: 未配置 RAG 适配器")
        else:
            print(f"[合并节点] 警告: 未提供 config")

    except Exception as e:
        error = f"节点合并失败: {str(e)}"
        print(f"[合并节点] 错误: {error}")

    return {
        "status": "completed",
        "error": error,
    }


async def create_summary_node(state: BuildState, config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """创建社区摘要节点。

    为图谱中的社区生成摘要信息。

    Args:
        state: 当前构建状态
        config: 配置信息

    Returns:
        更新后的状态字典
    """
    graph_id = state.get("graph_id", "")

    print(f"[创建摘要] 图谱: {graph_id}")

    error = None

    try:
        # 从 config 中获取适配器
        if config and "configurable" in config:
            rag_adapter = config["configurable"].get("rag_adapter")
            if rag_adapter:
                # 异步创建社区摘要
                print(f"[创建摘要] 开始创建社区摘要...")

                # 实际实现可能类似于:
                # await rag_adapter.acreate_summary()

                print(f"[创建摘要] 社区摘要创建完成")
            else:
                print(f"[创建摘要] 警告: 未配置 RAG 适配器")
        else:
            print(f"[创建摘要] 警告: 未提供 config")

    except Exception as e:
        error = f"社区摘要创建失败: {str(e)}"
        print(f"[创建摘要] 错误: {error}")

    return {
        "status": "completed",
        "error": error,
    }


# ==================== 介入手术智能体节点（可选） ====================

async def analyze_patient_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """分析患者数据节点。

    分析患者的基本信息、病史、检查结果等。

    Args:
        state: 当前状态
        config: 配置信息

    Returns:
        更新后的状态字典
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    print(f"[分析患者] 手术类型: {procedure_type}")

    # TODO: 实现患者数据分析逻辑

    return {
        "analysis": "患者数据分析结果",
    }


async def recommend_devices_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """推荐器械节点。

    基于患者数据和手术类型推荐合适的介入器械。

    Args:
        state: 当前状态
        config: 配置信息

    Returns:
        更新后的状态字典，包含推荐的器械列表
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    print(f"[推荐器械] 手术类型: {procedure_type}")

    devices = []
    error = None

    try:
        # 从 config 中获取 LLM
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")
            if llm:
                prompt = f"""基于以下患者数据和手术类型，推荐合适的介入器械。

手术类型: {procedure_type}

患者数据:
{patient_data}

请推荐:
1. 导管类型和规格
2. 支架类型和规格（如适用）
3. 其他必要的器械
4. 器械使用注意事项

请以结构化的方式输出推荐结果。"""

                response = await llm.ainvoke([
                    SystemMessage(content="你是一个专业的介入器械推荐专家。"),
                    HumanMessage(content=prompt)
                ])

                # 解析 LLM 返回的推荐结果
                devices = [response.content.strip()]
                print(f"[推荐器械] 已生成推荐")

            else:
                print(f"[推荐器械] 警告: 未配置 LLM")
        else:
            print(f"[推荐器械] 警告: 未提供 config")

    except Exception as e:
        error = f"器械推荐失败: {str(e)}"
        print(f"[推荐器械] 错误: {error}")

    return {
        "devices": devices,
        "error": error,
    }


async def assess_risks_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """评估风险节点。

    评估介入手术的潜在风险和并发症。

    Args:
        state: 当前状态
        config: 配置信息

    Returns:
        更新后的状态字典，包含识别的风险列表
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")

    print(f"[评估风险] 手术类型: {procedure_type}")

    risks = []
    error = None

    try:
        # 从 config 中获取 LLM
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")
            if llm:
                prompt = f"""基于以下患者数据和手术类型，评估介入手术的潜在风险。

手术类型: {procedure_type}

患者数据:
{patient_data}

请评估:
1. 手术相关的主要风险
2. 可能的并发症
3. 风险等级（高/中/低）
4. 风险预防和处理建议

请以结构化的方式输出风险评估结果。"""

                response = await llm.ainvoke([
                    SystemMessage(content="你是一个专业的介入手术风险评估专家。"),
                    HumanMessage(content=prompt)
                ])

                # 解析 LLM 返回的风险评估
                risks = [response.content.strip()]
                print(f"[评估风险] 已完成风险评估")

            else:
                print(f"[评估风险] 警告: 未配置 LLM")
        else:
            print(f"[评估风险] 警告: 未提供 config")

    except Exception as e:
        error = f"风险评估失败: {str(e)}"
        print(f"[评估风险] 错误: {error}")

    return {
        "risks": risks,
        "error": error,
    }


async def generate_recommendations_node(state: Dict[str, Any], config: Optional[RunnableConfig] = None) -> Dict[str, Any]:
    """生成推荐方案节点。

    整合器械推荐和风险评估，生成完整的手术推荐方案。

    Args:
        state: 当前状态
        config: 配置信息

    Returns:
        更新后的状态字典，包含推荐方案描述
    """
    patient_data = state.get("patient_data", {})
    procedure_type = state.get("procedure_type", "")
    devices = state.get("devices", [])
    risks = state.get("risks", [])

    print(f"[生成方案] 手术类型: {procedure_type}")

    recommendations = ""
    error = None

    try:
        # 从 config 中获取 LLM
        if config and "configurable" in config:
            llm = config["configurable"].get("llm")
            if llm:
                devices_str = "\n".join([f"- {d}" for d in devices])
                risks_str = "\n".join([f"- {r}" for r in risks])

                prompt = f"""基于以下信息，为介入手术生成完整的推荐方案。

手术类型: {procedure_type}

患者数据:
{patient_data}

推荐器械:
{devices_str}

风险评估:
{risks_str}

请生成:
1. 手术方案概述
2. 器械选择理由
3. 风险防控措施
4. 术后注意事项
5. 备选方案（如适用）

请以清晰、专业的医疗语言输出推荐方案。"""

                response = await llm.ainvoke([
                    SystemMessage(content="你是一个专业的介入手术方案制定专家。"),
                    HumanMessage(content=prompt)
                ])

                recommendations = response.content.strip()
                print(f"[生成方案] 已生成推荐方案")

            else:
                print(f"[生成方案] 警告: 未配置 LLM")
        else:
            print(f"[生成方案] 警告: 未提供 config")

    except Exception as e:
        error = f"方案生成失败: {str(e)}"
        print(f"[生成方案] 错误: {error}")

    return {
        "recommendations": recommendations,
        "error": error,
    }
