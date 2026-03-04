# Storage package
from app.storage.json_storage import JSONReviewStorage

# 全局存储实例
storage: JSONReviewStorage = None


def init_storage(base_dir: str = "data/reviews") -> JSONReviewStorage:
    """初始化存储层"""
    global storage
    storage = JSONReviewStorage(base_dir)
    return storage
