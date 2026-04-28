import sys
from pathlib import Path

try:
    import clang.cindex as cindex
except ImportError:
    print(
        "エラー: clang パッケージが見つかりません。\n"
        "インストール方法: pip install clang",
        file=sys.stderr,
    )
    raise


def _read_as_utf8(filepath: Path) -> bytes:
    """ファイルを読み込み、UTF-8バイト列として返す。エンコーディングを自動検出する。"""
    raw = filepath.read_bytes()
    for enc in ("utf-8-sig", "utf-8", "cp932", "shift_jis", "latin-1"):
        try:
            return raw.decode(enc).encode("utf-8")
        except (UnicodeDecodeError, LookupError):
            continue
    return raw  # フォールバック: そのまま返す


def parse_file(filepath: Path) -> cindex.TranslationUnit:
    """
    C++ソースファイルをlibclangでパースしてTranslationUnitを返す。

    パースエラーが存在する場合は警告を stderr に出力し、処理を継続する。

    Args:
        filepath: パース対象のC++ファイルパス

    Returns:
        libclang の TranslationUnit オブジェクト
    """
    index = cindex.Index.create()

    # エンコーディングを正規化してUTF-8としてlibclangに渡す
    utf8_content = _read_as_utf8(filepath)
    unsaved = [(str(filepath), utf8_content.decode("utf-8"))]

    tu = index.parse(
        str(filepath),
        args=["-std=c++17"],
        unsaved_files=unsaved,
        options=cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
    )

    # パースエラー・警告を stderr に出力（処理は継続）
    errors = [d for d in tu.diagnostics if d.severity >= cindex.Diagnostic.Warning]
    for diag in errors:
        severity = "エラー" if diag.severity >= cindex.Diagnostic.Error else "警告"
        print(f"[{severity}] {filepath}: {diag.spelling}", file=sys.stderr)

    return tu
