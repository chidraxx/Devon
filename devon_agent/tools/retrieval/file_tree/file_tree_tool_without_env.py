import os
import pathspec
import xml.etree.ElementTree as ET

import yaml
from devon_agent.semantic_search.constants import (extension_to_language, json_config_files,
    supported_noncode_extensions)


class FileTreeTool:
    def __init__(self, root_dir, ignore_dir=[]):
        self.root_dir = os.path.abspath(os.path.normpath(root_dir))
        # self.ignore_dir = set(os.path.abspath(os.path.normpath(d)) for d in ignore_dir)
        self.file_tree = {}
        self.ignore_specs = self.load_gitignore_specs(self.root_dir)

    def load_gitignore_specs(self, root_path):
        ignore_specs = []
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
            if '.gitignore' in filenames:
                gitignore_path = os.path.join(dirpath, '.gitignore')
                with open(gitignore_path, 'r') as gitignore_file:
                    spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore_file)
                    ignore_specs.append((dirpath, spec))
            
            # Don't traverse into ignored directories
            dirnames[:] = [d for d in dirnames if not self.is_ignored(os.path.join(dirpath, d), ignore_specs)]

        # Sort ignore_specs so that root comes first, then by path length (descending)
        ignore_specs.sort(key=lambda x: (x[0] != root_path, -len(x[0])))
        return ignore_specs

    def is_ignored(self, path, ignore_specs=None):
        if ignore_specs is None:
            ignore_specs = self.ignore_specs

        path = os.path.abspath(path)
        
        for spec_path, spec in ignore_specs:
            if path.startswith(spec_path):
                # Get the path relative to the .gitignore file
                relative_path = os.path.relpath(path, spec_path)
                if spec.match_file(relative_path):
                    return True
                
        if os.path.isfile(path):
            file_extension = os.path.splitext(path)[1].lower()
            file_name = os.path.basename(path)

            # Check if the file should be processed based on its extension
            if not (file_extension in extension_to_language or 
                    (file_extension != '.json' and file_extension in supported_noncode_extensions) or 
                    (file_extension == '.json' and file_name in json_config_files)):
                return True 
        
        return False

    def get_tree_json(self, start_path=None):
        try:
            self.ignore_specs = self.load_gitignore_specs(self.root_dir)
            self.file_tree = self.get_file_tree_json(self.root_dir)

            if start_path is None:
                start_path = self.root_dir

            abs_start_path = os.path.abspath(os.path.normpath(start_path))
            if not os.path.exists(abs_start_path):
                return f"Error: The directory {abs_start_path} does not exist."

            self.file_tree = self.get_file_tree_json(abs_start_path)
            return self.file_tree

        except Exception as e:
            return f"Error generating file tree for {start_path}: {str(e)}"

    def get_current_tree_if_count_less_than(self, start_path, max_count):
        try:
            abs_start_path = os.path.abspath(os.path.normpath(start_path))
            if not os.path.exists(abs_start_path):
                return f"Error: The directory {abs_start_path} does not exist."
            self.file_tree = self.get_file_tree_json(abs_start_path)
            if self.file_tree["file_count"] <= max_count:
                return self.json_to_yaml(self.file_tree, self.root_dir)
            else:
                return "The directory is too big to be represented in a file tree."
        except Exception as e:
            return f"Error generating file tree for {start_path}: {str(e)}"

    def get_large_tree(self, start_path, max_count, min_count):
        try:
            self.get_tree_json(start_path)

            if self.file_tree["file_count"] < max_count * 2:
                return [], self.json_to_yaml(self.file_tree, self.root_dir)

            paths, tree = self.get_directories_with_file_count_less_than(
                self.file_tree, max_count, min_count
            )

            tree_str = (
                "The directory was too big to be displayed completely, children of some dir have been retracted. To view them use the tool on their path"
                + self.json_to_yaml(tree, self.root_dir)
            )

            return paths, tree_str
            # print(paths)
            # print(codebase.json_to_yaml(tree, codebase.root_dir))

        except Exception as e:
            return f"Error generating file tree for {start_path}: {str(e)}"
        

    
    def get_file_tree_json(self, start_path):
        # Helper function to create a node in the directory structure
        def create_node(name, node_type, abs_path, rel_path):
            if node_type == "file":
                return {
                    "name": name,
                    "type": node_type,
                    "path": abs_path,
                }
            else:
                return {
                    "name": name,
                    "type": node_type,
                    "path": abs_path,
                    "file_count": 0,
                    "children": [],
                }

        # Recursive function to build the directory structure
        def build_structure(current_path, rel_path):
            current_node = create_node(
                os.path.basename(current_path), "directory", current_path, rel_path
            )
            try:
                dir_entries = os.listdir(current_path)
            except PermissionError:
                return current_node
            except Exception as e:
                raise RuntimeError(
                    f"Error listing directory entries for {current_path}: {str(e)}"
                )

            file_count = 0
            for entry in sorted(dir_entries):
                entry_abs_path = os.path.join(current_path, entry)
                entry_rel_path = os.path.join(rel_path, entry)
                if (
                    entry.startswith(".") and os.path.isdir(entry_abs_path)
                ) or self.is_ignored(entry_abs_path):
                    continue
                if os.path.isdir(entry_abs_path):
                    child_node = build_structure(
                        entry_abs_path, entry_rel_path
                    )
                    current_node["children"].append(child_node)
                    file_count += (
                        child_node["file_count"] + 1
                    )  # Count the directory itself
                else:
                    file_node = create_node(
                        entry, "file", entry_abs_path, entry_rel_path
                    )
                    current_node["children"].append(file_node)
                    file_count += 1
            current_node["file_count"] = file_count
            return current_node

        start_path = os.path.abspath(os.path.normpath(start_path))

        # Check if the start_path is a directory
        if not os.path.isdir(start_path):
            raise NotADirectoryError(f"The path {start_path} is not a directory")

        # Normalize paths to ensure consistency
        start_path = os.path.normpath(start_path)

        # Build the directory structure recursively
        root_structure = build_structure(start_path, "")

        return root_structure

    @staticmethod
    def get_directories_with_file_count_less_than(file_tree, max_count, min_count):
        def has_code_files(node):
            code_extensions = {
                ".py",
                ".cpp",
                ".c",
                ".java",
                ".js",
                ".ts",
                ".rb",
                ".go",
                ".rs",
            }
            return any(node["name"].endswith(ext) for ext in code_extensions)

        def should_remove_directory(node):
            if node["type"] != "directory":
                return False

            subdirs = [
                child
                for child in node.get("children", [])
                if child["type"] == "directory"
            ]
            if len(subdirs) <= 20:
                return False

            file_count_less_than_8 = sum(
                1 for child in subdirs if child["file_count"] < 8
            )
            if file_count_less_than_8 / len(subdirs) < 0.9:
                return False

            return not any(has_code_files(child) for child in node.get("children", []))

        def filter_tree(node):
            if should_remove_directory(node):
                return False
            node["children"] = [
                child for child in node.get("children", []) if filter_tree(child)
            ]
            return True

        def traverse_and_collect(node, result, new_tree_parent):
            if node["type"] == "directory" and (
                min_count < node.get("file_count", 0) < max_count
            ):
                # print(node.get('file_count', 0))
                result.append(node["path"])
                new_node = {
                    "name": node["name"]
                    + f": [The directory is too large to display. Path - {node['path']} ]",
                    "type": node["type"],
                    "path": node["path"],
                    "children": [],
                }
                new_tree_parent["children"].append(new_node)
                # Do not traverse children of this node
                return

            new_node = {
                "name": node["name"],
                "type": node["type"],
                "path": node["path"],
                "children": [],
            }
            for child in node.get("children", []):
                traverse_and_collect(child, result, new_node)
            if new_node["type"] == "directory" and new_node["children"]:
                new_tree_parent["children"].append(new_node)
                new_node["children"].extend(
                    child
                    for child in node.get("children", [])
                    if child["type"] == "file"
                )

        try:
            # Filter the tree first to remove directories that meet the new condition
            filtered_tree = {
                "name": file_tree["name"],
                "type": file_tree["type"],
                "path": file_tree["path"],
                "children": [
                    child
                    for child in file_tree.get("children", [])
                    if filter_tree(child)
                ],
            }

            # Now apply the original logic to find directories with file count in the specified range
            result = []
            new_tree_root = {
                "name": filtered_tree["name"],
                "type": filtered_tree["type"],
                "path": filtered_tree["path"],
                "children": [],
            }
            traverse_and_collect(filtered_tree, result, new_tree_root)
            return result, new_tree_root
        except Exception as e:
            raise RuntimeError(f"Error filtering directories: {str(e)}")

    @staticmethod
    def json_to_xml(json_data):
        try:
            # Helper function to recursively build the XML tree
            def build_xml_tree(node, parent_element):
                element = ET.SubElement(
                    parent_element,
                    node["type"],
                    {"name": node["name"], "path": node["path"]},
                )
                for child_node in node.get("children", []):
                    build_xml_tree(child_node, element)

            # Convert JSON data to XML
            root_node = json_data
            xml_root = ET.Element("root")
            build_xml_tree(root_node, xml_root)

            xml_string = ET.tostring(xml_root, encoding="unicode")
            return xml_string
        except Exception as e:
            return f"Error converting JSON to XML: {str(e)}"

    @staticmethod
    def json_to_yaml(json_data, root_dir) -> str:
        try:

            def convert_node(node):
                if node["type"] == "file":
                    return node["name"]
                elif node["type"] == "directory":
                    children = [convert_node(child) for child in node["children"]]
                    return {node["name"]: children}

            # Convert JSON data to nested dictionary
            yaml_data = convert_node(json_data)

            # Convert nested dictionary to YAML string
            yaml_string = (
                f"relative directory path from project root: {os.path.relpath(json_data['path'], start=root_dir)}"
                + "\n"
                + yaml.dump(yaml_data, default_flow_style=False)
            )
            return yaml_string
        except Exception as e:
            return f"Error converting JSON to YAML: {str(e)}"
        

if __name__ == "__main__":
    result_list, result_tree = FileTreeTool("/Users/arnav/Desktop/devon/Devon").get_large_tree(
                None, 500, 20
            )
    print(result_tree)


# Example usage:
# codebase = FileTreeTool('/Users/arnav/Desktop/django/')
# print(codebase.get_large_tree("/Users/arnav/Desktop/django/", 500, 15)[1])

# # codebase = FileTreeTool('/Users/arnav/Desktop/django/django')
# # print(codebase.get_current_tree("/Users/arnav/Desktop/django/django"))

# paths, tree = codebase.get_large_tree(codebase.file_tree, 200, 15)
# print(tree)

# print(FileTreeTool.json_to_yaml(codebase.file_tree, codebase.root_dir))
# # print(FileTreeTool.json_to_yaml(tree, codebase.root_dir))
