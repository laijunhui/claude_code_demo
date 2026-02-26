# 多Agent代码自动评审工具

基于 FastAPI 的轻量化代码评审服务。

## 功能特性

- 🤖 **多Agent并行评审**：语法检查、安全扫描、规范检查
- 🔌 **Webhook集成**：GitHub PR 自动触发评审
- 📦 **轻量部署**：Docker 一键启动
- 🔧 **可扩展**：插件化 Agent 设计

## 快速开始

### 1. 安装依赖

```bash
# 克隆项目
git clone https://github.com/yourteam/code-reviewer.git
cd code-reviewer

# 创建虚拟环境（推荐）
python -m venv venv
source venv/bin/activate  # Linux/Mac
# 或
venv\Scripts\activate     # Windows

# 安装依赖
pip install -r requirements.txt

# 安装代码检查工具（可选）
pip install pylint bandit
```

### 2. 配置环境变量

```bash
# 复制配置模板
cp .env.example .env

# 编辑 .env 文件，填入你的 API Key
# - CLAUDE_API_KEY: Anthropic Claude API Key
# - API_TOKEN: API 认证 Token
# - GITHUB_TOKEN: GitHub Token（用于获取 PR 文件）
```

### 3. 启动服务

```bash
# 开发模式
python -m app.main

# 或者使用 uvicorn
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### 4. 访问

- API 文档：http://localhost:8000/docs
- 健康检查：http://localhost:8000/api/health

## API 使用

### 手动触发评审

```bash
curl -X POST http://localhost:8000/api/review \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer dev-token-change-in-production" \
  -d '{
    "files": [
      {
        "path": "example.py",
        "content": "def hello():\n    print(1/0)\n    eval(input())\n"
      }
    ]
  }'
```

### 查询评审结果

```bash
curl http://localhost:8000/api/review/{review_id}
```

## 配置 Webhook

在 GitHub 仓库设置中添加 Webhook：

- **URL**: `https://your-domain.com/webhook/github`
- **Content type**: `application/json`
- **Events**: `Pull requests`

## Docker 部署

```bash
# 构建镜像
docker build -t code-reviewer .

# 运行
docker run -d \
  -p 8000:8000 \
  -e CLAUDE_API_KEY=your_key \
  -e API_TOKEN=your_token \
  -e GITHUB_TOKEN=your_github_token \
  code-reviewer
```

## Agent 说明

| Agent | 工具 | 作用 |
|-------|------|------|
| Syntax | pylint | 语法错误检查 |
| Security | bandit | 安全漏洞扫描 |
| Style | Claude API | 代码规范建议 |

## 项目结构

```
code-reviewer/
├── app/
│   ├── main.py          # FastAPI 入口
│   ├── config.py        # 配置管理
│   ├── api/
│   │   ├── routes.py    # API 路由
│   │   └── webhooks.py  # Webhook 处理
│   └── agents/
│       ├── base.py      # Agent 基类
│       ├── manager.py   # Agent 管理器
│       ├── syntax.py   # 语法 Agent
│       ├── security.py # 安全 Agent
│       └── style.py    # 规范 Agent
├── requirements.txt
└── .env.example
```

## License

MIT
