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


def test_parse_valid_cpp_file(tmp_path):
    """正常なC++ファイルをパースしてTranslationUnitが返される (Req 2.7)"""
    f = tmp_path / "valid.cpp"
    f.write_text("int main() { return 0; }")

    tu = parse_file(f)

    assert tu is not None
    assert isinstance(tu, cindex.TranslationUnit)


def test_parse_valid_cpp_with_class(tmp_path):
    """クラスを含む正常なC++ファイルをパースできる (Req 2.7)"""
    f = tmp_path / "myclass.h"
    f.write_text("""
class MyClass {
public:
    int value;
    void doSomething();
};
""")

    tu = parse_file(f)

    assert tu is not None
    # カーソルのトラバースでクラスが見つかることを確認
    class_names = [
        c.spelling
        for c in tu.cursor.get_children()
        if c.kind == cindex.CursorKind.CLASS_DECL
    ]
    assert "MyClass" in class_names


def test_parse_file_with_syntax_error_continues(tmp_path, capsys):
    """構文エラーを含むファイルでも処理が継続され、TranslationUnitが返される (Req 2.7)"""
    f = tmp_path / "broken.cpp"
    f.write_text("int main() { this is not valid c++ !!!; }")

    # 例外を送出せず、TranslationUnit を返すことを確認
    tu = parse_file(f)

    assert tu is not None
    assert isinstance(tu, cindex.TranslationUnit)


def test_parse_file_with_syntax_error_outputs_warning(tmp_path, capsys):
    """構文エラーを含むファイルで警告が stderr に出力される (Req 2.7)"""
    f = tmp_path / "broken.cpp"
    f.write_text("int main() { this is not valid c++ !!!; }")

    parse_file(f)

    captured = capsys.readouterr()
    assert captured.err != "", "構文エラーの警告が stderr に出力されるべきです"


def test_parse_returns_translation_unit_type(tmp_path):
    """parse_file の戻り値が TranslationUnit 型である (Req 2.7)"""
    f = tmp_path / "simple.h"
    f.write_text("struct Foo { int x; };")

    result = parse_file(f)

    assert isinstance(result, cindex.TranslationUnit)
