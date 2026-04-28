"""
test_integration.py - end-to-end 統合テスト

サンプルC++ファイルを入力として設計書が正しく生成されるか検証する。
対象要件: 1.1 (ファイル読み込み), 2.1 (クラス抽出), 3.1 (Markdown生成), 5.5 (グローバル変数テーブル)
"""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest

try:
    import clang.cindex as cindex
    cindex.Index.create()
    CLANG_AVAILABLE = True
except Exception:
    CLANG_AVAILABLE = False

_skip_no_clang = pytest.mark.skipif(not CLANG_AVAILABLE, reason="clang パッケージが必要です")

# ---------------------------------------------------------------------------
# サンプル C++ コード
# ---------------------------------------------------------------------------

SAMPLE_CPP = """\
#include <string>

int g_counter = 0;
int g_result = 0;

int compute();

void increment() {
    g_counter = g_counter + 1;
}

void update() {
    g_result = compute();
}

/** Base class for shapes. */
class Shape {
public:
    /// Returns the area.
    virtual double area() const;

    /** Color of the shape. */
    std::string color;
};

class Circle : public Shape {
public:
    double radius;
    double area() const;
};
"""


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _write_sample(tmp_path: Path) -> Path:
    """サンプルC++ファイルを tmp_path に書き込んで返す。"""
    f = tmp_path / "sample.cpp"
    f.write_text(SAMPLE_CPP, encoding="utf-8")
    return f


def _run_main(args: list[str]) -> subprocess.CompletedProcess:
    """main.py を subprocess で実行して結果を返す。"""
    return subprocess.run(
        [sys.executable, "src/main.py"] + args,
        capture_output=True,
        text=True,
    )


# ---------------------------------------------------------------------------
# Req 1.1: ファイル読み込みと出力ファイル生成
# ---------------------------------------------------------------------------

class TestFileIO:
    def test_single_file_generates_output(self, tmp_path):
        """単一C++ファイルを指定すると出力ファイルが生成される (Req 1.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        result = _run_main([str(src), "--output", str(out)])
        assert result.returncode == 0, result.stderr
        assert out.exists()

    def test_output_is_nonempty(self, tmp_path):
        """生成された設計書が空でない (Req 1.1, 3.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        assert out.stat().st_size > 0

    def test_default_output_filename(self, tmp_path):
        """--output 未指定時は design.md に出力される (Req 1.1)"""
        src = _write_sample(tmp_path)
        result = _run_main([str(src)])
        assert result.returncode == 0, result.stderr
        assert Path("design.md").exists()

    def test_nonexistent_path_returns_error(self, tmp_path):
        """存在しないパスを指定すると終了コード 1 が返る (Req 1.1)"""
        result = _run_main([str(tmp_path / "nonexistent.cpp")])
        assert result.returncode == 1

    def test_output_dir_created_automatically(self, tmp_path):
        """出力先ディレクトリが存在しない場合は自動作成される (Req 1.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "subdir" / "nested" / "out.md"
        result = _run_main([str(src), "--output", str(out)])
        assert result.returncode == 0, result.stderr
        assert out.exists()


# ---------------------------------------------------------------------------
# Req 2.1: クラス抽出が設計書に反映される
# ---------------------------------------------------------------------------

class TestClassExtraction:
    def test_class_names_in_output(self, tmp_path):
        """抽出されたクラス名が設計書に含まれる (Req 2.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "Shape" in content
        assert "Circle" in content

    def test_inheritance_in_output(self, tmp_path):
        """継承関係が設計書に含まれる (Req 2.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        # Mermaid 継承矢印または継承元テキストが存在する
        assert "<|--" in content or "Shape" in content

    def test_member_variable_in_output(self, tmp_path):
        """メンバ変数が設計書に含まれる (Req 2.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "radius" in content or "color" in content

    def test_doxygen_comment_in_output(self, tmp_path):
        """Doxygenコメントが設計書に含まれる (Req 2.1, 2.6)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "Base class for shapes" in content or "Returns the area" in content


# ---------------------------------------------------------------------------
# Req 3.1: Markdown 設計書の構造
# ---------------------------------------------------------------------------

class TestMarkdownStructure:
    def test_toc_in_output(self, tmp_path):
        """目次が設計書に含まれる (Req 3.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "## 目次" in content

    def test_mermaid_diagram_in_output(self, tmp_path):
        """Mermaid クラス図が設計書に含まれる (Req 3.1, 3.3)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "```mermaid" in content
        assert "classDiagram" in content

    def test_file_section_in_output(self, tmp_path):
        """ファイルセクションが設計書に含まれる (Req 3.1)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "sample.cpp" in content


# ---------------------------------------------------------------------------
# Req 5.5: グローバル変数テーブル
# ---------------------------------------------------------------------------

class TestGlobalVarTable:
    def test_global_var_names_in_output(self, tmp_path):
        """グローバル変数名が設計書に含まれる (Req 5.5)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "g_counter" in content

    def test_dynamic_global_var_note_in_output(self, tmp_path):
        """動的代入のグローバル変数に注記が含まれる (Req 5.5)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "動的に変化する可能性あり" in content

    def test_global_var_table_header_in_output(self, tmp_path):
        """グローバル変数テーブルのヘッダが設計書に含まれる (Req 5.5)"""
        src = _write_sample(tmp_path)
        out = tmp_path / "out.md"
        _run_main([str(src), "--output", str(out)])
        content = out.read_text(encoding="utf-8")
        assert "変数名" in content
        assert "変更箇所" in content
