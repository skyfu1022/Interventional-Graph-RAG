"""
介入性治疗 API 路由模块。

该模块提供介入性治疗相关的 REST API 端点，包括：
- POST /api/v1/interventional/plan - 术前规划
- POST /api/v1/interventional/simulate - 手术模拟（SSE 流式）
- POST /api/v1/interventional/risk-assessment - 术前风险评估
- GET /api/v1/interventional/guidelines/{procedure_type} - 临床指南查询
- GET /api/v1/interventional/devices/{category} - 器械推荐查询
- POST /api/v1/interventional/postop-care - 术后护理规划

所有端点都基于 SDK 的 InterventionalClient 实现。
"""

from typing import AsyncIterator, Optional
import json
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import StreamingResponse
from fastapi import status
from pydantic import BaseModel, Field

from src.sdk.interventional import (
    InterventionalClient,
)
from src.core.logging import get_logger
from src.core.exceptions import QueryError, ValidationError as CoreValidationError

logger = get_logger(__name__)

# 创建路由器
router = APIRouter()


# ========== 请求/响应模型 ==========


class PatientDataModel(BaseModel):
    """患者数据模型。"""

    patient_id: Optional[str] = Field(None, description="患者 ID")
    age: int = Field(..., ge=0, le=150, description="年龄")
    gender: str = Field(..., pattern="^(male|female|other)$", description="性别")
    chief_complaint: Optional[str] = Field(None, description="主诉")
    diagnosis: list[str] = Field(default_factory=list, description="诊断列表")
    comorbidities: list[str] = Field(default_factory=list, description="合并症列表")
    medications: list[str] = Field(default_factory=list, description="用药列表")
    allergies: list[str] = Field(default_factory=list, description="过敏史")
    lab_results: dict = Field(default_factory=dict, description="实验室检查")
    imaging_findings: list[str] = Field(default_factory=list, description="影像学发现")


class InterventionalPlanRequest(BaseModel):
    """术前规划请求模型。"""

    patient_data: PatientDataModel = Field(..., description="患者数据")
    procedure_type: str = Field(..., description="手术类型（PCI, CAS, TAVI 等）")
    include_alternatives: bool = Field(True, description="是否包含备选方案")


class RiskAssessmentRequest(BaseModel):
    """风险评估请求模型。"""

    patient_data: PatientDataModel = Field(..., description="患者数据")
    procedure_type: str = Field(..., description="手术类型")
    include_mitigation: bool = Field(True, description="是否包含缓解策略")


class DeviceRecommendationRequest(BaseModel):
    """器械推荐请求模型。"""

    patient_data: PatientDataModel = Field(..., description="患者数据")
    procedure_type: str = Field(..., description="手术类型")
    include_alternatives: bool = Field(True, description="是否包含替代选项")


class ProcedureSimulationRequest(BaseModel):
    """手术模拟请求模型。"""

    patient_data: PatientDataModel = Field(..., description="患者数据")
    procedure_type: str = Field(..., description="手术类型")
    detail_level: str = Field(
        "standard", pattern="^(basic|standard|detailed)$", description="详细程度"
    )


class PostopCareRequest(BaseModel):
    """术后护理请求模型。"""

    patient_data: PatientDataModel = Field(..., description="患者数据")
    procedure_type: str = Field(..., description="手术类型")


# ========== 响应模型 ==========


class InterventionalPlanResponse(BaseModel):
    """术前规划响应模型。"""

    procedure_type: str = Field(..., description="手术类型")
    primary_plan: dict = Field(..., description="首选方案")
    alternative_plan: Optional[dict] = Field(None, description="备选方案")
    device_recommendations: list[dict] = Field(
        default_factory=list, description="器械推荐"
    )
    risk_assessment: list[dict] = Field(default_factory=list, description="风险评估")
    guidelines: list[dict] = Field(default_factory=list, description="相关指南")
    recommendations: str = Field(..., description="完整推荐方案")
    confidence_score: float = Field(..., ge=0.0, le=1.0, description="置信度分数")
    reasoning_steps: list[dict] = Field(default_factory=list, description="推理步骤")


