from abc import ABC, abstractmethod
from pathlib import Path
from devon_agent.semantic_search.graph_construction.utils import format_nodes, tree_parser
import tree_sitter
from typing import List, Dict, Tuple
from devon_agent.semantic_search.graph_construction.core.tree_sitter_parser import CodeHierarchyNodeParser, BaseNode, NodeRelationship, TextNode
from devon_agent.semantic_search.constants import RELATIONS_TYPES_MAP


class BaseParser(ABC):
    RELATIONS_TYPES_MAP = RELATIONS_TYPES_MAP

    def __init__(
        self,
        language: str,
        wildcard: str,
    ):
        self.language = language
        self.wildcard = wildcard

    def parse(
        self,
        file_path: str,
        root_path: str,
        visited_nodes: dict,
        global_imports: dict,
        level: int,
    ) -> Tuple[List[Dict], List[Dict]]:
        path = Path(file_path)
        if not path.exists():
            print(f"File {file_path} does not exist.")
            raise FileNotFoundError

        # Read the file content
        with open(file_path, 'r', encoding='utf-8') as file:
            file_content = file.read()

        # Create a simple document structure
        # documents = SimpleDirectoryReader(
        #     input_files=[path],
        #     file_metadata=lambda x: {"filepath": x},
        # ).load_data()

        document = TextNode(
        text=tree_parser.remove_non_ascii(file_content),
        metadata={"filepath": str(path)}
        )

        # Bug related to llama-index it's safer to remove non-ascii characters. Could be removed in the future
        document.text = tree_parser.remove_non_ascii(document.text)

        code = CodeHierarchyNodeParser(
            language=self.language,
            # chunk_min_characters=3,
            chunk_min_characters=3,
            # skeleton=False,
            code_splitter=None
            # code_splitter=None
        )

        try:
            split_nodes = code.get_nodes_from_documents([document])


        except TimeoutError:
            print(f"Timeout error: {file_path}")
            return [], [], {}

        node_list = []
        edges_list = []
        assignment_dict = {}

        # print("=====")

        file_node, file_relations = self.__process_node__(
            split_nodes.pop(0), file_path, "", visited_nodes, global_imports, assignment_dict, document, level
        )
        node_list.append(file_node)
        edges_list.extend(file_relations)

        for node in split_nodes:
            processed_node, relationships = self.__process_node__(
                node,
                file_path,
                file_node["attributes"]["node_id"],
                visited_nodes,
                global_imports,
                assignment_dict,
                document,
                level,
            )

            node_list.append(processed_node)
            edges_list.extend(relationships)

        return node_list, edges_list

    def __process_node__(
        self,
        node: BaseNode,
        file_path: str,
        file_node_id: str,
        visited_nodes: dict,
        global_imports: dict,
        assignment_dict: dict,
        document: TextNode,  # Changed from Dict to TextNode
        level: int,
    ) -> Tuple[Dict, List[Dict]]:
        no_extension_path = self._remove_extensions(file_path)
        relationships = []
        scope = node.metadata["inclusive_scopes"][-1] if node.metadata["inclusive_scopes"] else None
        type_node = scope["type"] if scope else "file"
        parent_level = level
        leaf = False

        if type_node == "function_definition":
            processed_node = format_nodes.format_function_node(node, scope, [], file_node_id)
        elif type_node == "class_definition":
            processed_node = format_nodes.format_class_node(node, scope, file_node_id, "")
        elif type_node == "interface_declaration":
            processed_node = format_nodes.format_interface_node(node, scope, file_node_id)
        elif type_node == "file":
            processed_node = format_nodes.format_file_node(node, file_path, [])
        else:
            processed_node = format_nodes.get_signature(node, scope, [], file_node_id)

        for relation in node.relationships.items():
            if relation[0] == NodeRelationship.CHILD:
                if len(relation[1]) == 0:
                    leaf = True
                for child in relation[1]:
                    relation_type = (
                        child.metadata["inclusive_scopes"][-1]["type"] if child.metadata["inclusive_scopes"] else ""
                    )
                    relationships.append(
                        {
                            "sourceId": node.node_id,
                            "targetId": child.node_id,
                            "type": self.RELATIONS_TYPES_MAP.get(relation_type, "UNKNOWN"),
                        }
                    )
            elif relation[0] == NodeRelationship.PARENT:
                if relation[1]:
                    parent_path = (
                        visited_nodes.get(relation[1].node_id, {}).get("path", no_extension_path).replace("/", ".")
                    )
                    parent_level = visited_nodes.get(relation[1].node_id, {}).get("level", level)

                    node_path = f"{parent_path}.{processed_node['attributes']['name']}"
                else:
                    node_path = no_extension_path.replace("/", ".")

        start_line, end_line = self.get_start_and_end_line_from_byte(
            document.text, node.metadata["start_byte"], node.metadata["end_byte"]
        )
        processed_node["attributes"]["start_line"] = start_line
        processed_node["attributes"]["end_line"] = end_line
        processed_node["attributes"]["path"] = node_path
        processed_node["attributes"]["file_path"] = file_path
        processed_node["attributes"]["level"] = parent_level + 1
        processed_node["attributes"]["leaf"] = leaf

        processed_node["type"] = type_node

        global_imports[node_path] = {
            "id": processed_node["attributes"]["node_id"],
            "type": processed_node["type"],
        }
        visited_nodes[node.node_id] = {"path": node_path, "level": parent_level + 1}
        return processed_node, relationships    
    
    def _get_imports(self, path: str, file_node_id: str, root_path: str) -> dict:
        parser = tree_sitter.get_parser(self.language)
        with open(path, "r") as file:
            code = file.read()
        tree = parser.parse(bytes(code, "utf-8"))

        imports = {"_*wildcard*_": {"path": [], "alias": "", "type": "wildcard"}}
        for node in tree.root_node.children:
            # From Statement Case
            if node.type == "import_from_statement":
                import_statements = node.named_children

                from_statement = import_statements[0]
                from_text = from_statement.text.decode()
                for import_statement in import_statements[1:]:
                    if import_statement.text.decode() == self.wildcard:
                        imports["_*wildcard*_"]["path"].append(self.resolve_import_path(from_text, path, root_path))
                    imports[import_statement.text.decode()] = {
                        "path": self.resolve_import_path(from_text, path, root_path),
                        "alias": "",
                        "type": "import_from_statement",
                    }
            # Direct Import Case
            elif node.type == "import_statement":
                import_statement = node.named_children[0]
                from_text = import_statement.text.decode()

                if import_statement.type == "aliased_import":
                    # If the import statement is aliased
                    from_statement, _, alias = import_statement.children
                    from_text = from_statement.text.decode()
                    imports[alias.text.decode()] = {
                        "path": self.resolve_import_path(from_text, path, root_path),
                        "alias": alias.text.decode(),
                        "type": "aliased_import",
                    }
                else:
                    # If it's a simple import statement
                    imports[import_statement.text.decode()] = {
                        "path": self.resolve_import_path(from_text, path, root_path),
                        "alias": "",
                        "type": "import_statement",
                    }
        return {file_node_id: imports}
    
    def get_start_and_end_line_from_byte(self, file_contents, start_byte, end_byte):
        start_line = file_contents.count("\n", 0, start_byte) + 1
        end_line = file_contents.count("\n", 0, end_byte) + 1

        return start_line, end_line
    
    def _remove_extensions(self, file_path):
        no_extension_path = str(file_path)
        for extension in self.extensions:
            no_extension_path = no_extension_path.replace(extension, "")
        return no_extension_path

    # @abstractmethod
    # def resolve_import_path(self, from_text: str, path: str, root_path: str):
    #     pass

    # @abstractmethod
    # def _remove_extensions(self, path: str) -> str:
    #     """
    #     Remove file extensions from the given path.
    #     This method is used in __process_node__ and should be implemented by subclasses.
    #     """
    #     pass

    # @abstractmethod
    # def is_package(self, directory: str) -> bool:
    #     pass

    # @abstractmethod
    # def skip_directory(self, directory: str) -> bool:
    #     pass
