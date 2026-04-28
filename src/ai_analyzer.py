"""
ai_analyzer.py - AI APIを使ってC++コード要素の説明を生成するモジュール
"""
from __future__ import annotations

import os
import sys
from dataclasses import dataclass

from models import ClassInfo, FileInfo, GlobalVarInfo, MethodInfo

# ---------------------------------------------------------------------------
# プロバイダー設定マッピング
# ---------------------------------------------------------------------------

PROVIDER_ENV_VARS: dict[str, str] = {
    "openai": "OPENAI_API_KEY",
    "anthropic": "ANTHROPIC_API_KEY",
    "gemini": "GEMINI_API_KEY",
}

PROVIDER_DEFAULT_MODELS: dict[str, str] = {
    "openai": "gpt-4o-mini",
    "anthropic": "claude-3-5-haiku-latest",
    "gemini": "gemini-2.0-flash",
}

VALID_PROVIDERS = set(PROVIDER_ENV_VARS.keys())


# ---------------------------------------------------------------------------
# AIConfig dataclass (8.1)
# ---------------------------------------------------------------------------

@dataclass
class AIConfig:
    provider: str
    model: str | None
    api_key: str

    def __post_init__(self) -> None:
        if self.provider not in VALID_PROVIDERS:
            raise ValueError(
                f"不正なプロバイダー: '{self.provider}'\n"
                f"有効な選択肢: {', '.join(sorted(VALID_PROVIDERS))}"
            )
        if not self.api_key:
            env_var = PROVIDER_ENV_VARS[self.provider]
            raise ValueError(
                f"APIキーが設定されていません。\n"
                f"環境変数 {env_var} を設定してください。\n"
                f"例: export {env_var}=your_api_key"
            )
        # model が None の場合はデフォルトモデルを使用
        if self.model is None:
            self.model = PROVIDER_DEFAULT_MODELS[self.provider]

    @classmethod
    def from_env(cls, provider: str = "openai", model: str | None = None) -> "AIConfig":
        """環境変数からAPIキーを取得して AIConfig を生成する。"""
        if provider not in VALID_PROVIDERS:
            raise ValueError(
                f"不正なプロバイダー: '{provider}'\n"
                f"有効な選択肢: {', '.join(sorted(VALID_PROVIDERS))}"
            )
        env_var = PROVIDER_ENV_VARS[provider]
        api_key = os.environ.get(env_var, "")
        if not api_key:
            raise ValueError(
                f"APIキーが設定されていません。\n"
                f"環境変数 {env_var} を設定してください。\n"
                f"例: export {env_var}=your_api_key"
            )
        return cls(provider=provider, model=model, api_key=api_key)


# ---------------------------------------------------------------------------
# プロンプト構築ヘルパー
# ---------------------------------------------------------------------------

def _build_class_prompt(cls: ClassInfo) -> str:
    members = ", ".join(f"{m.type} {m.name}" for m in cls.members)
    methods = ", ".join(
        f"{m.return_type} {m.name}({', '.join(t for t, _ in m.parameters)})"
        for m in cls.methods
    )
    ns = f"名前空間: {cls.namespace}\n" if cls.namespace else ""
    bases = f"継承元: {', '.join(cls.bases)}\n" if cls.bases else ""
    comment = f"既存コメント: {cls.comment}\n" if cls.comment else ""
    return (
        f"以下のC++クラスについて、概要・責務・設計上の意図を日本語で簡潔に説明してください。\n\n"
        f"クラス名: {cls.name}\n"
        f"{ns}{bases}{comment}"
        f"メンバ変数: {members or 'なし'}\n"
        f"メソッド: {methods or 'なし'}\n\n"
        f"説明は3〜5文程度でまとめてください。"
    )


