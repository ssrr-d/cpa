from pathlib import Path

_CPP_EXTENSIONS = {".cpp", ".h", ".hpp"}


def collect_files(path: str, recursive: bool = False) -> list[Path]:
    """
    指定パスから .cpp / .h / .hpp ファイルを収集して返す。

    Args:
        path: ファイルまたはディレクトリのパス
        recursive: True の場合、サブディレクトリを再帰的に検索する

    Returns:
        収集したファイルの Path リスト

    Raises:
        FileNotFoundError: 指定パスが存在しない場合
    """
    p = Path(path)

    if not p.exists():
        raise FileNotFoundError(f"指定されたパスが存在しません: {path}")

    if p.is_file():
        return [p] if p.suffix in _CPP_EXTENSIONS else []

    # ディレクトリの場合
    pattern = "**/*" if recursive else "*"
    files = [
        f for f in p.glob(pattern)
        if f.is_file() and f.suffix in _CPP_EXTENSIONS
    ]
    return sorted(files)
