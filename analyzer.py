"""AST-based discovery for small Python packages."""

from __future__ import annotations

import ast
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class FunctionInfo:
    """Metadata needed to generate characterization tests."""

    module: str
    qualname: str
    name: str
    parameters: tuple[str, ...]
    type_hints: dict[str, str]
    return_hint: str | None
    docstring: str
    source: str
    file_path: str
    lineno: int

    @property
    def import_name(self) -> str:
        return self.qualname.split(".")[-1]

    @property
    def arity(self) -> int:
        return len(self.parameters)


@dataclass(frozen=True)
class Analysis:
    """Public API discovered in a target package."""

    root: Path
    package: str
    functions: tuple[FunctionInfo, ...]


def analyze(root: str | Path, package: str | None = None) -> Analysis:
    """Discover public top-level functions and public class methods."""
    root_path = Path(root).resolve()
    if not root_path.exists():
        raise FileNotFoundError(root_path)

    package_name = package or root_path.name
    functions: list[FunctionInfo] = []
    for file_path in sorted(root_path.rglob("*.py")):
        if file_path.name == "__init__.py":
            continue
        module = _module_name(root_path, package_name, file_path)
        source = file_path.read_text(encoding="utf-8")
        tree = ast.parse(source, filename=str(file_path))
        lines = source.splitlines()
        functions.extend(_top_level_functions(tree, module, file_path, lines))
        functions.extend(_class_methods(tree, module, file_path, lines))

    return Analysis(root=root_path, package=package_name, functions=tuple(functions))


def _module_name(root: Path, package: str, file_path: Path) -> str:
    relative = file_path.relative_to(root).with_suffix("")
    parts = (package, *relative.parts)
    return ".".join(parts)


def _top_level_functions(
    tree: ast.Module, module: str, file_path: Path, lines: list[str]
) -> list[FunctionInfo]:
    found: list[FunctionInfo] = []
    for node in tree.body:
        if isinstance(node, ast.FunctionDef) and _is_public(node.name):
            found.append(_function_info(node, module, node.name, file_path, lines))
    return found


def _class_methods(
    tree: ast.Module, module: str, file_path: Path, lines: list[str]
) -> list[FunctionInfo]:
    found: list[FunctionInfo] = []
    for class_node in tree.body:
        if not isinstance(class_node, ast.ClassDef) or not _is_public(class_node.name):
            continue
        for node in class_node.body:
            if isinstance(node, ast.FunctionDef) and _is_public(node.name):
                qualname = f"{class_node.name}.{node.name}"
                found.append(_function_info(node, module, qualname, file_path, lines))
    return found


def _function_info(
    node: ast.FunctionDef, module: str, qualname: str, file_path: Path, lines: list[str]
) -> FunctionInfo:
    parameters: list[str] = []
    hints: dict[str, str] = {}
    for arg in node.args.args:
        if arg.arg in {"self", "cls"}:
            continue
        parameters.append(arg.arg)
        if arg.annotation is not None:
            hints[arg.arg] = ast.unparse(arg.annotation)

    source = _source_segment(node, lines)
    return FunctionInfo(
        module=module,
        qualname=qualname,
        name=qualname,
        parameters=tuple(parameters),
        type_hints=hints,
        return_hint=ast.unparse(node.returns) if node.returns is not None else None,
        docstring=ast.get_docstring(node) or "",
        source=source,
        file_path=str(file_path),
        lineno=node.lineno,
    )


def _source_segment(node: ast.AST, lines: list[str]) -> str:
    end = getattr(node, "end_lineno", node.lineno)
    return "\n".join(lines[node.lineno - 1 : end])


def _is_public(name: str) -> bool:
    return not name.startswith("_")

