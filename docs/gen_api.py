"""Generate docs/api.md, the API reference, from the package's docstrings and signatures.

Run ``python docs/gen_api.py`` after changing the public API; ``tests/test_docs.py``
fails when docs/api.md is out of date.
"""

from __future__ import annotations

import ast
import dataclasses
import enum
import importlib
import inspect
import textwrap
from pathlib import Path

MODULES = [
    "streaming",
    "detectors",
    "calibration",
    "online_fdr",
    "preprocess",
    "bootstrap",
    "monitor",
    "metrics",
    "streams",
    "datasets",
    "integrations.prometheus",
    "integrations.mlflow",
    "integrations.nannyml",
]
OUT = Path(__file__).with_name("api.md")


def field_docs(module) -> dict[str, dict[str, str]]:
    """Docstrings written right under dataclass fields: {class: {field: doc}}."""
    tree = ast.parse(inspect.getsource(module))
    out: dict[str, dict[str, str]] = {}
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        docs, body = {}, node.body
        for a, b in zip(body, body[1:]):
            if isinstance(a, ast.AnnAssign) and isinstance(a.target, ast.Name):
                if isinstance(b, ast.Expr) and isinstance(b.value, ast.Constant) and isinstance(b.value.value, str):
                    docs[a.target.id] = " ".join(inspect.cleandoc(b.value.value).split())
        out[node.name] = docs
    return out


def signature(obj, name: str) -> str:
    """``name(params) -> ret`` with string annotations unquoted and ``self``/``cls`` dropped."""
    try:
        sig = inspect.signature(obj)
    except (TypeError, ValueError):
        return f"{name}(...)"
    parts, seen_kwonly = [], False
    for p in sig.parameters.values():
        if p.name in ("self", "cls"):
            continue
        if p.kind is p.KEYWORD_ONLY and not seen_kwonly:
            parts.append("*")
            seen_kwonly = True
        text = ("*" if p.kind is p.VAR_POSITIONAL else "**" if p.kind is p.VAR_KEYWORD else "") + p.name
        if p.annotation is not p.empty:
            ann = p.annotation if isinstance(p.annotation, str) else getattr(p.annotation, "__name__", str(p.annotation))
            text += f": {ann}"
        if p.default is not p.empty:
            text += f" = {p.default!r}" if p.annotation is not p.empty else f"={p.default!r}"
        parts.append(text)
    ret = ""
    if sig.return_annotation is not sig.empty:
        r = sig.return_annotation
        ret = " -> " + (r.strip('"\'') if isinstance(r, str) else getattr(r, "__name__", str(r)))
    return f"{name}({', '.join(parts)}){ret}"


def doc(obj) -> str:
    return inspect.getdoc(obj) or ""


def public_members(cls):
    for name, member in vars(cls).items():
        if name.startswith("_"):
            continue
        if isinstance(member, property):
            yield name, "property", member
        elif isinstance(member, (classmethod, staticmethod)):
            yield name, "classmethod" if isinstance(member, classmethod) else "staticmethod", getattr(cls, name)
        elif inspect.isfunction(member):
            yield name, "method", getattr(cls, name)


def render_class(cls, fdocs: dict[str, str]) -> list[str]:
    bases = [b.__name__ for b in cls.__bases__ if b is not object]
    head = f"### `{cls.__name__}`" + (f" ({', '.join(bases)})" if bases else "")
    if issubclass(cls, enum.Enum):  # the Enum constructor's signature differs between Python versions
        lines = [head, ""]
        if cls.__doc__:
            lines += [inspect.cleandoc(cls.__doc__), ""]
        lines += ["| member | value |", "|---|---|", *[f"| `{cls.__name__}.{m.name}` | `{m.value!r}` |" for m in cls], ""]
        return lines + [""]
    lines = [head, "", f"```python\n{signature(cls, cls.__name__)}\n```", ""]
    if cls.__doc__:
        lines += [inspect.cleandoc(cls.__doc__), ""]
    if dataclasses.is_dataclass(cls):
        rows = []
        for f in dataclasses.fields(cls):
            if f.name.startswith("_"):
                continue
            default = f.default if f.default is not dataclasses.MISSING else (
                f"{f.default_factory.__name__}()" if f.default_factory is not dataclasses.MISSING else "required")
            ftype = f.type if isinstance(f.type, str) else getattr(f.type, "__name__", str(f.type))
            rows.append(f"| `{f.name}` | `{ftype}` | `{default!r}` | {fdocs.get(f.name, '')} |".replace("'required'", "required"))
        if rows:
            lines += ["| field | type | default | description |", "|---|---|---|---|", *rows, ""]
    for name, kind, member in public_members(cls):
        if kind == "property":
            lines += [f"- **`{name}`** *(property)* — {' '.join(doc(member).split())}"]
        else:
            text = textwrap.indent(doc(member), "  ")
            prefix = f"*({kind})* " if kind != "method" else ""
            lines += [f"- **`{signature(member, name)}`** {prefix}", "", text, ""] if text.strip() else [
                f"- **`{signature(member, name)}`** {prefix}"]
    return lines + [""]


def render_module(modname: str) -> list[str]:
    module = importlib.import_module(f"driftfdr.{modname}")
    fdocs = field_docs(module)
    lines = [f"## `driftfdr.{modname}`", ""]
    if module.__doc__:
        lines += [inspect.cleandoc(module.__doc__), ""]
    items = [
        (name, obj)
        for name, obj in vars(module).items()
        if not name.startswith("_")
        and (inspect.isclass(obj) or inspect.isfunction(obj))
        and getattr(obj, "__module__", None) == module.__name__
    ]
    items.sort(key=lambda it: inspect.getsourcelines(it[1])[1])
    for name, obj in items:
        if inspect.isclass(obj):
            lines += render_class(obj, fdocs.get(name, {}))
        else:
            lines += [f"### `{name}`", "", f"```python\n{signature(obj, name)}\n```", "", doc(obj), ""]
    return lines


def generate() -> str:
    import driftfdr

    lines = [
        "# API reference",
        "",
        "Generated from the docstrings by `python docs/gen_api.py`; do not edit by hand.",
        "Everything listed under `driftfdr.__all__` can be imported from the top-level package.",
        "",
        "Top-level exports: " + ", ".join(f"`{n}`" for n in sorted(driftfdr.__all__)) + ".",
        "",
        "## Contents",
        "",
        *[f"- [`driftfdr.{m}`](#driftfdr{m.replace('.', '')})" for m in MODULES],
        "",
    ]
    for m in MODULES:
        lines += render_module(m)
    text = "\n".join(lines)
    while "\n\n\n" in text:
        text = text.replace("\n\n\n", "\n\n")
    return text.rstrip() + "\n"


if __name__ == "__main__":
    OUT.write_text(generate())
    print(f"wrote {OUT}")
