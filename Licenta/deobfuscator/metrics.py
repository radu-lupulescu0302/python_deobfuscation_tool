import time
import ast 

class DeobfuscationMetrics:
    def start(self, source):
        self.start_time = time.time()
        self.original_nodes = len(list(ast.walk(ast.parse(source))))

    def end(self, final_tree):
        self.duration = time.time() - self.start_time
        self.final_nodes = len(list(ast.walk(final_tree)))

    def print_report(self):
        print("\n=== Deobfuscation Report ===")
        delta = self.final_nodes - self.original_nodes
        if delta < 0:
            summary = f"reduced by {-delta} nodes (obfuscation added complexity)"
        elif delta > 0:
            summary = f"expanded by {delta} nodes (packed payload is larger than its wrapper)"
        else:
            summary = "unchanged"
        print(f"AST nodes: {self.original_nodes} -> {self.final_nodes}  [{summary}]")
        print(f"Time taken: {self.duration:.2f}s")