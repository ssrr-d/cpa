"""
main.py - C++ 設計書ジェネレーター CLI エントリーポイント
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from dotenv import load_dotenv
load_dotenv()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="cpp-doc-gen",
        description="C++ソースコードを解析してMarkdown設計書を生成します。",
    )
    parser.add_argument(
        "path",
        help="解析対象のファイルまたはディレクトリ",
    )
    parser.add_argument(
        "-o", "--output",
        default=None,
        help="出力ファイルパス (default: design.md)",
    )
    parser.add_argument(
        "-r", "--recursive",
        action="store_true",
        default=False,
        help="サブディレクトリを再帰的に検索する",
    )
    parser.add_argument(
        "--ai",
        action="store_true",
        default=False,
        help="AI解析を有効化してクラス・メソッド・グローバル変数の説明を生成する",
    )
    parser.add_argument(
        "--ai-provider",
        default="openai",
        choices=["openai", "anthropic", "gemini"],
        metavar="PROVIDER",
        help="AIプロバイダー: openai | anthropic | gemini (default: openai)",
    )
    parser.add_argument(
        "--ai-model",
        default=None,
        metavar="MODEL",
        help="使用するモデル名 (省略時は各プロバイダーのデフォルト)",
    )
    return parser


def main() -> int:
    parser = _build_parser()
    args = parser.parse_args()

    # --- import はここで行い、libclang 未インストール時に分かりやすいエラーを出す ---
    try:
        import clang.cindex  # noqa: F401
    except ImportError:
        print(
            "エラー: libclang Python バインディングが見つかりません。\n"
            "  pip install clang\n"
            "を実行してインストールしてください。",
            file=sys.stderr,
        )
        return 1

    # src/ を sys.path に追加（同一ディレクトリからの相対インポート対応）
    src_dir = Path(__file__).parent
    if str(src_dir) not in sys.path:
        sys.path.insert(0, str(src_dir))

    from file_collector import collect_files
    from cpp_parser import parse_file
    from extractor import extract
    from renderer import render
    from ai_analyzer import AIConfig, VALID_PROVIDERS, analyze

    # 1. ファイル収集
    try:
        files = collect_files(args.path, recursive=args.recursive)
    except FileNotFoundError as e:
        print(f"エラー: {e}", file=sys.stderr)
        return 1

    if not files:
        print("エラー: 対象の .cpp / .h / .hpp ファイルが見つかりませんでした。", file=sys.stderr)
        return 1

    print(f"{len(files)} 件のファイルを読み込みました。")

    # 2. パース → 抽出
    file_infos = []
    for filepath in files:
        tu = parse_file(filepath)
        if tu is None:
            continue
        file_infos.append(extract(tu, filepath))

    if not file_infos:
        print("エラー: 解析できるファイルがありませんでした。", file=sys.stderr)
        return 1

    # 3. AI解析 (オプション)
    if args.ai:
        # プロバイダーバリデーション
        if args.ai_provider not in VALID_PROVIDERS:
            print(
                f"エラー: 不正なプロバイダー '{args.ai_provider}'\n"
                f"有効な選択肢: {', '.join(sorted(VALID_PROVIDERS))}",
                file=sys.stderr,
            )
            return 1
        try:
            ai_config = AIConfig.from_env(
                provider=args.ai_provider,
                model=args.ai_model,
            )
        except ValueError as e:
            print(f"エラー: {e}", file=sys.stderr)
            return 1
        print(f"AI解析を実行中 (provider={ai_config.provider}, model={ai_config.model}) ...")
        file_infos = analyze(file_infos, ai_config)

    # 4. レンダリング
    markdown = render(file_infos)

    # 5. 出力ファイルの書き込み (6.2)
    output_path = Path(args.output) if args.output else Path("design.md")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(markdown, encoding="utf-8")

    print(f"設計書を出力しました: {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