class RiskAssessmentResponse(BaseModel):
    """风险评估响应模型。"""

    overall_risk_level: str = Field(..., description="整体风险等级")
    primary_risk_factors: list[dict] = Field(
        default_factory=list, description="主要风险因素"
    )
    risk_mitigation_strategies: list[str] = Field(
        default_factory=list, description="风险缓解策略"
    )
    contraindications: dict = Field(default_factory=dict, description="禁忌症")
    confidence: float = Field(..., ge=0.0, le=1.0, description="评估置信度")
    reasoning: str = Field(..., description="评估推理")


class DeviceRecommendationResponse(BaseModel):
    """器械推荐响应模型。"""

    device_name: str = Field(..., description="器械名称")
    device_type: str = Field(..., description="器械类型")
    specifications: dict = Field(default_factory=dict, description="规格参数")
    rationale: str = Field(..., description="选择理由")
    contraindications: list[str] = Field(default_factory=list, description="禁忌症")
    alternatives: list[dict] = Field(default_factory=list, description="替代选项")


class GuidelineResponse(BaseModel):
    """临床指南响应模型。"""

    title: str = Field(..., description="指南标题")
    source: str = Field(..., description="指南来源")
    year: int = Field(..., description="发布年份")
    recommendation: str = Field(..., description="推荐内容")
    evidence_level: str = Field("", description="证据等级")
    indication: str = Field("", description="适应症")
    contraindication: str = Field("", description="禁忌症")


class PostopCareResponse(BaseModel):
    """术后护理响应模型。"""

    monitoring_plan: list[str] = Field(default_factory=list, description="监测计划")
    medication_plan: list[dict] = Field(default_factory=list, description="用药计划")
    activity_restrictions: list[str] = Field(
        default_factory=list, description="活动限制"
    )
    follow_up_schedule: list[dict] = Field(default_factory=list, description="随访安排")
    warning_signs: list[str] = Field(default_factory=list, description="警示信号")


# ========== 辅助函数 ==========


def convert_patient_data_to_dict(patient_data: PatientDataModel) -> dict:
    """将患者数据模型转换为字典。

    Args:
        patient_data: 患者数据模型

    Returns:
        患者数据字典
    """
    return patient_data.model_dump()


async def get_interventional_client() -> InterventionalClient:
    """获取介入性治疗客户端实例。

    Returns:
        InterventionalClient: 客户端实例

    Raises:
        HTTPException: 客户端创建失败
    """
    try:
        # 创建客户端
        client = InterventionalClient()
        await client.__aenter__()
        return client

    except Exception as e:
        logger.error(f"创建介入性治疗客户端失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "ClientCreationError",
                "message": "创建客户端失败",
            },
        ) from e


async def stream_simulation_response(
    patient_data_dict: dict,
    procedure_type: str,
    detail_level: str,
) -> AsyncIterator[str]:
    """流式模拟响应生成器。

    Args:
        patient_data_dict: 患者数据字典
        procedure_type: 手术类型
        detail_level: 详细程度

    Yields:
        str: SSE 格式的数据块
    """
    try:
        client = InterventionalClient()

        async with client:
            async for chunk in client.simulate_procedure(
                patient_data=patient_data_dict,
                procedure_type=procedure_type,
                detail_level=detail_level,
            ):
                # 发送文本块
                data = {"chunk": chunk}
                yield f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

            # 发送完成信号
            done_data = {"done": True}
            yield f"data: {json.dumps(done_data, ensure_ascii=False)}\n\n"

    except Exception as e:
        logger.error(f"流式模拟错误: {e}", exc_info=True)
        error_data = {"error": str(e)}
        yield f"data: {json.dumps(error_data, ensure_ascii=False)}\n\n"


# ========== API 端点 ==========


