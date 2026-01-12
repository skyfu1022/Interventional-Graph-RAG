"""
介入性治疗 SDK 客户端模块。

该模块提供介入性治疗规划功能的 Python SDK 客户端接口，
用于与 Medical Graph RAG 系统的介入性治疗智能体进行交互。

主要功能:
- 术前规划（plan_intervention）
- 术前风险评估（assess_preop_risks）
- 器械推荐（get_device_recommendations）
- 手术模拟（simulate_procedure，流式）
- 临床指南查询（get_guidelines）
- 术后护理规划（plan_postop_care）

使用示例:
    >>> from src.sdk.interventional import InterventionalClient
    >>> import asyncio
    >>>
    >>> async def main():
    >>>     # 使用异步上下文管理器（推荐）
    >>>     async with InterventionalClient() as client:
    >>>         # 术前规划
    >>>         plan = await client.plan_intervention(
    >>>             patient_data={
    >>>                 "age": 65,
    >>>                 "gender": "male",
    >>>                 "diagnosis": ["冠心病"],
    >>>                 "comorbidities": ["高血压", "糖尿病"]
    >>>             },
    >>>             procedure_type="PCI"
    >>>         )
    >>>         print(plan["recommendations"])
    >>>
    >>>         # 流式模拟手术
    >>>         async for chunk in client.simulate_procedure(
    >>>             procedure_type="PCI",
    >>>             patient_data=patient_data
    >>>         ):
    >>>             print(chunk, end="")
    >>>
    >>> asyncio.run(main)

基于 LangGraph 工作流和 LightRAG 实现。
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, AsyncIterator
from dataclasses import dataclass, field

from src.sdk.client import MedGraphClient
from src.sdk.exceptions import (
    MedGraphSDKError,
    ConfigError as SDKConfigError,
    ValidationError as SDKValidationError,
)
from src.core.logging import get_logger
from src.core.exceptions import QueryError, ValidationError as CoreValidationError

# 导入工作流
from src.agents.workflows.interventional import create_preop_workflow


# ========== 结果数据类 ==========


@dataclass
class InterventionalPlan:
    """介入性治疗规划结果。

    Attributes:
        procedure_type: 手术类型
        primary_plan: 首选方案
        alternative_plan: 备选方案
        device_recommendations: 器械推荐列表
        risk_assessment: 风险评估结果
        guidelines: 相关临床指南
        recommendations: 完整推荐方案（JSON 格式）
        confidence_score: 置信度分数（0-1）
        reasoning_steps: 推理步骤列表
    """

    procedure_type: str
    primary_plan: Dict[str, Any]
    alternative_plan: Optional[Dict[str, Any]] = None
    device_recommendations: List[Dict[str, Any]] = field(default_factory=list)
    risk_assessment: List[Dict[str, Any]] = field(default_factory=list)
    guidelines: List[Dict[str, Any]] = field(default_factory=list)
    recommendations: str = ""
    confidence_score: float = 0.0
    reasoning_steps: List[Dict[str, Any]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "procedure_type": self.procedure_type,
            "primary_plan": self.primary_plan,
            "alternative_plan": self.alternative_plan,
            "device_recommendations": self.device_recommendations,
            "risk_assessment": self.risk_assessment,
            "guidelines": self.guidelines,
            "recommendations": self.recommendations,
            "confidence_score": self.confidence_score,
            "reasoning_steps": self.reasoning_steps,
            "metadata": self.metadata,
        }


@dataclass
class PreopRiskAssessment:
    """术前风险评估结果。

    Attributes:
        overall_risk_level: 整体风险等级（low, medium, high, critical）
        primary_risk_factors: 主要风险因素列表
        risk_mitigation_strategies: 风险缓解策略列表
        contraindications: 禁忌症列表
        confidence: 评估置信度
        reasoning: 评估推理说明
    """

    overall_risk_level: str
    primary_risk_factors: List[Dict[str, Any]] = field(default_factory=list)
    risk_mitigation_strategies: List[str] = field(default_factory=list)
    contraindications: Dict[str, List[str]] = field(default_factory=dict)
    confidence: float = 0.8
    reasoning: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "overall_risk_level": self.overall_risk_level,
            "primary_risk_factors": self.primary_risk_factors,
            "risk_mitigation_strategies": self.risk_mitigation_strategies,
            "contraindications": self.contraindications,
            "confidence": self.confidence,
            "reasoning": self.reasoning,
            "metadata": self.metadata,
        }


@dataclass
class DeviceRecommendation:
    """器械推荐结果。

    Attributes:
        device_name: 器械名称
        device_type: 器械类型
        specifications: 规格参数
        rationale: 选择理由
        contraindications: 禁忌症
        alternatives: 替代选项
    """

    device_name: str
    device_type: str
    specifications: Dict[str, Any] = field(default_factory=dict)
    rationale: str = ""
    contraindications: List[str] = field(default_factory=list)
    alternatives: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "device_name": self.device_name,
            "device_type": self.device_type,
            "specifications": self.specifications,
            "rationale": self.rationale,
            "contraindications": self.contraindications,
            "alternatives": self.alternatives,
            "metadata": self.metadata,
        }


@dataclass
class GuidelineInfo:
    """临床指南信息。

    Attributes:
        title: 指南标题
        source: 指南来源
        year: 发布年份
        recommendation: 推荐内容
        evidence_level: 证据等级
        indication: 适应症
        contraindication: 禁忌症
    """

    title: str
    source: str
    year: int
    recommendation: str
    evidence_level: str = ""
    indication: str = ""
    contraindication: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "title": self.title,
            "source": self.source,
            "year": self.year,
            "recommendation": self.recommendation,
            "evidence_level": self.evidence_level,
            "indication": self.indication,
            "contraindication": self.contraindication,
            "metadata": self.metadata,
        }


@dataclass
class PostopCarePlan:
    """术后护理计划。

    Attributes:
        monitoring_plan: 监测计划
        medication_plan: 用药计划
        activity_restrictions: 活动限制
        follow_up_schedule: 随访安排
        warning_signs: 警示信号
    """

    monitoring_plan: List[str] = field(default_factory=list)
    medication_plan: List[Dict[str, str]] = field(default_factory=list)
    activity_restrictions: List[str] = field(default_factory=list)
    follow_up_schedule: List[Dict[str, str]] = field(default_factory=list)
    warning_signs: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式。"""
        return {
            "monitoring_plan": self.monitoring_plan,
            "medication_plan": self.medication_plan,
            "activity_restrictions": self.activity_restrictions,
            "follow_up_schedule": self.follow_up_schedule,
            "warning_signs": self.warning_signs,
            "metadata": self.metadata,
        }


