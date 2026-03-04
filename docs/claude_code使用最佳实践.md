# Claude Code 使用最佳实践

作为 Claude Code 初级使用者，本文将帮助你快速掌握核心概念和实战技巧。

---

## 一、核心指令和使用技巧

### 1.1 基础交互方式

Claude Code 提供多种交互方式，适用于不同场景：

| 交互方式 | 说明 | 适用场景 |
|---------|------|---------|
| **直接对话** | 最常用的自然语言交互 | 日常开发任务、问题解答 |
| **Slash Commands** | 快捷命令，如 `/edit`、`/commit` | 快速执行特定操作 |
| **多模态输入** | 支持图片、PDF、截图分析 | 代码截图分析、文档理解 |
| **MCP Tools** | 调用外部工具和服务 | 扩展能力、自动化工作流 |

### 1.2 常用 Slash Commands

```
/help           # 获取帮助信息
/commit         # 创建 Git 提交
/review-pr      # 审查 Pull Request
/pdf            # 处理 PDF 文档
/test           # 生成测试代码
/explain        # 解释代码逻辑
/refactor       # 重构代码
```

### 1.3 高效使用技巧

#### 技巧1：项目初始化和结构了解
```bash
# 首次使用时，Claude 会自动扫描项目结构
# 你可以主动让 Claude 了解项目布局
"请帮我了解这个项目的结构"
```

#### 技巧2：使用专用工具而非 Shell 命令
```bash
# ✅ 推荐：使用专用工具
Glob(pattern: "**/*.py")          # 查找 Python 文件
Grep(pattern: "def.*test", type: "py")  # 搜索代码
Read(file_path: "src/main.py")    # 读取文件

# ❌ 避免：使用 cat/grep/find 等 shell 命令
cat src/main.py
```

#### 技巧3：精确的文件操作
```bash
# 分页读取大文件
Read(file_path: "large_file.py", limit: 100, offset: 0)

# 使用行号定位
Read(file_path: "src/utils.py", limit: 20, offset: 10)
```

#### 技巧4：Git 协作
```bash
# Claude 内置 Git 工具，可以直接使用
git status          # 查看状态
git diff            # 查看变更
git log             # 查看提交历史
```

#### 技巧5：上下文管理
```bash
# 在 .claude/settings.local.json 中配置权限
{
  "permissions": {
    "allow": ["Bash(python *)", "Bash(npm *)"],
    "deny": ["Bash(rm -rf /**)"]
  }
}
```

### 1.4 最佳实践要点

1. **明确任务描述**
   ```bash
   # ✅ 好的任务描述
   "请在 src/user.py 中添加一个 send_email 方法，接收邮箱地址和内容参数"

   # ❌ 模糊的任务描述
   "帮我完善用户模块"
   ```

2. **分步执行复杂任务**
   ```bash
   # 复杂任务拆分为多个步骤
   "首先，帮我创建一个用户模型"
   "然后，添加 CRUD 接口"
   "最后，编写单元测试"
   ```

3. **及时反馈**
   - 对输出给予确认或纠正
   - 不满意时明确说明期望

4. **重要文件操作前备份**
   ```bash
   # 操作前先确认
   "在修改之前，请先备份原文件"
   ```

---

## 二、MCP 和 Skills 最佳实践

### 2.1 MCP (Model Context Protocol) 详解

MCP 是一种标准化协议，用于 Claude Code 与外部工具和服务的集成。

#### 常用 MCP 服务推荐

| MCP 服务 | 功能 | 场景 |
|---------|------|------|
| **filesystem** | 本地文件读写 | 直接操作项目文件 |
| **github** | GitHub API 操作 | PR 管理、Issue、Actions |
| **database** | 数据库操作 | SQL 查询、数据处理 |
| **brave-search** | 网页搜索 | 获取最新信息 |
| **slack** | Slack 通知 | 团队协作通知 |

#### MCP 配置示例

```json
// .claude/settings.json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem", "/Users/dingmaomao/Workplace"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"]
    }
  }
}
```

#### MCP 最佳实践

1. **按需启用**：只启用当前需要的 MCP 服务
2. **权限控制**：配置合理的访问权限
3. **定期更新**：`npx -y @modelcontextprotocol/xxx@latest`
4. **本地优先**：敏感操作尽量使用本地 MCP

### 2.2 Skills 详解

Skills 是预定义的命令模板，用于自动化常见任务。

#### 内置 Skills

```
/commit    # 自动创建规范的 Git 提交
/review-pr # Pull Request 审查
/pdf       # PDF 文档处理
```

#### 自定义 Skills

```json
// .claude/settings.json
{
  "skills": [
    {
      "name": "deploy-prod",
      "description": "部署应用到生产环境",
      "commands": [
        "npm run build",
        "npm run deploy:prod"
      ]
    },
    {
      "name": "test-coverage",
      "description": "运行测试并生成覆盖率报告",
      "commands": [
        "npm run test -- --coverage"
      ]
    }
  ]
}
```

