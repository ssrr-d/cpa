"""
extractor.py - libclang ASTからC++コード情報を抽出するモジュール
"""
from __future__ import annotations

import sys
from pathlib import Path

import clang.cindex as cindex

from models import (
    ClassInfo,
    FileInfo,
    GlobalVarInfo,
    GlobalVarEffect,
    IncludeInfo,
    MemberVarInfo,
    MethodInfo,
)

# アクセス修飾子マッピング
_ACCESS_MAP = {
    cindex.AccessSpecifier.PUBLIC: "public",
    cindex.AccessSpecifier.PROTECTED: "protected",
    cindex.AccessSpecifier.PRIVATE: "private",
}


# ---------------------------------------------------------------------------
# Doxygenコメント抽出
# ---------------------------------------------------------------------------

def _get_doxygen_comment(cursor: cindex.Cursor) -> str | None:
    """カーソルに紐付くDoxygenコメントを返す。なければ None。"""
    raw = cursor.raw_comment
    if not raw:
        return None
    # /** ... */ または /// ... 形式を整形して返す
    lines = raw.splitlines()
    cleaned: list[str] = []
    for line in lines:
        line = line.strip()
        # 行頭の /** / * / */ / /// を除去
        for prefix in ("/**", "*/", "///", "//", "*"):
            if line.startswith(prefix):
                line = line[len(prefix):].strip()
                break
        if line:
            cleaned.append(line)
    return " ".join(cleaned) if cleaned else None


# ---------------------------------------------------------------------------
# メソッド本体解析: 内部処理・グローバル変数影響 (新規)
# ---------------------------------------------------------------------------

def _collect_method_body_info(
    cursor: cindex.Cursor,
    global_names: set[str],
) -> tuple[list[str], list["GlobalVarEffect"]]:
    """
    メソッド本体のASTを走査して内部処理概要とグローバル変数への影響を収集する。

    Returns:
        (body_summary, global_var_effects)
        - body_summary: 呼び出し関数名のリスト
        - global_var_effects: GlobalVarEffect のリスト
    """
    calls: list[str] = []
    effects_map: dict[str, str] = {}  # var_name -> "read" | "write" | "read/write"

    def _walk(node: cindex.Cursor, in_lhs: bool = False) -> None:
        # 関数呼び出し収集
        if node.kind == cindex.CursorKind.CALL_EXPR and node.spelling:
            if node.spelling not in calls:
                calls.append(node.spelling)

        # グローバル変数の読み書き検出
        if node.kind == cindex.CursorKind.BINARY_OPERATOR:
            children = list(node.get_children())
            if len(children) == 2:
                lhs, rhs = children
                # 左辺への代入 → write
                if lhs.kind == cindex.CursorKind.DECL_REF_EXPR and lhs.spelling in global_names:
                    var = lhs.spelling
                    effects_map[var] = "read/write" if effects_map.get(var) == "read" else "write"
                # 右辺での参照 → read
                _collect_reads(rhs, global_names, effects_map)
                return  # 子は上で処理済み

        # 代入以外での参照 → read
        if node.kind == cindex.CursorKind.DECL_REF_EXPR and node.spelling in global_names:
            var = node.spelling
            if var not in effects_map:
                effects_map[var] = "read"
            elif effects_map[var] == "write":
                effects_map[var] = "read/write"

        for child in node.get_children():
            _walk(child)

    def _collect_reads(node: cindex.Cursor, names: set[str], em: dict[str, str]) -> None:
        if node.kind == cindex.CursorKind.DECL_REF_EXPR and node.spelling in names:
            var = node.spelling
            if var not in em:
                em[var] = "read"
            elif em[var] == "write":
                em[var] = "read/write"
        for child in node.get_children():
            _collect_reads(child, names, em)

    # メソッド本体（COMPOUND_STMT）を走査
    for child in cursor.get_children():
        if child.kind == cindex.CursorKind.COMPOUND_STMT:
            _walk(child)

    effects = [GlobalVarEffect(var_name=k, effect=v) for k, v in effects_map.items()]
    return calls, effects


# ---------------------------------------------------------------------------
# クラス・メンバ・メソッド抽出 (4.1)
# ---------------------------------------------------------------------------

def _extract_method(cursor: cindex.Cursor, global_names: set[str] | None = None) -> MethodInfo:
    """メソッドカーソルから MethodInfo を生成する。"""
    params: list[tuple[str, str]] = []
    for child in cursor.get_children():
        if child.kind == cindex.CursorKind.PARM_DECL:
            params.append((child.type.spelling, child.spelling))

    body_summary: list[str] = []
    global_var_effects: list = []
    if global_names is not None:
        body_summary, global_var_effects = _collect_method_body_info(cursor, global_names)

    return MethodInfo(
        name=cursor.spelling,
        return_type=cursor.result_type.spelling,
        parameters=params,
        access=_ACCESS_MAP.get(cursor.access_specifier, "public"),
        comment=_get_doxygen_comment(cursor),
        body_summary=body_summary,
        global_var_effects=global_var_effects,
    )


