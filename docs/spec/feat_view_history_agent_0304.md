# 功能规范文档：代码审查历史记录查看功能

**文档版本**: 1.0
**创建日期**: 2026-03-04
**功能模块**: 历史记录管理
**关联需求**: 为代码审查系统增加历史记录查看功能

---

## 1. 概述

### 1.1 需求背景

当前代码审查系统已完成基础功能建设，支持通过 REST API 提交代码审查任务，并能够并行执行 SyntaxAgent（语法检查）、SecurityAgent（安全扫描）、StyleAgent（代码风格）三个 Agent 进行代码评审。然而，系统目前缺乏历史记录管理能力：

- 审查结果仅存储在内存字典 `review_results` 中（`routes.py:15`）
- 重启服务后历史数据丢失
- 无法查看历史审查列表
- 无法对历史审查结果进行统计分析

这限制了用户对代码质量趋势的追踪，也无法满足团队协作场景下对审查历史的查阅需求。

### 1.2 需求目标

本次功能开发旨在为代码审查系统增加历史记录查看功能，实现以下目标：

1. **持久化存储**：将审查记录持久化保存，支持服务重启后数据不丢失
2. **列表查看**：支持用户查看已提交的代码审查记录列表
3. **详情查看**：支持用户查看单条审查记录的详细信息和当前状态
4. **数据管理**：支持删除单条审查记录，保持数据整洁
5. **统计分析**（方案二）：提供审查总量、通过率、平均处理时长等统计信息

---

## 2. 功能需求

### 2.1 列表查看功能

**功能描述**：用户可以查看所有历史代码审查记录的列表

**需求详情**：

| 需求项 | 描述 | 优先级 |
|--------|------|--------|
| 列表展示 | 以列表形式展示所有审查记录，按创建时间倒序排列 | P0 |
| 分页支持 | 支持分页展示，每页默认 20 条记录 | P0 |
| 基础信息 | 每条记录显示：review_id、状态、文件数、问题数、创建时间 | P0 |
| 状态筛选 | 支持按审查状态（pending/running/completed/failed）筛选 | P1 |
| 时间筛选 | 支持按创建时间范围筛选 | P1 |

### 2.2 详情查看功能

**功能描述**：用户可以查看单条审查记录的完整详细信息

**需求详情**：

| 需求项 | 描述 | 优先级 |
|--------|------|--------|
| 审查状态 | 显示当前审查状态（pending/running/completed/failed） | P0 |
| 摘要信息 | 显示文件数、总问题数、各严重程度问题数量、处理时长 | P0 |
| 问题列表 | 列出所有发现的问题，包含文件路径、行号、严重程度、类型、描述、建议 | P0 |
| Agent 结果 | 显示各 Agent（SyntaxAgent、SecurityAgent、StyleAgent）的执行结果 | P0 |
| 审查文件 | 显示被审查的文件列表 | P0 |
| 实时更新 | 对于 pending/running 状态的审查，支持查看实时进度 | P1 |

### 2.3 删除功能

**功能描述**：用户可以删除单条审查记录

**需求详情**：

| 需求项 | 描述 | 优先级 |
|--------|------|--------|
| 单条删除 | 支持通过 review_id 删除单条审查记录 | P1 |
| 删除确认 | 删除前返回记录详情供确认 | P1 |

### 2.4 统计功能（方案二专有）

**功能描述**：提供代码审查的统计分析数据

**需求详情**：

| 需求项 | 描述 | 优先级 |
|--------|------|--------|
| 总量统计 | 显示审查记录总数 | P1 |
| 状态分布 | 显示各状态（pending/running/completed/failed）的数量分布 | P1 |
| 平均时长 | 计算平均处理时长 | P1 |
| 平均问题数 | 计算平均每次审查发现的问题数 | P1 |

---

## 3. 技术方案

### 3.1 方案一：轻量级方案（JSON 文件持久化）

#### 3.1.1 设计思路

采用文件系统存储审查记录，使用 JSON 格式保存数据：

- **存储位置**：`data/reviews/` 目录
- **索引文件**：`data/reviews/index.json` - 存储审查记录索引列表
- **详情文件**：`data/reviews/{review_id}.json` - 存储每条审查的完整详情
- **启动加载**：服务启动时加载索引到内存，加快列表查询

#### 3.1.2 架构组件