### 2.3 推荐开发相关的 Skills 和 MCP

#### 必装 MCP
1. **filesystem** - 文件操作基础
2. **github** - 代码管理集成
3. **brave-search** - 搜索能力扩展

#### 推荐 Skills
1. **/commit** - 规范提交
2. **/review-pr** - PR 审查
3. 自定义 `lint` - 代码检查
4. 自定义 `test` - 测试运行

---

## 三、虚拟团队协作模式

### 3.1 多代理协作架构

Claude Code 支持创建多个子代理进行协作，常见模式：

```
┌─────────────────────────────────────────────────────────┐
│                      主代理 (Main)                        │
│              负责任务分配、结果汇总、决策                   │
└─────────────────────┬───────────────────────────────────┘
                      │
        ┌─────────────┼─────────────┐
        ▼             ▼             ▼
   ┌─────────┐   ┌─────────┐   ┌─────────┐
   │ Agent 1 │   │ Agent 2 │   │ Agent 3 │
   │ 代码审查 │   │ 文档编写 │   │ 测试生成 │
   └─────────┘   └─────────┘   └─────────┘
```

### 3.2 协作模式

#### 模式1：主从模式
- 一个主代理协调多个子代理
- 主代理负责任务分配和结果汇总
- 适合：复杂项目的分工协作

#### 模式2：并行模式
- 多个代理同时处理独立任务
- 适用于：大规模代码分析、批量处理
- 优势：显著缩短处理时间

#### 模式3：流水线模式
- 任务按阶段顺序执行
- 每个阶段由特定代理负责
- 适合：需求→设计→实现→测试流程

### 3.3 团队协作工作流

#### 需求分析阶段
```
人类 → 主代理: "我需要一个用户认证系统"
主代理 → 需求代理: 分析功能需求
需求代理 → 主代理: 输出需求文档
主代理 → 人类: 确认需求
```

#### 方案设计阶段
```
主代理 → 架构代理: "设计用户认证系统架构"
架构代理 → 主代理: 输出架构方案
主代理 → 人类: 确认方案
```

#### 研发阶段
```
主代理 → 前端代理: 实现前端代码
主代理 → 后端代理: 实现后端代码
前端代理 → 主代理: 前端完成
后端代理 → 主代理: 后端完成
```

#### 测试阶段
```
主代理 → 测试代理: "为用户认证系统编写测试"
测试代理 → 主代理: 测试代码
主代理 → 人类: 确认测试覆盖
```

### 3.4 研发人员角色和职责

在使用 Claude Code 虚拟团队时，研发人员需要：

| 角色 | 职责 | 具体操作 |
|-----|------|---------|
| **产品经理** | 定义需求、确认方向 | 提供清晰的需求描述，确认输出 |
| **架构师** | 审核方案、把控质量 | 审查 Claude 提出的架构设计 |
| **开发者** | 实现代码、调试问题 | 审核生成的代码，运行测试 |
| **测试工程师** | 编写测试、验证功能 | 审核测试用例，确认覆盖率 |

### 3.5 高效协作建议

1. **明确职责边界**：每个代理有明确的职责
2. **结构化输出**：使用 JSON/Markdown 便于结果整合
3. **设置检查点**：关键节点需要人工确认
4. **统一沟通协议**：建立标准的输入输出格式
5. **合理的超时和重试**：避免长时间等待

---

## 四、其他实用技巧和建议

### 4.1 代码生成优化技巧

#### 解决"生成结果模糊"问题

**问题**：Claude 生成的代码不符合预期

**解决思路**：

1. **提供具体约束**
   ```bash
   # ✅ 具体约束
   "使用 Python 的 FastAPI 框架，添加 JWT 认证，返回 JSON 格式"

   # ❌ 模糊描述
   "帮我写个用户认证"
   ```

2. **提供参考代码**
   ```bash
   "参考以下代码风格，帮我实现..."
   ```

3. **明确验收标准**
   ```bash
   "实现后应该：1) 支持注册 2) 支持登录 3) 返回 token"
   ```

4. **分步生成**
   ```bash
   "先帮我创建数据模型"
   "然后创建 API 路由"
   "最后添加中间件"
   ```

### 4.2 会话管理技巧

1. **长期任务使用 TodoWrite**
   ```bash
   # 使用 TodoWrite 跟踪复杂任务进度
   TodoWrite(todos: [
     {"content": "创建用户模型", "status": "completed"},
     {"content": "实现 API 接口", "status": "in_progress"},
     {"content": "编写测试", "status": "pending"}
   ])
   ```

2. **记忆功能**
   - Claude Code 会记住会话中的重要信息
   - 可在 `memory/` 目录保存持久化信息

3. **工作目录切换**
   - 使用绝对路径
   - 避免频繁 `cd`

### 4.3 权限和安全性

