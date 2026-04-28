"""
test_extractor.py - extractor.py の単体テスト

対象要件: 2.1 (クラス継承), 2.6 (Doxygenコメント), 5.2 (グローバル変数変更箇所), 5.6 (動的代入注記)
"""
import sys
import pytest
from pathlib import Path

try:
    import clang.cindex as cindex
    # Verify the native libclang library actually loads
    cindex.Index.create()
    CLANG_AVAILABLE = True
except Exception:
    CLANG_AVAILABLE = False

pytestmark = pytest.mark.skipif(not CLANG_AVAILABLE, reason="clang パッケージが必要です")

from src.cpp_parser import parse_file
from src.extractor import extract


# ---------------------------------------------------------------------------
# ヘルパー
# ---------------------------------------------------------------------------

def _parse_and_extract(tmp_path: Path, filename: str, code: str):
    """C++コードを一時ファイルに書き込んでパース・抽出する。"""
    f = tmp_path / filename
    f.write_text(code, encoding="utf-8")
    tu = parse_file(f)
    return extract(tu, f)


# ---------------------------------------------------------------------------
# Req 2.1: クラス継承の抽出
# ---------------------------------------------------------------------------

class TestClassInheritance:
    def test_single_base_class(self, tmp_path):
        """単一継承のクラスで bases に親クラス名が含まれる (Req 2.1)"""
        code = """
class Base {};
class Derived : public Base {};
"""
        file_info = _parse_and_extract(tmp_path, "inherit.h", code)
        derived = next(c for c in file_info.classes if c.name == "Derived")
        assert any("Base" in b for b in derived.bases)

    def test_multiple_base_classes(self, tmp_path):
        """多重継承のクラスで bases に複数の親クラス名が含まれる (Req 2.1)"""
        code = """
class A {};
class B {};
class C : public A, public B {};
"""
        file_info = _parse_and_extract(tmp_path, "multi_inherit.h", code)
        c_class = next(c for c in file_info.classes if c.name == "C")
        assert len(c_class.bases) == 2
        base_names = " ".join(c_class.bases)
        assert "A" in base_names
        assert "B" in base_names

    def test_no_inheritance(self, tmp_path):
        """継承なしのクラスで bases が空リストになる (Req 2.1)"""
        code = "class Standalone {};"
        file_info = _parse_and_extract(tmp_path, "standalone.h", code)
        cls = next(c for c in file_info.classes if c.name == "Standalone")
        assert cls.bases == []

    def test_class_name_extracted(self, tmp_path):
        """クラス名が正しく抽出される (Req 2.1)"""
        code = "class MyClass {};"
        file_info = _parse_and_extract(tmp_path, "myclass.h", code)
        names = [c.name for c in file_info.classes]
        assert "MyClass" in names


# ---------------------------------------------------------------------------
# Req 2.6: Doxygenコメントの抽出と紐付け
# ---------------------------------------------------------------------------

class TestDoxygenComments:
    def test_class_doxygen_comment(self, tmp_path):
        """クラスに付いた /** */ コメントが ClassInfo.comment に格納される (Req 2.6)"""
        code = """
/** This is MyClass description. */
class MyClass {};
"""
        file_info = _parse_and_extract(tmp_path, "doxy_class.h", code)
        cls = next(c for c in file_info.classes if c.name == "MyClass")
        assert cls.comment is not None
        assert "MyClass description" in cls.comment

    def test_method_doxygen_comment(self, tmp_path):
        """メソッドに付いた /// コメントが MethodInfo.comment に格納される (Req 2.6)"""
        code = """
class Foo {
public:
    /// Computes the result.
    int compute(int x);
};
"""
        file_info = _parse_and_extract(tmp_path, "doxy_method.h", code)
        cls = next(c for c in file_info.classes if c.name == "Foo")
        method = next(m for m in cls.methods if m.name == "compute")
        assert method.comment is not None
        assert "Computes" in method.comment

    def test_member_doxygen_comment(self, tmp_path):
        """メンバ変数に付いた /** */ コメントが MemberVarInfo.comment に格納される (Req 2.6)"""
        code = """
class Bar {
public:
    /** The value field. */
    int value;
};
"""
        file_info = _parse_and_extract(tmp_path, "doxy_member.h", code)
        cls = next(c for c in file_info.classes if c.name == "Bar")
        member = next(m for m in cls.members if m.name == "value")
        assert member.comment is not None
        assert "value field" in member.comment

    def test_no_comment_returns_none(self, tmp_path):
        """コメントなしの要素は comment が None になる (Req 2.6)"""
        code = "class NoComment {};"
        file_info = _parse_and_extract(tmp_path, "no_comment.h", code)
        cls = next(c for c in file_info.classes if c.name == "NoComment")
        assert cls.comment is None


