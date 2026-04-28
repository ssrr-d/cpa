"""
test_renderer.py - renderer.py の単体テスト

対象要件: 3.1 (Markdown生成・目次), 3.3 (Mermaidクラス図), 5.5 (グローバル変数テーブル)
"""
import sys
import os
from pathlib import Path

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "src"))

from models import ClassInfo, FileInfo, GlobalVarInfo, MemberVarInfo, MethodInfo
from renderer import render


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _make_file_info(name: str, classes=None, global_vars=None) -> FileInfo:
    return FileInfo(
        filepath=Path(f"/tmp/{name}"),
        classes=classes or [],
        global_vars=global_vars or [],
    )


# ---------------------------------------------------------------------------
# Req 3.1: Markdown生成・目次
# ---------------------------------------------------------------------------

class TestTableOfContents:
    def test_toc_is_present(self):
        """目次セクションが出力に含まれる (Req 3.1)"""
        fi = _make_file_info("foo.h")
        result = render([fi])
        assert "## 目次" in result

    def test_toc_contains_filename(self):
        """目次にファイル名のリンクが含まれる (Req 3.1)"""
        fi = _make_file_info("bar.h")
        result = render([fi])
        assert "bar.h" in result

    def test_toc_contains_class_name(self):
        """目次にクラス名のリンクが含まれる (Req 3.1)"""
        cls = ClassInfo(name="MyClass", namespace=None, bases=[], members=[], methods=[])
        fi = _make_file_info("bar.h", classes=[cls])
        result = render([fi])
        assert "MyClass" in result

    def test_toc_contains_global_var_entry(self):
        """グローバル変数が存在する場合、目次にグローバル変数エントリが含まれる (Req 3.1)"""
        gv = GlobalVarInfo(name="g_count", type="int", initial_value="0")
        fi = _make_file_info("baz.cpp", global_vars=[gv])
        result = render([fi])
        assert "グローバル変数" in result

    def test_multiple_files_in_toc(self):
        """複数ファイルがすべて目次に含まれる (Req 3.1)"""
        fi1 = _make_file_info("a.h")
        fi2 = _make_file_info("b.cpp")
        result = render([fi1, fi2])
        assert "a.h" in result
        assert "b.cpp" in result


# ---------------------------------------------------------------------------
# Req 3.3: Mermaid クラス図
# ---------------------------------------------------------------------------

class TestMermaidDiagram:
    def test_mermaid_block_present_for_class(self):
        """クラスが存在する場合 Mermaid classDiagram ブロックが出力される (Req 3.3)"""
        cls = ClassInfo(name="Animal", namespace=None, bases=[], members=[], methods=[])
        fi = _make_file_info("animal.h", classes=[cls])
        result = render([fi])
        assert "```mermaid" in result
        assert "classDiagram" in result

    def test_mermaid_contains_class_name(self):
        """Mermaid 図にクラス名が含まれる (Req 3.3)"""
        cls = ClassInfo(name="Vehicle", namespace=None, bases=[], members=[], methods=[])
        fi = _make_file_info("vehicle.h", classes=[cls])
        result = render([fi])
        assert "Vehicle" in result

    def test_mermaid_inheritance_arrow(self):
        """継承関係が Mermaid の継承矢印として出力される (Req 3.3)"""
        cls = ClassInfo(name="Dog", namespace=None, bases=["Animal"], members=[], methods=[])
        fi = _make_file_info("dog.h", classes=[cls])
        result = render([fi])
        assert "<|--" in result
        assert "Animal" in result
        assert "Dog" in result

    def test_mermaid_namespace_sanitized(self):
        """名前空間付きクラスの :: が Mermaid で使える文字に変換される (Req 3.3)"""
        cls = ClassInfo(name="Foo", namespace="ns", bases=[], members=[], methods=[])
        fi = _make_file_info("ns.h", classes=[cls])
        result = render([fi])
        # "::" は "__" に変換される
        assert "ns__Foo" in result


