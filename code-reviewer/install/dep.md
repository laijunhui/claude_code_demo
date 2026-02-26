# 依赖安装与启动

## 依赖安装

```bash
cd /Users/dingmaomao/Workplace/claude_demo2/code-reviewer

# 创建虚拟环境
python -m venv venv
source venv/bin/activate  # Mac/Linux
# 或
venv\Scripts\activate     # Windows

# 安装 Python 依赖
pip install -r requirements.txt

# 安装代码检查工具（必须）
pip install pylint bandit
```

## 配置

```bash
# 1. 复制配置模板
cp .env.example .env

# 2. 编辑 .env，填入以下环境变量：
# - CLAUDE_API_KEY: Anthropic Claude API Key（必须）
# - API_TOKEN: API 认证 Token
# - GITHUB_TOKEN: GitHub Token（可选，用于获取 PR 文件）
```

## 启动服务

```bash
# 开发模式
python -m app.main

# 或使用 uvicorn（推荐）
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 验证

服务启动后访问：
- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

## Docker 部署（可选）

```bash
# 构建镜像
docker build -t code-reviewer .

# 运行
docker run -d \
  -p 8000:8000 \
  -e CLAUDE_API_KEY=your_key \
  -e API_TOKEN=your_token \
  code-reviewer
```
