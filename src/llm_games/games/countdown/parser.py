"""Validate bare arithmetic expressions with a restricted AST; never execute code."""
import ast

from .rules import ValidationResult, puzzle_key, tiles_available


def validate_expression(expression: str, numbers, target: int) -> ValidationResult:
    """Check syntax, tile multiplicity, positive intermediates, and exact division.

    Input is a bare expression (no ``Expression:`` prefix). Invalid expressions
    return a result; invalid puzzle definitions raise ValueError.
    """
    tiles, _ = puzzle_key(numbers, target)
    used: list[int] = []

    def visit(node: ast.AST) -> int:
        if isinstance(node, ast.Constant) and type(node.value) is int:
            used.append(node.value)
            if not tiles_available(used, tiles):
                raise ValueError("Expression uses unavailable tiles")
            return node.value
        if not isinstance(node, ast.BinOp) or type(node.op) not in (
            ast.Add, ast.Sub, ast.Mult, ast.Div
        ):
            raise ValueError("Only integer tiles and +, -, *, / are allowed")
        left, right = visit(node.left), visit(node.right)
        if isinstance(node.op, ast.Add):
            value = left + right
        elif isinstance(node.op, ast.Sub):
            value = left - right
        elif isinstance(node.op, ast.Mult):
            value = left * right
        else:
            if right == 0 or left % right:
                raise ValueError("Division must be exact with a nonzero divisor")
            value = left // right
        if value <= 0:
            raise ValueError("Every intermediate value must be a positive integer")
        return value

    try:
        if not isinstance(expression, str) or not expression.strip():
            raise ValueError("Expected a nonempty expression")
        if len(expression) > 4096:
            raise ValueError("Expression is too long")
        tree = ast.parse(expression.strip(), mode="eval")
        # A legal expression has one leaf per used tile and one fewer operation.
        if sum(1 for _ in ast.walk(tree)) > 4 * len(tiles):
            raise ValueError("Expression is too complex for the available tiles")
        value = visit(tree.body)
        return ValidationResult(True, value == target, value, used_tiles=tuple(used))
    except (SyntaxError, ValueError, RecursionError) as exc:
        return ValidationResult(False, False, error=str(exc), used_tiles=tuple(used))
