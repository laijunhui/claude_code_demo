# Agent 基类定义
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Optional
import time


@dataclass
class Issue:
    """评审问题"""
    file_path: str
    line: int
    column: int = 1
    severity: str = "info"  # critical, error, warning, info
    type: str = "general"
    message: str = ""
    suggestion: str = ""

    def to_dict(self):
        return {
            "file_path": self.file_path,
            "line": self.line,
            "column": self.column,
            "severity": self.severity,
            "type": self.type,
            "message": self.message,
            "suggestion": self.suggestion,
        }


@dataclass
class AgentResult:
    """Agent 执行结果"""
    agent_name: str
    issues: List[Issue] = field(default_factory=list)
    duration_ms: int = 0
    error: Optional[str] = None

    def to_dict(self):
        return {
            "name": self.agent_name,
            "agent_name": self.agent_name,
            "status": "success" if not self.error else "failed",
            "output": self.error if self.error else f"分析了 {len(self.issues)} 个问题",
            "issues": [i.to_dict() for i in self.issues],
            "duration_ms": self.duration_ms,
            "error": self.error,
        }


@dataclass
class CodeFile:
    """待评审的代码文件"""
    file_path: str
    content: str
    language: str = ""


class BaseAgent(ABC):
    """Agent 基类"""

    name: str = "base"
    supported_languages: List[str] = []

    def __init__(self):
        self._run_count = 0

    @abstractmethod
    async def analyze(self, file: CodeFile) -> AgentResult:
        """执行评审分析"""
        pass

    def should_run(self, language: str) -> bool:
        """判断是否需要运行此 Agent"""
        if not self.supported_languages:
            return True
        return language.lower() in [l.lower() for l in self.supported_languages]

    def get_file_extension(self, file_path: str) -> str:
        """获取文件扩展名"""
        import os
        _, ext = os.path.splitext(file_path)
        return ext.lstrip('.')

    def _detect_language(self, file_path: str) -> str:
        """根据文件扩展名检测语言"""
        ext = self.get_file_extension(file_path)
        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "rb": "ruby",
            "php": "php",
        }
        return lang_map.get(ext, "unknown")