def _extract_class(cursor: cindex.Cursor, namespace: str | None, global_names: set[str] | None = None) -> ClassInfo:
    """クラスカーソルから ClassInfo を生成する。"""
    bases: list[str] = []
    members: list[MemberVarInfo] = []
    methods: list[MethodInfo] = []

    for child in cursor.get_children():
        kind = child.kind

        # 継承元
        if kind == cindex.CursorKind.CXX_BASE_SPECIFIER:
            bases.append(child.type.spelling)

        # メンバ変数
        elif kind == cindex.CursorKind.FIELD_DECL:
            members.append(MemberVarInfo(
                name=child.spelling,
                type=child.type.spelling,
                access=_ACCESS_MAP.get(child.access_specifier, "private"),
                comment=_get_doxygen_comment(child),
            ))

        # メソッド（コンストラクタ・デストラクタ含む）
        elif kind in (
            cindex.CursorKind.CXX_METHOD,
            cindex.CursorKind.CONSTRUCTOR,
            cindex.CursorKind.DESTRUCTOR,
            cindex.CursorKind.FUNCTION_TEMPLATE,
        ):
            methods.append(_extract_method(child, global_names))

    return ClassInfo(
        name=cursor.spelling,
        namespace=namespace,
        bases=bases,
        members=members,
        methods=methods,
        comment=_get_doxygen_comment(cursor),
    )


# ---------------------------------------------------------------------------
# 名前空間・include抽出 (4.2)
# ---------------------------------------------------------------------------

def _extract_includes(tu: cindex.TranslationUnit) -> list[IncludeInfo]:
    """TranslationUnit から #include 依存関係を抽出する。"""
    includes: list[IncludeInfo] = []
    seen: set[str] = set()
    for inc in tu.get_includes():
        # depth==1 が直接 include のみ
        if inc.depth == 1:
            name = inc.include.name
            if name not in seen:
                seen.add(name)
                # <...> 形式かどうかはソーストークンから判定が難しいため
                # システムヘッダは通常 /usr/ や compiler built-in パスに存在する
                is_system = any(
                    seg in name for seg in ("/usr/", "/lib/", "clang/", "bits/")
                )
                includes.append(IncludeInfo(included_file=name, is_system=is_system))
    return includes


# ---------------------------------------------------------------------------
# グローバル変数抽出・状態追跡 (4.3)
# ---------------------------------------------------------------------------

def _is_literal_or_const(cursor: cindex.Cursor) -> bool:
    """カーソルがリテラルまたは定数参照かを簡易判定する。"""
    literal_kinds = {
        cindex.CursorKind.INTEGER_LITERAL,
        cindex.CursorKind.FLOATING_LITERAL,
        cindex.CursorKind.STRING_LITERAL,
        cindex.CursorKind.CHARACTER_LITERAL,
        cindex.CursorKind.CXX_BOOL_LITERAL_EXPR,
        cindex.CursorKind.CXX_NULL_PTR_LITERAL_EXPR,
    }
    return cursor.kind in literal_kinds


def _get_literal_value(cursor: cindex.Cursor) -> str | None:
    """リテラルカーソルからトークン文字列を返す。"""
    tokens = list(cursor.get_tokens())
    if tokens:
        return "".join(t.spelling for t in tokens)
    return None


def _collect_literal_values(cursor: cindex.Cursor) -> list[str]:
    """カーソル配下のリテラル値を再帰的に収集する。"""
    values: list[str] = []
    if _is_literal_or_const(cursor):
        v = _get_literal_value(cursor)
        if v:
            values.append(v)
    for child in cursor.get_children():
        values.extend(_collect_literal_values(child))
    return values


def _has_dynamic_rhs(cursor: cindex.Cursor) -> bool:
    """代入右辺に動的要素（関数呼び出し・DeclRef等）が含まれるか判定する。"""
    dynamic_kinds = {
        cindex.CursorKind.CALL_EXPR,
        cindex.CursorKind.DECL_REF_EXPR,
        cindex.CursorKind.UNARY_OPERATOR,
        cindex.CursorKind.ARRAY_SUBSCRIPT_EXPR,
        cindex.CursorKind.MEMBER_REF_EXPR,
    }
    for child in cursor.get_children():
        if child.kind in dynamic_kinds:
            return True
        if _has_dynamic_rhs(child):
            return True
    return False


def _find_enclosing_function(cursor: cindex.Cursor) -> str | None:
    """カーソルの祖先から最も近い関数名を返す。"""
    func_kinds = {
        cindex.CursorKind.FUNCTION_DECL,
        cindex.CursorKind.CXX_METHOD,
        cindex.CursorKind.CONSTRUCTOR,
        cindex.CursorKind.DESTRUCTOR,
        cindex.CursorKind.FUNCTION_TEMPLATE,
    }
    parent = cursor.semantic_parent
    while parent and parent.kind != cindex.CursorKind.TRANSLATION_UNIT:
        if parent.kind in func_kinds:
            return parent.spelling
        parent = parent.semantic_parent
    return None


