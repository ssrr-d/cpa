# C++ Design Document Generator

C++ソースコードを静的解析して、Markdown形式の設計書を自動生成するCLIツールです。
オプションでAI（OpenAI / Anthropic / Gemini）を使った自然言語説明の追記にも対応しています。

## 機能

- クラス構造・継承関係・メンバ変数・メソッドシグネチャの抽出
- Doxygenコメントの紐付け
- グローバル変数の状態追跡（変更箇所・取りうる値）
- Mermaidクラス図の生成
- AI による設計意図・リスク・改善提案の自動生成

## インストール

Python 3.10+ が必要です。

```bash
pip install -r requirements.txt
```

libclang のネイティブライブラリも必要です。

- Windows: [LLVM公式](https://releases.llvm.org/) からインストーラーをダウンロード
- macOS: `brew install llvm`
- Ubuntu: `sudo apt install libclang-dev`

## セットアップ

`.env` ファイルにAPIキーを記載します（AI機能を使う場合のみ）。

```
OPENAI_API_KEY=sk-...
ANTHROPIC_API_KEY=sk-ant-...
GEMINI_API_KEY=AIza...
```

各プロバイダーのAPIキー発行場所：

| プロバイダー | 発行URL |
|---|---|
| OpenAI | https://platform.openai.com/api-keys |
| Anthropic | https://console.anthropic.com/settings/keys |
| Gemini | https://aistudio.google.com/app/apikey |

## 使い方

```bash
python src/main.py <path> [options]
```

### 基本的な使い方

```bash
# 単一ファイルを解析
python src/main.py path/to/MyClass.h

# ディレクトリを再帰的に解析
python src/main.py path/to/src/ --recursive

# 出力先を指定
python src/main.py path/to/src/ --output docs/design.md
```

### AI解析を有効化

```bash
# OpenAI（デフォルト）
python src/main.py path/to/src/ --ai

# Anthropicを使用
python src/main.py path/to/src/ --ai --ai-provider anthropic

# モデルを指定
python src/main.py path/to/src/ --ai --ai-provider openai --ai-model gpt-4o
```

### オプション一覧

| オプション | 説明 | デフォルト |
|---|---|---|
| `path` | 解析対象のファイルまたはディレクトリ | 必須 |
| `-o`, `--output` | 出力ファイルパス | `design.md` |
| `-r`, `--recursive` | サブディレクトリを再帰的に検索 | `false` |
| `--ai` | AI解析を有効化 | `false` |
| `--ai-provider` | AIプロバイダー (`openai` / `anthropic` / `gemini`) | `openai` |
| `--ai-model` | 使用するモデル名 | 各プロバイダーのデフォルト |

### デフォルトモデル

| プロバイダー | デフォルトモデル |
|---|---|
| openai | `gpt-4o-mini` |
| anthropic | `claude-3-5-haiku-latest` |
| gemini | `gemini-2.0-flash` |

## テスト

```bash
pytest tests/
```

## プロジェクト構成

```
.
├── src/
│   ├── main.py           # CLIエントリーポイント
│   ├── file_collector.py # ファイル収集
│   ├── cpp_parser.py     # libclang ASTパーサー
│   ├── extractor.py      # データ抽出
│   ├── renderer.py       # Markdownレンダラー
│   ├── ai_analyzer.py    # AI解析
│   └── models.py         # データモデル
├── tests/                # テストコード
├── .env                  # APIキー（gitignore済み）
└── requirements.txt
```
