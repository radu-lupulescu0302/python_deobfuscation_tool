import ast
import io
import contextlib


def run_expr(transformer_cls, src: str) -> str:
    """Parse src as an expression, run transformer, return unparsed result."""
    tree = ast.parse(src, mode="eval")
    result = transformer_cls().visit(tree)
    ast.fix_missing_locations(result)
    return ast.unparse(result)


def run_stmt(transformer_cls, src: str) -> str:
    """Parse src as a module, run transformer, return unparsed result."""
    tree = ast.parse(src)
    result = transformer_cls().visit(tree)
    ast.fix_missing_locations(result)
    return ast.unparse(result)


def silent(fn):
    """Suppress stdout from fn() — keeps test output clean."""
    buf = io.StringIO()
    with contextlib.redirect_stdout(buf):
        return fn()
