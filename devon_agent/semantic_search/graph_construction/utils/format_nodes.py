import os
import uuid
from devon_agent.semantic_search.graph_construction.core.tree_sitter_parser import BaseNode



def format_function_node(node: BaseNode, scope: dict, function_calls: list[str], file_node_id: str) -> dict:
    name = scope["name"]
    signature = scope["signature"].strip()

    processed_node = {
        "type": "FUNCTION",
        "attributes": {
            "name": name,
            "signature": signature,
            "text": node.text.strip(),
            "node_id": node.node_id,
            "function_calls": function_calls,
            "file_node_id": file_node_id,
        },
    }

    return processed_node


def get_signature(node: BaseNode, scope: dict, function_calls: list[str], file_node_id: str) -> dict:
    name = scope["name"]
    signature = scope["signature"].strip()

    processed_node = {
        "attributes": {
            "name": name,
            "signature": signature,
            "text": node.text.strip(),
            "node_id": node.node_id,
            "function_calls": function_calls,
            "file_node_id": file_node_id,
        },
    }


    return processed_node

def format_class_node(node: BaseNode, scope: dict, file_node_id: str, inheritances: list[str]) -> dict:
    name = scope["name"]
    signature = scope["signature"].strip()

    processed_node = {
        "type": "CLASS",
        "attributes": {
            "name": name,
            "signature": signature,
            "text": node.text.strip(),
            "node_id": node.node_id,
            "file_node_id": file_node_id,
            "inheritances": inheritances,
        },
    }

    return processed_node

def format_interface_node(node: BaseNode, scope: dict, file_node_id: str) -> dict:
    name = scope["name"]
    signature = scope["signature"].strip()

    processed_node = {
        "type": "CLASS",
        "attributes": {
            "name": name,
            "signature": signature,
            "text": node.text.strip(),
            "node_id": node.node_id,
            "file_node_id": file_node_id,
        },
    }

    return processed_node


def format_file_node(node: BaseNode, no_extension_path: str, function_calls: list[str]) -> dict:
    processed_node = {
        "type": "FILE",
        "attributes": {
            "text": node.text.strip(),
            "node_id": node.node_id,
            "function_calls": function_calls,
            "name": os.path.basename(no_extension_path),
        },
    }

    return processed_node



def format_directory_node(path: str, package: bool, level: int) -> dict:
    processed_node = {
        "attributes": {
            "path": path,
            "file_path": path,
            "name": os.path.basename(path),
            "node_id": str(uuid.uuid4()),
            "level": level,
            "type": "directory" if package else "directory",
        },
        
    }

    return processed_node
