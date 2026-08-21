"""The `when` expression language, which is intentionally almost nothing."""

from __future__ import annotations

import pytest

from skillforge.errors import ExprError
from skillforge.expr import evaluate, references

PARAMS = {"langs": ["python", "go"], "framework": "react", "strict": True, "count": 2}


@pytest.mark.parametrize(
    ("source", "expected"),
    [
        ("params.strict", True),
        ("not params.strict", False),
        ('params.framework == "react"', True),
        ('params.framework != "react"', False),
        ('"python" in params.langs', True),
        ('"rust" in params.langs', False),
        ('params.strict and "go" in params.langs', True),
        ('params.strict and "rust" in params.langs', False),
        ('params.strict or "rust" in params.langs', True),
        ('(params.framework == "vue") or params.strict', True),
        ("params.count == 2", True),
        ("not (params.count == 3)", True),
    ],
)
def test_evaluation(source, expected):
    assert evaluate(source, PARAMS) is expected


@pytest.mark.parametrize(
    "source",
    [
        "params.missing",
        "os.environ",
        "params",
        "params.a.b",
        "1 +",
        '"unterminated',
        "__import__('os')",
    ],
)
def test_invalid_expressions_raise(source):
    with pytest.raises(ExprError):
        evaluate(source, PARAMS)


def test_references_lists_params_without_evaluating():
    assert references('params.strict and "x" in params.langs') == {"strict", "langs"}
