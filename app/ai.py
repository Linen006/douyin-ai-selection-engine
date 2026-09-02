"""LLM assistant with a deterministic mock fallback.

When DEEPSEEK_API_KEY is configured the app calls DeepSeek for a suggested
review decision. Without a key it returns a clearly labelled mock result so
the whole pipeline still runs offline.
"""

from __future__ import annotations

import json

import requests

from app.config import DEEPSEEK_API_KEY, DEEPSEEK_MODEL


class MockClient:
    mode = "mock"

    def review_suggestion(self, title: str, transcript: str, checks_text: str) -> dict:
        return {
            "decision": "manual",
            "reason": "Mock 模式：未配置 DEEPSEEK_API_KEY，返回人工判断占位。",
        }


class DeepSeekClient:
    mode = "deepseek"

    def __init__(self, api_key: str, model: str) -> None:
        self.api_key = api_key
        self.model = model
        self.url = "https://api.deepseek.com/chat/completions"

    def review_suggestion(self, title: str, transcript: str, checks_text: str) -> dict:
        prompt = (
            "你是短视频带货素材审核助手。根据素材标题、口播文本和规则命中结果，"
            "给出建议动作。只返回 JSON：{\"decision\":\"approve|reject|manual\","
            "\"reason\":\"一句话理由\"}。\n\n"
            f"素材标题：{title}\n口播文本：{transcript}\n规则命中：{checks_text}"
        )
        try:
            response = requests.post(
                self.url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": "你只输出合法 JSON。"},
                        {"role": "user", "content": prompt},
                    ],
                    "temperature": 0,
                    "response_format": {"type": "json_object"},
                },
                timeout=30,
            )
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            try:
                return json.loads(content)
            except json.JSONDecodeError:
                return {"decision": "manual", "reason": content[:200]}
        except (requests.RequestException, KeyError, ValueError) as exc:
            return {"decision": "manual", "reason": f"DeepSeek 调用失败，转人工判断：{exc}"}


def get_ai_client():
    if DEEPSEEK_API_KEY:
        return DeepSeekClient(DEEPSEEK_API_KEY, DEEPSEEK_MODEL)
    return MockClient()


def ai_mode() -> str:
    return "deepseek" if DEEPSEEK_API_KEY else "mock"
