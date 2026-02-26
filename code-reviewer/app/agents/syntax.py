# 语法检查 Agent - 使用 pylint
import asyncio
import io
import sys
import time
from typing import List
from app.agents.base import BaseAgent, AgentResult, Issue, CodeFile


class SyntaxAgent(BaseAgent):
    """语法检查 Agent - 使用 pylint"""

    name = "syntax"
    supported_languages = ["python", "py"]

    def __init__(self):
        super().__init__()

    async def analyze(self, file: CodeFile) -> AgentResult:
        """使用 pylint 进行语法检查"""
        start_time = time.time()

        # 只有 Python 文件才需要语法检查
        if not self.should_run(file.language) and not self.should_run(self._detect_language(file.file_path)):
            return AgentResult(agent_name=self.name, issues=[], duration_ms=0)

        try:
            # 动态导入 pylint（延迟导入，避免启动时依赖未安装报错）
            from pylint.lint import Run
            from pylint.reporters.text import TextReporter

            # 创建临时文件供 pylint 检查
            import tempfile
            import os

            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(file.content)
                temp_file = f.name

            try:
                # 捕获 pylint 输出
                output = io.StringIO()
                reporter = TextReporter(output)

                # 运行 pylint（-E 只检查错误，--disable 禁用某些检查）
                args = [
                    temp_file,
                    '--disable=all',
                    '--enable=E',  # 只启用语法错误
                    '--score=no',
                    '--msg-template={path}:{line}:{column}: {msg_id}: {msg}',
                ]

                # 在子进程中运行 pylint（避免阻塞）
                proc = await asyncio.create_subprocess_exec(
                    'python', '-m', 'pylint', *args,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await proc.communicate()
                output_text = stdout.decode('utf-8', errors='ignore')

                # 解析 pylint 输出
                issues = self._parse_pylint_output(output_text, file.file_path)

                duration_ms = int((time.time() - start_time) * 1000)
                return AgentResult(
                    agent_name=self.name,
                    issues=issues,
                    duration_ms=duration_ms,
                )

            finally:
                # 清理临时文件
                if os.path.exists(temp_file):
                    os.unlink(temp_file)

        except ImportError:
            # pylint 未安装，返回提示信息
            return AgentResult(
                agent_name=self.name,
                issues=[
                    Issue(
                        file_path=file.file_path,
                        line=1,
                        severity="warning",
                        type="config",
                        message="pylint not installed, skipping syntax check",
                        suggestion="Install pylint: pip install pylint"
                    )
                ],
                duration_ms=int((time.time() - start_time) * 1000),
            )
        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_name=self.name,
                issues=[],
                duration_ms=duration_ms,
                error=str(e)
            )

    def _parse_pylint_output(self, output: str, file_path: str) -> List[Issue]:
        """解析 pylint 输出"""
        issues = []
        lines = output.strip().split('\n')

        for line in lines:
            if not line or ':' not in line:
                continue

            try:
                # 格式: path:line:column: msg_id: message
                parts = line.split(':', 3)
                if len(parts) >= 4:
                    path = parts[0]
                    line_num = int(parts[1])
                    # column = int(parts[2])
                    message = parts[3]

                    issues.append(Issue(
                        file_path=file_path,
                        line=line_num,
                        column=1,
                        severity="error",
                        type="syntax",
                        message=f"Syntax error: {message.strip()}",
                        suggestion="Fix the syntax error"
                    ))
            except (ValueError, IndexError):
                continue

        return issues