@router.post(
    "/plan",
    response_model=InterventionalPlanResponse,
    summary="术前规划",
    description="执行完整的术前规划工作流，包括适应症评估、禁忌症评估、风险评估、器械匹配和方案生成。",
    tags=["interventional"],
)
async def create_interventional_plan(
    request: InterventionalPlanRequest,
) -> InterventionalPlanResponse:
    """执行术前规划。

    该端点接收患者数据和手术类型，执行完整的术前评估工作流，
    返回个性化的手术方案建议。

    Args:
        request: 术前规划请求

    Returns:
        InterventionalPlanResponse: 术前规划响应

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 规划执行失败

    Example:
        >>> POST /api/v1/interventional/plan
        >>> {
        >>>     "patient_data": {
        >>>         "age": 65,
        >>>         "gender": "male",
        >>>         "diagnosis": ["冠心病"],
        >>>         "comorbidities": ["高血压", "糖尿病"]
        >>>     },
        >>>     "procedure_type": "PCI"
        >>> }
    """
    logger.info(
        f"收到术前规划请求 | 手术类型: {request.procedure_type} | "
        f"患者: {request.patient_data.patient_id or '未知'}"
    )

    try:
        # 转换患者数据
        patient_data_dict = convert_patient_data_to_dict(request.patient_data)

        # 创建客户端并执行规划
        async with InterventionalClient() as client:
            plan = await client.plan_intervention(
                patient_data=patient_data_dict,
                procedure_type=request.procedure_type,
            )

        # 转换为 API 响应格式
        response = InterventionalPlanResponse(
            procedure_type=plan.procedure_type,
            primary_plan=plan.primary_plan,
            alternative_plan=plan.alternative_plan,
            device_recommendations=plan.device_recommendations,
            risk_assessment=plan.risk_assessment,
            guidelines=plan.guidelines,
            recommendations=plan.recommendations,
            confidence_score=plan.confidence_score,
            reasoning_steps=plan.reasoning_steps,
        )

        logger.info(
            f"术前规划完成 | 置信度: {response.confidence_score:.2f} | "
            f"推理步骤: {len(response.reasoning_steps)}"
        )

        return response

    except CoreValidationError as e:
        logger.warning(f"术前规划参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except QueryError as e:
        logger.error(f"术前规划执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(f"术前规划处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "术前规划处理失败，请稍后重试",
            },
        ) from e


@router.post(
    "/simulate",
    summary="手术模拟",
    description="以流式方式生成手术模拟过程，包括术前准备、手术步骤、注意事项和应急处理。",
    tags=["interventional"],
)
async def simulate_procedure(
    request: ProcedureSimulationRequest,
    http_request: Request,
) -> StreamingResponse:
    """执行手术模拟。

    该端点接收患者数据和手术类型，以 Server-Sent Events (SSE) 格式
    逐块返回手术模拟内容。

    SSE 格式：
    - data: {"chunk": "文本片段"}
    - data: {"done": true}

    Args:
        request: 手术模拟请求
        http_request: FastAPI Request 对象

    Returns:
        StreamingResponse: 流式响应

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 模拟执行失败
        HTTPException 499: 客户端断开连接

    Example:
        >>> POST /api/v1/interventional/simulate
        >>> {
        >>>     "patient_data": {
        >>>         "age": 65,
        >>>         "diagnosis": ["冠心病"]
        >>>     },
        >>>     "procedure_type": "PCI",
        >>>     "detail_level": "standard"
        >>> }
    """
    logger.info(
        f"收到手术模拟请求 | 手术类型: {request.procedure_type} | "
        f"详细程度: {request.detail_level}"
    )

    try:
        # 检查客户端是否断开连接
        if await http_request.is_disconnected():
            logger.info("客户端已断开连接")
            raise HTTPException(
                status_code=status.HTTP_499_REQUEST_CANCELLED,
                detail="客户端已断开连接",
            )

        # 转换患者数据
        patient_data_dict = convert_patient_data_to_dict(request.patient_data)

        # 创建流式响应
        return StreamingResponse(
            stream_simulation_response(
                patient_data_dict=patient_data_dict,
                procedure_type=request.procedure_type,
                detail_level=request.detail_level,
            ),
            media_type="text/event-stream",
            headers={
                "Cache-Control": "no-cache",
                "Connection": "keep-alive",
                "X-Accel-Buffering": "no",
            },
        )

    except CoreValidationError as e:
        logger.warning(f"手术模拟参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except HTTPException:
        raise

    except Exception as e:
        logger.error(f"手术模拟处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "手术模拟处理失败，请稍后重试",
            },
        ) from e


