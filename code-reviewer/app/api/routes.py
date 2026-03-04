# API 路由
from typing import List, Optional
from fastapi import APIRouter, HTTPException, BackgroundTasks, Header, Query
from pydantic import BaseModel
from app.agents.base import CodeFile
from app.agents.manager import AgentManager, ReviewReport
from app.logger import logger
from app.storage import init_storage
from app.storage.json_storage import JSONReviewStorage
from app.config import settings

router = APIRouter()

# 全局 Agent 管理器
agent_manager = AgentManager()

# 全局存储实例
storage: JSONReviewStorage = None


def init_storage_on_startup():
    """在服务启动时初始化存储层"""
    global storage
    storage = init_storage(settings.storage_base_dir)
    logger.info(f"Storage initialized at {settings.storage_base_dir}")


# 存储评审结果（内存缓存 + 持久化）
review_results: dict = {}


# ============ 请求/响应模型 ============

class ReviewRequest(BaseModel):
    """评审请求"""
    files: List[dict]  # [{"path": "xxx.py", "content": "code"}]
    config: Optional[dict] = None  # Agent 配置


class ReviewResponse(BaseModel):
    """评审响应"""
    review_id: str
    status: str
    summary: dict


class ReviewDetailResponse(BaseModel):
    """评审详情响应"""
    review_id: str
    status: str
    summary: dict
    issues: List[dict]
    agents_results: List[dict]
    duration_ms: int
    files: List[str] = []


# ============ API 端点 ============

@router.post("/api/review", response_model=ReviewResponse)
async def create_review(
    request: ReviewRequest,
    background_tasks: BackgroundTasks,
    authorization: Optional[str] = Header(None)
):
    """手动触发代码评审"""

    # 简单的 Token 验证
    from app.config import settings
    if authorization:
        token = authorization.replace("Bearer ", "")
        if token != settings.api_token:
            raise HTTPException(status_code=401, detail="Invalid token")

    # 验证输入
    if not request.files:
        raise HTTPException(status_code=400, detail="No files provided")

    if len(request.files) > 50:
        raise HTTPException(status_code=400, detail="Too many files (max 50)")

    # 创建代码文件对象
    code_files = []
    for f in request.files:
        if "content" not in f or "path" not in f:
            raise HTTPException(status_code=400, detail="Invalid file format")

        code_files.append(CodeFile(
            file_path=f["path"],
            content=f["content"]
        ))

    # 创建评审任务
    import uuid
    review_id = f"review_{uuid.uuid4().hex[:8]}"
    logger.info(f"Creating review task: {review_id} with {len(code_files)} files")

    # 存储任务信息
    review_results[review_id] = {
        "status": "pending",
        "files": request.files,
        "config": request.config,
    }

    # 后台执行评审
    background_tasks.add_task(
        run_review_task,
        review_id,
        code_files,
        request.config
    )

    return ReviewResponse(
        review_id=review_id,
        status="pending",
        summary={"message": "Review task created"}
    )


@router.get("/api/review/{review_id}", response_model=ReviewDetailResponse)
async def get_review(review_id: str):
    """查询评审结果"""

    if review_id not in review_results:
        raise HTTPException(status_code=404, detail="Review not found")

    result = review_results[review_id]

    if "report" not in result:
        return ReviewDetailResponse(
            review_id=review_id,
            status=result["status"],
            summary={"message": "Review in progress"},
            issues=[],
            agents_results=[],
            duration_ms=0,
            files=[f.get("path", "") for f in result.get("files", [])]
        )

    report: ReviewReport = result["report"]

    return ReviewDetailResponse(
        review_id=review_id,
        status="completed",
        summary=report.get_summary(),
        issues=[i.to_dict() for i in report.issues],
        agents_results=[r.to_dict() for r in report.agents_results],
        duration_ms=report.duration_ms,
        files=report.files
    )


@router.get("/api/health")
async def health_check():
    """健康检查"""
    return {
        "status": "healthy",
        "agents": [
            {"name": agent.name, "enabled": True}
            for agent in agent_manager.agents
        ]
    }


