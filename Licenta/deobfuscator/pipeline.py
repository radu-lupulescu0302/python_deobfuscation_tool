import ast
from .static.transformers.encodings import EncodingsTransformer
from .static.transformers.folding import FoldingTransformer
from .static.transformers.imports import ImportsTransformer
from .static.transformers.execution import ExecutionTransformer
from .static.transformers.xor_arithmetic import XorArithmeticTransformer
from .static.transformers.propagation import ConstantPropagationTransformer
from .static.transformers.dead_code import DeadCodeTransformer
from .dynamic.hooks import ExecutionHooks
from .metrics import DeobfuscationMetrics
from .ioc_extractor import IOCExtractor
from .behavior_profiler import BehaviorProfiler
from . import stats as _stats
from config import Config


def _complexity_score(
    technique_counts: dict,
    iterations: int,
    dynamic_resolved: int,
    ioc: IOCExtractor,
) -> int:
    unique      = len(technique_counts)
    ioc_cats    = sum(1 for v in ioc.hits.values() if v)

    pts  = min(unique * 10, 40)            # up to 40 — breadth of techniques
    pts += min((iterations - 1) * 8, 24)  # up to 24 — depth / iteration count
    pts += min(dynamic_resolved * 15, 15) # up to 15 — needed runtime execution
    pts += min(ioc_cats * 5, 21)          # up to 21 — IOC diversity

    return min(pts, 100)


def _complexity_label(score: int) -> str:
    if score <= 20:  return "Low"
    if score <= 40:  return "Moderate"
    if score <= 60:  return "High"
    if score <= 80:  return "Very High"
    return "Extreme"


class HybridDeobfuscator:
    def __init__(self, use_dynamic=True, debug=True):
        self.use_dynamic = use_dynamic
        self.debug = debug
        self.metrics = DeobfuscationMetrics()
        self.hooks = ExecutionHooks()

    def deobfuscate(self, source: str, filename="script.py"):
        _stats.reset()
        self.metrics.start(source)
        tree = ast.parse(source)

        print(f"[+] Starting deobfuscation on {filename}\n")

        transformers = [
            FoldingTransformer,
            EncodingsTransformer,
            XorArithmeticTransformer,
            ConstantPropagationTransformer,
            ImportsTransformer,
            ExecutionTransformer,
            FoldingTransformer,
        ]

        ioc = IOCExtractor()
        iterations_run = 0

        for iteration in range(Config.MAX_STATIC_ITERATIONS):
            start_dump = ast.dump(tree, indent=None)
            print(f"[ITERATION {iteration + 1}]")

            for T in transformers:
                t = T()
                if self.debug:
                    print(f"  -> Running {T.__name__}...")
                before = ast.dump(tree, indent=None)
                tree = t.visit(tree)
                tree = ast.fix_missing_locations(tree)
                if ast.dump(tree, indent=None) != before:
                    print(f"     {T.__name__} made changes")

            ioc.scan(tree)

            if self.debug:
                print(f"  -> Running DeadCodeTransformer...")
            before = ast.dump(tree, indent=None)
            tree = DeadCodeTransformer().visit(tree)
            tree = ast.fix_missing_locations(tree)
            if ast.dump(tree, indent=None) != before:
                print(f"     DeadCodeTransformer made changes")

            iterations_run = iteration + 1
            if ast.dump(tree, indent=None) == start_dump:
                print(f"\n[+] Static phase stabilized after {iterations_run} iterations")
                break

        print(f"\n[+] Static phase finished. Nodes: {len(list(ast.walk(tree)))}")

        # ==================== DYNAMIC PHASE ====================
        dynamic_resolved = 0
        if self.use_dynamic:
            print("\n[+] Starting Dynamic Phase...")
            sites = self.hooks.find_execution_sites(tree)
            print(f"    Found {len(sites)} exec/eval sites")

            for i, site in enumerate(sites):
                print(f"  [{i+1}/{len(sites)}] Processing exec at line {site['lineno']}")
                result = self.hooks.process_site(site, tree)

                if result.get("success"):
                    tree = self._replace_node(tree, site["node"], result["new_node"])
                    tree = ast.fix_missing_locations(tree)
                    dynamic_resolved += 1
                    print(f"     Replaced exec with recovered payload!")

        ioc.scan(tree)

        final_code = ast.unparse(tree)
        self.metrics.end(tree)
        self.ioc = ioc

        counts = _stats.get_counts()
        self._print_technique_summary(counts)

        score = _complexity_score(counts, iterations_run, dynamic_resolved, ioc)
        print(f"\nObfuscation Complexity Score: {score}/100  [{_complexity_label(score)}]")

        ioc.print_report()

        profiler = BehaviorProfiler()
        profiler.print_report(profiler.profile(ioc, counts))

        return final_code

    def _print_technique_summary(self, counts: dict):
        if not counts:
            return
        print("\n=== Obfuscation Techniques Detected ===")
        for technique, count in sorted(counts.items(), key=lambda x: -x[1]):
            conf = _stats.get_confidence(technique)
            conf_str = f"  [confidence: {conf}%]" if conf is not None else ""
            print(f"  {technique:<35} x{count}{conf_str}")

    def _replace_node(self, tree, old_node, new_node):
        class NodeReplacer(ast.NodeTransformer):
            def visit(self, node):
                if node is old_node:
                    return new_node
                return self.generic_visit(node)
        return NodeReplacer().visit(tree)
