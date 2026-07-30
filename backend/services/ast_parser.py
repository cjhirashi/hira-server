"""Genera diagramas Mermaid flowchart TD desde código Python usando ast stdlib."""
import ast
from typing import Optional

_MAX_STMTS = 30


def generate_mermaid_flowchart(code: str, script_name: str) -> str:
    """Parsea código Python y retorna un string flowchart TD Mermaid."""
    if not code or not code.strip():
        return f'flowchart TD\n    START(["{_safe(script_name)}"])\n    END(["⏹ Fin"])\n    START --> END'

    try:
        tree = ast.parse(code)
    except SyntaxError as exc:
        return (
            f'flowchart TD\n'
            f'    ERR["⚠ Error de sintaxis: {_safe(str(exc))}"]\n'
        )

    builder = _FlowchartBuilder(script_name)
    builder.visit_stmts(tree.body)
    return builder.build()


def _safe(text: str) -> str:
    return text.replace('"', "'").replace('\n', ' ')[:80]


class _FlowchartBuilder:
    def __init__(self, script_name: str) -> None:
        self._name = script_name
        self._nodes: list[str] = []   # node definitions
        self._edges: list[str] = []   # edge definitions
        self._counter = 0
        self._prev: Optional[str] = None
        self._start = "START"
        self._end = "END"

    def _new_id(self) -> str:
        self._counter += 1
        return f"N{self._counter}"

    def _add_node(self, node_id: str, shape: str) -> None:
        self._nodes.append(f"    {shape}")
        if self._prev is not None:
            self._edges.append(f"    {self._prev} --> {node_id}")
        self._prev = node_id

    def _rect(self, node_id: str, label: str) -> str:
        return f'{node_id}["{_safe(label)}"]'

    def _diamond(self, node_id: str, label: str) -> str:
        return f'{node_id}{{"{_safe(label)}"}}'

    def visit_stmts(self, stmts: list) -> None:
        truncated = stmts[:_MAX_STMTS]
        for stmt in truncated:
            self._visit(stmt)
        if len(stmts) > _MAX_STMTS:
            nid = self._new_id()
            extra = len(stmts) - _MAX_STMTS
            self._add_node(nid, self._rect(nid, f"... ({extra} statements más)"))

    def _visit(self, node: ast.AST) -> None:
        if isinstance(node, ast.Expr) and isinstance(node.value, ast.Call):
            self._visit_call(node.value)
        elif isinstance(node, ast.Assign):
            label = self._stmt_label(node)
            nid = self._new_id()
            self._add_node(nid, self._rect(nid, label))
        elif isinstance(node, (ast.If,)):
            self._visit_if(node)
        elif isinstance(node, (ast.For, ast.While)):
            self._visit_loop(node)
        elif isinstance(node, ast.FunctionDef):
            nid = self._new_id()
            self._add_node(nid, self._rect(nid, f"def {node.name}()"))
        elif isinstance(node, ast.Return):
            nid = self._new_id()
            label = "return " + (ast.unparse(node.value) if node.value else "")
            self._add_node(nid, self._rect(nid, label))
        else:
            label = self._stmt_label(node)
            if label:
                nid = self._new_id()
                self._add_node(nid, self._rect(nid, label))

    def _visit_call(self, call: ast.Call) -> None:
        label = ast.unparse(call)
        nid = self._new_id()
        self._add_node(nid, self._rect(nid, label))

    def _visit_if(self, node: ast.If) -> None:
        cond_id = self._new_id()
        cond_label = ast.unparse(node.test)
        self._nodes.append(f"    {self._diamond(cond_id, cond_label)}")
        if self._prev is not None:
            self._edges.append(f"    {self._prev} --> {cond_id}")

        # True branch
        merge_id = self._new_id()  # reserve merge node id
        self._prev = cond_id
        true_entry = None
        if node.body:
            first_id = self._new_id()
            first_label = self._stmt_label(node.body[0])
            self._nodes.append(f"    {self._rect(first_id, first_label)}")
            self._edges.append(f"    {cond_id} -- Sí --> {first_id}")
            self._prev = first_id
            true_entry = first_id
            for s in node.body[1:]:
                self._visit(s)
        true_last = self._prev

        # False branch
        self._prev = cond_id
        false_last = cond_id
        if node.orelse:
            first_else_id = self._new_id()
            first_else_label = self._stmt_label(node.orelse[0])
            self._nodes.append(f"    {self._rect(first_else_id, first_else_label)}")
            self._edges.append(f"    {cond_id} -- No --> {first_else_id}")
            self._prev = first_else_id
            for s in node.orelse[1:]:
                self._visit(s)
            false_last = self._prev
        else:
            self._edges.append(f"    {cond_id} -- No --> MERGE_{merge_id}")

        # Merge
        merge_node = f"MERGE_{merge_id}"
        self._nodes.append(f"    {merge_node}(( ))")
        if true_last and true_last != cond_id:
            self._edges.append(f"    {true_last} --> {merge_node}")
        if false_last and false_last != cond_id:
            self._edges.append(f"    {false_last} --> {merge_node}")
        self._prev = merge_node

    def _visit_loop(self, node: ast.For | ast.While) -> None:
        nid = self._new_id()
        if isinstance(node, ast.For):
            cond = f"for {ast.unparse(node.target)} in {ast.unparse(node.iter)}"
        else:
            cond = f"while {ast.unparse(node.test)}"
        self._nodes.append(f"    {self._diamond(nid, cond)}")
        if self._prev is not None:
            self._edges.append(f"    {self._prev} --> {nid}")
        # Loop body (first stmt only for brevity)
        if node.body:
            body_id = self._new_id()
            body_label = self._stmt_label(node.body[0])
            self._nodes.append(f"    {self._rect(body_id, body_label)}")
            self._edges.append(f"    {nid} -- Sí --> {body_id}")
            self._edges.append(f"    {body_id} --> {nid}")
        self._edges.append(f"    {nid} -- No --> EXIT_{nid}(( ))")
        self._prev = f"EXIT_{nid}"

    def _stmt_label(self, node: ast.AST) -> str:
        try:
            return ast.unparse(node)
        except Exception:
            return type(node).__name__

    def build(self) -> str:
        lines = ["flowchart TD"]
        lines.append(f'    {self._start}(["▶ {_safe(self._name)}"])')
        lines.extend(self._nodes)
        lines.append(f'    {self._end}(["⏹ Fin"])')

        # First edge: START to first node
        all_edges = list(self._edges)
        node_ids_defined = set()
        for n in self._nodes:
            # extract id from node definition (first token)
            tok = n.strip().split('[')[0].split('{')[0].split('(')[0]
            node_ids_defined.add(tok)

        if node_ids_defined:
            first_id = self._nodes[0].strip().split('[')[0].split('{')[0].split('(')[0]
            all_edges.insert(0, f"    {self._start} --> {first_id}")

        # Last edge: last prev to END
        if self._prev and self._prev != self._start:
            all_edges.append(f"    {self._prev} --> {self._end}")
        else:
            all_edges.append(f"    {self._start} --> {self._end}")

        lines.extend(all_edges)
        return "\n".join(lines)