# ============ 审查列表端点 ============

class ReviewListResponse(BaseModel):
    """审查列表响应"""
    items: List[dict]
    total: int
    page: int
    page_size: int
    total_pages: int


@router.get("/api/reviews", response_model=ReviewListResponse)
async def list_reviews(
    page: int = Query(1, ge=1, description="页码"),
    page_size: int = Query(20, ge=1, le=100, description="每页数量"),
    status: Optional[str] = Query(None, description="状态筛选: pending, running, completed, failed")
):
    """获取审查列表（支持分页和状态筛选）"""
    # 确保存储层已初始化
    if storage is None:
        init_storage_on_startup()

    result = storage.list_reviews(page=page, page_size=page_size, status=status)
    return ReviewListResponse(**result)


@router.get("/api/reviews/{review_id}")
async def get_review_detail(review_id: str):
    """获取审查详情"""
    # 优先从内存缓存获取（最新的数据）
    if review_id in review_results:
        result = review_results[review_id]

        if "report" not in result:
            return ReviewDetailResponse(
                review_id=review_id,
                status=result["status"],
                summary={"message": "Review in progress"},
                issues=[],
                agents_results=[],
                duration_ms=0,
                files=[f.get("path", "") for f in result.get("files", [])]
            )

        report: ReviewReport = result["report"]

        return ReviewDetailResponse(
            review_id=review_id,
            status="completed",
            summary=report.get_summary(),
            issues=[i.to_dict() for i in report.issues],
            agents_results=[r.to_dict() for r in report.agents_results],
            duration_ms=report.duration_ms,
            files=report.files
        )

    # 从持久化存储获取
    if storage is None:
        init_storage_on_startup()

    stored = storage.get_review(review_id)
    if stored is None:
        raise HTTPException(status_code=404, detail="Review not found")

    return ReviewDetailResponse(
        review_id=review_id,
        status=stored.get("status", "unknown"),
        summary=stored.get("summary", {}),
        issues=stored.get("issues", []),
        agents_results=stored.get("agents_results", []),
        duration_ms=stored.get("duration_ms", 0),
        files=stored.get("files", [])
    )


@router.delete("/api/reviews/{review_id}")
async def delete_review(review_id: str):
    """删除审查记录"""
    # 从内存缓存删除
    if review_id in review_results:
        del review_results[review_id]

    # 从持久化存储删除
    if storage is None:
        init_storage_on_startup()

    success = storage.delete_review(review_id)
    if not success:
        raise HTTPException(status_code=404, detail="Review not found")

    return {"message": "Review deleted successfully", "review_id": review_id}


# ============ 内部函数 ============

async def run_review_task(review_id: str, files: List[CodeFile], config: Optional[dict]):
    """执行评审任务"""
    # 确保存储层已初始化
    if storage is None:
        init_storage_on_startup()

    try:
        # 更新状态
        review_results[review_id]["status"] = "running"

        # 持久化状态到存储层
        storage.save_review(review_id, review_results[review_id])

        # 执行评审
        report = await agent_manager.run_review(files, config)

        # 保存结果到内存
        review_results[review_id]["status"] = "completed"
        review_results[review_id]["report"] = report

        # 持久化完整结果到存储层
        review_data = {
            "status": "completed",
            "files": [f.file_path for f in files],
            "config": config,
            "summary": report.get_summary(),
            "issues": [i.to_dict() for i in report.issues],
            "agents_results": [r.to_dict() for r in report.agents_results],
            "duration_ms": report.duration_ms,
        }
        storage.save_review(review_id, review_data)

    except Exception as e:
        # 标记失败
        logger.error(f"Review task {review_id} failed: {str(e)}")
        review_results[review_id]["status"] = "failed"
        review_results[review_id]["error"] = str(e)

        # 持久化失败状态
        storage.save_review(review_id, review_results[review_id])
    else:
        logger.info(f"Review task {review_id} completed successfully")
