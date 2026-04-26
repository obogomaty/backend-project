import re

from sympy import Eq, diff, integrate, solve, sympify, symbols

_MATH_WORDS = re.compile(
    r"\b(sqrt|sin|cos|tan|log|ln|exp|pi|abs|factorial|integrate|differentiate|diff)\b",
    re.IGNORECASE,
)


def looks_like_structured_math(text: str) -> bool:
    """
    True only when the string plausibly contains a SymPy expression.
    Prevents sympify() from treating plain English as a single Symbol (e.g. "hello" -> hello).
    """
    t = text.strip()
    if not t:
        return False

    lower = t.lower()
    if lower.startswith(("solve", "differentiate", "integrate")):
        return True

    if any(ch.isdigit() for ch in t):
        return True

    if any(op in t for op in "+-*/^"):
        return True

    if "=" in t:
        return True

    if _MATH_WORDS.search(t):
        return True

    return False


def safe_math(input_text: str):
    try:
        text = input_text.strip()
        lower = text.lower()

        if lower.startswith("solve"):
            expr = lower.replace("solve", "", 1).strip()
            if not expr:
                return "Error: solve requires an expression"
            if "=" not in expr:
                return "Error: solve requires an equation with ="
            left, right = expr.split("=", 1)
            x = symbols("x")
            equation = Eq(sympify(left), sympify(right))
            return solve(equation, x)

        if lower.startswith("differentiate"):
            expr = lower.replace("differentiate", "", 1).strip()
            if not expr:
                return "Error: differentiate requires an expression"
            x = symbols("x")
            return diff(sympify(expr), x)

        if lower.startswith("integrate"):
            expr = lower.replace("integrate", "", 1).strip()
            if not expr:
                return "Error: integrate requires an expression"
            x = symbols("x")
            return integrate(sympify(expr), x)

        if not looks_like_structured_math(text):
            return "Error: not a structured math expression"

        return sympify(lower)

    except Exception as e:
        return f"Error: {str(e)}"
