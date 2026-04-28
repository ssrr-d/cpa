import pytest
from pathlib import Path
from src.file_collector import collect_files


def test_single_cpp_file(tmp_path):
    """単一の .cpp ファイルを指定した場合、そのファイルが返される (Req 1.1)"""
    f = tmp_path / "main.cpp"
    f.write_text("int main() {}")
    result = collect_files(str(f))
    assert result == [f]


def test_single_h_file(tmp_path):
    """単一の .h ファイルを指定した場合、そのファイルが返される (Req 1.1)"""
    f = tmp_path / "foo.h"
    f.write_text("class Foo {};")
    result = collect_files(str(f))
    assert result == [f]


def test_single_non_cpp_file_returns_empty(tmp_path):
    """C++以外の拡張子のファイルを指定した場合、空リストが返される"""
    f = tmp_path / "readme.txt"
    f.write_text("hello")
    result = collect_files(str(f))
    assert result == []


def test_directory_collects_cpp_files(tmp_path):
    """ディレクトリを指定した場合、直下の .cpp / .h ファイルが収集される (Req 1.2)"""
    (tmp_path / "a.cpp").write_text("")
    (tmp_path / "b.h").write_text("")
    (tmp_path / "c.txt").write_text("")
    result = collect_files(str(tmp_path))
    assert sorted(result) == sorted([tmp_path / "a.cpp", tmp_path / "b.h"])


def test_directory_non_recursive_excludes_subdirs(tmp_path):
    """recursive=False の場合、サブディレクトリのファイルは収集されない (Req 1.2)"""
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.cpp").write_text("")
    (sub / "nested.cpp").write_text("")
    result = collect_files(str(tmp_path), recursive=False)
    assert result == [tmp_path / "top.cpp"]


def test_directory_recursive_includes_subdirs(tmp_path):
    """recursive=True の場合、サブディレクトリのファイルも収集される (Req 1.2)"""
    sub = tmp_path / "sub"
    sub.mkdir()
    (tmp_path / "top.cpp").write_text("")
    (sub / "nested.h").write_text("")
    result = collect_files(str(tmp_path), recursive=True)
    assert sorted(result) == sorted([tmp_path / "top.cpp", sub / "nested.h"])


def test_nonexistent_path_raises(tmp_path):
    """存在しないパスを指定した場合、FileNotFoundError が送出される (Req 1.3)"""
    with pytest.raises(FileNotFoundError):
        collect_files(str(tmp_path / "does_not_exist.cpp"))
