from devon_agent.semantic_search.graph_construction.core.base_parser import BaseParser

class JavaParser(BaseParser):
    extensions = [".java"]

    def __init__(self):
        super().__init__("java", "*")

    def parse_file(
        self,
        file_path: str,
        root_path: str,
        visited_nodes: dict,
        global_imports: dict,
        level: int,
    ):
        return self.parse(file_path, root_path, visited_nodes, global_imports, level)
