# 多 Agent 代码审查系统工作机制研究

## 高层摘要

本系统是一个基于 FastAPI 的多 Agent 并行代码审查工具，通过插件化架构实现对 Python 代码的自动化评审。系统包含三个核心 Agent：SyntaxAgent（使用 pylint 进行语法检查）、SecurityAgent（使用 bandit 进行安全扫描）、StyleAgent（使用 MiniMax AI API 进行代码风格分析）。审查流程通过异步并行执行提升效率，结果由 AgentManager 统一聚合后返回。

## 详细发现

### 1. 核心数据模型

#### 1.1 Issue（问题）数据结构

定义于 [base.py:8-28](code-reviewer/app/agents/base.py#L8-L28)

```python
@dataclass
class Issue:
    file_path: str      # 文件路径
    line: int           # 行号
    column: int = 1     # 列号
    severity: str       # 严重程度: critical, error, warning, info
    type: str           # 问题类型: syntax, security, style, general
    message: str        # 问题描述
    suggestion: str     # 修复建议
```

#### 1.2 AgentResult（Agent 执行结果）

定义于 [base.py:31-48](code-reviewer/app/agents/base.py#L31-L48)

```python
@dataclass
class AgentResult:
    agent_name: str
    issues: List[Issue]
    duration_ms: int
    error: Optional[str]
```

#### 1.3 CodeFile（待评审代码文件）

定义于 [base.py:51-56](code-reviewer/app/agents/base.py#L51-L56)

```python
@dataclass
class CodeFile:
    file_path: str
    content: str
    language: str = ""
```

#### 1.4 ReviewReport（评审报告）

定义于 [manager.py:12-52](code-reviewer/app/agents/manager.py#L12-L52)

包含 `review_id`、`files`、`issues`、`duration_ms`、`agents_results` 字段，提供 `get_summary()` 方法按严重程度和问题类型统计。

### 2. Agent 架构

#### 2.1 BaseAgent 抽象基类

定义于 [base.py:59-98](code-reviewer/app/agents/base.py#L59-L98)

所有 Agent 继承自 `BaseAgent`，核心方法：

- `async analyze(file: CodeFile) -> AgentResult`：抽象方法，由子类实现
- `should_run(language: str) -> bool`：判断是否需要运行此 Agent
- `_detect_language(file_path: str) -> str`：根据文件扩展名检测语言

#### 2.2 三个核心 Agent 实现

**SyntaxAgent**（[syntax.py:10-134](code-reviewer/app/agents/syntax.py#L10-L134)）
- 使用 pylint 进行 Python 语法检查
- `supported_languages = ["python", "py"]`
- 执行命令：`python -m pylint temp_file --disable=all --enable=E`
- 仅启用语法错误（E 类），忽略风格警告

**SecurityAgent**（[security.py:12-220](code-reviewer/app/agents/security.py#L12-L220)）
- 使用 bandit 进行安全扫描
- `supported_languages = ["python", "py"]`
- 执行命令：`python -m bandit -f json -x temp_file`
- 严重程度映射：HIGH→critical, MEDIUM→error, LOW→warning
- 内置 100+ 条安全规则建议（[security.py:150-220](code-reviewer/app/agents/security.py#L150-L220)）

**StyleAgent**（[style.py:9-203](code-reviewer/app/agents/style.py#L9-L203)）
- 使用 MiniMax AI API 进行代码风格分析
- `supported_languages = []`（支持所有语言）
- 调用端点：`{base_url}/text/chatcompletion_v2`
- 通过 prompt 要求 AI 返回 JSON 格式的 issues 列表

### 3. Agent 管理器

#### 3.1 AgentManager 核心逻辑

定义于 [manager.py:55-167](code-reviewer/app/agents/manager.py#L55-L167)

```python
class AgentManager:
    def __init__(self):
        self.agents = [
            SyntaxAgent(),
            SecurityAgent(),
            StyleAgent(),
        ]
```

核心方法 `run_review()`：

1. **任务构建**（[manager.py:88-93](code-reviewer/app/agents/manager.py#L88-L93)）：为每个文件的每个启用的 Agent 创建分析任务
2. **并行执行**（[manager.py:95-96](code-reviewer/app/agents/manager.py#L95-L96)）：使用 `asyncio.gather(*tasks, return_exceptions=True)` 并行运行所有任务
3. **结果聚合**（[manager.py:98-113](code-reviewer/app/agents/manager.py#L98-L113)）：收集所有 Agent 的结果，按严重程度排序（critical→error→warning→info）
4. **报告生成**（[manager.py:117-123](code-reviewer/app/agents/manager.py#L117-L123)）：返回 `ReviewReport` 对象

#### 3.2 任务执行流程

```
for file in files:
    for agent in enabled_agents:
        if agent.should_run(file.language):
            tasks.append(self._run_agent(agent, file))

results = await asyncio.gather(*tasks, return_exceptions=True)
```

异常处理在 `_run_agent()` 方法（[manager.py:125-143](code-reviewer/app/agents/manager.py#L125-L143)）中实现，Agent 执行失败时会生成类型为 `agent_error` 的 Issue。

### 4. API 接入层

#### 4.1 核心端点

定义于 [routes.py](code-reviewer/app/api/routes.py)

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/review` | POST | 创建评审任务 |
| `/api/review/{review_id}` | GET | 查询评审结果 |
| `/api/health` | GET | 健康检查 |

#### 4.2 审查请求处理流程

1. **请求验证**（[routes.py:54-77](code-reviewer/app/api/routes.py#L54-L77)）：验证 Token、检查文件数量（最多 50 个）
2. **CodeFile 构建**（[routes.py:69-77](code-reviewer/app/api/routes.py#L69-L77)）：将请求中的文件列表转换为 `CodeFile` 对象
3. **后台任务执行**（[routes.py:91-97](code-reviewer/app/api/routes.py#L91-L97)）：使用 `BackgroundTasks` 异步执行 `run_review_task()`
4. **结果存储**（[routes.py:15](code-reviewer/app/api/routes.py#L15)）：内存字典 `review_results` 存储审查结果（生产环境应使用数据库）

#### 4.3 状态查询

通过 `/api/review/{review_id}` 查询，返回状态：`pending` → `running` → `completed` 或 `failed`

### 5. 数据流

```
POST /api/review
    │
    ▼
ReviewRequest (files: List[dict])
    │
    ▼
CodeFile objects (file_path, content, language)
    │
    ▼
AgentManager.run_review(files, config)
    │
    ├──► SyntaxAgent.analyze(file) ──► pylint ──► List[Issue]
    │
    ├──► SecurityAgent.analyze(file) ──► bandit ──► List[Issue]
    │
    └──► StyleAgent.analyze(file) ──► MiniMax API ──► List[Issue]
    │
    ▼
ReviewReport (aggregated issues, sorted by severity)
    │
    ▼
ReviewDetailResponse (JSON)
```

## 组件连接

| 组件 | 依赖 | 说明 |
|------|------|------|
| `main.py` | FastAPI 应用 | 入口，注册路由 |
| `routes.py` | `AgentManager`, `CodeFile` | API 端点处理 |
| `manager.py` | `BaseAgent`, 三个 Agent 类 | 任务调度与结果聚合 |
| `base.py` | 无 | 数据模型定义 |
| `syntax.py` | `pylint` 库 | 语法检查 |
| `security.py` | `bandit` 库 | 安全扫描 |
| `style.py` | `httpx`, MiniMax API | AI 风格分析 |

## 环境配置

关键配置项（[config.py](code-reviewer/app/config.py)）：

- `MINIMAX_API_KEY`：MiniMax AI API 密钥
- `MINIMAX_MODEL`：模型名称（默认 MiniMax-M2.1）
- `API_TOKEN`：API 认证 Token
- `HOST`/`PORT`：服务地址（默认 0.0.0.0:8000）
