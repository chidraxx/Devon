
import hashlib
import json
import os
import tiktoken
from typing import List, Tuple, Dict
import uuid
import pickle
import pathspec
from devon_agent.tools.utils import (cwd_normalize_path, file_exists, read_binary_file, read_file,
    write_binary_file, write_file, write_file_tool)

import networkx as nx
from devon_agent.semantic_search.graph_construction.utils import format_nodes

from devon_agent.semantic_search.graph_construction.languages.python.python_parser import PythonParser
from devon_agent.semantic_search.graph_construction.languages.javascript.javascript_parser import JavaScriptParser
from devon_agent.semantic_search.graph_construction.languages.typescript.typescript_parser import TypeScriptParser
from devon_agent.semantic_search.graph_construction.languages.java.java_parser import JavaParser
from devon_agent.semantic_search.graph_construction.languages.cpp.cpp_parser import CPPParser
from devon_agent.semantic_search.graph_construction.languages.go.go_parser import GoParser
from devon_agent.semantic_search.graph_construction.core.base_parser import BaseParser
from devon_agent.semantic_search.constants import extension_to_language, json_config_files
from devon_agent.semantic_search.constants import supported_noncode_extensions
from devon_agent.tools.utils import cwd_normalize_path, file_exists, make_abs_path
from devon_agent.tool import ToolContext

    
class GraphConstructor:
    def __init__(self, ctx: ToolContext, root_path: str, graph_storage_path: str, update: bool, ignore_dirs: List[str] = None):
        self.ctx = ctx
        self.root_path = self.normalize_path(root_path)
        self.graph_storage_path = self.normalize_path(graph_storage_path)
        self.graph_path = self.normalize_path(os.path.join(self.graph_storage_path, "graph.pickle"))
        self.hash_path = self.normalize_path(os.path.join(self.graph_storage_path, "hashes.json"))
        self.ignore_dirs = [self.normalize_path(d) for d in (ignore_dirs or [])]
        self.ignore_specs = self.load_gitignore_specs(self.root_path)

        self.supported_extensions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.cxx', '.cc', '.hpp', '.h', '.go']
        self.supported_noncode_extensions = supported_noncode_extensions  # Assuming this is defined elsewhere

        self.parser = None  # Initialize parser as needed

        if not self.directory_exists(self.graph_storage_path):
            self.ctx["environment"].execute(f"mkdir -p {self.graph_storage_path}")

        if not (update and self.file_exists(self.graph_path) and self.file_exists(self.hash_path)):
            print("Creating new graphs and hashes")
            self.graph = nx.DiGraph()
            self.hashes = {}
        else:
            print("Loading existing graphs and hashes")
            self.load_graph(self.graph_path)
            self.hashes = self.load_hashes(self.hash_path)
            print("Number of nodes in graph", len(self.graph.nodes))

    def normalize_path(self, path: str) -> str:
        return cwd_normalize_path(self.ctx, path)

    def file_exists(self, path: str) -> bool:
        return file_exists(self.ctx, path)

    def directory_exists(self, path: str) -> bool:
        out, rc = self.ctx["environment"].execute(f"test -d {path}")
        return rc == 0

    def load_gitignore_specs(self, root_path: str) -> List[Tuple[str, pathspec.PathSpec]]:
        ignore_specs = []
        for dirpath, dirnames, filenames in self.walk(root_path):
            if '.gitignore' in filenames:
                gitignore_path = os.path.join(dirpath, '.gitignore')
                content, _ = self.ctx["environment"].execute(f"cat {gitignore_path}")
                spec = pathspec.PathSpec.from_lines('gitwildmatch', content.splitlines())
                ignore_specs.append((dirpath, spec))
            
            # Don't traverse into ignored directories
            dirnames[:] = [d for d in dirnames if not self.is_ignored(os.path.join(dirpath, d), ignore_specs)]

        # Sort ignore_specs so that root comes first, then by path length (descending)
        ignore_specs.sort(key=lambda x: (x[0] != root_path, -len(x[0])))
        return ignore_specs

    def is_ignored(self, path: str, ignore_specs: List[Tuple[str, pathspec.PathSpec]] = None) -> bool:
        if ignore_specs is None:
            ignore_specs = self.ignore_specs

        path = make_abs_path(self.ctx, path)
        
        for spec_path, spec in ignore_specs:
            if path.startswith(spec_path):
                # Get the path relative to the .gitignore file
                relative_path = os.path.relpath(path, spec_path)
                if spec.match_file(relative_path):
                    return True
        
        return False

    def walk(self, top: str):
        try:
            names, _ = self.ctx["environment"].execute(f"ls -1A {top}")
            names = names.splitlines()
        except Exception as e:
            return

        dirs, nondirs = [], []
        for name in names:
            full_path = os.path.join(top, name)
            if self.directory_exists(full_path):
                dirs.append(name)
            else:
                nondirs.append(name)

        yield top, dirs, nondirs

        for name in dirs:
            new_path = os.path.join(top, name)
            yield from self.walk(new_path)



    @staticmethod
    def count_tokens(text: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        num_tokens = len(encoding.encode(text))
        return num_tokens

    @staticmethod
    def parser_matcher(extension: str) -> BaseParser:
        if extension in PythonParser.extensions:
            return PythonParser()
        elif extension in JavaScriptParser.extensions:
            return JavaScriptParser()
        elif extension in TypeScriptParser.extensions:
            return TypeScriptParser()
        elif extension in JavaParser.extensions:
            return JavaParser()
        elif extension in CPPParser.extensions:
            return CPPParser()
        elif extension in GoParser.extensions:
            return GoParser()
        else:
            raise ValueError(f"Unsupported file extension: {extension}")
        


    def load_graph(self, graph_path):
        try:
            binary_content = read_binary_file(self.ctx, graph_path)
            self.graph = pickle.loads(binary_content)
        except Exception as e:
            self.ctx["config"].logger.error(f"Failed to load graph from {graph_path}. Error: {str(e)}")
            raise

    def load_hashes(self, hash_path):
        try:
            if file_exists(self.ctx, hash_path):
                content = read_file(self.ctx, hash_path)
                return json.loads(content)
            return {}
        except Exception as e:
            self.ctx["config"].logger.error(f"Failed to load hashes from {hash_path}. Error: {str(e)}")
            raise

    def save_graph(self, graph_path):
        try:
            binary_content = pickle.dumps(self.graph)
            write_binary_file(self.ctx, graph_path, binary_content)
        except Exception as e:
            self.ctx["config"].logger.error(f"Failed to save graph to {graph_path}. Error: {str(e)}")
            raise

    def save_hashes(self, hash_path, hashes):
        try:
            self.hashes = hashes
            json_content = json.dumps(hashes)
            write_file_tool(self.ctx, hash_path, json_content)
        except Exception as e:
            self.ctx["config"].logger.error(f"Failed to save hashes to {hash_path}. Error: {str(e)}")
            raise


    def compute_file_hash(self, file_path):
        hasher = hashlib.sha256()
        with open(file_path, 'rb') as f:
            buf = f.read()
            hasher.update(buf)
        return hasher.hexdigest()
    
    def detect_changes(self):
        current_hashes = {}
        actions = {"add": [], "update": [], "delete": []}
        stored_hashes = self.hashes
        ignored_paths = set()
        visited_nodes = set()

        def traverse_directory(dir_path, parent_node_id):
            # Get the children of the current directory node in the graph
            children_in_graph = {
                self.normalize_path(self.graph.nodes[child]['path']): child
                for child in list(self.graph.successors(parent_node_id))
                if 'path' in self.graph.nodes[child]
            }

            dirs, files = [], []
            
            ls_output, _ = self.ctx["environment"].execute(f"ls -1a {dir_path}")
            entries = ls_output.splitlines()

            for entry in entries:
                abs_path = self.normalize_path(os.path.join(dir_path, entry))

                if self.is_ignored(abs_path) or entry.startswith("."):
                    continue
                
                if self.directory_exists(abs_path) and entry not in self.ignore_dirs:
                    dirs.append(abs_path)
                elif self.file_exists(abs_path):
                    file_extension = os.path.splitext(entry)[1]

                    if file_extension in self.supported_extensions:
                        content, _ = self.ctx["environment"].execute(f"cat {abs_path}")
                        char_count = len(content)
                        
                        if char_count <= 350000:
                            files.append(abs_path)
                    
                    elif file_extension in self.supported_noncode_extensions:
                        content, _ = self.ctx["environment"].execute(f"cat {abs_path}")
                        char_count = len(content)
                        
                        if char_count <= 70000:
                            files.append(abs_path)
            
            # Process directories
            for sub_dir in dirs:
                if sub_dir not in children_in_graph:
                    # Create the directory node if it doesn't exist in the graph
                    sub_dir_node_id = self.create_dir(sub_dir, parent_node_id)
                    visited_nodes.add(sub_dir_node_id)
                    traverse_directory(sub_dir, sub_dir_node_id)
                else:
                    # Traverse the existing directory node
                    sub_dir_node_id = children_in_graph[sub_dir]
                    visited_nodes.add(sub_dir_node_id)
                    traverse_directory(sub_dir, sub_dir_node_id)
            
            # Process files
            for file_path in files:
                if file_path in ignored_paths:
                    continue

                current_hashes[file_path] = self.compute_file_hash(file_path)

                if file_path not in stored_hashes:
                    actions["add"].append((file_path, parent_node_id))
                elif stored_hashes[file_path] != current_hashes[file_path]:
                    actions["update"].append((file_path, parent_node_id))
                
                if file_path in children_in_graph:
                    visited_nodes.add(children_in_graph[file_path])
            
            # Handle deletions
            for child_path, node_id in children_in_graph.items():
                if child_path not in current_hashes and node_id not in visited_nodes:
                    if not self.directory_exists(child_path):
                        self.delete_file_or_dir(node_id, actions)
                    else:
                        actions["delete"].append((child_path, parent_node_id))

        root_node_id = self.graph.graph.get('root_id')

        # Find or create the root directory node
        if root_node_id is None:
            for node_id, data in self.graph.nodes(data=True):
                if data.get("path") == self.root_path and data.get("type") == "directory":
                    root_node_id = node_id
                    break
        if root_node_id is None:
            root_node_id = self.create_dir(self.root_path, None)

        self.graph.graph['root_id'] = root_node_id
        
        traverse_directory(self.root_path, root_node_id)
        return actions, current_hashes

    def delete_file_or_dir(self, node_id, actions = None):
        if (self.graph.nodes[node_id]["type"] == "file"):
            if actions is not None:
                actions["delete"].append((self.graph.nodes[node_id]["path"], node_id))
        elif (self.graph.nodes[node_id]["type"] == "directory"):
            pass
        children = list(self.graph.successors(node_id))
        for child in children:
            self.delete_file_or_dir(child, actions)
        self.graph.remove_node(node_id)

    def create_dir(self, path, parent_node_id):
        print("creating dir", path)
        
        directory_node = format_nodes.format_directory_node(path, False, 0)  # Adjust level as needed
        directory_node_id = directory_node["attributes"]["node_id"]
        self.graph.add_node(directory_node_id, **directory_node["attributes"])


        if parent_node_id is not None:
            self.graph.add_edge(parent_node_id, directory_node_id, type="CONTAINS")

        # if parent_node_id == self.graph.graph.get('root_id'):

        #     children_in_graph = {
        #         self.graph.nodes[child]['path']: child
        #         for child in list(self.graph.successors(parent_node_id))
        #         if 'path' in self.graph.nodes[child]
        #     }

        return directory_node_id

    def build_or_update_graph(self, ctx : ToolContext):
        self.ctx = ctx
        self.ignore_specs = self.load_gitignore_specs(self.root_path)
        actions, current_hashes = self.detect_changes()
        
        for file in actions["add"]:
            self.process_file(file, action="add")
        for file in actions["update"]:
            self.process_file(file, action="update")
        for file in actions["delete"]:
            self.process_file(file, action="delete")
        

        return actions, current_hashes  # Return the actions list

    def process_file(self, parent_id_and_file_path, action):
        if action == "update":
            self.remove_file_from_graph(parent_id_and_file_path)
            success = self.parse_file_and_update_graph(parent_id_and_file_path)
            # if success:
                  # Ensure old nodes are removed before adding new ones
            # self.delete_file_or_dir()
            
        elif action == "add":
            self.parse_file_and_update_graph(parent_id_and_file_path)
        elif action == "delete":
            # self.remove_file_from_graph(file_path)
            pass

    def parse_file_and_update_graph(self, parent_id_and_file_path):
        parent_id = parent_id_and_file_path[1]
        file_path = parent_id_and_file_path[0]
        file_name = os.path.basename(file_path)
        file_extension = os.path.splitext(file_path)[len(os.path.splitext(file_path)) - 1]
        try:
            if (file_extension == ".json" and file_name in json_config_files) or (file_extension != ".json" and file_extension in self.supported_noncode_extensions):
                # return
                node= {}
                node["file_path"] = file_path
                node["path"] = file_path
                node["level"] = self.graph.nodes[parent_id].get("level", 0) + 1
                node["leaf"] = True
                node['type'] = "file"
                node['lang'] = "no_code"
                node['node_id'] = self.node_id = str(uuid.uuid4())

                with open(file_path, 'r') as f:
                    node["text"] = f.read()

                self.graph.add_node(node["node_id"], **node)
                self.graph.add_edge(parent_id, node["node_id"], type="CONTAINS")
                return True
            else:
                self.parser = GraphConstructor.parser_matcher(file_extension)
                print(file_path)
                nodes, relationships = self.parser.parse_file(file_path, self.root_path, {}, {}, level=0, extension = file_extension)

        except Exception as e:
            print(e, file_path)
            # raise e
            return False

        if len(nodes) == 0:
            return
        
        for node in nodes:
            
            node["attributes"]['path'] = file_path
            node["attributes"]['type'] = node["type"]

            if extension_to_language.get(file_extension) is None:
                raise Exception(f"extention '{(file_extension)}' is not supported: {file_path}")
            
            node["attributes"]['lang'] = extension_to_language.get(file_extension)
            self.graph.add_node(node["attributes"]["node_id"], **node["attributes"])
        
        for relationship in relationships:
            self.graph.add_edge(relationship["sourceId"], relationship["targetId"], type=relationship["type"])
        
        self.graph.add_edge(parent_id, nodes[0]["attributes"]["node_id"], type="CONTAINS")
        return True

    def remove_file_from_graph(self, parent_id_and_file_path):
        parent_node_id = parent_id_and_file_path[1]
        file_path = parent_id_and_file_path[0]
        
        # Get the file node using the parent_node_id
        node_id_to_remove = None
        for child in self.graph.successors(parent_node_id):
            if self.graph.nodes[child].get("path") == file_path:
                node_id_to_remove = child
                break
        
        if node_id_to_remove is not None:
            self.delete_file_or_dir(node_id_to_remove, None)
        else:
            print("Node to remove not found for path:", file_path)