"""
Plugin: calculator
Safely evaluates basic math expressions.
"""
import ast
import operator

SAFE_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
}


def _eval(node):
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.BinOp):
        op = SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {node.op}")
        return op(_eval(node.left), _eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = SAFE_OPS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unsupported operator: {node.op}")
        return op(_eval(node.operand))
    raise ValueError(f"Unsupported expression: {node}")


@mcp.tool()
def calculate(expression: str) -> str:
    """Evaluate a mathematical expression and return the result. E.g. '2 + 2', '10 / 3', '2 ** 8'."""
    try:
        tree = ast.parse(expression, mode="eval")
        result = _eval(tree.body)
        return str(result)
    except Exception as e:
        return f"Error: {e}"
