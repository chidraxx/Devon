import ast
import os
import sys
from tree_sitter_languages import get_parser
from tree_sitter import Node
from typing import List, Optional, Tuple, Dict


def extract_imports(node: Node, source_code: bytes) -> list:
    imports = []
    
    if node.type == 'import_statement':
        for child in node.children:
            if child.type == 'dotted_name':
                import_name = source_code[child.start_byte:child.end_byte].decode('utf8')
                alias = None
                # Check for alias
                if child.next_sibling and child.next_sibling.type == 'identifier':
                    alias = source_code[child.next_sibling.start_byte:child.next_sibling.end_byte].decode('utf8')
                imports.append(('import', import_name, alias))
    elif node.type == 'import_from_statement':
        module = next((child for child in node.children if child.type == 'dotted_name'), None)
        if module:
            module_name = source_code[module.start_byte:module.end_byte].decode('utf8')
        else:
            # Handle relative imports
            module_name = '.' * len([c for c in node.children if c.type == '.'])
        for child in node.children:
            if child.type == 'dotted_name' and child != module:
                name = source_code[child.start_byte:child.end_byte].decode('utf8')
                alias = None
                # Check for alias
                if child.next_sibling and child.next_sibling.type == 'identifier':
                    alias = source_code[child.next_sibling.start_byte:child.next_sibling.end_byte].decode('utf8')
                imports.append(('from', module_name, name, alias))
            elif child.type == 'aliased_import':
                name = next(c for c in child.children if c.type == 'dotted_name')
                name_str = source_code[name.start_byte:name.end_byte].decode('utf8')
                alias = next(c for c in child.children if c.type == 'identifier')
                alias_str = source_code[alias.start_byte:alias.end_byte].decode('utf8')
                imports.append(('from', module_name, name_str, alias_str))
    
    for child in node.children:
        imports.extend(extract_imports(child, source_code))
    
    return imports


def is_library_path(path: str, project_root: str) -> bool:
    return (path.startswith(sys.prefix) or
            '/site-packages/' in path or
            '/.venv/' in path or
            not path.startswith(project_root))

def resolve_import_path(import_info: Tuple, current_file: str, root_path: str) -> Tuple[Optional[str], str, bool, Optional[int]]:
    import_type, *parts = import_info
    project_root = root_path
    
    if import_type == 'import':
        module_name, alias = parts
        path = find_module_file(module_name, current_file)
        is_module = True
        line_number = None
    elif import_type == 'from':
        module_name, item_name, alias = parts
        module_path = find_module_file(module_name, current_file)
        path, line_number = find_item_in_module(module_path, item_name) if module_path else (None, None)
        is_module = path != module_path if path else False
    else:
        return None, "unknown", False, None

    if path:
        category = "library" if is_library_path(path, project_root) else "in_codebase"
    else:
        category = "unknown"
    
    return path, category, is_module, line_number


def find_module_file(module_name: str, current_file: str) -> Optional[str]:
    if module_name.startswith('.'):
        return resolve_relative_import(module_name, current_file)
    
    module_parts = module_name.split('.')
    for path in sys.path:
        full_path = os.path.join(path, *module_parts)
        if os.path.isfile(full_path + '.py'):
            return full_path + '.py'
        if os.path.isdir(full_path) and os.path.isfile(os.path.join(full_path, '__init__.py')):
            return os.path.join(full_path, '__init__.py')
    
    # If not found in sys.path, try relative to the current file's directory
    current_dir = os.path.dirname(current_file)
    full_path = os.path.join(current_dir, *module_parts)
    if os.path.isfile(full_path + '.py'):
        return full_path + '.py'
    if os.path.isdir(full_path) and os.path.isfile(os.path.join(full_path, '__init__.py')):
        return os.path.join(full_path, '__init__.py')
    
    return None


def find_declaration_line(file_path: str, item_name: str) -> Optional[int]:
    try:
        with open(file_path, 'r') as file:
            tree = ast.parse(file.read(), filename=file_path)
            
        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.ClassDef, ast.AsyncFunctionDef)) and node.name == item_name:
                return node.lineno
            elif isinstance(node, ast.Assign):
                for target in node.targets:
                    if isinstance(target, ast.Name) and target.id == item_name:
                        return node.lineno
        
        return None
    except Exception as e:
        print(f"Error parsing {file_path}: {e}")
        return None

def find_item_in_module(module_path: str, item_name: str) -> Tuple[Optional[str], Optional[int]]:
    if module_path and os.path.isfile(module_path):
        # Check if the item is defined in the module file
        line_number = find_declaration_line(module_path, item_name)
        if line_number:
            return module_path, line_number
    
    # If not found in the module file, check for a submodule
    dir_path = os.path.dirname(module_path)
    item_path = os.path.join(dir_path, f"{item_name}.py")
    if os.path.isfile(item_path):
        return item_path, None  # For submodules, we don't specify a line number
    
    # If it's neither a function/class in the module nor a submodule, return the module path
    return module_path, None

def resolve_relative_import(module_name: str, current_file: str) -> Optional[str]:
    current_dir = os.path.dirname(current_file)
    level = 0
    while module_name.startswith('.'):
        level += 1
        module_name = module_name[1:]
    
    for _ in range(level):
        current_dir = os.path.dirname(current_dir)
    
    if module_name:
        return find_module_file(module_name, os.path.join(current_dir, '__init__.py'))
    else:
        return os.path.join(current_dir, '__init__.py')

def process_file_imports(file_path: str, root_path: str) -> List[Dict]:
    parser = get_parser('python')
    
    with open(file_path, 'rb') as file:
        source_code = file.read()
    
    tree = parser.parse(source_code)
    imports = extract_imports(tree.root_node, source_code)
    
    file_imports = []
    
    for imp in imports:
        resolved_path, category, is_module, line_number = resolve_import_path(imp, file_path, root_path)
        
        import_info = {
            'type': category,
            'alias': imp[-1],  # Last element is always the alias (None if no alias)
            'import_type': imp[0],
            'module_name': imp[1],
            'resolved_path': resolved_path,
            'is_module_import': is_module,
            'declaration_line': line_number
        }
        
        if imp[0] == 'from':
            import_info['item_name'] = imp[2]
        
        file_imports.append(import_info)
    
    return file_imports

def analyze_imports(directory: str, root_path: str) -> Dict[str, List[Dict]]:
    all_imports = {}
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                file_imports = process_file_imports(file_path, root_path)
                all_imports[file_path] = file_imports
    
    return all_imports

def main(directory: str, root_path: str):
    import_analysis = analyze_imports(directory, root_path)
    
    for file_path, imports in import_analysis.items():
        print(f"File: {file_path}")
        for imp in imports:
            print(imp)
        #     print(f"  Import Type: {imp['import_type']}")
        #     print(f"  Module Name: {imp['module_name']}")
        #     if 'item_name' in imp:
        #         print(f"  Item Name: {imp['item_name']}")
        #     print(f"  Resolved Path: {imp['resolved_path']}")
        #     print(f"  Type: {imp['type']}")
        #     print(f"  Alias: {imp['alias']}")
        #     print(f"  Is Module Import: {imp['is_module_import']}")
        #     print(f"  Declaration Line: {imp['declaration_line']}")
        #     print()
        # print()

if __name__ == "__main__":
    main("/Users/arnav/Desktop/devon/Devon/devon_agent/semantic_search/graph_construction/", "/Users/arnav/Desktop/devon/Devon/")