# ---------------------------------------------------------------------------
# Req 5.5: グローバル変数テーブル
# ---------------------------------------------------------------------------

class TestGlobalVarTable:
    def test_global_var_table_present(self):
        """グローバル変数テーブルが出力に含まれる (Req 5.5)"""
        gv = GlobalVarInfo(name="g_val", type="int", initial_value="0")
        fi = _make_file_info("main.cpp", global_vars=[gv])
        result = render([fi])
        assert "g_val" in result
        assert "int" in result

    def test_global_var_initial_value(self):
        """グローバル変数の初期値がテーブルに含まれる (Req 5.5)"""
        gv = GlobalVarInfo(name="g_max", type="int", initial_value="100")
        fi = _make_file_info("main.cpp", global_vars=[gv])
        result = render([fi])
        assert "100" in result

    def test_global_var_modified_in(self):
        """変更箇所の関数名がテーブルに含まれる (Req 5.5)"""
        gv = GlobalVarInfo(name="g_flag", type="bool", initial_value="false",
                           modified_in=["setFlag", "reset"])
        fi = _make_file_info("main.cpp", global_vars=[gv])
        result = render([fi])
        assert "setFlag" in result
        assert "reset" in result

    def test_global_var_possible_values(self):
        """取りうる値がテーブルに含まれる (Req 5.5)"""
        gv = GlobalVarInfo(name="g_mode", type="int", initial_value="0",
                           possible_values=["1", "2", "3"])
        fi = _make_file_info("main.cpp", global_vars=[gv])
        result = render([fi])
        assert "1" in result
        assert "2" in result

    def test_dynamic_global_var_note(self):
        """is_dynamic=True の場合「動的に変化する可能性あり」が出力される (Req 5.5)"""
        gv = GlobalVarInfo(name="g_dyn", type="int", initial_value=None, is_dynamic=True)
        fi = _make_file_info("main.cpp", global_vars=[gv])
        result = render([fi])
        assert "動的に変化する可能性あり" in result

    def test_extern_global_var_note(self):
        """is_extern=True の場合「外部参照」が出力される (Req 5.5)"""
        gv = GlobalVarInfo(name="g_ext", type="int", initial_value=None, is_extern=True)
        fi = _make_file_info("main.cpp", global_vars=[gv])
        result = render([fi])
        assert "外部参照" in result

    def test_no_global_vars_no_table(self):
        """グローバル変数がない場合はテーブルが出力されない (Req 5.5)"""
        fi = _make_file_info("empty.cpp")
        result = render([fi])
        assert "変数名" not in result


# ---------------------------------------------------------------------------
# 追加: クラス詳細テーブル (Req 3.2)
# ---------------------------------------------------------------------------

class TestClassDetailTables:
    def test_member_var_table(self):
        """メンバ変数テーブルが出力される"""
        member = MemberVarInfo(name="x", type="int", access="public", comment="x座標")
        cls = ClassInfo(name="Point", namespace=None, bases=[], members=[member], methods=[])
        fi = _make_file_info("point.h", classes=[cls])
        result = render([fi])
        assert "x" in result
        assert "int" in result
        assert "public" in result
        assert "x座標" in result

    def test_method_table(self):
        """メソッドテーブルが出力される"""
        method = MethodInfo(name="getX", return_type="int",
                            parameters=[], access="public", comment="x取得")
        cls = ClassInfo(name="Point", namespace=None, bases=[], members=[], methods=[method])
        fi = _make_file_info("point.h", classes=[cls])
        result = render([fi])
        assert "getX" in result
        assert "x取得" in result

    def test_class_comment_in_output(self):
        """クラスのDoxygenコメントが出力に含まれる (Req 3.4)"""
        cls = ClassInfo(name="Foo", namespace=None, bases=[], members=[], methods=[],
                        comment="Foo クラスの説明")
        fi = _make_file_info("foo.h", classes=[cls])
        result = render([fi])
        assert "Foo クラスの説明" in result
