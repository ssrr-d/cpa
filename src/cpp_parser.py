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
    tu = index.parse(
        str(filepath),
        args=["-std=c++17"],
        options=cindex.TranslationUnit.PARSE_DETAILED_PROCESSING_RECORD,
    )

    # パースエラー・警告を stderr に出力（処理は継続）
    errors = [d for d in tu.diagnostics if d.severity >= cindex.Diagnostic.Warning]
    for diag in errors:
        severity = "エラー" if diag.severity >= cindex.Diagnostic.Error else "警告"
        print(f"[{severity}] {filepath}: {diag.spelling}", file=sys.stderr)

    return tu
