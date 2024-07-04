
import hashlib
import json
import os
import tiktoken
import uuid
import pickle

import networkx as nx
from devon_agent.semantic_search.graph_construction.utils import format_nodes

from devon_agent.semantic_search.graph_construction.languages.python.python_parser import PythonParser
from devon_agent.semantic_search.graph_construction.languages.javascript.javascript_parser import JavaScriptParser
from devon_agent.semantic_search.graph_construction.languages.typescript.typescript_parser import TypeScriptParser
from devon_agent.semantic_search.graph_construction.languages.java.java_parser import JavaParser
from devon_agent.semantic_search.graph_construction.languages.cpp.cpp_parser import CPPParser
from devon_agent.semantic_search.graph_construction.languages.go.go_parser import GoParser
from devon_agent.semantic_search.graph_construction.core.base_parser import BaseParser
from devon_agent.semantic_search.constants import extension_to_language
from devon_agent.semantic_search.constants import supported_noncode_extentions

# Import other parsers as needed, e.g., JavaScriptParser, etc.

class GraphConstructor:
    def __init__(self, root_path, graph_storage_path, update, ignore_dirs=None):
        # self.language = language
        self.root_path = root_path
        self.graph_storage_path = graph_storage_path
        self.graph_path = os.path.join(self.graph_storage_path, f"graph.pickle")
        self.hash_path = os.path.join(self.graph_storage_path, f"hashes.json")
        self.ignore_dirs = ignore_dirs if ignore_dirs else []

        self.supported_extentions = ['.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.cpp', '.cxx', '.cc', '.hpp', '.h', '.go']
        self.supported_noncode_extentions = supported_noncode_extentions
        self.parser : BaseParser = None

        # # Choose the appropriate parser based on the language
        # if language == "python":
        #     self.parser = PythonParser()
        # # Add more language parsers as needed
        # else:
        #     raise ValueError(f"Language {language} is not supported.")

        if not os.path.exists(graph_storage_path):
            os.makedirs(graph_storage_path)

        if not (update and os.path.exists(self.graph_path) and os.path.exists(self.hash_path)):
            print("creating new graphs and hashes")
            self.graph = nx.DiGraph()
            self.hashes = {}

        else:
            print("loading existing graphs and hashes")
            self.load_graph(self.graph_path)
            self.hashes = self.load_hashes(self.hash_path)
            print("Number of nodes in graph", len(self.graph.nodes))


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
        with open(graph_path, 'rb') as f:
            self.graph = pickle.load(f)

    def load_hashes(self, hash_path):
        if os.path.exists(hash_path):
            with open(hash_path, 'r') as f:
                return json.load(f)
        return {}

    def save_graph(self, graph_path):
        with open(graph_path, 'wb') as f:
            pickle.dump(self.graph, f)

    def save_hashes(self, hash_path, hashes):
        self.hashes = hashes
        with open(hash_path, 'w') as f:
            json.dump(hashes, f)


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

        def read_gitignore(path):
            gitignore_path = os.path.join(path, ".gitignore")
            if os.path.exists(gitignore_path):
                with open(gitignore_path, "r") as gitignore_file:
                    for line in gitignore_file:
                        line = line.strip()
                        if line and not line.startswith("#"):
                            if line.startswith("/"):
                                normalized_path = os.path.normpath(line[1:])
                                absolute_path = os.path.abspath(os.path.join(path, normalized_path))
                            else:
                                normalized_path = os.path.normpath(line)
                                absolute_path = os.path.abspath(os.path.join(path, normalized_path))
                            ignored_paths.add(absolute_path)

        def traverse_directory(dir_path, parent_node_id):
            read_gitignore(dir_path)
            
            # Get the children of the current directory node in the graph
            children_in_graph = {
                os.path.normpath(self.graph.nodes[child]['path']): child
                for child in list(self.graph.successors(parent_node_id))
                if 'path' in self.graph.nodes[child]
            }

            dirs, files = [], []
            
            for entry in os.scandir(dir_path):
                abs_path = os.path.abspath(entry.path)
                if abs_path in ignored_paths or entry.name.startswith("."):
                    continue
                
                if entry.is_dir() and entry.name not in self.ignore_dirs:
                    dirs.append(entry.path)
                elif entry.is_file():
                    # Check file extension before processing
                    file_extension = os.path.splitext(entry.name)[len(os.path.splitext(entry.name)) - 1]

                    if file_extension in self.supported_extentions:
                        with open(entry.path, 'r') as f:
                            content = f.read()
                            char_count = len(content)
                            
                            if char_count <= 350000:
                                files.append(entry.path)
                       
                    elif file_extension in self.supported_noncode_extentions:
                        with open(entry.path, 'r') as f:
                            content = f.read()
                            char_count = len(content)
                            
                            if char_count <= 70000:
                                files.append(entry.path)
            
            # Process directories
            for sub_dir in dirs:
                # print(sub_dir)

                if sub_dir not in children_in_graph.keys():
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
                    if not os.path.isdir(child_path):
                        self.delete_file_or_dir(node_id, actions)
                    else:
                        actions["delete"].append((child_path, parent_node_id))
                    

        root_node_id = self.graph.graph.get('root_id')
        # children_in_graph = {
        #     self.graph.nodes[child]['path']: child
        #     for child in list(self.graph.successors(root_node_id))
        #     if 'path' in self.graph.nodes[child]
        # }
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

    def build_or_update_graph(self):
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
        file_extension = os.path.splitext(file_path)[len(os.path.splitext(file_path)) - 1]
        try:
            if file_extension in self.supported_noncode_extentions:
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

            self.parser = GraphConstructor.parser_matcher(file_extension)
            print(file_path)
            nodes, relationships = self.parser.parse_file(file_path, self.root_path, {}, {}, level=0)

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