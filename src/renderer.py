"""
renderer.py - FileInfo リストから Markdown 設計書を生成するモジュール
"""
from __future__ import annotations

from pathlib import Path

from models import ClassInfo, FileInfo, GlobalVarInfo, MemberVarInfo, MethodInfo


# ---------------------------------------------------------------------------
# 5.1 基本構造: 目次・ファイルセクション・クラスセクション骨格
# ---------------------------------------------------------------------------

def _anchor(text: str) -> str:
    """GitHub Markdown 互換のアンカー文字列を生成する。"""
    return text.lower().replace(" ", "-").replace("/", "").replace(".", "").replace(":", "").replace("::", "-")


def _build_toc(file_infos: list[FileInfo]) -> str:
    """目次 (Table of Contents) を生成する。"""
    lines: list[str] = ["## 目次\n"]
    for fi in file_infos:
        fname = fi.filepath.name
        lines.append(f"- [{fname}](#{_anchor(fname)})")
        for cls in fi.classes:
            label = _class_label(cls, fi)
            lines.append(f"  - [{label}](#{_anchor(label)})")
        if fi.global_vars:
            lines.append(f"  - [グローバル変数](#{_anchor(fname + '-global')})")
    return "\n".join(lines)


def _class_label(cls: ClassInfo, fi: FileInfo) -> str:
    """同名クラスを名前空間・ファイル名で区別するラベルを返す。"""
    if cls.namespace:
        return f"{cls.namespace}::{cls.name}"
    return cls.name


# ---------------------------------------------------------------------------
# 5.2 クラス詳細テーブル
# ---------------------------------------------------------------------------

def _render_member_table(members: list[MemberVarInfo]) -> str:
    """メンバ変数テーブルを生成する。"""
    if not members:
        return ""
    lines = [
        "| 名前 | 型 | アクセス修飾子 | 説明 |",
        "| --- | --- | --- | --- |",
    ]
    for m in members:
        desc = m.comment or ""
        lines.append(f"| `{m.name}` | `{m.type}` | {m.access} | {desc} |")
    return "\n".join(lines)


def _render_method_table(methods: list[MethodInfo]) -> str:
    """メソッドテーブルを生成する。"""
    if not methods:
        return ""
    lines = [
        "| 名前 | 引数 | 戻り値型 | 説明 |",
        "| --- | --- | --- | --- |",
    ]
    for m in methods:
        params = ", ".join(f"{t} {n}" if n else t for t, n in m.parameters)
        desc = m.comment or ""
        lines.append(f"| `{m.name}` | `{params}` | `{m.return_type}` | {desc} |")

    # AI descriptions for individual methods (Requirement 7.3)
    ai_notes = [m for m in methods if m.ai_description]
    if ai_notes:
        lines.append("")
        lines.append("**AI解析 - メソッド説明:**")
        lines.append("")
        for m in ai_notes:
            lines.append(f"- **`{m.name}`**: {m.ai_description}")

    return "\n".join(lines)


def _render_class_section(cls: ClassInfo, fi: FileInfo) -> str:
    """クラス1つ分のセクションを生成する。"""
    label = _class_label(cls, fi)
    parts: list[str] = [f"### {label}"]

    if cls.comment:
        parts.append(f"\n{cls.comment}\n")

    # AI generated class description (Requirement 7.2)
    if cls.ai_description:
        parts.append(f"> **AI解析:** {cls.ai_description}\n")

    if cls.bases:
        parts.append(f"**継承元:** {', '.join(f'`{b}`' for b in cls.bases)}\n")

    # Mermaid クラス図 (5.3)
    diagram = _render_mermaid_diagram([cls])
    if diagram:
        parts.append(diagram)

    # メンバ変数テーブル (5.2)
    member_table = _render_member_table(cls.members)
    if member_table:
        parts.append("#### メンバ変数\n")
        parts.append(member_table)

    # メソッドテーブル (5.2)
    method_table = _render_method_table(cls.methods)
    if method_table:
        parts.append("\n#### メソッド\n")
        parts.append(method_table)

    return "\n".join(parts)


# ---------------------------------------------------------------------------
# 5.3 Mermaid クラス図
# ---------------------------------------------------------------------------

def _sanitize_mermaid(name: str) -> str:
    """Mermaid で使えない文字を除去する。"""
    return name.replace("::", "__").replace("<", "_").replace(">", "_").replace(" ", "_")


def _render_mermaid_diagram(classes: list[ClassInfo]) -> str:
    """クラスリストから Mermaid classDiagram を生成する。"""
    if not classes:
        return ""

    lines: list[str] = ["```mermaid", "classDiagram"]

    for cls in classes:
        safe_name = _sanitize_mermaid(cls.namespace + "::" + cls.name if cls.namespace else cls.name)

        # クラス定義
        lines.append(f"  class {safe_name}")

        # 継承関係
        for base in cls.bases:
            safe_base = _sanitize_mermaid(base)
            lines.append(f"  {safe_base} <|-- {safe_name}")

    lines.append("```")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# 5.4 グローバル変数テーブル
# ---------------------------------------------------------------------------

def _render_global_var_table(global_vars: list[GlobalVarInfo]) -> str:
    """グローバル変数テーブルを生成する。"""
    if not global_vars:
        return ""
    lines = [
        "| 変数名 | 型 | 初期値 | 変更箇所 | 取りうる値 | 備考 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for v in global_vars:
        init = v.initial_value or ""
        modified = ", ".join(v.modified_in) if v.modified_in else "-"
        possible = ", ".join(v.possible_values) if v.possible_values else "-"
        note = "動的に変化する可能性あり" if v.is_dynamic else ""
        if v.is_extern:
            note = ("外部参照 / " + note).rstrip(" /") if note else "外部参照"
        lines.append(f"| `{v.name}` | `{v.type}` | `{init}` | {modified} | {possible} | {note} |")

    # AI descriptions for global variables (Requirement 7.4)
    ai_notes = [v for v in global_vars if v.ai_description]
    if ai_notes:
        lines.append("")
        lines.append("**AI解析 - グローバル変数の用途・リスク・改善提案:**")
        lines.append("")
        for v in ai_notes:
            lines.append(f"- **`{v.name}`**: {v.ai_description}")

    return "\n".join(lines)


# ---------------------------------------------------------------------------
# メインエントリーポイント
# ---------------------------------------------------------------------------

def render(file_infos: list[FileInfo]) -> str:
    """
    FileInfo のリストから Markdown 設計書文字列を生成して返す。

    Args:
        file_infos: 解析済みファイル情報のリスト

    Returns:
        Markdown 形式の設計書文字列
    """
    sections: list[str] = ["# C++ 設計書\n"]

    # 目次 (6.1)
    sections.append(_build_toc(file_infos))
    sections.append("")

    # ファイルごとのセクション (6.2)
    for fi in file_infos:
        fname = fi.filepath.name
        sections.append(f"---\n\n## {fname}\n")

        # クラスセクション (3.2, 6.3)
        if fi.classes:
            for cls in fi.classes:
                sections.append(_render_class_section(cls, fi))
                sections.append("")

        # グローバル変数テーブル (5.5)
        if fi.global_vars:
            sections.append(f"### グローバル変数\n")
            sections.append(_render_global_var_table(fi.global_vars))
            sections.append("")

    return "\n".join(sections)