```
code-reviewer/
├── app/
│   ├── storage/              # 新增：存储层
│   │   ├── __init__.py
│   │   └── json_storage.py  # JSON 文件存储实现
│   └── api/
│       └── routes.py         # 修改：接入持久化存储
└── data/
    └── reviews/              # 审查记录存储目录
        ├── index.json        # 索引文件
        ├── review_abc123.json
        └── review_def456.json
```

#### 3.1.3 核心类设计

```python
# app/storage/json_storage.py

class JSONReviewStorage:
    """基于 JSON 文件的审查记录存储"""

    def __init__(self, base_dir: str = "data/reviews"):
        self.base_dir = Path(base_dir)
        self.index_file = self.base_dir / "index.json"
        self._ensure_dir()

    def save_review(self, review_id: str, data: dict) -> None:
        """保存审查记录"""
        # 写入详情文件
        detail_file = self.base_dir / f"{review_id}.json"
        detail_file.write_text(json.dumps(data, ensure_ascii=False, indent=2))

        # 更新索引文件
        self._update_index(review_id, data)

    def get_review(self, review_id: str) -> Optional[dict]:
        """获取单条审查详情"""
        detail_file = self.base_dir / f"{review_id}.json"
        if not detail_file.exists():
            return None
        return json.loads(detail_file.read_text())

    def list_reviews(self, page: int = 1, page_size: int = 20,
                     status: str = None) -> dict:
        """获取审查列表（支持分页和状态筛选）"""
        index_data = self._load_index()
        reviews = index_data.get("reviews", [])

        # 筛选
        if status:
            reviews = [r for r in reviews if r.get("status") == status]

        # 排序（按创建时间倒序）
        reviews.sort(key=lambda x: x.get("created_at", ""), reverse=True)

        # 分页
        total = len(reviews)
        start = (page - 1) * page_size
        end = start + page_size
        items = reviews[start:end]

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": end < total
        }

    def delete_review(self, review_id: str) -> bool:
        """删除审查记录"""
        # 删除详情文件
        detail_file = self.base_dir / f"{review_id}.json"
        if detail_file.exists():
            detail_file.unlink()

        # 从索引中移除
        self._remove_from_index(review_id)
        return True
```

#### 3.1.4 优缺点分析

| 维度 | 说明 |
|------|------|
| **优点** | 部署简单，无需额外依赖；数据可备份、易迁移（复制文件即可）；开发工作量较小；适合中小规模使用场景 |
| **缺点** | 并发写入需要加锁；大规模数据查询性能有限；无内置统计报表功能；不支持复杂筛选和排序 |

---

### 3.2 方案二：完整方案（SQLite 数据库）

#### 3.2.1 设计思路

采用 SQLite 数据库作为存储后端，使用 SQLAlchemy 作为 ORM 框架：

- **数据库文件**：`data/reviews.db`
- **ORM 框架**：SQLAlchemy
- **连接方式**：单例模式管理数据库连接

#### 3.2.2 架构组件

```
code-reviewer/
├── app/
│   ├── models/               # 新增：数据模型层
│   │   ├── __init__.py
│   │   └── review.py         # SQLAlchemy 模型定义
│   ├── repository/           # 新增：数据访问层
│   │   ├── __init__.py
│   │   └── review_repo.py    # 审查记录仓储
│   ├── database.py           # 新增：数据库连接管理
│   └── api/
│       └── routes.py         # 修改：接入数据库查询
└── data/
    └── reviews.db             # SQLite 数据库文件
```

#### 3.2.3 核心类设计

