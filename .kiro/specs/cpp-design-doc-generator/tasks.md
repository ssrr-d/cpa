# Implementation Plan

- [x] 1. プロジェクト構造とデータモデルのセットアップ





  - `src/` ディレクトリに `models.py` を作成し、`MethodInfo`, `MemberVarInfo`, `ClassInfo`, `GlobalVarInfo`, `IncludeInfo`, `FileInfo` dataclassを定義する
  - `requirements.txt` に `clang`, `pytest` を追加する
  - _Requirements: 2.1, 2.2, 2.3, 2.4, 2.5, 5.1, 5.2, 5.3_
-

- [x] 2. ファイル収集モジュールの実装




- [x] 2.1 `file_collector.py` を実装する


  - `collect_files(path, recursive) -> list[Path]` を実装する
  - 単一ファイル・ディレクトリ・再帰検索に対応する
  - 存在しないパスの場合は `FileNotFoundError` を送出する
  - _Requirements: 1.1, 1.2, 1.3, 1.4_
- [x] 2.2 `file_collector.py` の単体テストを書く






  - 単一ファイル・ディレクトリ・再帰・存在しないパスのケースをテストする
  - _Requirements: 1.1, 1.2, 1.3_

- [x] 3. C++パーサーモジュールの実装





- [x] 3.1 `cpp_parser.py` を実装する


  - `parse_file(filepath) -> TranslationUnit` を実装する
  - libclangの `Index.parse()` を呼び出す
  - パースエラーを警告として stderr に出力し処理を継続する
  - _Requirements: 2.7_
- [x] 3.2 `cpp_parser.py` の単体テストを書く












  - 正常なC++ファイルと構文エラーを含むファイルでテストする
  - _Requirements: 2.7_

- [x] 4. データ抽出モジュールの実装





- [x] 4.1 クラス・メンバ・メソッド・継承の抽出を実装する


  - `extractor.py` に `extract(tu, filepath) -> FileInfo` を実装する
  - ASTをトラバースしてクラス名・継承元・アクセス修飾子・メンバ変数・メソッドシグネチャを抽出する
  - Doxygenコメント（`/** */` / `///`）を対応要素に紐付ける
  - _Requirements: 2.1, 2.2, 2.3, 2.6_
- [x] 4.2 名前空間・include依存関係の抽出を実装する


  - 名前空間（namespace）を抽出してクラスに紐付ける
  - `#include` 依存関係を `IncludeInfo` として抽出する
  - _Requirements: 2.4, 2.5_
- [x] 4.3 グローバル変数の抽出と状態追跡を実装する


  - ファイルスコープのグローバル変数（型・名前・初期値）を抽出する
  - ASTの代入式をトラバースして変更箇所（関数名）を列挙する
  - リテラル・定数代入から取りうる値の候補を収集する
  - `extern` 宣言を識別する
  - 動的代入の場合は `is_dynamic=True` をセットする
  - _Requirements: 5.1, 5.2, 5.3, 5.4, 5.6_
- [x] 4.4 抽出モジュールの単体テストを書く







  - クラス継承・Doxygenコメント・グローバル変数変更箇所・動的代入注記のテストケースを作成する
  - _Requirements: 2.1, 2.6, 5.2, 5.6_

- [x] 5. ドキュメントレンダラーの実装





- [x] 5.1 Markdownレンダラーの基本構造を実装する


  - `renderer.py` に `render(file_infos) -> str` を実装する
  - 目次・ファイルセクション・クラスセクションの骨格を作成する
  - _Requirements: 3.1, 3.2, 6.1, 6.2_
- [x] 5.2 クラス詳細テーブルの出力を実装する

  - メンバ変数テーブル（名前・型・アクセス修飾子・説明）を出力する
  - メソッドテーブル（名前・引数・戻り値型・説明）を出力する
  - 同名クラスを名前空間・ファイル名で区別して出力する
  - _Requirements: 3.4, 6.3, 6.4_
- [x] 5.3 Mermaidクラス図の生成を実装する

  - クラス間の継承・依存関係をMermaid `classDiagram` 形式で出力する
  - _Requirements: 3.3_
