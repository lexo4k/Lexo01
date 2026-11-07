"""Camada simbólica determinística da NEXORA.

Classifica caracteres e estruturas textuais e avalia aritmética simples com AST
restrita. Não executa código arbitrário e não confunde reconhecimento de símbolos
com compreensão aprendida por um modelo.
"""
from __future__ import annotations

import ast
import operator
import unicodedata
from typing import Any

_BINARY = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
_UNARY = {ast.UAdd: operator.pos, ast.USub: operator.neg}
_MAX_EXPR = 160
_MAX_ABS = 10**12


def _safe_node(node: ast.AST) -> int | float:
    if isinstance(node, ast.Expression):
        return _safe_node(node.body)
    if isinstance(node, ast.Constant) and type(node.value) in (int, float):
        value = node.value
    elif isinstance(node, ast.BinOp) and type(node.op) in _BINARY:
        left, right = _safe_node(node.left), _safe_node(node.right)
        if isinstance(node.op, ast.Pow) and abs(right) > 8:
            raise ValueError("Expoente acima do limite permitido.")
        value = _BINARY[type(node.op)](left, right)
    elif isinstance(node, ast.UnaryOp) and type(node.op) in _UNARY:
        value = _UNARY[type(node.op)](_safe_node(node.operand))
    else:
        raise ValueError("Expressão contém elemento não permitido.")
    if isinstance(value, complex) or abs(value) > _MAX_ABS:
        raise ValueError("Resultado fora do limite permitido.")
    return value


def calculate_arithmetic(expression: str) -> dict[str, Any]:
    """Calcula somente operações aritméticas explícitas, sem nomes ou chamadas."""
    raw = expression.strip()
    if not raw or len(raw) > _MAX_EXPR:
        raise ValueError("Expressão vazia ou longa demais.")
    try:
        tree = ast.parse(raw, mode="eval")
        result = _safe_node(tree)
    except (SyntaxError, ZeroDivisionError, OverflowError) as exc:
        raise ValueError("Não foi possível calcular a expressão.") from exc
    return {"expression": raw, "result": result, "engine": "nexora-safe-arithmetic-v1"}


def inspect_symbols(text: str) -> dict[str, Any]:
    """Resume classes de caracteres e estruturas, sem descartar o texto original."""
    counts = {
        "letters": 0, "digits": 0, "whitespace": 0,
        "operators": 0, "punctuation": 0, "symbols": 0, "other": 0,
    }
    operators = set("+-*/%=<>!&|^~")
    delimiters = {"(": ")", "[": "]", "{": "}"}
    stack: list[str] = []
    pairs = 0
    mismatches = 0
    for char in text:
        category = unicodedata.category(char)
        if char.isalpha():
            counts["letters"] += 1
        elif char.isdigit():
            counts["digits"] += 1
        elif char.isspace():
            counts["whitespace"] += 1
        elif char in operators:
            counts["operators"] += 1
        elif category.startswith("P"):
            counts["punctuation"] += 1
        elif category.startswith("S"):
            counts["symbols"] += 1
        else:
            counts["other"] += 1

        if char in delimiters:
            stack.append(delimiters[char])
        elif char in ")]}":
            if stack and stack[-1] == char:
                stack.pop()
                pairs += 1
            else:
                mismatches += 1

    return {
        "length_characters": len(text),
        "utf8_bytes": len(text.encode("utf-8")),
        "counts": counts,
        "balanced_delimiter_pairs": pairs,
        "unmatched_open_delimiters": len(stack),
        "unmatched_close_delimiters": mismatches,
        "engine": "nexora-symbolic-inspector-v1",
    }
