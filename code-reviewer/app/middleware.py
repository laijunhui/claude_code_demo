# 请求/响应日志中间件
import time
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from app.logger import logger


class LoggingMiddleware(BaseHTTPMiddleware):
    """统一日志拦截器"""

    async def dispatch(self, request: Request, call_next):
        # 记录请求开始时间
        start_time = time.time()

        # 记录请求信息
        request_id = id(request)
        logger.info(
            f"--> {request.method} {request.url.path} "
            f"[client: {request.client.host if request.client else 'unknown'}]"
        )

        # 记录请求体（如果是POST/PUT且有body）
        body = None
        if request.method in ["POST", "PUT", "PATCH"]:
            try:
                body = await request.body()
                if body:
                    # 尝试解析JSON，失败则记录原始长度
                    try:
                        body_json = json.loads(body)
                        # 敏感信息脱敏
                        body_json = self._sanitize(body_json)
                        logger.debug(f"    Request Body: {json.dumps(body_json, ensure_ascii=False)[:500]}")
                    except:
                        logger.debug(f"    Request Body: <binary {len(body)} bytes>")
            except Exception:
                pass

        # 调用实际的路由处理函数
        response = await call_next(request)

        # 计算处理时间
        process_time = (time.time() - start_time) * 1000

        # 记录响应信息
        logger.info(
            f"<-- {request.method} {request.url.path} "
            f"status={response.status_code} "
            f"duration={process_time:.2f}ms"
        )

        # 添加自定义响应头
        response.headers["X-Process-Time"] = str(process_time)

        return response

    def _sanitize(self, data: dict) -> dict:
        """敏感信息脱敏"""
        sensitive_keys = ["password", "token", "api_key", "secret", "authorization"]
        sanitized = {}

        for key, value in data.items():
            lower_key = key.lower()
            if any(s in lower_key for s in sensitive_keys):
                sanitized[key] = "***"
            elif isinstance(value, dict):
                sanitized[key] = self._sanitize(value)
            else:
                sanitized[key] = value

        return sanitized
