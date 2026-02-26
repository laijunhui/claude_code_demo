# Agent 管理器 - 任务分发与聚合
import asyncio
import time
from dataclasses import dataclass, field
from typing import List, Dict
from app.agents.base import BaseAgent, AgentResult, Issue, CodeFile
from app.agents.syntax import SyntaxAgent
from app.agents.security import SecurityAgent
from app.agents.style import StyleAgent


@dataclass
class ReviewReport:
    """评审报告"""
    review_id: str
    files: List[str]
    issues: List[Issue] = field(default_factory=list)
    duration_ms: int = 0
    agents_results: List[AgentResult] = field(default_factory=list)

    def get_summary(self) -> Dict:
        """获取摘要"""
        severity_count = {"critical": 0, "error": 0, "warning": 0, "info": 0}
        type_count = {"syntax": 0, "security": 0, "style": 0, "general": 0}

        for issue in self.issues:
            if issue.severity in severity_count:
                severity_count[issue.severity] += 1
            if issue.type in type_count:
                type_count[issue.type] += 1
            else:
                type_count["general"] += 1

        return {
            "review_id": self.review_id,
            "files_count": len(self.files),
            "total_issues": len(self.issues),
            "by_severity": severity_count,
            "by_type": type_count,
            "duration_ms": self.duration_ms,
        }

    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            "review_id": self.review_id,
            "files": self.files,
            "summary": self.get_summary(),
            "issues": [i.to_dict() for i in self.issues],
            "agents_results": [r.to_dict() for r in self.agents_results],
            "duration_ms": self.duration_ms,
        }


class AgentManager:
    """Agent 管理器"""

    def __init__(self):
        # 初始化所有 Agent
        self.agents: List[BaseAgent] = [
            SyntaxAgent(),      # 语法检查
            SecurityAgent(),    # 安全扫描
            StyleAgent(),       # 规范检查（Claude API）
        ]

    def get_enabled_agents(self, config: Dict = None) -> List[BaseAgent]:
        """获取启用的 Agent"""
        if not config:
            return self.agents

        enabled = []
        for agent in self.agents:
            if config.get(agent.name, True):
                enabled.append(agent)

        return enabled

    async def run_review(self, files: List[CodeFile], config: Dict = None) -> ReviewReport:
        """执行评审"""
        start_time = time.time()

        review_id = f"review_{int(start_time * 1000)}"
        file_paths = [f.file_path for f in files]

        # 获取启用的 Agent
        enabled_agents = self.get_enabled_agents(config)

        # 构建任务列表
        tasks = []
        for file in files:
            for agent in enabled_agents:
                if agent.should_run(file.language) or agent.should_run(self._detect_language(file.file_path)):
                    tasks.append(self._run_agent(agent, file))

        # 并行执行所有任务
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 收集结果
        all_issues = []
        agents_results = []

        for result in results:
            if isinstance(result, Exception):
                continue

            if isinstance(result, AgentResult):
                agents_results.append(result)
                if result.issues:
                    all_issues.extend(result.issues)

        # 按严重程度排序
        severity_order = {"critical": 0, "error": 1, "warning": 2, "info": 3}
        all_issues.sort(key=lambda x: (severity_order.get(x.severity, 3), x.line))

        duration_ms = int((time.time() - start_time) * 1000)

        return ReviewReport(
            review_id=review_id,
            files=file_paths,
            issues=all_issues,
            duration_ms=duration_ms,
            agents_results=agents_results,
        )

    async def _run_agent(self, agent: BaseAgent, file: CodeFile) -> AgentResult:
        """运行单个 Agent"""
        try:
            return await agent.analyze(file)
        except Exception as e:
            return AgentResult(
                agent_name=agent.name,
                error=str(e),
                issues=[
                    Issue(
                        file_path=file.file_path,
                        line=1,
                        severity="error",
                        type="agent_error",
                        message=f"Agent {agent.name} failed: {str(e)}",
                        suggestion="Check agent configuration"
                    )
                ]
            )

    def _detect_language(self, file_path: str) -> str:
        """检测语言"""
        import os
        _, ext = os.path.splitext(file_path)
        ext = ext.lstrip('.').lower()

        lang_map = {
            "py": "python",
            "js": "javascript",
            "ts": "typescript",
            "jsx": "javascript",
            "tsx": "typescript",
            "java": "java",
            "go": "go",
            "rs": "rust",
            "rb": "ruby",
            "php": "php",
            "c": "c",
            "cpp": "cpp",
            "cs": "csharp",
        }

        return lang_map.get(ext, "unknown")
