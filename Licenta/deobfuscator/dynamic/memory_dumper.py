class MemoryDumper:
    def extract(self, namespace: dict):
        return {k: v for k, v in namespace.items() 
                if not k.startswith("__") and isinstance(v, (str, bytes, int, list, dict))}