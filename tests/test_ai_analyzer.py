"""
test_ai_analyzer.py - ai_analyzer.py の単体テスト

対象要件:
  7.7 - APIキー未設定時に ValueError を送出する
  7.8 - AI API呼び出し失敗時は警告を出力して None を返し、処理を継続する
"""
from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from src.ai_analyzer import (
    AIConfig,
    PROVIDER_DEFAULT_MODELS,
    _build_class_prompt,
    _build_global_var_prompt,
    _build_method_prompt,
    analyze,
)
from src.models import ClassInfo, FileInfo, GlobalVarInfo, MemberVarInfo, MethodInfo


# ---------------------------------------------------------------------------
# フィクスチャ
# ---------------------------------------------------------------------------

def _make_file_info() -> FileInfo:
    method = MethodInfo(
        name="getValue",
        return_type="int",
        parameters=[],
        access="public",
        comment=None,
    )
    private_method = MethodInfo(
        name="_helper",
        return_type="void",
        parameters=[("int", "x")],
        access="private",
        comment=None,
    )
    cls = ClassInfo(
        name="MyClass",
        namespace="myns",
        bases=["BaseClass"],
        members=[MemberVarInfo(name="value_", type="int", access="private")],
        methods=[method, private_method],
        comment="MyClass の説明",
    )
    var = GlobalVarInfo(
        name="g_count",
        type="int",
        initial_value="0",
        modified_in=["increment", "reset"],
        possible_values=["0", "1", "2"],
        is_dynamic=False,
    )
    return FileInfo(filepath=Path("test.cpp"), classes=[cls], global_vars=[var])


# ---------------------------------------------------------------------------
# Req 7.7: AIConfig バリデーション
# ---------------------------------------------------------------------------

class TestAIConfigValidation:
    def test_invalid_provider_raises(self):
        with pytest.raises(ValueError, match="不正なプロバイダー"):
            AIConfig(provider="unknown", model=None, api_key="key")

    def test_empty_api_key_raises(self):
        with pytest.raises(ValueError, match="APIキーが設定されていません"):
            AIConfig(provider="openai", model=None, api_key="")

    def test_valid_config_sets_default_model(self):
        cfg = AIConfig(provider="openai", model=None, api_key="test-key")
        assert cfg.model == PROVIDER_DEFAULT_MODELS["openai"]

    def test_explicit_model_is_preserved(self):
        cfg = AIConfig(provider="anthropic", model="claude-3-opus", api_key="test-key")
        assert cfg.model == "claude-3-opus"

    def test_from_env_missing_key_raises(self, monkeypatch):
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        with pytest.raises(ValueError, match="APIキーが設定されていません"):
            AIConfig.from_env(provider="openai")

    def test_from_env_reads_key(self, monkeypatch):
        monkeypatch.setenv("OPENAI_API_KEY", "env-key")
        cfg = AIConfig.from_env(provider="openai")
        assert cfg.api_key == "env-key"


# ---------------------------------------------------------------------------
# プロンプト構築
# ---------------------------------------------------------------------------

class TestPromptBuilding:
    def setup_method(self):
        self.file_info = _make_file_info()
        self.cls = self.file_info.classes[0]
        self.method = self.cls.methods[0]
        self.var = self.file_info.global_vars[0]

    def test_class_prompt_contains_class_name(self):
        prompt = _build_class_prompt(self.cls)
        assert "MyClass" in prompt

    def test_class_prompt_contains_namespace(self):
        prompt = _build_class_prompt(self.cls)
        assert "myns" in prompt

    def test_class_prompt_contains_base(self):
        prompt = _build_class_prompt(self.cls)
        assert "BaseClass" in prompt

    def test_method_prompt_contains_method_name(self):
        prompt = _build_method_prompt(self.method, "MyClass")
        assert "getValue" in prompt

    def test_method_prompt_contains_class_name(self):
        prompt = _build_method_prompt(self.method, "MyClass")
        assert "MyClass" in prompt

    def test_global_var_prompt_contains_var_name(self):
        prompt = _build_global_var_prompt(self.var)
        assert "g_count" in prompt

    def test_global_var_prompt_dynamic_note(self):
        dynamic_var = GlobalVarInfo(
            name="g_val", type="int", initial_value="0", is_dynamic=True
        )
        prompt = _build_global_var_prompt(dynamic_var)
        assert "動的" in prompt