@router.post(
    "/risk-assessment",
    response_model=RiskAssessmentResponse,
    summary="术前风险评估",
    description="评估患者进行特定手术的风险等级和主要风险因素。",
    tags=["interventional"],
)
async def assess_preop_risks(
    request: RiskAssessmentRequest,
) -> RiskAssessmentResponse:
    """执行术前风险评估。

    Args:
        request: 风险评估请求

    Returns:
        RiskAssessmentResponse: 风险评估响应

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 评估执行失败

    Example:
        >>> POST /api/v1/interventional/risk-assessment
        >>> {
        >>>     "patient_data": {
        >>>         "age": 75,
        >>>         "comorbidities": ["糖尿病", "肾功能不全"]
        >>>     },
        >>>     "procedure_type": "PCI"
        >>> }
    """
    logger.info(
        f"收到风险评估请求 | 手术类型: {request.procedure_type} | "
        f"患者: {request.patient_data.patient_id or '未知'}"
    )

    try:
        # 转换患者数据
        patient_data_dict = convert_patient_data_to_dict(request.patient_data)

        # 创建客户端并执行评估
        async with InterventionalClient() as client:
            risks = await client.assess_preop_risks(
                patient_data=patient_data_dict,
                procedure_type=request.procedure_type,
            )

        # 转换为 API 响应格式
        response = RiskAssessmentResponse(
            overall_risk_level=risks.overall_risk_level,
            primary_risk_factors=risks.primary_risk_factors,
            risk_mitigation_strategies=risks.risk_mitigation_strategies,
            contraindications=risks.contraindications,
            confidence=risks.confidence,
            reasoning=risks.reasoning,
        )

        logger.info(
            f"术前风险评估完成 | 风险等级: {response.overall_risk_level} | "
            f"风险因素数: {len(response.primary_risk_factors)}"
        )

        return response

    except CoreValidationError as e:
        logger.warning(f"风险评估参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except QueryError as e:
        logger.error(f"风险评估执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(f"风险评估处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "风险评估处理失败，请稍后重试",
            },
        ) from e


@router.get(
    "/guidelines/{procedure_type}",
    response_model=list[GuidelineResponse],
    summary="获取临床指南",
    description="检索特定手术类型相关的临床指南和循证医学证据。",
    tags=["interventional"],
)
async def get_guidelines(
    procedure_type: str,
    limit: int = 10,
) -> list[GuidelineResponse]:
    """获取临床指南。

    Args:
        procedure_type: 手术类型（PCI, CAS, TAVI 等）
        limit: 返回数量限制

    Returns:
        list[GuidelineResponse]: 临床指南列表

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 检索执行失败

    Example:
        >>> GET /api/v1/interventional/guidelines/PCI?limit=5
    """
    logger.info(f"收到临床指南请求 | 手术类型: {procedure_type}")

    try:
        # 创建客户端并检索指南
        async with InterventionalClient() as client:
            guidelines = await client.get_guidelines(
                procedure_type=procedure_type,
                limit=limit,
            )

        # 转换为 API 响应格式
        response = [
            GuidelineResponse(
                title=g.title,
                source=g.source,
                year=g.year,
                recommendation=g.recommendation,
                evidence_level=g.evidence_level,
                indication=g.indication,
                contraindication=g.contraindication,
            )
            for g in guidelines
        ]

        logger.info(f"临床指南获取完成 | 返回数量: {len(response)}")

        return response

    except CoreValidationError as e:
        logger.warning(f"临床指南参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except QueryError as e:
        logger.error(f"临床指南检索失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(f"临床指南处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "临床指南检索失败，请稍后重试",
            },
        ) from e