def _build_method_prompt(method: MethodInfo, class_name: str) -> str:
    params = ", ".join(f"{t} {n}" for t, n in method.parameters)
    comment = f"既存コメント: {method.comment}\n" if method.comment else ""
    return (
        f"以下のC++メソッドについて、動作・引数の意味・戻り値の意味を日本語で簡潔に説明してください。\n\n"
        f"クラス: {class_name}\n"
        f"メソッド: {method.return_type} {method.name}({params})\n"
        f"アクセス修飾子: {method.access}\n"
        f"{comment}"
        f"説明は2〜3文程度でまとめてください。"
    )


def _build_global_var_prompt(var: GlobalVarInfo) -> str:
    modified = ", ".join(var.modified_in) if var.modified_in else "なし"
    values = ", ".join(var.possible_values) if var.possible_values else "不明"
    dynamic_note = "（動的に変化する可能性あり）" if var.is_dynamic else ""
    return (
        f"以下のC++グローバル変数について、用途・リスク・改善提案を日本語で簡潔に説明してください。\n\n"
        f"変数名: {var.name}\n"
        f"型: {var.type}\n"
        f"初期値: {var.initial_value or '不明'}{dynamic_note}\n"
        f"変更箇所: {modified}\n"
        f"取りうる値: {values}\n\n"
        f"説明は2〜4文程度でまとめてください。"
    )


# ---------------------------------------------------------------------------
# プロバイダー別クライアント呼び出し (8.2)
# ---------------------------------------------------------------------------

def _call_openai(prompt: str, config: AIConfig) -> str | None:
    try:
        import openai
        client = openai.OpenAI(api_key=config.api_key)
        response = client.chat.completions.create(
            model=config.model,
            messages=[{"role": "user", "content": prompt}],
            max_tokens=512,
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"警告: OpenAI API呼び出し失敗: {e}", file=sys.stderr)
        return None


def _call_anthropic(prompt: str, config: AIConfig) -> str | None:
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=config.api_key)
        response = client.messages.create(
            model=config.model,
            max_tokens=512,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.content[0].text
    except Exception as e:
        print(f"警告: Anthropic API呼び出し失敗: {e}", file=sys.stderr)
        return None


def _call_gemini(prompt: str, config: AIConfig) -> str | None:
    try:
        import google.generativeai as genai
        genai.configure(api_key=config.api_key)
        model = genai.GenerativeModel(config.model)
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        print(f"警告: Gemini API呼び出し失敗: {e}", file=sys.stderr)
        return None


_PROVIDER_CALLERS = {
    "openai": _call_openai,
    "anthropic": _call_anthropic,
    "gemini": _call_gemini,
}


def _generate(prompt: str, config: AIConfig) -> str | None:
    """プロバイダーに応じてAI APIを呼び出し、生成テキストを返す。失敗時は None。"""
    caller = _PROVIDER_CALLERS.get(config.provider)
    if caller is None:
        print(f"警告: 未知のプロバイダー '{config.provider}'", file=sys.stderr)
        return None
    return caller(prompt, config)


# ---------------------------------------------------------------------------
# analyze エントリーポイント (8.3)
# ---------------------------------------------------------------------------

def analyze(file_infos: list[FileInfo], config: AIConfig) -> list[FileInfo]:
    """
    各 FileInfo の ClassInfo・MethodInfo・GlobalVarInfo に対して AI API を呼び出し、
    ai_description フィールドに説明を格納して返す。

    Args:
        file_infos: 抽出済みの FileInfo リスト
        config: AI プロバイダー設定

    Returns:
        ai_description が付加された FileInfo リスト（同一オブジェクトを変更して返す）
    """
    for file_info in file_infos:
        for cls in file_info.classes:
            # クラス説明
            cls.ai_description = _generate(_build_class_prompt(cls), config)

            # パブリックメソッド説明
            for method in cls.methods:
                if method.access == "public":
                    method.ai_description = _generate(
                        _build_method_prompt(method, cls.name), config
                    )

        # グローバル変数説明
        for var in file_info.global_vars:
            var.ai_description = _generate(_build_global_var_prompt(var), config)

    return file_infos