```python
# app/models/review.py

from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

class Review(Base):
    """审查记录主表"""
    __tablename__ = "reviews"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String(64), unique=True, nullable=False, index=True)
    status = Column(String(20), nullable=False, default="pending")  # pending/running/completed/failed

    # 统计字段（冗余存储，优化查询性能）
    files_count = Column(Integer, default=0)
    total_issues = Column(Integer, default=0)
    critical_count = Column(Integer, default=0)
    error_count = Column(Integer, default=0)
    warning_count = Column(Integer, default=0)
    info_count = Column(Integer, default=0)
    duration_ms = Column(Integer, default=0)

    # 时间戳
    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)

    # 关联
    issues = relationship("ReviewIssue", back_populates="review", cascade="all, delete-orphan")
    files = relationship("ReviewFile", back_populates="review", cascade="all, delete-orphan")

    __table_args__ = (
        Index("idx_reviews_created_at", "created_at"),
        Index("idx_reviews_status", "status"),
    )


class ReviewIssue(Base):
    """审查问题详情表"""
    __tablename__ = "review_issues"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String(64), ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512))
    line = Column(Integer)
    column_num = Column(Integer)
    severity = Column(String(20))  # critical/error/warning/info
    issue_type = Column(String(50))
    message = Column(Text)
    suggestion = Column(Text)

    review = relationship("Review", back_populates="issues")


class ReviewFile(Base):
    """审查文件表"""
    __tablename__ = "review_files"

    id = Column(Integer, primary_key=True, autoincrement=True)
    review_id = Column(String(64), ForeignKey("reviews.review_id", ondelete="CASCADE"), nullable=False)
    file_path = Column(String(512))
    language = Column(String(20))

    review = relationship("Review", back_populates="files")
```

```python
# app/repository/review_repo.py

class ReviewRepository:
    """审查记录数据访问仓储"""

    def __init__(self, db: Session):
        self.db = db

    def create(self, review_data: dict) -> Review:
        """创建审查记录"""
        review = Review(
            review_id=review_data["review_id"],
            status=review_data.get("status", "pending"),
            files_count=len(review_data.get("files", [])),
        )
        self.db.add(review)
        self.db.commit()
        self.db.refresh(review)
        return review

    def get_by_id(self, review_id: str) -> Optional[Review]:
        """根据 ID 获取审查记录"""
        return self.db.query(Review).filter(Review.review_id == review_id).first()

    def update(self, review_id: str, data: dict) -> Optional[Review]:
        """更新审查记录"""
        review = self.get_by_id(review_id)
        if not review:
            return None

        for key, value in data.items():
            if hasattr(review, key):
                setattr(review, key, value)

        self.db.commit()
        self.db.refresh(review)
        return review

    def list(self, page: int = 1, page_size: int = 20,
             status: str = None, created_after: datetime = None) -> dict:
        """获取审查列表（支持分页和筛选）"""
        query = self.db.query(Review)

        # 筛选条件
        if status:
            query = query.filter(Review.status == status)
        if created_after:
            query = query.filter(Review.created_at >= created_after)

        # 排序
        query = query.order_by(Review.created_at.desc())

        # 分页
        total = query.count()
        items = query.offset((page - 1) * page_size).limit(page_size).all()

        return {
            "items": items,
            "total": total,
            "page": page,
            "page_size": page_size,
            "has_more": (page * page_size) < total
        }

    def delete(self, review_id: str) -> bool:
        """删除审查记录"""
        review = self.get_by_id(review_id)
        if not review:
            return False
        self.db.delete(review)
        self.db.commit()
        return True

    def get_stats(self) -> dict:
        """获取统计信息"""
        from sqlalchemy import func

        # 总数
        total = self.db.query(func.count(Review.id)).scalar()

        # 状态分布
        status_counts = self.db.query(
            Review.status,
            func.count(Review.id)
        ).group_by(Review.status).all()
        by_status = {status: count for status, count in status_counts}

        # 平均处理时长
        avg_duration = self.db.query(
            func.avg(Review.duration_ms)
        ).filter(Review.status == "completed").scalar() or 0

        # 平均问题数
        avg_issues = self.db.query(
            func.avg(Review.total_issues)
        ).scalar() or 0

        return {
            "total_reviews": total,
            "by_status": by_status,
            "avg_duration_ms": int(avg_duration),
            "avg_issues_per_review": round(float(avg_issues), 1)
        }
```

#### 3.2.4 优缺点分析

| 维度 | 说明 |
|------|------|
| **优点** | 高并发支持，查询性能优异；内置统计功能；支持复杂筛选、排序、聚合查询；可扩展性强（易于迁移到 MySQL/PostgreSQL）；数据完整性强（支持事务和约束） |
| **缺点** | 需要额外依赖（SQLAlchemy）；部署稍复杂；需要处理数据库迁移；单机文件数据库，并发写入有瓶颈 |

---

### 3.3 方案对比与选择建议

