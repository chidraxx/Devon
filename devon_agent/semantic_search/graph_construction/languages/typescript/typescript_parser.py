from devon_agent.semantic_search.graph_construction.core.base_parser import BaseParser
class TypeScriptParser(BaseParser):
    extensions = [".ts", ".tsx"]

    def __init__(self):
        super().__init__("typescript", "*")

    def parse_file(
        self,
        file_path: str,
        root_path: str,
        visited_nodes: dict,
        global_imports: dict,
        level: int,
        extension: str = None,
    ):
        if extension == ".tsx":
            self.language = "tsx"
        return self.parse(file_path, root_path, visited_nodes, global_imports, level)