```json
// .claude/settings.local.json 推荐配置
{
  "permissions": {
    "allow": [
      "Bash(npm *)",
      "Bash(python *)",
      "Bash(git *)",
      "Glob(**/*)",
      "Read(**/*)",
      "Edit(**/*)"
    ],
    "deny": [
      "Bash(rm -rf /**)",
      "Bash(sudo *)",
      "Bash(curl *)"
    ]
  }
}
```

### 4.4 项目案例参考

#### 案例：完整项目开发流程

```
1. 项目初始化
   人类: "帮我创建一个 Python FastAPI 项目"
   → Claude: 生成项目结构、依赖文件

2. 核心功能开发
   人类: "添加用户 CRUD 接口"
   → Claude: 生成 models, schemas, routes

3. 测试编写
   人类: "为用户接口编写单元测试"
   → Claude: 生成 pytest 测试用例

4. 代码审查
   人类: "审查一下生成的代码"
   → Claude: 分析潜在问题、优化建议

5. 提交代码
   人类: "/commit"
   → Claude: 创建规范提交
```

---

## 五、常见问题和解决方案

### Q1: 操作被拒绝，提示权限不足

**原因**：权限配置不够

**解决**：
```json
// 在 .claude/settings.local.json 中添加
{
  "permissions": {
    "allow": ["Bash(python *)", "Bash(npm *)"]
  }
}
```

### Q2: 找不到文件或路径错误

**原因**：工作目录或路径问题

**解决**：
- 使用绝对路径：`/Users/dingmaomao/project/src/main.py`
- 先用 `Glob` 确认文件存在
- 检查当前工作目录

### Q3: 大文件处理失败

**原因**：文件过大超出上下文

**解决**：
```bash
# 分页读取
Read(file_path: "large.py", limit: 100, offset: 0)
Read(file_path: "large.py", limit: 100, offset: 100)

# 先定位关键内容
Grep(pattern: "class.*User", path: "large.py", output_mode: "content")
```

### Q4: 代码理解错误

**原因**：上下文信息不足

**解决**：
- 提供更多背景信息
- 明确指定预期行为
- 添加注释解释复杂逻辑

### Q5: 生成代码不符合项目规范

**原因**：未提供规范上下文

**解决**：
- 告知项目使用的框架版本
- 提供现有代码风格示例
- 明确命名规范

### Q6: 会话上下文丢失

**原因**：上下文窗口限制

**解决**：
- 使用 TodoWrite 跟踪进度
- 定期总结已完成的工作
- 关键信息保存到 memory 文件

---

## 六、练习项目和资源

### 6.1 官方资源

| 资源 | 链接 | 说明 |
|-----|------|------|
| 官方文档 | [docs.anthropic.com](https://docs.anthropic.com) | 权威文档 |
| GitHub | [github.com/anthropics/claude-code](https://github.com/anthropics/claude-code) | 示例和源码 |
| Discord | Anthropic Discord | 社区交流 |

### 6.2 练习项目建议

#### 入门练习（1-2天）
1. **CLI 工具开发**
   - 创建命令行待办事项应用
   - 练习文件读写、命令行参数处理

2. **简单 Web API**
   - 使用 FastAPI/Express 创建 REST API
   - 练习 CRUD 操作

#### 中级练习（3-5天）
1. **MCP 集成**
   - 配置 GitHub MCP
   - 实现 PR 自动审查功能

2. **多代理协作**
   - 创建代码审查工作流
   - 实现文档自动生成

#### 高级练习（1周+）
1. **完整项目**
   - 从需求分析到测试的完整流程

2. **团队协作系统**
   - 多代理需求分析系统
   - 自动化开发工作流

### 6.3 学习路径建议

```
Week 1: 基础操作
├── 掌握基本对话和 slash commands
├── 熟悉文件操作工具
├── 了解权限配置

Week 2: MCP 和 Skills
├── 安装配置常用 MCP
├── 创建自定义 Skills
├── 集成开发工具链

Week 3: 协作开发
├── 多代理协作模式
├── 完整项目开发流程
├── 代码审查和优化

Week 4: 高级应用
├── 工作流自动化
├── 团队协作系统
└── 自定义工具开发
```

---

## 七、总结

### 核心要点回顾

1. **从基础命令开始**：先掌握直接对话、文件操作、Git 协作
2. **善用 MCP 和 Skills**：扩展能力，自动化常见任务
3. **虚拟团队协作**：多代理分工，提高效率
4. **明确任务描述**：具体、清晰、分步骤
5. **持续练习**：通过实际项目积累经验

### 快速上手清单

- [ ] 安装 Claude Code 并完成初始配置
- [ ] 尝试基础对话和文件操作
- [ ] 配置常用 MCP（filesystem, github）
- [ ] 尝试创建第一个小项目
- [ ] 练习使用 /commit 等内置 Skills
- [ ] 尝试多代理协作
- [ ] 建立适合项目的 settings 配置

---

> **提示**：本文档会持续更新，建议收藏。如需最新信息，请访问 [Anthropic 官方文档](https://docs.anthropic.com)。

---

*文档创建日期：2026-02-28*