# ========== SDK 客户端主类 ==========


class InterventionalClient:
    """介入性治疗 SDK 客户端。

    提供介入性治疗规划相关的功能接口，整合 LangGraph 工作流
    和 LightRAG 知识图谱检索能力。

    Attributes:
        base_client: 基础 MedGraphClient 实例
        logger: 日志记录器

    Example:
        >>> # 使用异步上下文管理器
        >>> async with InterventionalClient() as client:
        >>>     plan = await client.plan_intervention(
        >>>         patient_data={"age": 65, "diagnosis": ["冠心病"]},
        >>>         procedure_type="PCI"
        >>>     )
        >>>     print(plan.recommendations)
        >>>
        >>> # 使用自定义配置
        >>> async with InterventionalClient(
        ...     workspace="interventional",
        ...     log_level="DEBUG"
        ... ) as client:
        >>>     risks = await client.assess_preop_risks(
        ...         patient_data=patient_data,
        ...         procedure_type="PCI"
        ...     )
        >>>     print(risks.overall_risk_level)
    """

    def __init__(
        self, workspace: str = "interventional", log_level: str = "INFO", **kwargs
    ):
        """初始化介入性治疗客户端。

        Args:
            workspace: 工作空间名称
            log_level: 日志级别
            **kwargs: 额外的配置参数

        Raises:
            SDKConfigError: 配置无效
        """
        self.logger = get_logger("InterventionalClient")
        self.workspace = workspace
        self.log_level = log_level
        self._config = kwargs

        # 创建基础客户端（延迟初始化）
        self._base_client: Optional[MedGraphClient] = None
        self._initialized = False

        self.logger.debug(
            f"介入性治疗客户端创建 | 工作空间: {workspace} | "
            f"自定义配置: {len(kwargs)} 项"
        )

    async def __aenter__(self) -> "InterventionalClient":
        """进入异步上下文。

        Returns:
            InterventionalClient: 客户端实例
        """
        self.logger.info(f"进入介入性治疗客户端上下文 | 工作空间: {self.workspace}")

        # 初始化基础客户端
        self._base_client = MedGraphClient(
            workspace=self.workspace, log_level=self.log_level, **self._config
        )

        # 初始化基础客户端
        await self._base_client.__aenter__()

        self._initialized = True
        self.logger.info(f"介入性治疗客户端上下文就绪 | 工作空间: {self.workspace}")

        return self

    async def __aexit__(
        self,
        exc_type: Optional[type],
        exc_val: Optional[Exception],
        exc_tb: Optional[Any],
    ) -> None:
        """退出异步上下文。

        Args:
            exc_type: 异常类型
            exc_val: 异常值
            exc_tb: 异常追踪
        """
        self.logger.info(
            f"退出介入性治疗客户端上下文 | 工作空间: {self.workspace} | "
            f"异常: {exc_type.__name__ if exc_type else '无'}"
        )

        if self._base_client:
            await self._base_client.__aexit__(exc_type, exc_val, exc_tb)

        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """确保客户端已初始化。

        Raises:
            SDKConfigError: 客户端未初始化
        """
        if not self._initialized or not self._base_client:
            raise SDKConfigError(
                "客户端未初始化，请使用 async with 或调用 initialize()",
                config_key="client_initialization",
            )

    # ========== 主要功能方法 ==========

    async def plan_intervention(
        self, patient_data: Dict[str, Any], procedure_type: str, **kwargs
    ) -> InterventionalPlan:
        """术前规划。

        使用完整的术前评估工作流，包括：
        - 意图识别
        - U-Retrieval 知识检索
        - 适应症评估
        - 禁忌症评估
        - 风险评估
        - 器械匹配
        - 方案生成

        Args:
            patient_data: 患者数据字典
                - patient_id: 患者 ID
                - age: 年龄
                - gender: 性别
                - chief_complaint: 主诉
                - diagnosis: 诊断列表
                - comorbidities: 合并症列表
                - medications: 用药列表
                - allergies: 过敏史
                - lab_results: 实验室检查
                - imaging_findings: 影像学发现
            procedure_type: 手术类型（PCI, CAS, TAVI 等）
            **kwargs: 额外的配置参数

        Returns:
            InterventionalPlan: 术前规划结果

        Raises:
            SDKValidationError: 参数验证失败
            MedGraphSDKError: 规划执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with InterventionalClient() as client:
            >>>     plan = await client.plan_intervention(
            ...         patient_data={
            ...             "patient_id": "P001",
            ...             "age": 65,
            ...             "gender": "male",
            ...             "diagnosis": ["冠心病"],
            ...             "comorbidities": ["高血压", "糖尿病"]
            ...         },
            ...         procedure_type="PCI"
            ...     )
            ...     print(plan.primary_plan)
            ...     print(f"置信度: {plan.confidence_score:.2f}")
        """
        await self._ensure_initialized()

        self.logger.info(
            f"执行术前规划 | 手术类型: {procedure_type} | "
            f"患者: {patient_data.get('patient_id', '未知')}"
        )

        try:
            # 构建工作流输入状态
            workflow_input = {
                "patient_data": patient_data,
                "procedure_type": procedure_type,
            }

            # 创建工作流（使用基础客户端的适配器）
            workflow = create_preop_workflow(
                rag_adapter=self._base_client._adapter, llm=kwargs.get("llm")
            )

            # 执行工作流
            config = kwargs.get("config", {})
            if "configurable" not in config:
                config["configurable"] = {}

            # 添加适配器和 LLM 到配置
            config["configurable"]["rag_adapter"] = self._base_client._adapter
            if "llm" in kwargs:
                config["configurable"]["llm"] = kwargs["llm"]

            result = await workflow.ainvoke(workflow_input, config=config)

            # 构建返回结果
            plan = InterventionalPlan(
                procedure_type=procedure_type,
                primary_plan=result.get("procedure_plan", {}).get(
                    "primary_procedure", {}
                ),
                alternative_plan=result.get("procedure_plan", {}).get(
                    "alternative_procedures"
                ),
                device_recommendations=result.get("device_recommendations", []),
                risk_assessment=result.get("risk_assessment", []),
                guidelines=result.get("matched_guidelines", []),
                recommendations=result.get("recommendations", ""),
                confidence_score=result.get("confidence_score", 0.0),
                reasoning_steps=result.get("reasoning_steps", []),
                metadata={
                    "sources": result.get("sources", []),
                    "error": result.get("error"),
                },
            )

            self.logger.info(
                f"术前规划完成 | 置信度: {plan.confidence_score:.2f} | "
                f"推理步骤: {len(plan.reasoning_steps)}"
            )

            return plan

        except CoreValidationError as e:
            self.logger.warning(f"术前规划参数验证失败: {e}")
            raise SDKValidationError(
                str(e),
                field=getattr(e, "field", None),
            ) from e

        except QueryError as e:
            self.logger.error(f"术前规划执行失败: {e}")
            raise MedGraphSDKError(
                f"术前规划失败: {e}",
                details={"procedure_type": procedure_type},
            ) from e

        except Exception as e:
            self.logger.error(f"术前规划异常: {e}")
            raise MedGraphSDKError(
                f"术前规划异常: {e}",
                details={"procedure_type": procedure_type},
            ) from e

    async def assess_preop_risks(
        self, patient_data: Dict[str, Any], procedure_type: str, **kwargs
    ) -> PreopRiskAssessment:
        """术前风险评估。

        评估患者进行特定手术的风险等级和主要风险因素。

        Args:
            patient_data: 患者数据字典
            procedure_type: 手术类型
            **kwargs: 额外的配置参数

        Returns:
            PreopRiskAssessment: 风险评估结果

        Raises:
            SDKValidationError: 参数验证失败
            SDKQueryError: 评估执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with InterventionalClient() as client:
            >>>     risks = await client.assess_preop_risks(
            ...         patient_data={"age": 75, "comorbidities": ["糖尿病"]},
            ...         procedure_type="PCI"
            ...     )
            ...     print(f"风险等级: {risks.overall_risk_level}")
            ...     for risk in risks.primary_risk_factors:
            ...         print(f"- {risk['factor']}: {risk['impact']}")
        """
        await self._ensure_initialized()

        self.logger.info(
            f"执行术前风险评估 | 手术类型: {procedure_type} | "
            f"患者: {patient_data.get('patient_id', '未知')}"
        )

        try:
            # 使用完整规划工作流，但只提取风险评估部分
            plan = await self.plan_intervention(
                patient_data=patient_data, procedure_type=procedure_type, **kwargs
            )

            # 提取风险评估信息
            risk_assessment = PreopRiskAssessment(
                overall_risk_level=self._extract_risk_level(plan.risk_assessment),
                primary_risk_factors=plan.risk_assessment,
                risk_mitigation_strategies=self._extract_mitigation_strategies(
                    plan.risk_assessment
                ),
                contraindications=self._extract_contraindications(plan.guidelines),
                confidence=plan.confidence_score,
                reasoning=plan.recommendations[:500] if plan.recommendations else "",
                metadata={"sources": plan.metadata.get("sources", [])},
            )

            self.logger.info(
                f"术前风险评估完成 | 风险等级: {risk_assessment.overall_risk_level} | "
                f"风险因素数: {len(risk_assessment.primary_risk_factors)}"
            )

            return risk_assessment

        except (SDKValidationError, MedGraphSDKError):
            raise
        except Exception as e:
            self.logger.error(f"术前风险评估异常: {e}")
            raise MedGraphSDKError(
                f"术前风险评估异常: {e}",
                details={"procedure_type": procedure_type},
            ) from e

    async def get_device_recommendations(
        self, patient_data: Dict[str, Any], procedure_type: str, **kwargs
    ) -> List[DeviceRecommendation]:
        """获取器械推荐。

        根据患者特征和手术类型推荐合适的介入器械。

        Args:
            patient_data: 患者数据字典
            procedure_type: 手术类型
            **kwargs: 额外的配置参数

        Returns:
            List[DeviceRecommendation]: 器械推荐列表

        Raises:
            SDKValidationError: 参数验证失败
            SDKQueryError: 推荐执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with InterventionalClient() as client:
            >>>     devices = await client.get_device_recommendations(
            ...         patient_data={"age": 65, "anatomy": "左前降支病变"},
            ...         procedure_type="PCI"
            ...     )
            ...     for device in devices:
            ...         print(f"{device.device_name} ({device.device_type})")
            ...         print(f"  理由: {device.rationale}")
        """
        await self._ensure_initialized()

        self.logger.info(
            f"获取器械推荐 | 手术类型: {procedure_type} | "
            f"患者: {patient_data.get('patient_id', '未知')}"
        )

        try:
            # 使用完整规划工作流，但只提取器械推荐部分
            plan = await self.plan_intervention(
                patient_data=patient_data, procedure_type=procedure_type, **kwargs
            )

            # 转换为器械推荐列表
            device_recommendations = []

            for device_dict in plan.device_recommendations:
                if isinstance(device_dict, dict):
                    device_recommendations.append(
                        DeviceRecommendation(
                            device_name=device_dict.get("device_name", ""),
                            device_type=device_dict.get("device_type", ""),
                            specifications=device_dict.get("specifications", {}),
                            rationale=device_dict.get("rationale", ""),
                            contraindications=device_dict.get("contraindications", []),
                            alternatives=device_dict.get("alternatives", []),
                        )
                    )

            self.logger.info(
                f"器械推荐完成 | 推荐器械数: {len(device_recommendations)}"
            )

            return device_recommendations

        except (SDKValidationError, MedGraphSDKError):
            raise
        except Exception as e:
            self.logger.error(f"器械推荐异常: {e}")
            raise MedGraphSDKError(
                f"器械推荐异常: {e}",
                details={"procedure_type": procedure_type},
            ) from e

    async def simulate_procedure(
        self, patient_data: Dict[str, Any], procedure_type: str, **kwargs
    ) -> AsyncIterator[str]:
        """模拟手术过程（流式）。

        逐步生成手术模拟说明，包括：
        - 术前准备
        - 手术步骤
        - 注意事项
        - 应急处理

        Args:
            patient_data: 患者数据字典
            procedure_type: 手术类型
            **kwargs: 额外的配置参数

        Yields:
            str: 流式输出的模拟内容片段

        Raises:
            SDKValidationError: 参数验证失败
            SDKQueryError: 模拟执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with InterventionalClient() as client:
            >>>     async for chunk in client.simulate_procedure(
            ...         patient_data={"age": 65, "diagnosis": ["冠心病"]},
            ...         procedure_type="PCI"
            ...     ):
            ...         print(chunk, end="", flush=True)
        """
        await self._ensure_initialized()

        self.logger.info(
            f"开始手术模拟 | 手术类型: {procedure_type} | "
            f"患者: {patient_data.get('patient_id', '未知')}"
        )

        try:
            # 生成手术模拟内容
            simulation_content = self._generate_simulation_content(
                patient_data, procedure_type
            )

            # 流式输出内容
            chunk_size = 100  # 每次输出 100 字符
            for i in range(0, len(simulation_content), chunk_size):
                chunk = simulation_content[i : i + chunk_size]
                yield chunk

            self.logger.info(f"手术模拟完成 | 手术类型: {procedure_type}")

        except Exception as e:
            self.logger.error(f"手术模拟异常: {e}")
            yield f"\n[模拟失败: {str(e)}]"

    async def get_guidelines(
        self, procedure_type: str, **kwargs
    ) -> List[GuidelineInfo]:
        """获取临床指南。

        检索特定手术类型相关的临床指南。

        Args:
            procedure_type: 手术类型
            **kwargs: 额外的配置参数
                - filters: 过滤条件
                - limit: 返回数量限制

        Returns:
            List[GuidelineInfo]: 临床指南列表

        Raises:
            SDKValidationError: 参数验证失败
            SDKQueryError: 检索执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with InterventionalClient() as client:
            >>>     guidelines = await client.get_guidelines(
            ...         procedure_type="PCI",
            ...         limit=5
            ...     )
            ...     for guideline in guidelines:
            ...         print(f"[{guideline.source} {guideline.year}]")
            ...         print(f"  {guideline.title}")
            ...         print(f"  推荐: {guideline.recommendation}")
        """
        await self._ensure_initialized()

        self.logger.info(f"获取临床指南 | 手术类型: {procedure_type}")

        try:
            # 构建查询
            query_text = f"{procedure_type} 临床指南 适应症 禁忌症 推荐"

            # 使用基础客户端查询
            result = await self._base_client.query(
                query_text=query_text,
                mode="global",
                graph_id=self.workspace,
            )

            # 解析结果为指南列表
            guidelines = self._parse_guidelines_from_result(result, procedure_type)

            limit = kwargs.get("limit", 10)
            if limit and len(guidelines) > limit:
                guidelines = guidelines[:limit]

            self.logger.info(f"临床指南获取完成 | 返回数量: {len(guidelines)}")

            return guidelines

        except (SDKValidationError, MedGraphSDKError):
            raise
        except Exception as e:
            self.logger.error(f"临床指南获取异常: {e}")
            raise MedGraphSDKError(
                f"临床指南获取异常: {e}",
                details={"procedure_type": procedure_type},
            ) from e

    async def plan_postop_care(
        self, patient_data: Dict[str, Any], procedure_type: str, **kwargs
    ) -> PostopCarePlan:
        """术后护理规划。

        生成个性化术后护理计划。

        Args:
            patient_data: 患者数据字典
            procedure_type: 手术类型
            **kwargs: 额外的配置参数

        Returns:
            PostopCarePlan: 术后护理计划

        Raises:
            SDKValidationError: 参数验证失败
            MedGraphSDKError: 规划执行失败
            SDKConfigError: 客户端未初始化

        Example:
            >>> async with InterventionalClient() as client:
            >>>     care_plan = await client.plan_postop_care(
            ...         patient_data={"age": 65, "comorbidities": ["糖尿病"]},
            ...         procedure_type="PCI"
            ...     )
            ...     print("监测计划:")
            ...     for item in care_plan.monitoring_plan:
            ...         print(f"- {item}")
        """
        await self._ensure_initialized()

        self.logger.info(
            f"生成术后护理计划 | 手术类型: {procedure_type} | "
            f"患者: {patient_data.get('patient_id', '未知')}"
        )

        try:
            # 构建查询
            query_parts = [
                f"{procedure_type} 术后护理",
                f"患者年龄: {patient_data.get('age', '未知')}",
            ]

            if patient_data.get("comorbidities"):
                query_parts.append(
                    f"合并症: {', '.join(patient_data['comorbidities'])}"
                )

            query_text = " | ".join(query_parts)

            # 使用基础客户端查询
            result = await self._base_client.query(
                query_text=query_text,
                mode="hybrid",
                graph_id=self.workspace,
            )

            # 解析结果为护理计划
            care_plan = self._parse_care_plan_from_result(
                result, patient_data, procedure_type
            )

            self.logger.info(
                f"术后护理计划生成完成 | "
                f"监测项: {len(care_plan.monitoring_plan)} | "
                f"用药: {len(care_plan.medication_plan)}"
            )

            return care_plan

        except (SDKValidationError, MedGraphSDKError):
            raise
        except Exception as e:
            self.logger.error(f"术后护理计划生成异常: {e}")
            raise MedGraphSDKError(
                f"术后护理计划生成异常: {e}",
                details={"procedure_type": procedure_type},
            ) from e

    # ========== 辅助方法 ==========

    def _extract_risk_level(self, risk_assessment: List[Dict[str, Any]]) -> str:
        """提取整体风险等级。

        Args:
            risk_assessment: 风险评估列表

        Returns:
            风险等级字符串
        """
        if not risk_assessment:
            return "low"

        # 查找最高风险等级
        risk_levels = ["low", "medium", "high", "critical"]

        for level in reversed(risk_levels):
            for risk in risk_assessment:
                if isinstance(risk, dict):
                    impact = risk.get("impact", "").lower()
                else:
                    impact = getattr(risk, "impact", "").lower()

                if level in impact:
                    return level

        return "medium"

    def _extract_mitigation_strategies(
        self, risk_assessment: List[Dict[str, Any]]
    ) -> List[str]:
        """提取风险缓解策略。

        Args:
            risk_assessment: 风险评估列表

        Returns:
            风险缓解策略列表
        """
        strategies = []

        for risk in risk_assessment:
            if isinstance(risk, dict):
                mitigation = risk.get("mitigation_strategy", "")
                if mitigation and mitigation not in strategies:
                    strategies.append(mitigation)

        return strategies

    def _extract_contraindications(
        self, guidelines: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """提取禁忌症信息。

        Args:
            guidelines: 指南列表

        Returns:
            禁忌症字典（absolute/relative）
        """
        contraindications = {
            "absolute": [],
            "relative": [],
        }

        for guideline in guidelines:
            if isinstance(guideline, dict):
                contraindication = guideline.get("contraindication", "")
                if not contraindication:
                    continue

                # 简单分类
                absolute_keywords = ["绝对禁忌", "严禁", "禁止"]
                relative_keywords = ["相对禁忌", "谨慎", "慎重"]

                if any(kw in contraindication for kw in absolute_keywords):
                    contraindications["absolute"].append(contraindication)
                elif any(kw in contraindication for kw in relative_keywords):
                    contraindications["relative"].append(contraindication)

        return contraindications

    def _generate_simulation_content(
        self, patient_data: Dict[str, Any], procedure_type: str
    ) -> str:
        """生成手术模拟内容。

        Args:
            patient_data: 患者数据
            procedure_type: 手术类型

        Returns:
            模拟内容字符串
        """
        # 基于手术类型生成模拟内容
        simulations = {
            "PCI": """
# PCI 手术模拟

## 术前准备
1. 患者体位：平卧位，右上肢外展
2. 消毒铺巾：双侧腹股沟区及前臂消毒
3. 局麻：1% 利多卡因局部浸润麻醉
4. 穿刺：桡动脉/股动脉穿刺，置入鞘管

## 手术步骤
1. 导管插入：沿导丝送入指引导管至冠脉口
2. 导丝通过：将指引导丝送过病变部位
3. 球囊扩张：沿导丝送入球囊，预扩张病变
4. 支架植入：送入药物洗脱支架，精准释放
5. 后扩张：必要时进行后扩张，确保支架贴壁

## 注意事项
- 持续监测心电、血压、血氧饱和度
- 肝素化：ACT 维持在 250-300 秒
- 造影剂使用：控制总量，注意肾功能
- 准备好临时起搏器和 IABP

## 应急处理
- 冠脉穿孔：立即心包穿刺引流
- 支架血栓：立即球囊扩张 + 血栓抽吸
- 边支闭塞：导丝重入 + 球囊扩张
""",
            "CAS": """
# CAS 手术模拟

## 术前准备
1. 神经功能评估
2. 双抗血小板治疗（阿司匹林 + 氯吡格雷）
3. 全身麻醉或局部麻醉

## 手术步骤
1. 股动脉穿刺，置入 8F 鞘管
2. 导管选择性颈动脉造影
3. 路径图指导下，保护伞送至颈内动脉远端
4. 预扩张球囊扩张狭窄段
5. 释放颈动脉支架
6. 后扩张（必要时）
7. 回收保护伞

## 注意事项
- 控制血压：收缩压控制在 140-160 mmHg
- 心率监测：心动过缓时使用阿托品
- 脑保护：全程使用保护伞
""",
            "TAVI": """
# TAVI 手术模拟

## 术前准备
1. CT 评估瓣环尺寸、入路血管
2. 全身麻醉
3. 起搏器置入备用

## 手术步骤
1. 股动脉穿刺，建立入路
2. 临时起搏器置入
3. 球囊预扩张瓣膜（必要时）
4. 送入瓣膜支架系统
5. 准确定位后释放瓣膜
6. 造影评估瓣膜功能
7. 撤出导管，缝合血管

## 注意事项
- 快速起搏：180 次/分，降低心输出量
- 精确定位：避免冠脉开口阻塞
- 防止房室传导阻滞
""",
        }

        return simulations.get(
            procedure_type,
            f"# {procedure_type} 手术模拟\n\n具体手术步骤请参考临床指南。",
        )

    def _parse_guidelines_from_result(
        self, result: Any, procedure_type: str
    ) -> List[GuidelineInfo]:
        """从查询结果解析指南列表。

        Args:
            result: 查询结果
            procedure_type: 手术类型

        Returns:
            指南列表
        """
        guidelines = []

        # 从结果中提取指南信息
        answer = getattr(result, "answer", "")
        if not answer:
            return guidelines

        # 简单解析（实际应用中需要更复杂的 NLP 解析）
        lines = answer.split("\n")
        current_guideline = None

        for line in lines:
            line = line.strip()

            # 检测指南标题
            if any(keyword in line for keyword in ["指南", "Guideline", "推荐"]):
                if current_guideline:
                    guidelines.append(current_guideline)

                current_guideline = {
                    "title": line,
                    "source": "Unknown",
                    "year": 2023,
                    "recommendation": "",
                    "evidence_level": "",
                }

            # 检测证据等级
            elif "Class" in line or "Level" in line:
                if current_guideline:
                    current_guideline["evidence_level"] = line

            # 检测推荐内容
            elif current_guideline and line:
                if current_guideline["recommendation"]:
                    current_guideline["recommendation"] += " " + line
                else:
                    current_guideline["recommendation"] = line

        # 添加最后一个指南
        if current_guideline:
            guidelines.append(current_guideline)

        # 转换为 GuidelineInfo 对象
        return [
            GuidelineInfo(
                title=g["title"],
                source=g["source"],
                year=g["year"],
                recommendation=g["recommendation"],
                evidence_level=g["evidence_level"],
            )
            for g in guidelines
        ]

    def _parse_care_plan_from_result(
        self, result: Any, patient_data: Dict[str, Any], procedure_type: str
    ) -> PostopCarePlan:
        """从查询结果解析护理计划。

        Args:
            result: 查询结果
            patient_data: 患者数据
            procedure_type: 手术类型

        Returns:
            术后护理计划
        """
        # 默认护理计划
        care_plan = PostopCarePlan()

        # 添加基本监测项目
        care_plan.monitoring_plan = [
            "心电监测：持续 24 小时",
            "血压监测：每小时测量，稳定后每 4 小时",
            "穿刺部位观察：每 2 小时检查出血、血肿",
            "肢体末梢循环：每 2 小时评估",
            "症状观察：胸痛、呼吸困难、心悸等",
        ]

        # 添加基本用药计划
        care_plan.medication_plan = [
            {"medication": "阿司匹林", "dosage": "100mg qd", "duration": "长期"},
            {"medication": "氯吡格雷", "dosage": "75mg qd", "duration": "12个月"},
            {"medication": "他汀类药物", "dosage": "睡前服用", "duration": "长期"},
        ]

        # 添加活动限制
        care_plan.activity_restrictions = [
            "术后 24 小时卧床休息",
            "穿刺侧肢体制动 6-8 小时",
            "避免剧烈活动 1 周",
            "避免提重物 (>5kg) 2 周",
        ]

        # 添加随访安排
        care_plan.follow_up_schedule = [
            {"time": "术后 1 周", "purpose": "门诊随访，评估伤口"},
            {"time": "术后 1 月", "purpose": "复查心电图、心脏超声"},
            {"time": "术后 3 月", "purpose": "评估症状，调整用药"},
            {"time": "术后 6 月", "purpose": "全面复查"},
        ]

        # 添加警示信号
        care_plan.warning_signs = [
            "穿刺部位出血、肿胀",
            "胸痛、胸闷加重",
            "呼吸困难、端坐呼吸",
            "心悸、晕厥",
            "发热 (>38°C)",
            "肢体肿胀、疼痛",
        ]

        # 根据患者合并症调整
        if "糖尿病" in patient_data.get("comorbidities", []):
            care_plan.monitoring_plan.append("血糖监测：每日 4 次（空腹 + 三餐后）")

        if "肾功能不全" in patient_data.get("comorbidities", []):
            care_plan.monitoring_plan.append("肾功能监测：术后 3 天、7 天复查")
            care_plan.medication_plan.append(
                {
                    "medication": "水化治疗",
                    "dosage": "1ml/kg/h",
                    "duration": "术后 12 小时",
                }
            )

        return care_plan


# ========== 导出的公共接口 ==========

__all__ = [
    "InterventionalClient",
    "InterventionalPlan",
    "PreopRiskAssessment",
    "DeviceRecommendation",
    "GuidelineInfo",
    "PostopCarePlan",
]