# ---------------------------------------------------------------------------
# Req 5.2: グローバル変数の変更箇所（関数名）の列挙
# ---------------------------------------------------------------------------

class TestGlobalVarModifiedIn:
    def test_assignment_in_function_detected(self, tmp_path):
        """関数内でグローバル変数に代入している箇所が modified_in に記録される (Req 5.2)"""
        code = """
int g_count = 0;

void increment() {
    g_count = 1;
}
"""
        file_info = _parse_and_extract(tmp_path, "global_assign.cpp", code)
        var = next(v for v in file_info.global_vars if v.name == "g_count")
        assert "increment" in var.modified_in

    def test_multiple_functions_modifying_same_var(self, tmp_path):
        """複数の関数が同じグローバル変数を変更する場合、すべて modified_in に含まれる (Req 5.2)"""
        code = """
int g_val = 0;

void setA() { g_val = 10; }
void setB() { g_val = 20; }
"""
        file_info = _parse_and_extract(tmp_path, "multi_assign.cpp", code)
        var = next(v for v in file_info.global_vars if v.name == "g_val")
        assert "setA" in var.modified_in
        assert "setB" in var.modified_in

    def test_unmodified_global_has_empty_modified_in(self, tmp_path):
        """どこからも変更されないグローバル変数の modified_in は空リストになる (Req 5.2)"""
        code = "int g_static = 42;"
        file_info = _parse_and_extract(tmp_path, "unmodified.cpp", code)
        var = next(v for v in file_info.global_vars if v.name == "g_static")
        assert var.modified_in == []

    def test_initial_value_extracted(self, tmp_path):
        """グローバル変数の初期値が正しく抽出される (Req 5.1)"""
        code = "int g_num = 99;"
        file_info = _parse_and_extract(tmp_path, "init_val.cpp", code)
        var = next(v for v in file_info.global_vars if v.name == "g_num")
        assert var.initial_value == "99"


# ---------------------------------------------------------------------------
# Req 5.6: 動的代入の注記 (is_dynamic)
# ---------------------------------------------------------------------------

class TestDynamicAssignment:
    def test_function_call_rhs_is_dynamic(self, tmp_path):
        """関数呼び出しの戻り値を代入する場合 is_dynamic=True になる (Req 5.6)"""
        code = """
int get_value();
int g_result = 0;

void update() {
    g_result = get_value();
}
"""
        file_info = _parse_and_extract(tmp_path, "dynamic_assign.cpp", code)
        var = next(v for v in file_info.global_vars if v.name == "g_result")
        assert var.is_dynamic is True

    def test_literal_assignment_is_not_dynamic(self, tmp_path):
        """リテラル値のみの代入では is_dynamic=False のまま (Req 5.6)"""
        code = """
int g_fixed = 0;

void set_fixed() {
    g_fixed = 100;
}
"""
        file_info = _parse_and_extract(tmp_path, "literal_assign.cpp", code)
        var = next(v for v in file_info.global_vars if v.name == "g_fixed")
        assert var.is_dynamic is False

    def test_possible_values_from_literal_assignments(self, tmp_path):
        """リテラル代入から possible_values が収集される (Req 5.3)"""
        code = """
int g_mode = 0;

void set_mode_a() { g_mode = 1; }
void set_mode_b() { g_mode = 2; }
"""
        file_info = _parse_and_extract(tmp_path, "possible_vals.cpp", code)
        var = next(v for v in file_info.global_vars if v.name == "g_mode")
        assert "1" in var.possible_values
        assert "2" in var.possible_values