# ---------------------------------------------------------------------------
# Req 7.8: API呼び出し失敗時の継続
# ---------------------------------------------------------------------------

class TestAnalyzeErrorContinuation:
    def _make_config(self, provider: str = "openai") -> AIConfig:
        return AIConfig(provider=provider, model=None, api_key="test-key")

    def test_api_failure_returns_none_and_continues(self, capsys):
        """_generate が None を返しても処理が継続され ai_description=None のまま。"""
        config = self._make_config()
        file_info = _make_file_info()

        with patch("src.ai_analyzer._generate", return_value=None):
            result = analyze([file_info], config)

        # 処理が継続されて FileInfo が返る
        assert len(result) == 1
        # ai_description は None のまま
        assert result[0].classes[0].ai_description is None
        assert result[0].global_vars[0].ai_description is None

    def test_api_failure_prints_warning(self, capsys):
        """API 失敗時に stderr へ警告が出力される（_call_openai 内部の例外処理）。"""
        config = self._make_config()
        file_info = _make_file_info()

        mock_openai = MagicMock()
        mock_openai.OpenAI.return_value.chat.completions.create.side_effect = RuntimeError("timeout")

        with patch.dict(sys.modules, {"openai": mock_openai}):
            analyze([file_info], config)

        captured = capsys.readouterr()
        assert "警告" in captured.err or captured.err != ""


# ---------------------------------------------------------------------------
# Req 7.8: 正常系 - レスポンスが ai_description に格納される
# ---------------------------------------------------------------------------

class TestAnalyzeResponseStored:
    def _make_config(self, provider: str = "openai") -> AIConfig:
        return AIConfig(provider=provider, model=None, api_key="test-key")

    def test_openai_description_stored_in_class(self):
        config = self._make_config("openai")
        file_info = _make_file_info()

        with patch("src.ai_analyzer._generate", return_value="クラスの説明"):
            result = analyze([file_info], config)

        assert result[0].classes[0].ai_description == "クラスの説明"

    def test_openai_description_stored_in_public_method(self):
        config = self._make_config("openai")
        file_info = _make_file_info()

        with patch("src.ai_analyzer._generate", return_value="メソッドの説明"):
            result = analyze([file_info], config)

        public_method = result[0].classes[0].methods[0]  # getValue (public)
        assert public_method.ai_description == "メソッドの説明"

    def test_private_method_skipped(self):
        """private メソッドには AI 説明を生成しない。"""
        config = self._make_config("openai")
        file_info = _make_file_info()

        with patch("src.ai_analyzer._generate", return_value="説明") as mock_gen:
            result = analyze([file_info], config)

        private_method = result[0].classes[0].methods[1]  # _helper (private)
        assert private_method.ai_description is None

    def test_global_var_description_stored(self):
        config = self._make_config("openai")
        file_info = _make_file_info()

        with patch("src.ai_analyzer._generate", return_value="変数の説明"):
            result = analyze([file_info], config)

        assert result[0].global_vars[0].ai_description == "変数の説明"

    def test_anthropic_description_stored(self):
        config = self._make_config("anthropic")
        file_info = _make_file_info()

        with patch("src.ai_analyzer._generate", return_value="Anthropic説明"):
            result = analyze([file_info], config)

        assert result[0].classes[0].ai_description == "Anthropic説明"

    def test_gemini_description_stored(self):
        config = self._make_config("gemini")
        file_info = _make_file_info()

        with patch("src.ai_analyzer._generate", return_value="Gemini説明"):
            result = analyze([file_info], config)

        assert result[0].classes[0].ai_description == "Gemini説明"

    def test_multiple_files_all_processed(self):
        """複数の FileInfo がすべて処理される。"""
        config = self._make_config("openai")
        file_infos = [_make_file_info(), _make_file_info()]

        with patch("src.ai_analyzer._generate", return_value="説明"):
            result = analyze(file_infos, config)

        assert len(result) == 2
        assert all(fi.classes[0].ai_description == "説明" for fi in result)
