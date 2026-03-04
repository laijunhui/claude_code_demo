# JSON 文件存储层实现
import json
import os
from datetime import datetime
from pathlib import Path
from typing import Optional, List, Dict

from app.logger import logger


class JSONReviewStorage:
    """基于 JSON 文件的审查记录存储"""

    def __init__(self, base_dir: str = "data/reviews"):
        self.base_dir = Path(base_dir)
        self.index_file = self.base_dir / "index.json"
        self._ensure_dir()

    def _ensure_dir(self):
        """确保目录存在"""
        self.base_dir.mkdir(parents=True, exist_ok=True)
        if not self.index_file.exists():
            self._save_index({"reviews": [], "total": 0})

    def _load_index(self) -> dict:
        """加载索引文件"""
        try:
            with open(self.index_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError):
            return {"reviews": [], "total": 0}

    def _save_index(self, index: dict):
        """保存索引文件"""
        with open(self.index_file, "w", encoding="utf-8") as f:
            json.dump(index, f, ensure_ascii=False, indent=2)

    def _update_index(self, review_id: str, data: dict):
        """更新索引"""
        index = self._load_index()

        # 检查是否已存在
        existing_idx = None
        for i, item in enumerate(index.get("reviews", [])):
            if item.get("review_id") == review_id:
                existing_idx = i
                break

        # 创建索引项
        index_item = {
            "review_id": review_id,
            "status": data.get("status", "unknown"),
            "created_at": data.get("created_at", datetime.now().isoformat()),
            "updated_at": data.get("updated_at", datetime.now().isoformat()),
            "files_count": len(data.get("files", [])),
            "total_issues": data.get("summary", {}).get("total_issues", 0),
        }

        if existing_idx is not None:
            index["reviews"][existing_idx] = index_item
        else:
            index["reviews"].insert(0, index_item)
            index["total"] += 1

        # 按更新时间排序
        index["reviews"].sort(
            key=lambda x: x.get("updated_at", ""),
            reverse=True
        )

        self._save_index(index)

    def _remove_from_index(self, review_id: str):
        """从索引移除"""
        index = self._load_index()

        original_count = len(index.get("reviews", []))
        index["reviews"] = [
            r for r in index.get("reviews", [])
            if r.get("review_id") != review_id
        ]

        if len(index["reviews"]) < original_count:
            index["total"] = len(index["reviews"])
            self._save_index(index)
            return True

        return False

    def save_review(self, review_id: str, data: dict) -> None:
        """保存审查记录"""
        # 添加时间戳
        now = datetime.now().isoformat()
        if "created_at" not in data:
            data["created_at"] = now
        data["updated_at"] = now

        # 写入详情文件
        detail_file = self.base_dir / f"{review_id}.json"
        with open(detail_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

        # 更新索引
        self._update_index(review_id, data)

        logger.info(f"Saved review {review_id} to {detail_file}")

    def get_review(self, review_id: str) -> Optional[dict]:
        """获取单条审查详情"""
        detail_file = self.base_dir / f"{review_id}.json"

        if not detail_file.exists():
            return None

        try:
            with open(detail_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except (FileNotFoundError, json.JSONDecodeError) as e:
            logger.error(f"Failed to load review {review_id}: {e}")
            return None

    def list_reviews(
        self,
        page: int = 1,
        page_size: int = 20,
        status: str = None
    ) -> dict:
        """获取审查列表（支持分页和状态筛选）"""
        index = self._load_index()
        reviews = index.get("reviews", [])

        # 状态筛选
        if status:
            reviews = [r for r in reviews if r.get("status") == status]

        # 分页
        total = len(reviews)
        start = (page - 1) * page_size
        end = start + page_size
        paginated_reviews = reviews[start:end]

        return {
            "items": paginated_reviews,
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
        }

    def delete_review(self, review_id: str) -> bool:
        """删除审查记录"""
        # 删除详情文件
        detail_file = self.base_dir / f"{review_id}.json"
        if detail_file.exists():
            try:
                detail_file.unlink()
            except OSError as e:
                logger.error(f"Failed to delete review file {review_id}: {e}")
                return False

        # 从索引移除
        return self._remove_from_index(review_id)
