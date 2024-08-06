import os
from typing import List, Dict, Optional
from tree_sitter import Node
from tree_sitter_languages import get_parser
import ast

class FunctionInfo:
    def __init__(self, name: str, file_path: str, start_line: int, end_line: int, parent: Optional[str] = None):
        self.name = f"{parent}.{name}" if parent else name
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.code = ""
        self.doc = ""

class ClassInfo:
    def __init__(self, name: str, file_path: str, start_line: int, end_line: int):
        self.name = name
        self.file_path = file_path
        self.start_line = start_line
        self.end_line = end_line
        self.methods: List[str] = []
        self.code = ""
        self.doc = ""

class FunctionTable:
    def __init__(self):
        self.functions: Dict[str, List[FunctionInfo]] = {}

    def add_function(self, func_info: FunctionInfo):
        if func_info.name not in self.functions:
            self.functions[func_info.name] = []
        self.functions[func_info.name].append(func_info)

    def get_function(self, name: str) -> List[FunctionInfo]:
        return self.functions.get(name, [])

class ClassTable:
    def __init__(self):
        self.classes: Dict[str, List[ClassInfo]] = {}

    def add_class(self, class_info: ClassInfo):
        if class_info.name not in self.classes:
            self.classes[class_info.name] = []
        self.classes[class_info.name].append(class_info)

    def get_class(self, name: str) -> List[ClassInfo]:
        return self.classes.get(name, [])

class CodebaseIndexer:
    def __init__(self, root_path: str):
        self.root_path = root_path
        self.function_table = FunctionTable()
        self.class_table = ClassTable()
        self.parser = get_parser('python')

    def index_codebase(self):
        for root, _, files in os.walk(self.root_path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self._index_file(file_path)

    def _index_file(self, file_path: str):
        with open(file_path, 'r') as file:
            content = file.read()
            tree = self.parser.parse(content.encode())
            ast_tree = ast.parse(content)
        self._traverse_tree(tree.root_node, file_path, content, ast_tree)

    def _traverse_tree(self, node: Node, file_path: str, content: str, ast_tree: ast.AST, parent: Optional[str] = None):
        if node.type == 'function_definition':
            func_name = node.child_by_field_name('name').text.decode('utf-8')
            full_name = f"{parent}.{func_name}" if parent else func_name
            func_info = FunctionInfo(
                name=full_name,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1
            )
            func_info.code = content[node.start_byte:node.end_byte]
            
            # Extract docstring
            for item in ast.walk(ast_tree):
                if isinstance(item, ast.FunctionDef) and item.name == func_name:
                    func_info.doc = ast.get_docstring(item) or ""
                    break
            
            self.function_table.add_function(func_info)
            
            # If this function is a method of a class, add it to the class's method list
            if parent and parent in self.class_table.classes:
                for class_info in self.class_table.classes[parent]:
                    if class_info.file_path == file_path:
                        class_info.methods.append(full_name)
            
            # Traverse for nested functions
            for child in node.children:
                if child.type == 'block':
                    self._traverse_tree(child, file_path, content, ast_tree, parent=full_name)

        elif node.type == 'class_definition':
            class_name = node.child_by_field_name('name').text.decode('utf-8')
            class_info = ClassInfo(
                name=class_name,
                file_path=file_path,
                start_line=node.start_point[0] + 1,
                end_line=node.end_point[0] + 1
            )
            class_info.code = content[node.start_byte:node.end_byte]
            
            # Extract docstring
            for item in ast.walk(ast_tree):
                if isinstance(item, ast.ClassDef) and item.name == class_name:
                    class_info.doc = ast.get_docstring(item) or ""
                    break
            
            self.class_table.add_class(class_info)
            
            # Traverse for methods
            for child in node.children:
                if child.type == 'block':
                    self._traverse_tree(child, file_path, content, ast_tree, parent=class_name)

        else:
            for child in node.children:
                self._traverse_tree(child, file_path, content, ast_tree, parent)

    def get_function_info(self, function_name: str) -> List[Dict]:
        function_infos = self.function_table.get_function(function_name)
        return [
            {
                "location": {
                    "file_path": info.file_path,
                    "start_line": info.start_line,
                    "end_line": info.end_line
                },
                "code": info.code,
                "type": "function",
                "doc": info.doc,
                "name": info.name
            }
            for info in function_infos
        ]

    def get_class_info(self, class_name: str) -> List[Dict]:
        class_infos = self.class_table.get_class(class_name)
        return [
            {
                "location": {
                    "file_path": info.file_path,
                    "start_line": info.start_line,
                    "end_line": info.end_line
                },
                "code": info.code,
                "type": "class",
                "doc": info.doc,
                "methods": info.methods
            }
            for info in class_infos
        ]

# Usage example:
if __name__ == "__main__":
    indexer = CodebaseIndexer("/Users/arnav/Desktop/django/django/django/")
    indexer.index_codebase()

    # Get info about a function or method using full name
    function_infos = indexer.get_function_info("MultiPartParser._parse")
    for info in function_infos:
        print(f"Function/Method: {info['name']}")
        print(f"Location: {info['location']['file_path']}:{info['location']['start_line']}-{info['location']['end_line']}")
        print(f"Code:\n{info['code']}")
        print(f"Docstring: {info['doc']}")
        print()

    # Get info about a class
    class_infos = indexer.get_class_info("MultiPartParser")
    for info in class_infos:
        print(f"Class: {info['location']['file_path']}:{info['location']['start_line']}-{info['location']['end_line']}")
        print(f"Code:\n{info['code']}")
        print(f"Docstring: {info['doc']}")
        print(f"Methods: {', '.join(info['methods'])}")
        print()
        