# FastAPI 主应用入口
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from app.api import routes, webhooks
from app.config import settings
from app.logger import logger
from app.middleware import LoggingMiddleware
from pydantic import BaseModel  # 用于定义数据模型（自动校验）

# 创建 FastAPI 应用
app = FastAPI(
    title="Code Reviewer API",
    description="多Agent代码自动评审工具 - API",
    version="1.0.0",
)

# 启动时记录日志
logger.info(f"Starting Code Reviewer API on {settings.host}:{settings.port}")

# 添加日志中间件
app.add_middleware(LoggingMiddleware)

# 配置 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 注册路由
app.include_router(routes.router, prefix="", tags=["Review"])
app.include_router(webhooks.router, prefix="", tags=["Webhook"])

# 配置templates目录（仅用于可能的动态模板）
import os
templates = Jinja2Templates(directory=os.path.join(os.path.dirname(__file__), "templates"))

# 挂载静态文件目录（前端页面）
app.mount("/static", StaticFiles(directory=os.path.join(os.path.dirname(__file__), "templates")), name="static")


@app.get("/")
async def root():
    """根路径 - 返回前端页面"""
    from fastapi.responses import FileResponse
    logger.info("Root endpoint accessed")
    return FileResponse(os.path.join(os.path.dirname(__file__), "templates", "index.html"))


# 定义GET请求接口：路径为/，请求方法GET
@app.get("/hello")
def read_root():
    """根路径接口，返回简单响应"""
    return {"message": "Hello FastAPI!"}

# 路径参数：{item_id} 作为函数参数传入，指定类型（自动校验）
@app.get("/items/{item_id}")
def read_item(item_id: int, q: str = None):
    """
    - item_id：路径参数，类型int（传字符串会自动返回422错误）
    - q：查询参数，可选（默认None），访问示例：/items/10?q=test
    """
    return {"item_id": item_id, "query": q}

# 多路径参数示例
@app.get("/users/{user_id}/orders/{order_id}")
def read_user_order(user_id: int, order_id: str):
    return {"user_id": user_id, "order_id": order_id}

# 定义请求体模型（类似表单/JSON结构）
class Item(BaseModel):
    name: str
    price: float
    is_offer: bool = None  # 可选字段，默认None

# POST请求，接收JSON请求体
@app.post("/items/")
def create_item(item: Item):
    """接收JSON请求体，自动校验字段类型和必填项"""
    return {"item_name": item.name, "item_price": item.price, "is_offer": item.is_offer}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host=settings.host,
        port=settings.port,
        reload=True
    )