def _collect_global_var_mutations(
    cursor: cindex.Cursor,
    global_names: set[str],
    var_map: dict[str, GlobalVarInfo],
    filepath: Path,
) -> None:
    """ASTを再帰トラバースしてグローバル変数への代入を検出する。"""
    # 対象ファイルのノードのみ処理
    if cursor.location.file and Path(cursor.location.file.name) != filepath:
        return

    if cursor.kind == cindex.CursorKind.BINARY_OPERATOR:
        children = list(cursor.get_children())
        if len(children) == 2:
            lhs, rhs = children
            # 左辺がグローバル変数参照かチェック
            if lhs.kind == cindex.CursorKind.DECL_REF_EXPR and lhs.spelling in global_names:
                var_name = lhs.spelling
                info = var_map[var_name]

                func_name = _find_enclosing_function(cursor)
                location = func_name or f"<global scope:{cursor.location.line}>"
                if location not in info.modified_in:
                    info.modified_in.append(location)

                # 右辺がリテラル/定数のみ → possible_values に追加
                literals = _collect_literal_values(rhs)
                for lit in literals:
                    if lit not in info.possible_values:
                        info.possible_values.append(lit)

                # 動的代入チェック
                if _has_dynamic_rhs(rhs):
                    info.is_dynamic = True

    for child in cursor.get_children():
        _collect_global_var_mutations(child, global_names, var_map, filepath)


def _extract_global_vars(
    tu: cindex.TranslationUnit, filepath: Path
) -> list[GlobalVarInfo]:
    """ファイルスコープのグローバル変数を抽出し、状態追跡を行う。"""
    var_map: dict[str, GlobalVarInfo] = {}

    for cursor in tu.cursor.get_children():
        # 対象ファイルのノードのみ
        if not cursor.location.file:
            continue
        if Path(cursor.location.file.name) != filepath:
            continue

        if cursor.kind != cindex.CursorKind.VAR_DECL:
            continue

        # extern 判定
        is_extern = cursor.storage_class == cindex.StorageClass.EXTERN

        # 初期値: 子ノードのリテラルから取得
        initial_value: str | None = None
        possible_values: list[str] = []
        is_dynamic = False

        children = list(cursor.get_children())
        if children:
            init_cursor = children[-1]  # 最後の子が初期化式
            literals = _collect_literal_values(init_cursor)
            if literals:
                initial_value = literals[0]
                possible_values = list(literals)
            elif _has_dynamic_rhs(init_cursor):
                is_dynamic = True

        info = GlobalVarInfo(
            name=cursor.spelling,
            type=cursor.type.spelling,
            initial_value=initial_value,
            possible_values=possible_values,
            is_dynamic=is_dynamic,
            is_extern=is_extern,
        )
        var_map[cursor.spelling] = info

    # 代入箇所・動的変化を全ASTからトラバースして収集
    if var_map:
        _collect_global_var_mutations(
            tu.cursor, set(var_map.keys()), var_map, filepath
        )

    return list(var_map.values())


# ---------------------------------------------------------------------------
# メインエントリーポイント
# ---------------------------------------------------------------------------

def _traverse(
    cursor: cindex.Cursor,
    filepath: Path,
    namespace_stack: list[str],
    classes: list[ClassInfo],
    global_names: set[str] | None = None,
) -> None:
    """ASTを再帰トラバースしてクラスと名前空間を収集する。"""
    # 対象ファイルのノードのみ処理（インクルード先は除外）
    if cursor.location.file and Path(cursor.location.file.name) != filepath:
        return

    if cursor.kind == cindex.CursorKind.NAMESPACE:
        namespace_stack.append(cursor.spelling)
        for child in cursor.get_children():
            _traverse(child, filepath, namespace_stack, classes, global_names)
        namespace_stack.pop()
        return

    if cursor.kind in (
        cindex.CursorKind.CLASS_DECL,
        cindex.CursorKind.STRUCT_DECL,
        cindex.CursorKind.CLASS_TEMPLATE,
    ):
        # 定義のあるクラスのみ（前方宣言を除外）
        if cursor.is_definition():
            ns = "::".join(namespace_stack) if namespace_stack else None
            classes.append(_extract_class(cursor, ns, global_names))
        return  # クラス内のネストは _extract_class が処理

    for child in cursor.get_children():
        _traverse(child, filepath, namespace_stack, classes, global_names)


def extract(tu: cindex.TranslationUnit, filepath: Path) -> FileInfo:
    """
    libclang TranslationUnit から FileInfo を抽出して返す。

    Args:
        tu: libclang の TranslationUnit
        filepath: 解析対象ファイルの Path

    Returns:
        抽出結果を格納した FileInfo
    """
    filepath = filepath.resolve()

    # グローバル変数を先に抽出してクラス解析に名前セットを渡す (4.3)
    global_vars = _extract_global_vars(tu, filepath)
    global_names = {v.name for v in global_vars}

    # クラス抽出 (4.1, 4.2)
    classes: list[ClassInfo] = []
    _traverse(tu.cursor, filepath, [], classes, global_names)

    # include抽出 (4.2)
    includes = _extract_includes(tu)

    return FileInfo(
        filepath=filepath,
        classes=classes,
        global_vars=global_vars,
        includes=includes,
    )
