import ast
import inspect


tagged = {}


def __check_recursive_yield(func, *args, **kwargs):
    out = func(*args, **kwargs)
    if func in tagged:  # alternatively we could use inspect.isgeneratorfunction but might be too inefficient
        for r in out:
            yield r


def easy_parse(input):
    parsed = ast.parse(input)
    assert isinstance(parsed, ast.Module)
    assert len(parsed.body) == 1
    parsed = parsed.body[0]
    return parsed.value if isinstance(parsed, ast.Expr) else parsed


# noinspection PyPep8Naming
class RecursiveYielder(ast.NodeTransformer):
    def __init__(self):
        self.changed = False

    def visit_FunctionDef(self, node: ast.FunctionDef):
        body = [easy_parse('from musicript.recursiveyielder import __check_recursive_yield')]
        body.extend([self.visit(subnode) for subnode in node.body])
        node.body[:] = body
        node.decorator_list.pop(0)  # if this is the wrong one well good luck lol
        return node

    def visit_Expr(self, node: ast.Expr):
        call = node.value
        if isinstance(call, ast.Call):          # we are only interested in Calls as a single expression
            self.changed = True
            node = easy_parse('for i in __check_recursive_yield(): yield i')
            assert isinstance(node, ast.For)    # For and Expr are interchangeable (both stmt)
            assert isinstance(node.iter, ast.Call)
            call.args = [call.func] + call.args
            call.func = node.iter.func
            node.iter = call
            return node
        else:
            return super().generic_visit(node)


def track_worker(debug=False, transform=True):
    def do_transform(func):
        tag = None
        if transform:
            transformer = RecursiveYielder()
            visited = transformer.visit(ast.parse(inspect.getsource(func)))
            if transformer.changed:
                if debug:
                    import astor
                    print(astor.to_source(visited))
                env = func.__globals__
                name = func.__name__
                compiled = compile(ast.fix_missing_locations(visited), '', 'exec')
                exec(compiled, env)
                func = env[name]
                tag = compiled
        tagged[func] = tag
        return func
    return do_transform


def get_worker_source(func):
    result = tagged.get(func)
    if result is None:
        return inspect.getsource(func)
    return result
