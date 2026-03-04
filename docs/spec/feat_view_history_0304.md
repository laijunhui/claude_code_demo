# 功能规范：代码审核历史记录查看

## 需求概述

为现有代码审查系统增加历史记录查看功能，用户可以：
1. 查看已提交的代码审查记录列表
2. 查看单条审查记录的详细信息和状态

## 当前系统状态

现有实现（[routes.py:15](code-reviewer/app/api/routes.py#L15)）：
- 使用内存字典 `review_results: dict = {}` 存储审查结果
- 仅支持通过 `review_id` 查询单个审查结果
- 无列表展示、无分页、无持久化

---

## 方案一：轻量级方案（内存 + 文件持久化）

### 产品设计

| 功能 | 描述 |
|------|------|
| 列表页 | 展示所有历史审查记录，含：review_id、状态、文件数、创建时间 |
| 详情页 | 展示单条审查的完整结果（issues、agents_results、summary） |
| 分页 | 支持按时间倒序，固定每页 20 条 |
| 删除 | 支持手动删除单条记录 |

### 技术设计

**数据存储**

- 使用 JSON 文件存储审查记录（位于 `data/reviews/` 目录）
- 文件命名：`{review_id}.json`
- 服务启动时加载历史索引到内存

**新增 API 端点**

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/reviews` | GET | 获取审查记录列表（分页） |
| `/api/reviews/{review_id}` | GET | 获取单条审查详情 |
| `/api/reviews/{review_id}` | DELETE | 删除单条审查记录 |

**数据库表结构（JSON 文件）**

```json
// reviews/index.json - 索引文件
{
  "reviews": [
    {
      "review_id": "review_abc123",
      "status": "completed",
      "files_count": 3,
      "total_issues": 12,
      "created_at": "2026-03-04T10:30:00Z",
      "duration_ms": 1500
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20
}

// reviews/review_abc123.json - 详情文件
{
  "review_id": "review_abc123",
  "status": "completed",
  "files": ["app/main.py", "app/config.py"],
  "summary": { ... },
  "issues": [ ... ],
  "agents_results": [ ... ],
  "created_at": "2026-03-04T10:30:00Z",
  "duration_ms": 1500
}
```

**核心代码改动**

1. 新增 `ReviewStorage` 类（[storage.py](code-reviewer/app/storage.py)）负责 JSON 文件读写
2. 修改 [routes.py](code-reviewer/app/api/routes.py)：将 `review_results` 替换为持久化存储
3. 新增列表查询接口和删除接口

**优点**
- 部署简单，无需额外依赖
- 数据可备份、易迁移
- 适合中小规模使用

**缺点**
- 并发写入需加锁
- 大规模数据查询性能有限
- 无内置统计报表

---

## 方案二：完整方案（SQLite 数据库）

### 产品设计

| 功能 | 描述 |
|------|------|
| 列表页 | 展示历史审查记录，支持：时间筛选、状态筛选、文件路径搜索 |
| 详情页 | 展示完整审查结果 |
| 分页 | 支持 cursor-based 分页 |
| 统计 | 提供简单统计（总数、通过/失败数、平均处理时长） |
| 保留策略 | 支持自动清理 30 天前记录（可选） |

### 技术设计

**数据存储**

- 使用 SQLite 数据库（位于 `data/reviews.db`）
- 使用 SQLAlchemy 作为 ORM

**新增 API 端点**

| 端点 | 方法 | 功能 |
|------|------|------|
| `/api/reviews` | GET | 获取审查列表（支持分页、筛选、排序） |
| `/api/reviews/{review_id}` | GET | 获取单条审查详情 |
| `/api/reviews/{review_id}` | DELETE | 删除单条审查记录 |
| `/api/reviews/stats` | GET | 获取统计信息 |

**数据库表结构**

```sql
-- 审查记录主表
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL,  -- pending, running, completed, failed
    files_count INTEGER DEFAULT 0,
    total_issues INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    completed_at TIMESTAMP
);

-- 审查问题详情表
CREATE TABLE review_issues (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id VARCHAR(64) NOT NULL,
    file_path VARCHAR(512),
    line INTEGER,
    column_num INTEGER,
    severity VARCHAR(20),
    issue_type VARCHAR(50),
    message TEXT,
    suggestion TEXT,
    FOREIGN KEY (review_id) REFERENCES reviews(review_id) ON DELETE CASCADE
);

-- 审查文件表
CREATE TABLE review_files (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id VARCHAR(64) NOT NULL,
    file_path VARCHAR(512),
    language VARCHAR(20),
    FOREIGN KEY (review_id) REFERENCES reviews(review_id) ON DELETE CASCADE
);

-- 索引
CREATE INDEX idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_review_issues_review_id ON review_issues(review_id);
```

**核心代码改动**

1. 新增 [models.py](code-reviewer/app/models.py)：SQLAlchemy 模型定义
2. 新增 [database.py](code-reviewer/app/database.py)：数据库连接和初始化
3. 新增 `ReviewRepository` 类（[repository.py](code-reviewer/app/repository.py)）负责数据访问
4. 修改 [routes.py](code-reviewer/app/api/routes.py)：接入数据库查询

**API 响应示例**

```json
// GET /api/reviews?page=1&page_size=20&status=completed
{
  "items": [
    {
      "review_id": "review_abc123",
      "status": "completed",
      "files_count": 3,
      "total_issues": 12,
      "critical_count": 1,
      "error_count": 2,
      "warning_count": 5,
      "info_count": 4,
      "created_at": "2026-03-04T10:30:00Z",
      "duration_ms": 1500
    }
  ],
  "total": 100,
  "page": 1,
  "page_size": 20,
  "has_more": true
}

// GET /api/reviews/stats
{
  "total_reviews": 100,
  "by_status": {
    "completed": 85,
    "failed": 10,
    "pending": 3,
    "running": 2
  },
  "avg_duration_ms": 2500,
  "avg_issues_per_review": 8
}
```

**优点**
- 高并发支持，查询性能优
- 内置统计功能
- 支持复杂筛选和排序
- 可扩展性强（易于迁移到 MySQL/PostgreSQL）

**缺点**
- 需要额外依赖（SQLAlchemy）
- 部署稍复杂
- 需处理数据库迁移

---

## 方案对比

| 维度 | 方案一（JSON 文件） | 方案二（SQLite） |
|------|---------------------|------------------|
| 部署复杂度 | 低 | 中 |
| 查询性能 | 一般 | 优 |
| 并发支持 | 需手动加锁 | 良好 |
| 依赖 | 无 | SQLAlchemy |
| 统计功能 | 需自行实现 | 内置 |
| 数据迁移 | 复制文件即可 | 导出 SQL/CSV |
| 建议场景 | 个人/小团队使用 | 团队协作/生产环境 |

---

## 推荐

- **快速验证 / 个人使用**：选择方案一
- **团队协作 / 生产环境**：选择方案二

建议先采用方案一快速上线，后期根据用户量增长平滑迁移到方案二。
