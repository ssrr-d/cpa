# Requirements Document

## Introduction

C++のソースコードファイルを入力として受け取り、コードを解析して設計書（ドキュメント）を自動生成するプログラム。
クラス構造、関数シグネチャ、依存関係、コメントなどを抽出し、読みやすい設計書フォーマット（Markdown等）で出力する。

## Requirements

### Requirement 1: C++ソースファイルの読み込み

**User Story:** 開発者として、C++のソースファイル（.cpp / .h）を指定して読み込みたい。そうすることで、解析対象のコードをプログラムに渡せる。

#### Acceptance Criteria

1. WHEN ユーザーがファイルパスまたはディレクトリパスを指定する THEN システムは指定された .cpp / .h ファイルを読み込む SHALL
2. WHEN ディレクトリが指定される THEN システムは再帰的にすべての .cpp / .h ファイルを収集する SHALL
3. IF 指定されたファイルが存在しない THEN システムはエラーメッセージを表示して処理を中断する SHALL
4. WHEN ファイルの読み込みに成功する THEN システムは読み込んだファイル数を表示する SHALL

### Requirement 2: C++コードの解析

**User Story:** 開発者として、C++ソースコードの構造を自動的に解析したい。そうすることで、手動でコードを読まずに設計情報を把握できる。

#### Acceptance Criteria

1. WHEN ソースファイルが読み込まれる THEN システムはクラス名・継承関係を抽出する SHALL
2. WHEN ソースファイルが読み込まれる THEN システムはpublic / protected / privateメンバ変数と型を抽出する SHALL
3. WHEN ソースファイルが読み込まれる THEN システムはメンバ関数のシグネチャ（名前・引数・戻り値型）を抽出する SHALL
4. WHEN ソースファイルが読み込まれる THEN システムは名前空間（namespace）を抽出する SHALL
5. WHEN ソースファイルが読み込まれる THEN システムは #include による依存関係を抽出する SHALL
6. WHEN コードにDoxygenスタイルのコメント（/** ... */ や /// ...）が存在する THEN システムはそのコメントを対応する要素に紐付けて抽出する SHALL
7. IF コードが解析できない構文を含む THEN システムは警告を出力しつつ解析可能な部分のみ処理を続行する SHALL

### Requirement 3: 設計書の生成

**User Story:** 開発者として、解析結果をもとに読みやすい設計書を自動生成したい。そうすることで、ドキュメント作成の手間を大幅に削減できる。

#### Acceptance Criteria

1. WHEN 解析が完了する THEN システムはMarkdown形式の設計書を生成する SHALL
2. WHEN 設計書が生成される THEN クラス一覧・クラス詳細（メンバ変数・メソッド）・依存関係が含まれる SHALL
3. WHEN 設計書が生成される THEN クラス間の継承・依存関係をMermaidクラス図として出力する SHALL
4. WHEN Doxygenコメントが存在する THEN 設計書の対応する箇所にその説明文を含める SHALL
5. WHEN 出力先パスが指定される THEN システムは指定パスに設計書ファイルを書き出す SHALL
6. IF 出力先パスが指定されない THEN システムはカレントディレクトリに design.md として出力する SHALL

### Requirement 4: コマンドラインインターフェース

**User Story:** 開発者として、コマンドラインからシンプルに操作したい。そうすることで、CI/CDパイプラインや自動化スクリプトに組み込める。

#### Acceptance Criteria

1. WHEN プログラムを実行する THEN 入力パス（ファイルまたはディレクトリ）を引数として受け取る SHALL
2. WHEN `--output` オプションが指定される THEN 出力ファイルパスとして使用する SHALL
3. WHEN `--help` オプションが指定される THEN 使用方法を表示する SHALL
4. WHEN `--recursive` オプションが指定される THEN サブディレクトリも再帰的に検索する SHALL
5. WHEN 処理が正常に完了する THEN 終了コード 0 を返す SHALL
6. WHEN エラーが発生する THEN 終了コード 1 を返しエラー内容を stderr に出力する SHALL

### Requirement 5: グローバル変数の解析と状態追跡

**User Story:** 開発者として、各ファイルのグローバル変数がどのように変化するか、またどのような値を取りうるかを把握したい。そうすることで、グローバル状態に起因するバグや副作用を素早く特定できる。

#### Acceptance Criteria

1. WHEN ソースファイルが解析される THEN システムはファイルスコープのグローバル変数（型・名前・初期値）を抽出する SHALL
2. WHEN グローバル変数が解析される THEN システムはその変数に代入・変更を行っている関数・箇所を列挙する SHALL
3. WHEN グローバル変数が解析される THEN システムはリテラル値や定数による代入からその変数が取りうる値の候補を列挙する SHALL
4. WHEN `extern` 宣言が存在する THEN システムは他ファイルから参照されるグローバル変数として識別する SHALL
5. WHEN 設計書が生成される THEN グローバル変数ごとに「変数名・型・初期値・変更箇所・取りうる値」をテーブル形式で出力する SHALL
6. IF グローバル変数への代入が動的（関数の戻り値・ユーザー入力等）である THEN システムは「動的に変化する可能性あり」と注記する SHALL

### Requirement 7: AI を使用したコード解析と説明生成

**User Story:** 開発者として、AIを使ってC++コードの意図・設計上の判断・潜在的な問題点を自然言語で説明してほしい。そうすることで、コードを読んだことがないメンバーでも設計書だけで内容を理解できる。

#### Acceptance Criteria

1. WHEN `--ai` オプションが指定される THEN システムはAI APIを呼び出してクラス・関数・グローバル変数の説明を生成する SHALL
2. WHEN AI説明が生成される THEN 各クラスの概要・責務・設計上の意図を自然言語で設計書に追記する SHALL
3. WHEN AI説明が生成される THEN 各パブリックメソッドの動作説明・引数の意味・戻り値の意味を設計書に追記する SHALL
4. WHEN AI説明が生成される THEN グローバル変数の用途・リスク・改善提案を設計書に追記する SHALL
5. WHEN `--ai-provider` オプションが指定される THEN 指定されたAIプロバイダー（openai / anthropic / gemini）を使用する SHALL
6. IF `--ai-provider` が指定されない THEN デフォルトとして `openai` を使用する SHALL
7. WHEN AIプロバイダーのAPIキーが環境変数に設定されていない THEN システムはエラーメッセージと設定方法を stderr に出力して終了コード 1 を返す SHALL
8. WHEN AI API呼び出しが失敗する THEN システムは警告を出力しAI説明なしで設計書生成を継続する SHALL
9. WHEN `--ai-model` オプションが指定される THEN 指定されたモデル名を使用する SHALL
10. IF `--ai-model` が指定されない THEN 各プロバイダーのデフォルトモデルを使用する SHALL

### Requirement 6: 出力品質

**User Story:** 開発者として、生成された設計書が実用的な品質であってほしい。そうすることで、そのままチームへの共有やレビューに使える。

#### Acceptance Criteria

1. WHEN 設計書が生成される THEN 目次（Table of Contents）が先頭に含まれる SHALL
2. WHEN 複数ファイルが解析される THEN ファイルごとのセクションに分けて出力する SHALL
3. WHEN クラスが存在する THEN クラスごとにメンバ変数テーブルとメソッドテーブルを出力する SHALL
4. WHEN 同名のクラスが複数ファイルに存在する THEN 名前空間またはファイル名で区別して出力する SHALL
