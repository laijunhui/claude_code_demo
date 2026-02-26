# 安全扫描 Agent - 使用 bandit
import asyncio
import io
import json
import os
import tempfile
import time
from typing import List
from app.agents.base import BaseAgent, AgentResult, Issue, CodeFile


class SecurityAgent(BaseAgent):
    """安全扫描 Agent - 使用 bandit"""

    name = "security"
    supported_languages = ["python", "py"]

    # 严重程度映射
    SEVERITY_MAP = {
        "HIGH": "critical",
        "MEDIUM": "error",
        "LOW": "warning",
        "UNDEFINED": "info",
    }

    def __init__(self):
        super().__init__()

    async def analyze(self, file: CodeFile) -> AgentResult:
        """使用 bandit 进行安全扫描"""
        start_time = time.time()

        # 只有 Python 文件才需要安全扫描
        if not self.should_run(file.language) and not self.should_run(self._detect_language(file.file_path)):
            return AgentResult(agent_name=self.name, issues=[], duration_ms=0)

        try:
            # 创建临时文件供 bandit 检查
            with tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False) as f:
                f.write(file.content)
                temp_file = f.name

            try:
                # 运行 bandit（JSON 格式输出便于解析）
                proc = await asyncio.create_subprocess_exec(
                    'python', '-m', 'bandit', '-f', 'json', '-x', temp_file,
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                )

                stdout, stderr = await proc.communicate()
                output_text = stdout.decode('utf-8', errors='ignore')

                # 解析 JSON 输出
                issues = self._parse_bandit_output(output_text, file.file_path)

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
            # bandit 未安装
            return AgentResult(
                agent_name=self.name,
                issues=[
                    Issue(
                        file_path=file.file_path,
                        line=1,
                        severity="warning",
                        type="config",
                        message="bandit not installed, skipping security check",
                        suggestion="Install bandit: pip install bandit"
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

    def _parse_bandit_output(self, output: str, file_path: str) -> List[Issue]:
        """解析 bandit JSON 输出"""
        issues = []

        try:
            data = json.loads(output)
            results = data.get("results", [])

            for item in results:
                # 获取问题信息
                line_num = item.get("line_number", 1)
                issue_code = item.get("issue_id", "")
                message = item.get("issue_text", "")
                severity = item.get("severity", "LOW")
                confidence = item.get("confidence", "MEDIUM")

                # 映射严重程度
                mapped_severity = self.SEVERITY_MAP.get(severity, "warning")

                # 生成修复建议
                suggestion = self._generate_suggestion(issue_code, message)

                issues.append(Issue(
                    file_path=file_path,
                    line=line_num,
                    column=1,
                    severity=mapped_severity,
                    type="security",
                    message=f"[{severity}] {message}",
                    suggestion=suggestion
                ))

        except json.JSONDecodeError:
            # JSON 解析失败，尝试解析文本输出
            issues = self._parse_text_output(output, file_path)

        return issues

    def _parse_text_output(self, output: str, file_path: str) -> List[Issue]:
        """备用：解析文本格式输出"""
        issues = []
        lines = output.split('\n')

        for line in lines:
            if 'Issue' in line or '[W' in line or '[E' in line or '[H' in line:
                issues.append(Issue(
                    file_path=file_path,
                    line=1,
                    severity="warning",
                    type="security",
                    message=line.strip(),
                    suggestion="Review security issue"
                ))

        return issues

    def _generate_suggestion(self, issue_code: str, message: str) -> str:
        """根据问题代码生成修复建议"""
        suggestions = {
            "B101": "Remove or properly secure hardcoded password",
            "B102": "Avoid using exec() - serious security risk",
            "B103": "Check file permissions - avoid overly permissive modes",
            "B104": "Hardcoded binding to all network interfaces - security risk",
            "B105": "Hardcoded password detected",
            "B106": "Hardcoded password in function call detected",
            "B107": "Hardcoded password assigned to function parameter",
            "B201": "Avoid using pickle - can execute arbitrary code",
            "B301": "Avoid using marshal - can execute arbitrary code",
            "B302": "Avoid using deserialization",
            "B303": "Use of insecure MD5 or SHA1 hash",
            "B304": "Use of insecure cipher",
            "B305": "Use of insecure random",
            "B306": "MKTempFile has predictable name",
            "B307": "Use of eval() - serious security risk",
            "B308": "Use of mark_safe() - XSS vulnerability",
            "B309": "Use of HTTPSConnection with cert verify disabled",
            "B310": "URL open - ensure URL is not malicious",
            "B311": "Use of insecure random - use secrets module",
            "B312": "Telnet usage - security risk",
            "B313": "XML external entity - XXE vulnerability",
            "B314": "XML entity expansion - DoS risk",
            "B315": "Using xml.etree - XML parsing vulnerability",
            "B316": "Y - safe_load recommended",
            "B317": "UseAML load of mktemp - predictable filename",
            "B318": "Use of marshal - can execute arbitrary code",
            "B319": "Use of pyclewn - debugging feature",
            "B320": "Using pickle - unpickling untrusted data",
            "B321": "Importing ftplib - FTP injection risk",
            "B322": "Using unverified HTTPS - cert verification disabled",
            "B323": "Using exec - security risk",
            "B324": "Use of weak cryptographic algorithm",
            "B325": "Using temp file with predictable name",
            "B401": "Import winreg - use on Windows only",
            "B402": "Import telnetlib - security risk",
            "B403": "Use of sha1 for security - use hashlib.sha256",
            "B404": "Import subprocess - check for shell=True",
            "B405": "Import xml - use defusedxml for parsing",
            "B406": "Import xml.sax - XXE vulnerability",
            "B407": "Import xml.etree - XXE vulnerability",
            "B408": "Import xml.minidom - XXE vulnerability",
            "B409": "Import xmlrpclib - XML vulnerability",
            "B410": "Import requests with verify=False - security risk",
            "B411": "Import ftplib - security risk",
            "B412": "Import telnetlib - security risk",
            "B413": "Import pycrypto - use cryptography library",
            "B501": "Request with verify=False - security risk",
            "B502": "SSL verification disabled - security risk",
            "B503": "SSL verification not configured - security risk",
            "B504": "SSL certificate verification not configured - security risk",
            "B505": "Weak cryptographic algorithm used",
            "B506": "YAML load - use safe_load",
            "B507": "SSH connection without verifying host key - security risk",
            "B601": "Paramiko call - potential command injection",
            "B602": "Paramiko call with shell=True - command injection risk",
            "B603": "Subprocess call without shell=True - check for injection",
            "B604": "Subprocess call with shell=True - command injection risk",
            "B605": "Starting a process with shell=True - command injection",
            "B606": "Starting a process without shell - security check",
            "B607": "Starting a process with executable path - security check",
            "B608": "Hardcoded SQL expression - SQL injection risk",
            "B611": "SQL query built from user-controlled sources",
            "B701": "HTML escape missing - XSS vulnerability",
            "B702": "Use of Mako templating engine - ensure safe",
            "B703": "Django debug mode - security risk",
        }

        return suggestions.get(issue_code, "Review and fix this security issue")