- [x] 5.4 グローバル変数テーブルの出力を実装する

  - 「変数名・型・初期値・変更箇所・取りうる値」のテーブルを出力する
  - `is_dynamic=True` の場合は「動的に変化する可能性あり」と注記する
  - _Requirements: 5.5, 5.6_
- [x] 5.5 レンダラーの単体テストを書く






  - サンプルの `FileInfo` を入力として期待するMarkdown出力を検証する
  - _Requirements: 3.1, 3.3, 5.5_

- [x] 6. CLIエントリーポイントの実装と統合




- [x] 6.1 `main.py` を実装する


  - `argparse` で `path`, `--output`, `--recursive`, `--help` を定義する
  - File Collector → Parser → Extractor → Renderer の処理フローを繋ぎ合わせる
  - 正常終了は終了コード 0、エラー時は終了コード 1 で stderr に出力する
  - _Requirements: 4.1, 4.2, 4.3, 4.4, 4.5, 4.6_
- [x] 6.2 出力ファイルの書き込みを実装する

  - `--output` 未指定時は `design.md` に出力する
  - 出力先ディレクトリが存在しない場合は自動作成する
  - _Requirements: 3.5, 3.6_
- [x] 6.3 統合テストを書く






  - サンプルC++ファイルを入力として設計書が正しく生成されるか end-to-end で検証する
  - _Requirements: 1.1, 2.1, 3.1, 5.5_

- [x] 7. データモデルにAI説明フィールドを追加する




  - `models.py` の `MethodInfo`, `ClassInfo`, `GlobalVarInfo` に `ai_description: str | None = None` フィールドを追加する
  - _Requirements: 7.2, 7.3, 7.4_
-

- [-] 8. AI Analyzerモジュールの実装


- [x] 8.1 `AIConfig` dataclassと `ai_analyzer.py` の骨格を実装する






  - `AIConfig(provider, model, api_key)` dataclassを定義する
  - プロバイダーごとの環境変数名・デフォルトモデルのマッピングを定義する
  - APIキー未設定時に `ValueError` を送出するバリデーションを実装する
  --_Requirements: 7.5, 7.6, 7.7_

- [x] 8.2 OpenAI / Anthropic / Gemini クライアントの呼び出しを実装する



  - 各プロバイダーのAPIクライアントを使ってテキスト生成を行う共通インターフェースを実装する
  - クラス・メソッド・グローバル変数ごとのプロンプトを構築する
  - API失敗時は警告を出力して `None` を返す
  - _Requirements: 7.1, 7.8_
- [x] 8.3 `analyze(file_infos, config) -> list[FileInfo]` を実装する






  - 各 `FileInfo` の `ClassInfo`・`MethodInfo`・`GlobalVarInfo` に対してAI APIを呼び出す
  - 生成された説明を `ai_description` フィールドに格納して返す
  --_Requirements: 7.2, 7.3, 7
.4_
- [x] 8.4 AI Analyzerの単体テストを書く





  - APIクライアントをモックしてプロンプト構築・レスポンス格納・エラー継続をテストする
  - _Requirements: 7.7, 7.8_

- [x] 9. レンダラーにAI説明の出力を追加する





  - `renderer.py` でクラス・メソッド・グローバル変数の `ai_description` が存在する場合に設計書へ追記する
  - _Requirements: 7.2, 7.3, 7.4_
- [x] 10. CLIに `--ai` / `--ai-provider` / `--ai-model` オプションを追加して統合する






- [ ] 10. CLIに `--ai` / `--ai-provider` / `--ai-model` オプションを追加して統合する

  - `main.py` に `--ai`, `--ai-provider`, `--ai-model` 引数を追加する
  - `--ai` 指定時に `AIConfig` を構築し `analyze()` を呼び出す処理フローを繋ぎ合わせる
  - 不正プロバイダー・APIキー未設定のエラーハンドリングを実装する
  - _Requirements: 7.1, 7.5, 7.6, 7.7, 7.9, 7.10_