@router.get(
    "/devices/{category}",
    response_model=list[DeviceRecommendationResponse],
    summary="获取器械推荐",
    description="根据手术类型和患者特征获取介入器械推荐。",
    tags=["interventional"],
)
async def get_device_recommendations(
    category: str,
    procedure_type: str,
    patient_age: Optional[int] = None,
) -> list[DeviceRecommendationResponse]:
    """获取器械推荐。

    Args:
        category: 器械类别（catheter, stent, balloon 等）
        procedure_type: 手术类型
        patient_age: 患者年龄（可选）

    Returns:
        list[DeviceRecommendationResponse]: 器械推荐列表

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 推荐执行失败

    Example:
        >>> GET /api/v1/interventional/devices/stent?procedure_type=PCI&patient_age=65
    """
    logger.info(f"收到器械推荐请求 | 类别: {category} | 手术类型: {procedure_type}")

    try:
        # 构建最小患者数据
        patient_data = {
            "age": patient_age or 65,
            "gender": "male",
            "diagnosis": [],
            "comorbidities": [],
        }

        # 创建客户端并获取推荐
        async with InterventionalClient() as client:
            devices = await client.get_device_recommendations(
                patient_data=patient_data,
                procedure_type=procedure_type,
            )

        # 过滤类别
        if category != "all":
            devices = [d for d in devices if d.device_type.lower() == category.lower()]

        # 转换为 API 响应格式
        response = [
            DeviceRecommendationResponse(
                device_name=d.device_name,
                device_type=d.device_type,
                specifications=d.specifications,
                rationale=d.rationale,
                contraindications=d.contraindications,
                alternatives=d.alternatives,
            )
            for d in devices
        ]

        logger.info(f"器械推荐完成 | 返回数量: {len(response)}")

        return response

    except CoreValidationError as e:
        logger.warning(f"器械推荐参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except QueryError as e:
        logger.error(f"器械推荐执行失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(f"器械推荐处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "器械推荐失败，请稍后重试",
            },
        ) from e


@router.post(
    "/postop-care",
    response_model=PostopCareResponse,
    summary="术后护理规划",
    description="生成个性化术后护理计划，包括监测计划、用药计划、活动限制和随访安排。",
    tags=["interventional"],
)
async def create_postop_care_plan(
    request: PostopCareRequest,
) -> PostopCareResponse:
    """生成术后护理计划。

    Args:
        request: 术后护理请求

    Returns:
        PostopCareResponse: 术后护理计划

    Raises:
        HTTPException 400: 请求参数验证失败
        HTTPException 500: 规划执行失败

    Example:
        >>> POST /api/v1/interventional/postop-care
        >>> {
        >>>     "patient_data": {
        >>>         "age": 65,
        >>>         "comorbidities": ["糖尿病"]
        >>>     },
        >>>     "procedure_type": "PCI"
        >>> }
    """
    logger.info(
        f"收到术后护理规划请求 | 手术类型: {request.procedure_type} | "
        f"患者: {request.patient_data.patient_id or '未知'}"
    )

    try:
        # 转换患者数据
        patient_data_dict = convert_patient_data_to_dict(request.patient_data)

        # 创建客户端并生成护理计划
        async with InterventionalClient() as client:
            care_plan = await client.plan_postop_care(
                patient_data=patient_data_dict,
                procedure_type=request.procedure_type,
            )

        # 转换为 API 响应格式
        response = PostopCareResponse(
            monitoring_plan=care_plan.monitoring_plan,
            medication_plan=care_plan.medication_plan,
            activity_restrictions=care_plan.activity_restrictions,
            follow_up_schedule=care_plan.follow_up_schedule,
            warning_signs=care_plan.warning_signs,
        )

        logger.info(
            f"术后护理计划生成完成 | "
            f"监测项: {len(response.monitoring_plan)} | "
            f"用药: {len(response.medication_plan)}"
        )

        return response

    except CoreValidationError as e:
        logger.warning(f"术后护理参数验证失败: {e}")
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail={
                "error": "ValidationError",
                "message": str(e),
                "field": getattr(e, "field", None),
            },
        ) from e

    except QueryError as e:
        logger.error(f"术后护理规划失败: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "QueryError",
                "message": str(e),
            },
        ) from e

    except Exception as e:
        logger.error(f"术后护理处理异常: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail={
                "error": "InternalServerError",
                "message": "术后护理规划失败，请稍后重试",
            },
        ) from e


# ========== 健康检查端点 ==========


@router.get(
    "/health",
    summary="介入性治疗服务健康检查",
    description="检查介入性治疗服务是否正常运行。",
    tags=["interventional"],
)
async def health_check() -> dict[str, str]:
    """介入性治疗服务健康检查。

    Returns:
        包含服务状态的字典
    """
    return {
        "service": "interventional",
        "status": "healthy",
    }


__all__ = ["router"]