| 对比维度 | 方案一（JSON 文件） | 方案二（SQLite） |
|----------|---------------------|------------------|
| **部署复杂度** | 低（无需额外依赖） | 中（需安装 SQLAlchemy） |
| **查询性能** | 一般（需遍历文件） | 优（索引支持） |
| **并发支持** | 需手动加锁 | 良好（SQLite 内置锁） |
| **额外依赖** | 无 | SQLAlchemy |
| **统计功能** | 需自行实现 | 内置支持 |
| **数据迁移** | 复制文件即可 | 导出 SQL/CSV |
| **推荐场景** | 个人开发者、小团队（< 1000 条/天） | 团队协作、生产环境 |

#### 选择建议

- **快速验证 / 个人使用**：选择方案一，开发周期短，可快速上线
- **团队协作 / 生产环境**：选择方案二，架构更规范，便于后续扩展

建议采用渐进式开发策略：先采用方案一快速上线 MVP 版本，后期根据用户量增长平滑迁移到方案二。

---

## 4. API 设计

### 4.1 方案一 API 设计

#### 4.1.1 端点总览

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/api/reviews` | GET | 获取审查列表 | 可选 |
| `/api/reviews/{review_id}` | GET | 获取审查详情 | 可选 |
| `/api/reviews/{review_id}` | DELETE | 删除审查记录 | 必选 |

#### 4.1.2 API 详情

**GET /api/reviews - 获取审查列表**

请求参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | query int | 否 | 1 | 页码 |
| page_size | query int | 否 | 20 | 每页数量 |
| status | query string | 否 | - | 按状态筛选 |

响应示例（200 OK）：

```json
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
```

**GET /api/reviews/{review_id} - 获取审查详情**

响应示例（200 OK）：

```json
{
  "review_id": "review_abc123",
  "status": "completed",
  "files": [
    "app/main.py",
    "app/config.py"
  ],
  "summary": {
    "review_id": "review_abc123",
    "files_count": 2,
    "total_issues": 12,
    "by_severity": {
      "critical": 1,
      "error": 2,
      "warning": 5,
      "info": 4
    },
    "by_type": {
      "syntax": 3,
      "security": 2,
      "style": 7
    },
    "duration_ms": 1500
  },
  "issues": [
    {
      "file_path": "app/main.py",
      "line": 10,
      "column": 5,
      "severity": "error",
      "type": "syntax",
      "message": "undefined name 'foo'",
      "suggestion": "Define 'foo' before using it"
    }
  ],
  "agents_results": [
    {
      "name": "syntax",
      "agent_name": "syntax",
      "status": "success",
      "output": "分析了 3 个问题",
      "issues": [],
      "duration_ms": 120
    }
  ],
  "duration_ms": 1500,
  "created_at": "2026-03-04T10:30:00Z"
}
```

**DELETE /api/reviews/{review_id} - 删除审查记录**

响应示例（200 OK）：

```json
{
  "message": "Review deleted successfully",
  "review_id": "review_abc123"
}
```

响应示例（404 Not Found）：

```json
{
  "detail": "Review not found"
}
```

---

### 4.2 方案二 API 设计

#### 4.2.1 端点总览

| 端点 | 方法 | 功能 | 认证 |
|------|------|------|------|
| `/api/reviews` | GET | 获取审查列表（支持筛选） | 可选 |
| `/api/reviews/{review_id}` | GET | 获取审查详情 | 可选 |
| `/api/reviews/{review_id}` | DELETE | 删除审查记录 | 必选 |
| `/api/reviews/stats` | GET | 获取统计信息 | 可选 |

#### 4.2.2 API 详情

**GET /api/reviews - 获取审查列表**

请求参数：

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| page | query int | 否 | 1 | 页码 |
| page_size | query int | 否 | 20 | 每页数量 |
| status | query string | 否 | - | 按状态筛选 |
| created_after | query string | 否 | - | 创建时间筛选（ISO 8601） |
| sort_by | query string | 否 | created_at | 排序字段 |
| sort_order | query string | 否 | desc | 排序方向（asc/desc） |

响应示例（200 OK）：与方案一相同

**GET /api/reviews/{review_id} - 获取审查详情**

响应示例（200 OK）：与方案一相同

**DELETE /api/reviews/{review_id} - 删除审查记录**

响应示例（200 OK）：与方案一相同

**GET /api/reviews/stats - 获取统计信息**

响应示例（200 OK）：

```json
{
  "total_reviews": 100,
  "by_status": {
    "completed": 85,
    "failed": 10,
    "pending": 3,
    "running": 2
  },
  "avg_duration_ms": 2500,
  "avg_issues_per_review": 8.5
}
```

---

## 5. 数据模型

### 5.1 方案一数据模型

#### 5.1.1 索引文件（index.json）

```json
{
  "reviews": [
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
  "page_size": 20
}
```

#### 5.1.2 详情文件（{review_id}.json）

```json
{
  "review_id": "review_abc123",
  "status": "completed",
  "files": [
    "app/main.py",
    "app/config.py"
  ],
  "summary": {
    "review_id": "review_abc123",
    "files_count": 2,
    "total_issues": 12,
    "by_severity": {
      "critical": 1,
      "error": 2,
      "warning": 5,
      "info": 4
    },
    "by_type": {
      "syntax": 3,
      "security": 2,
      "style": 7
    },
    "duration_ms": 1500
  },
  "issues": [
    {
      "file_path": "app/main.py",
      "line": 10,
      "column": 5,
      "severity": "error",
      "type": "syntax",
      "message": "undefined name 'foo'",
      "suggestion": "Define 'foo' before using it"
    }
  ],
  "agents_results": [
    {
      "name": "syntax",
      "agent_name": "syntax",
      "status": "success",
      "output": "分析了 3 个问题",
      "issues": [],
      "duration_ms": 120,
      "error": null
    }
  ],
  "duration_ms": 1500,
  "created_at": "2026-03-04T10:30:00Z"
}
```

---

### 5.2 方案二数据模型

#### 5.2.1 数据库表结构

```sql
-- 审查记录主表
CREATE TABLE reviews (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    review_id VARCHAR(64) UNIQUE NOT NULL,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',

    -- 统计字段
    files_count INTEGER DEFAULT 0,
    total_issues INTEGER DEFAULT 0,
    critical_count INTEGER DEFAULT 0,
    error_count INTEGER DEFAULT 0,
    warning_count INTEGER DEFAULT 0,
    info_count INTEGER DEFAULT 0,
    duration_ms INTEGER DEFAULT 0,

    -- 时间戳
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
CREATE INDEX idx_reviews_review_id ON reviews(review_id);
CREATE INDEX idx_reviews_created_at ON reviews(created_at DESC);
CREATE INDEX idx_reviews_status ON reviews(status);
CREATE INDEX idx_review_issues_review_id ON review_issues(review_id);
CREATE INDEX idx_review_files_review_id ON review_files(review_id);
```

#### 5.2.2 ER 图

```
┌─────────────────────┐       ┌─────────────────────┐
│      reviews        │       │    review_issues    │
├─────────────────────┤       ├─────────────────────┤
│ id (PK)             │       │ id (PK)             │
│ review_id (UQ)     │──1:N──│ review_id (FK)      │
│ status              │       │ file_path           │
│ files_count         │       │ line                │
│ total_issues        │       │ column_num          │
│ critical_count      │       │ severity            │
│ error_count         │       │ issue_type          │
│ warning_count       │       │ message             │
│ info_count          │       │ suggestion          │
│ duration_ms         │       └─────────────────────┘
│ created_at          │
│ completed_at        │       ┌─────────────────────┐
└─────────────────────┘       │    review_files     │
                             ├─────────────────────┤
                             │ id (PK)             │
                             │ review_id (FK)      │
                             │ file_path           │
                             │ language            │
                             └─────────────────────┘
```

---

## 6. 界面原型（文字描述）

### 6.1 审查记录列表页

```
+------------------------------------------------------------------+
|  代码审查系统                                          [Logo]     |
+------------------------------------------------------------------+
|                                                                   |
|  历史审查记录                                          [+ 新建审查] |
|  ---------------------------------------------------------------- |
|                                                                   |
|  [筛选: 全部状态 v]  [排序: 最新优先 v]                  [搜索]   |
|                                                                   |
|  +--------------------------------------------------------------+ |
|  | # | Review ID      | 状态      | 文件数 | 问题数 | 创建时间   | |
|  +--------------------------------------------------------------+ |
|  | 1 | review_abc123  | completed | 3      | 12     | 03-04 10:30| |
|  | 2 | review_def456  | completed | 1      | 5      | 03-04 09:15| |
|  | 3 | review_ghi789  | running    | 2      | -      | 03-04 09:00| |
|  | 4 | review_jkl012  | failed     | 1      | -      | 03-03 18:20| |
|  | 5 | review_mno345  | completed  | 5      | 23     | 03-03 16:45| |
|  +--------------------------------------------------------------+ |
|                                                                   |
|                           < 1 2 3 ... 5 >                        |
|                                                                   |
+------------------------------------------------------------------+
```

**说明**：
- 状态标签：completed（绿色）、running（蓝色）、pending（灰色）、failed（红色）
- 点击行可进入详情页
- 支持分页，每页 20 条

---

### 6.2 审查详情页

```
+------------------------------------------------------------------+
|  < 返回列表                    审查详情: review_abc123            |
+------------------------------------------------------------------+
|                                                                   |
|  [基本信息]                                                       |
|  ----------------------------------------------------------------|
|  状态:    [completed v]          创建时间: 2026-03-04 10:30:00   |
|  文件数:  3                      处理时长: 1.5s                   |
|                                                                   |
|  [问题统计]                                                       |
|  ----------------------------------------------------------------|
|  严重: 1  | 错误: 2  | 警告: 5  | 提示: 4  | 总计: 12            |
|  ----------------------------------------------------------------|
|  [████████████░░░░░░░░░░░░░░░░░] 37% (12/50 建议修复)            |
|                                                                   |
|  [问题列表]                         [Agent 结果]                 |
|  ----------------------------------------------------------------|
|  +----------------------------------------------------------+    |
|  | app/main.py:10 | error   | syntax | undefined name 'foo'|    |
|  | app/config.py: | warning | style  | 建议使用 snake_case   |    |
|  | app/main.py:25 | info    | style  | 缺少文档字符串        |    |
|  | ...                                                     |    |
|  +----------------------------------------------------------+    |
|                                                                   |
|  [删除此审查]                                                     |
|                                                                   |
+------------------------------------------------------------------+
```

**说明**：
- 问题按严重程度排序：critical > error > warning > info
- 可切换"问题列表"和"Agent 结果"标签页查看不同维度
- 提供删除按钮确认后可删除记录

---

### 6.3 统计页面（方案二专有）

```
+------------------------------------------------------------------+
|  代码审查系统 - 统计                                              |
+------------------------------------------------------------------+
|                                                                   |
|  [概览统计]                                                       |
|  ----------------------------------------------------------------|
|                                                                   |
|  +------------+  +------------+  +------------+  +------------+  |
|  | 总审查数   |  | 平均时长   |  | 平均问题数 |  | 完成率     |  |
|  |   100      |  |   2.5s     |  |   8.5      |  |   85%      |  |
|  +------------+  +------------+  +------------+  +------------+  |
|                                                                   |
|  [状态分布]                                                       |
|  ----------------------------------------------------------------|
|  completed: ████████████████████ 85 (85%)                        |
|  failed:    ███ 10 (10%)                                         |
|  pending:   ▌ 3 (3%)                                             |
|  running:   ▌ 2 (2%)                                             |
|                                                                   |
+------------------------------------------------------------------+
```

---

## 7. 实施计划

### 7.1 开发阶段划分

| 阶段 | 周期 | 目标 | 交付物 |
|------|------|------|--------|
| **阶段一：基础设施** | 1 天 | 搭建存储层框架 | 存储目录结构、基础类 |
| **阶段二：核心功能** | 2 天 | 实现列表和详情 API | 3 个 API 端点 |
| **阶段三：数据管理** | 1 天 | 实现删除功能 | DELETE 端点 |
| **阶段四：前端集成** | 2 天 | 页面开发 | 列表页、详情页 |
| **阶段五：测试验收** | 1 天 | 联调测试 | 功能测试报告 |

**总工期**：约 7 个工作日（方案一）/ 9 个工作日（方案二）

---

### 7.2 方案一实施任务

| 序号 | 任务 | 负责人 | 工时 | 依赖 |
|------|------|--------|------|------|
| 1.1 | 创建 `app/storage/` 目录结构 | - | 0.5h | - |
| 1.2 | 实现 `JSONReviewStorage` 类 | - | 4h | 1.1 |
| 1.3 | 修改 `routes.py` 集成存储层 | - | 2h | 1.2 |
| 2.1 | 实现 `GET /api/reviews` 列表接口 | - | 3h | 1.3 |
| 2.2 | 实现 `GET /api/reviews/{id}` 详情接口 | - | 2h | 1.3 |
| 3.1 | 实现 `DELETE /api/reviews/{id}` 删除接口 | - | 2h | 2.2 |
| 4.1 | 前端列表页开发 | - | 4h | 2.1 |
| 4.2 | 前端详情页开发 | - | 4h | 2.2 |
| 5.1 | 单元测试 | - | 3h | 3.1 |
| 5.2 | 联调测试 | - | 2h | 4.2 |

---

### 7.3 方案二实施任务

| 序号 | 任务 | 负责人 | 工时 | 依赖 |
|------|------|--------|------|------|
| 1.1 | 添加 SQLAlchemy 依赖 | - | 0.5h | - |
| 1.2 | 创建 `app/models/` 目录结构 | - | 0.5h | - |
| 1.3 | 实现数据库模型定义 | - | 3h | 1.2 |
| 1.4 | 实现 `app/database.py` 数据库管理 | - | 2h | 1.3 |
| 1.5 | 创建数据库初始化脚本 | - | 1h | 1.4 |
| 2.1 | 实现 `ReviewRepository` 仓储类 | - | 4h | 1.4 |
| 2.2 | 修改 `routes.py` 集成仓储层 | - | 2h | 2.1 |
| 3.1 | 实现 `GET /api/reviews` 列表接口 | - | 3h | 2.2 |
| 3.2 | 实现 `GET /api/reviews/{id}` 详情接口 | - | 2h | 2.2 |
| 3.3 | 实现 `DELETE /api/reviews/{id}` 删除接口 | - | 2h | 3.2 |
| 3.4 | 实现 `GET /api/reviews/stats` 统计接口 | - | 3h | 2.1 |
| 4.1 | 前端列表页开发 | - | 4h | 3.1 |
| 4.2 | 前端详情页开发 | - | 4h | 3.2 |
| 4.3 | 前端统计页开发 | - | 3h | 3.4 |
| 5.1 | 单元测试 | - | 3h | 3.3 |
| 5.2 | 联调测试 | - | 3h | 4.3 |

---

### 7.4 数据迁移说明

若从方案一切换到方案二，需执行以下数据迁移：

```python
# 迁移脚本伪代码

def migrate_from_json_to_sqlite(json_storage: JSONReviewStorage, repo: ReviewRepository):
    # 1. 读取所有历史记录
    index_data = json_storage._load_index()

    # 2. 逐条导入数据库
    for review_summary in index_data["reviews"]:
        review_id = review_summary["review_id"]

        # 读取完整详情
        review_detail = json_storage.get_review(review_id)
        if not review_detail:
            continue

        # 创建数据库记录
        repo.create({
            "review_id": review_id,
            "status": review_detail.get("status"),
            "files_count": review_summary.get("files_count"),
            "total_issues": review_summary.get("total_issues"),
            # ... 其他字段
        })

    print(f"Migration completed: {len(index_data['reviews'])} records")
```

---

### 7.5 风险与缓解

| 风险 | 影响 | 缓解措施 |
|------|------|----------|
| 并发写入冲突 | 数据丢失或不一致 | 使用文件锁或切换到方案二 |
| 大文件查询性能差 | 响应时间长 | 限制单次查询数量，增加索引 |
| 数据库文件损坏 | 数据丢失 | 定期备份，实现主从复制 |
| 前端分页数据不一致 | 用户体验差 | 使用游标分页，增加缓存层 |

---

## 附录

### A. 现有系统 API 参考

当前系统已实现的 API（供参考）：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/api/review` | POST | 提交代码审查 |
| `/api/review/{review_id}` | GET | 查询审查结果 |
| `/api/health` | GET | 健康检查 |
| `/webhook/github` | POST | GitHub Webhook |

### B. 数据字典

| 字段 | 类型 | 说明 |
|------|------|------|
| review_id | string | 审查记录唯一标识，格式：`review_{8位随机字符}` |
| status | string | 审查状态：`pending`（待处理）、`running`（处理中）、`completed`（完成）、`failed`（失败） |
| files_count | int | 审查的文件数量 |
| total_issues | int | 发现的问题总数 |
| severity | string | 问题严重程度：`critical`（严重）、`error`（错误）、`warning`（警告）、`info`（提示） |
| issue_type | string | 问题类型：`syntax`（语法）、`security`（安全）、`style`（风格）、`general`（通用） |
| duration_ms | int | 处理时长（毫秒） |
| created_at | datetime | 创建时间（ISO 8601 格式） |

---

*文档结束*
