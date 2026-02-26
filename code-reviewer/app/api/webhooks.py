# Webhook 处理
import hashlib
import hmac
import os
from typing import Optional
from fastapi import APIRouter, HTTPException, Header, BackgroundTasks
from pydantic import BaseModel
from app.config import settings
from app.api.routes import run_review_task, review_results
from app.agents.base import CodeFile
import httpx

router = APIRouter()


@router.post("/webhook/github")
async def github_webhook(
    payload: dict,
    background_tasks: BackgroundTasks,
    x_github_event: str = Header(None),
    x_hub_signature_256: Optional[str] = Header(None)
):
    """GitHub Webhook 入口"""

    # 验证签名（生产环境应该验证）
    # if not verify_github_signature(payload, x_hub_signature_256):
    #     raise HTTPException(status_code=401, detail="Invalid signature")

    event_type = x_github_event or "unknown"

    # 只处理 PR 事件
    if event_type != "pull_request":
        return {"status": "ignored", "reason": f"Event type {event_type} not supported"}

    action = payload.get("action")
    pr = payload.get("pull_request", {})

    # 只处理 PR 打开和更新
    if action not in ["opened", "reopened", "synchronize"]:
        return {"status": "ignored", "reason": f"Action {action} not supported"}

    # 获取 PR 信息
    repo_full_name = payload.get("repository", {}).get("full_name", "")
    pr_number = pr.get("number", 0)
    pr_title = pr.get("title", "")
    pr_files_url = pr.get("files_url", "")

    # 获取文件列表（通过 GitHub API）
    files = await fetch_pr_files(pr_files_url)

    if not files:
        return {"status": "error", "reason": "Failed to fetch PR files"}

    # 创建评审任务
    import uuid
    review_id = f"review_gh_{pr_number}_{uuid.uuid4().hex[:6]}"

    review_results[review_id] = {
        "status": "pending",
        "repo": repo_full_name,
        "pr_number": pr_number,
        "pr_title": pr_title,
        "files": files,
        "config": None,
    }

    # 创建 CodeFile 对象
    code_files = [
        CodeFile(file_path=f["filename"], content=f.get("patch", ""))
        for f in files
    ]

    # 后台执行评审
    background_tasks.add_task(run_review_task, review_id, code_files, None)

    return {
        "status": "accepted",
        "review_id": review_id,
        "pr": f"{repo_full_name}#{pr_number}"
    }


async def fetch_pr_files(files_url: str) -> list:
    """获取 PR 文件列表"""
    token = os.environ.get("GITHUB_TOKEN", "")

    if not token:
        # 没有 token，返回提示
        return [{
            "filename": "demo.py",
            "patch": "# Demo: Set GITHUB_TOKEN to fetch real files",
            "status": "modified"
        }]

    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json"
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.get(files_url, headers=headers)

            if response.status_code != 200:
                return []

            files = response.json()

            # 只返回已修改和新增的文件
            return [
                f for f in files
                if f.get("status") in ["modified", "added"]
            ]

    except Exception:
        return []


def verify_github_signature(payload: bytes, signature: Optional[str]) -> bool:
    """验证 GitHub Webhook 签名"""
    if not signature:
        return False

    secret = settings.github_webhook_secret.encode() if hasattr(settings, 'github_webhook_secret') else b""

    if not secret:
        return True  # 没有配置 secret，跳过验证

    sha_name, signature_hash = signature.split("=")

    if sha_name != "sha256":
        return False

    computed_hash = hmac.new(secret, payload, hashlib.sha256).hexdigest()

    return hmac.compare_digest(computed_hash, signature_hash)
