from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path


@dataclass
class MethodInfo:
    name: str
    return_type: str
    parameters: list[tuple[str, str]]  # (型, 引数名)
    access: str  # "public" | "protected" | "private"
    comment: str | None = None
    ai_description: str | None = None


@dataclass
class MemberVarInfo:
    name: str
    type: str
    access: str  # "public" | "protected" | "private"
    comment: str | None = None


@dataclass
class ClassInfo:
    name: str
    namespace: str | None
    bases: list[str]
    members: list[MemberVarInfo]
    methods: list[MethodInfo]
    comment: str | None = None
    ai_description: str | None = None


@dataclass
class GlobalVarInfo:
    name: str
    type: str
    initial_value: str | None
    modified_in: list[str] = field(default_factory=list)   # 変更している関数名のリスト
    possible_values: list[str] = field(default_factory=list)  # リテラル/定数から推定した取りうる値
    is_dynamic: bool = False                                # 動的変化の可能性
    is_extern: bool = False                                 # extern宣言かどうか
    ai_description: str | None = None


@dataclass
class IncludeInfo:
    included_file: str
    is_system: bool


@dataclass
class FileInfo:
    filepath: Path
    classes: list[ClassInfo] = field(default_factory=list)
    global_vars: list[GlobalVarInfo] = field(default_factory=list)
    includes: list[IncludeInfo] = field(default_factory=list)
