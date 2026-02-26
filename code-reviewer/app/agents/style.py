# 规范检查 Agent - 使用 MiniMax API
import os
import time
from typing import List
from app.agents.base import BaseAgent, AgentResult, Issue, CodeFile
from app.config import settings


class StyleAgent(BaseAgent):
    """规范检查 Agent - 使用 MiniMax API"""

    name = "style"
    supported_languages = []  # 支持所有语言

    def __init__(self):
        super().__init__()
        self.api_key = settings.minimax_api_key
        self.model = settings.minimax_model
        self.base_url = settings.minimax_base_url

    async def analyze(self, file: CodeFile) -> AgentResult:
        """使用 MiniMax API 进行代码规范检查"""
        start_time = time.time()

        if not self.api_key:
            return AgentResult(
                agent_name=self.name,
                issues=[
                    Issue(
                        file_path=file.file_path,
                        line=1,
                        severity="warning",
                        type="config",
                        message="MINIMAX_API_KEY not set, skipping style check",
                        suggestion="Set MINIMAX_API_KEY environment variable"
                    )
                ],
                duration_ms=int((time.time() - start_time) * 1000),
            )

        try:
            issues = await self._call_minimax_api(file)

            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_name=self.name,
                issues=issues,
                duration_ms=duration_ms,
            )

        except Exception as e:
            duration_ms = int((time.time() - start_time) * 1000)
            return AgentResult(
                agent_name=self.name,
                issues=[],
                duration_ms=duration_ms,
                error=str(e)
            )

    async def _call_minimax_api(self, file: CodeFile) -> List[Issue]:
        """调用 MiniMax API 进行代码审查"""
        import httpx

        prompt = self._build_prompt(file)

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "messages": [
                {
                    "role": "user",
                    "content": prompt
                }
            ]
        }

        async with httpx.AsyncClient(timeout=60.0) as client:
            try:
                response = await client.post(
                    f"{self.base_url}/text/chatcompletion_v2",
                    headers=headers,
                    json=payload
                )

                if response.status_code != 200:
                    return [
                        Issue(
                            file_path=file.file_path,
                            line=1,
                            severity="warning",
                            type="api_error",
                            message=f"MiniMax API error: {response.status_code}",
                            suggestion=response.text[:200]
                        )
                    ]

                data = response.json()
                choices = data.get("choices", [])
                if choices:
                    content = choices[0].get("message", {}).get("content", "")
                    return self._parse_minimax_response(content, file.file_path)
                else:
                    return []

            except httpx.TimeoutException:
                return [
                    Issue(
                        file_path=file.file_path,
                        line=1,
                        severity="warning",
                        type="timeout",
                        message="MiniMax API request timeout",
                        suggestion="Try again later or reduce file size"
                    )
                ]
            except Exception as e:
                return [
                    Issue(
                        file_path=file.file_path,
                        line=1,
                        severity="warning",
                        type="error",
                        message=f"MiniMax API error: {str(e)}",
                        suggestion="Check API key and try again"
                    )
                ]

    def _build_prompt(self, file: CodeFile) -> str:
        """构建提示词"""
        file_name = os.path.basename(file.file_path)

        prompt = f"""请审查以下代码文件: {file_name}

请从以下几个方面进行检查：
1. 代码风格规范（命名、格式、注释）
2. 最佳实践建议
3. 潜在的代码异味（code smell）
4. 可改进的地方

请以 JSON 格式返回结果，格式如下：
{{
    "issues": [
        {{
            "line": 行号,
            "severity": "warning" 或 "info",
            "type": "style" 或 "best_practice" 或 "code_smell",
            "message": "问题描述",
            "suggestion": "修复建议"
        }}
    ]
}}

如果某方面没有问题，返回空数组。

代码内容：
```{file.language}
{file.content}
```

请只返回 JSON，不要其他内容："""

        return prompt

    def _parse_minimax_response(self, response: str, file_path: str) -> List[Issue]:
        """解析 MiniMax API 响应"""
        import json

        issues = []

        try:
            json_start = response.find('{')
            json_end = response.rfind('}') + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response[json_start:json_end]
                data = json.loads(json_str)

                for item in data.get("issues", []):
                    issues.append(Issue(
                        file_path=file_path,
                        line=item.get("line", 1),
                        severity=item.get("severity", "info"),
                        type=item.get("type", "style"),
                        message=item.get("message", ""),
                        suggestion=item.get("suggestion", "")
                    ))

        except (json.JSONDecodeError, KeyError) as e:
            issues.append(Issue(
                file_path=file_path,
                line=1,
                severity="info",
                type="parse_note",
                message="MiniMax API response note",
                suggestion=response[:500] if len(response) > 500 else response
            ))

        return issues
