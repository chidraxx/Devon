from collections import defaultdict
from enum import Enum
from tree_sitter import Node
from typing import Any, Dict, List, Optional, Sequence, Tuple
import uuid



# Custom implementations or mock classes to replace llama_index imports

class CallbackManager:
    def __init__(self, *args):
        pass

class BaseExtractor:
    pass

class NodeParser:
    def __init__(self, *args, **kwargs):
        pass

class BaseNode:
    def __init__(self, text='', metadata=None, relationships=None):
        self.text = text
        self.metadata = metadata or {}
        self.relationships = relationships or {}

class NodeRelationship:
    CHILD = 'CHILD'
    PARENT = 'PARENT'
    SOURCE = 'SOURCE'

class TextNode(BaseNode):
    def __init__(self, text='', metadata=None, relationships=None, parent_node=None):
        super().__init__(text, metadata, relationships)
        self.node_id = str(uuid.uuid4())
        self.parent_node = parent_node
        self.relationships = relationships or {
            NodeRelationship.CHILD: [],
            NodeRelationship.PARENT: None,
        }

    def as_related_node_info(self):
        return self

class CodeSplitter:
    def get_nodes_from_documents(self, *args, **kwargs):
        return []

def get_tqdm_iterable(iterable, show_progress, description):
    return iterable

class _SignatureCaptureType:
    def __init__(self, type: str, inclusive: bool):
        self.type = type
        self.inclusive = inclusive
class _SignatureCaptureOptions:
    def __init__(self, start_signature_types: Optional[List[_SignatureCaptureType]] = None, 
                 end_signature_types: Optional[List[_SignatureCaptureType]] = None, 
                 name_identifier: str = ""):
        self.start_signature_types = start_signature_types
        self.end_signature_types = end_signature_types
        self.name_identifier = name_identifier


"""
Maps language -> Node Type -> SignatureCaptureOptions

The best way for a developer to discover these is to put a breakpoint at the TIP
tag in _chunk_node, and then create a unit test for some code, and then iterate
through the code discovering the node names.
"""
_DEFAULT_SIGNATURE_IDENTIFIERS: Dict[str, Dict[str, _SignatureCaptureOptions]] = {
    "python": {
        "function_definition": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="block", inclusive=False)],
            name_identifier="identifier",
        ),
        "class_definition": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="block", inclusive=False)],
            name_identifier="identifier",
        ),
    },
    "html": {
        "element": _SignatureCaptureOptions(
            start_signature_types=[_SignatureCaptureType(type="<", inclusive=True)],
            end_signature_types=[_SignatureCaptureType(type=">", inclusive=True)],
            name_identifier="tag_name",
        )
    },
    "cpp": {
        "class_specifier": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "function_definition": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="function_declarator",
        ),
        "struct_specifier": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "enum_specifier": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "namespace_definition": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "template_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "union_specifier": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "concept_definition": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
    },
    "typescript": {
        "interface_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "lexical_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "function_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "class_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "method_definition": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="property_identifier",
        ),
    },

    "javascript": {
        "function_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "arrow_function": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="=>", inclusive=True)],
            name_identifier="identifier",
        ),
        "method_definition": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="property_identifier",
        ),
        "class_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "variable_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type=";", inclusive=True)],
            name_identifier="variable_declarator",
        ),
        "lexical_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type=";", inclusive=True)],
            name_identifier="variable_declarator",
        ),
        "object": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="}", inclusive=False)],
            name_identifier="identifier",
        ),
        "export_statement": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type=";", inclusive=True)],
            name_identifier="identifier",
        ),
    },

    "java": {
        "class_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "method_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "interface_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "constructor_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "enum_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "annotation_type_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "record_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
    },

    "go": {
        "type_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="type_identifier",
        ),
        "function_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="identifier",
        ),
        "method_declaration": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="{", inclusive=False)],
            name_identifier="field_identifier",
        ),
        "struct_type": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="}", inclusive=False)],
            name_identifier="field_declaration_list",
        ),
        "interface_type": _SignatureCaptureOptions(
            end_signature_types=[_SignatureCaptureType(type="}", inclusive=False)],
            name_identifier="method_spec",
        ),
    },

}


class _ScopeMethod(Enum):
    INDENTATION = "INDENTATION"
    BRACKETS = "BRACKETS"
    HTML_END_TAGS = "HTML_END_TAGS"


class _CommentOptions():
    comment_template: str
    scope_method: _ScopeMethod

    def __init__(self, comment_template, scope_method) -> None:
        self.comment_template = comment_template
        self.scope_method = scope_method
        pass


_COMMENT_OPTIONS: Dict[str, _CommentOptions] = {
    "cpp": _CommentOptions(
        comment_template="// {}", scope_method=_ScopeMethod.BRACKETS
    ),
    "html": _CommentOptions(
        comment_template="<!-- {} -->", scope_method=_ScopeMethod.HTML_END_TAGS
    ),
    "python": _CommentOptions(
        comment_template="# {}", scope_method=_ScopeMethod.INDENTATION
    ),
    "typescript": _CommentOptions(
        comment_template="// {}", scope_method=_ScopeMethod.BRACKETS
    ),
    "javascript": _CommentOptions(
        comment_template="// {}", scope_method=_ScopeMethod.BRACKETS
    ),
    "java": _CommentOptions(
        comment_template="// {}", scope_method=_ScopeMethod.BRACKETS
    ),
    "go": _CommentOptions(
        comment_template="// {}", scope_method=_ScopeMethod.BRACKETS
    ),
}

assert all(
    language in _DEFAULT_SIGNATURE_IDENTIFIERS for language in _COMMENT_OPTIONS
), "Not all languages in _COMMENT_OPTIONS are in _DEFAULT_SIGNATURE_IDENTIFIERS"
assert all(
    language in _COMMENT_OPTIONS for language in _DEFAULT_SIGNATURE_IDENTIFIERS
), "Not all languages in _DEFAULT_SIGNATURE_IDENTIFIERS are in _COMMENT_OPTIONS"


class _ScopeItem:
    def __init__(self, name: str, type: str, signature: str):
        self.name = name
        self.type = type
        self.signature = signature

    def dict(self):
        return {
            "name": self.name,
            "type": self.type,
            "signature": self.signature,
        }

class _ChunkNodeOutput:
    def __init__(self, this_document: Optional[TextNode], upstream_children_documents: List[TextNode], all_documents: List[TextNode]):
        self.this_document = this_document
        self.upstream_children_documents = upstream_children_documents
        self.all_documents = all_documents


class CodeHierarchyNodeParser(NodeParser):
    @classmethod
    def class_name(cls) -> str:
        return "CodeHierarchyNodeParser"

    def __init__(
        self,
        language: str,
        skeleton: bool = True,
        signature_identifiers: Optional[Dict[str, _SignatureCaptureOptions]] = None,
        code_splitter: Optional[CodeSplitter] = None,
        callback_manager: Optional[CallbackManager] = None,
        metadata_extractor: Optional[BaseExtractor] = None,
        chunk_min_characters: int = 80,
    ):
        self.language = language
        self.skeleton = skeleton
        self.signature_identifiers = signature_identifiers or _DEFAULT_SIGNATURE_IDENTIFIERS.get(language, {})
        self.code_splitter = code_splitter
        self.callback_manager = callback_manager or CallbackManager([])
        self.metadata_extractor = metadata_extractor
        self.chunk_min_characters = chunk_min_characters

        if not self.signature_identifiers:
            raise ValueError(f"Must provide signature_identifiers for language {language}.")

        super().__init__(
            include_prev_next_rel=False,
            language=language,
            callback_manager=self.callback_manager,
            metadata_extractor=self.metadata_extractor,
            code_splitter=self.code_splitter,
            signature_identifiers=self.signature_identifiers,
            min_characters=self.chunk_min_characters,
            skeleton=self.skeleton,
        )

    def _get_node_name(self, node: Node) -> str:
        """Get the name of a node."""
        signature_identifier = self.signature_identifiers[node.type]

        def recur(node: Node) -> str:
            for child in node.children:
                if child.type == signature_identifier.name_identifier:
                    return child.text.decode()
                if child.children:
                    out = recur(child)
                    if out:
                        return out
            return ""

        return recur(node).strip()

    def _get_node_signature(self, text: str, node: Node) -> str:
        """Get the signature of a node."""
        signature_identifier = self.signature_identifiers[node.type]

        def find_start(node: Node) -> Optional[int]:
            if not signature_identifier.start_signature_types:
                signature_identifier.start_signature_types = []

            for st in signature_identifier.start_signature_types:
                if node.type == st.type:
                    if st.inclusive:
                        return node.start_byte
                    return node.end_byte

            for child in node.children:
                out = find_start(child)
                if out is not None:
                    return out

            return None

        def find_end(node: Node) -> Optional[int]:
            if not signature_identifier.end_signature_types:
                signature_identifier.end_signature_types = []

            for st in signature_identifier.end_signature_types:
                if node.type == st.type:
                    if st.inclusive:
                        return node.end_byte
                    return node.start_byte

            for child in node.children:
                out = find_end(child)
                if out is not None:
                    return out

            return None

        start_byte, end_byte = find_start(node), find_end(node)
        if start_byte is None:
            start_byte = node.start_byte
        if end_byte is None:
            end_byte = node.end_byte
        return text[start_byte:end_byte].strip()


    @staticmethod
    def get_code_hierarchy_from_nodes(
        nodes: Sequence[BaseNode],
        max_depth: int = -1,
    ) -> Tuple[Dict[str, Any], str]:
        """
        Creates a code hierarchy appropriate to put into a tool description or context
        to make it easier to search for code.

        Call after `get_nodes_from_documents` and pass that output to this function.
        """
        out: Dict[str, Any] = defaultdict(dict)

        def get_subdict(keys: List[str]) -> Dict[str, Any]:
            # Get the dictionary we are operating on
            this_dict = out
            for key in keys:
                if key not in this_dict:
                    this_dict[key] = defaultdict(dict)
                this_dict = this_dict[key]
            return this_dict

        def recur_inclusive_scope(node: BaseNode, i: int, keys: List[str]) -> None:
            if "inclusive_scopes" not in node.metadata:
                raise KeyError("inclusive_scopes not in node.metadata")
            if i >= len(node.metadata["inclusive_scopes"]):
                return
            scope = node.metadata["inclusive_scopes"][i]

            this_dict = get_subdict(keys)

            if scope["name"] not in this_dict:
                this_dict[scope["name"]] = defaultdict(dict)

            if i < max_depth or max_depth == -1:
                recur_inclusive_scope(node, i + 1, [*keys, scope["name"]])

        def dict_to_markdown(d: Dict[str, Any], depth: int = 0) -> str:
            markdown = ""
            indent = "  " * depth  # Two spaces per depth level

            for key, value in d.items():
                if isinstance(value, dict):  # Check if value is a dict
                    # Add the key with a bullet point and increase depth for nested dicts
                    markdown += f"{indent}- {key}\n{dict_to_markdown(value, depth + 1)}"
                else:
                    # Handle non-dict items if necessary
                    markdown += f"{indent}- {key}: {value}\n"

            return markdown

        for node in nodes:
            filepath = node.metadata["filepath"].split("/")
            filepath[-1] = filepath[-1].split(".")[0]
            recur_inclusive_scope(node, 0, filepath)

        return out, dict_to_markdown(out)

    def _parse_nodes(
        self,
        nodes: Sequence[BaseNode],
        show_progress: bool = False,
        **kwargs: Any,
    ) -> List[BaseNode]:
        out: List[BaseNode] = []

        try:
            import tree_sitter_languages
        except ImportError:
            raise ImportError(
                "Please install tree_sitter_languages to use CodeSplitter."
            )

        try:
            parser = tree_sitter_languages.get_parser(self.language)
        except Exception as e:
            print(
                f"Could not get parser for language {self.language}. Check "
                "https://github.com/grantjenks/py-tree-sitter-languages#license "
                "for a list of valid languages."
            )
            raise e  # noqa: TRY201

        nodes_with_progress = get_tqdm_iterable(
            nodes, show_progress, "Parsing documents into nodes"
        )
        for node in nodes_with_progress:
            text = node.text
            tree = parser.parse(bytes(text, "utf-8"))

            if (
                not tree.root_node.children
                or tree.root_node.children[0].type != "ERROR"
            ):
                _chunks = self._chunk_node(tree.root_node, node.text)
                assert _chunks.this_document is not None, "Root node must be a chunk"
                chunks = _chunks.all_documents

                for chunk in chunks:
                    chunk.metadata = {
                        "language": self.language,
                        **chunk.metadata,
                        **node.metadata,
                    }
                    chunk.relationships[
                        NodeRelationship.SOURCE
                    ] = node.as_related_node_info()

                if self.skeleton:
                    self._skeletonize_list(chunks)

                if self.code_splitter:
                    new_nodes = []
                    for original_node in chunks:
                        new_split_nodes = self.code_splitter.get_nodes_from_documents(
                            [original_node], show_progress=show_progress, **kwargs
                        )

                        new_split_nodes[0].id_ = original_node.id_

                        for i, new_split_node in enumerate(new_split_nodes[:-1]):
                            new_split_node.text = (
                                new_split_node.text
                                + "\n"
                                + self._create_comment_line(new_split_nodes[i + 1], 0)
                            ).strip()

                        for i, new_split_node in enumerate(new_split_nodes[1:]):
                            new_split_node.text = (
                                self._create_comment_line(new_split_nodes[i])
                                + new_split_node.text
                            ).strip()

                        for new_split_node in new_split_nodes:
                            new_split_node.relationships[
                                NodeRelationship.CHILD
                            ] = original_node.relationships.get(NodeRelationship.CHILD, [])
                            new_split_node.relationships[
                                NodeRelationship.PARENT
                            ] = original_node.relationships.get(NodeRelationship.PARENT, None)

                        for old_node in chunks:
                            new_children = []
                            for old_nodes_child in old_node.relationships.get(NodeRelationship.CHILD, []):
                                if old_nodes_child.node_id == original_node.node_id:
                                    new_children.append(
                                        new_split_nodes[0].as_related_node_info()
                                    )
                                new_children.append(old_nodes_child)
                            old_node.relationships[
                                NodeRelationship.CHILD
                            ] = new_children

                            if (
                                old_node.relationships.get(NodeRelationship.PARENT)
                                and old_node.relationships[NodeRelationship.PARENT].node_id
                                == original_node.node_id
                            ):
                                old_node.relationships[
                                    NodeRelationship.PARENT
                                ] = new_split_nodes[0].as_related_node_info()

                        new_nodes += new_split_nodes

                    chunks = new_nodes

                if self.metadata_extractor:
                    chunks = self.metadata_extractor.process_nodes(  # type: ignore
                        chunks
                    )

                out += chunks
            else:
                raise ValueError(f"Could not parse code with language {self.language}.")

        return out

    @staticmethod
    def _get_indentation(text: str, language: str) -> Tuple[str, int, int]:
        indent_char = None
        minimum_chain = None

        text_split = text.splitlines()
        if len(text_split) == 0:
            raise ValueError("Text should be at least one line long.")

        for line in text_split:
            stripped_line = line.lstrip()

            if stripped_line:  # Non-empty line
                spaces_count = len(line) - len(line.lstrip(' '))
                tabs_count = len(line) - len(line.lstrip('\t'))

                if not indent_char:
                    if tabs_count > 0:
                        indent_char = '\t'
                    elif spaces_count > 0:
                        indent_char = ' '

                # For Go, we'll be more lenient and prefer tabs
                if language == 'go':
                    if tabs_count > 0:
                        indent_char = '\t'
                        char_count = tabs_count
                    else:
                        char_count = spaces_count
                else:
                    if spaces_count > 0 and tabs_count > 0:
                        raise ValueError("Mixed indentation found.")
                    if indent_char == " " and tabs_count > 0:
                        raise ValueError("Mixed indentation found.")
                    if indent_char == "\t" and spaces_count > 0:
                        raise ValueError("Mixed indentation found.")
                    char_count = spaces_count if indent_char == ' ' else tabs_count

                if char_count > 0:
                    if minimum_chain is None or char_count < minimum_chain:
                        minimum_chain = char_count

        # Default values if no indentation found
        if indent_char is None:
            indent_char = '\t' if language == 'go' else ' '
        if minimum_chain is None or minimum_chain == 0:
            minimum_chain = 1

        # Calculate first indent count
        first_line = next((line for line in text_split if line.strip()), '')
        first_indent_count = len(first_line) - len(first_line.lstrip(indent_char))

        return indent_char, minimum_chain, max(1, first_indent_count // minimum_chain)

    @staticmethod
    def _get_comment_text(node: TextNode) -> str:
        """Gets just the natural language text for a skeletonize comment."""
        return f"Code replaced for brevity. See node_id {node.node_id}"

    @classmethod
    def _create_comment_line(cls, node: TextNode, indention_lvl: int = -1) -> str:
        """
        Creates a comment line for a node.

        Sometimes we don't use this in a loop because it requires recalculating
        a lot of the same information. But it is handy.
        """
        # Create the text to replace the child_node.text with
        language = node.metadata["language"]
        if language not in _COMMENT_OPTIONS:
            # TODO: Create a contribution message
            raise KeyError("Language not yet supported. Please contribute!")
        comment_options = _COMMENT_OPTIONS[language]
        (
            indentation_char,
            indentation_count_per_lvl,
            first_indentation_lvl,
        ) = cls._get_indentation(node.text)
        if indention_lvl != -1:
            first_indentation_lvl = indention_lvl
        else:
            first_indentation_lvl += 1
        return (
            indentation_char * indentation_count_per_lvl * first_indentation_lvl
            + comment_options.comment_template.format(cls._get_comment_text(node))
            + "\n"
        )

    @classmethod
    def _get_replacement_text(cls, child_node: TextNode) -> str:
        signature = child_node.metadata["inclusive_scopes"][-1]["signature"]
        language = child_node.metadata["language"]
        if language not in _COMMENT_OPTIONS:
            raise KeyError("Language not yet supported. Please contribute!")
        comment_options = _COMMENT_OPTIONS[language]

        indentation_char, indentation_count_per_lvl, first_indentation_lvl = cls._get_indentation(child_node.text, language)

        replacement_txt = (
            indentation_char * indentation_count_per_lvl * first_indentation_lvl
            + signature
        )

        if comment_options.scope_method == _ScopeMethod.BRACKETS:
            replacement_txt += " {\n"
            replacement_txt += (
                indentation_char
                * indentation_count_per_lvl
                * (first_indentation_lvl + 1)
                + comment_options.comment_template.format(
                    cls._get_comment_text(child_node)
                )
                + "\n"
            )
            replacement_txt += (
                indentation_char * indentation_count_per_lvl * first_indentation_lvl
                + "}"
            )
        elif comment_options.scope_method == _ScopeMethod.INDENTATION:
            replacement_txt += "\n"
            replacement_txt += indentation_char * indentation_count_per_lvl * (
                first_indentation_lvl + 1
            ) + comment_options.comment_template.format(
                cls._get_comment_text(child_node)
            )
        else:
            raise KeyError(f"Unrecognized scope method {comment_options.scope_method}")

        return replacement_txt
    
    def get_nodes_from_documents(self, documents: List[BaseNode]) -> List[BaseNode]:
        return self._parse_nodes(documents)

    @classmethod
    def _skeletonize(cls, parent_node: TextNode, child_node: TextNode) -> None:
        if child_node.text in parent_node.text:
            replacement_text = cls._get_replacement_text(child_node=child_node)
            index = parent_node.text.find(child_node.text)
            parent_node.text = (
                parent_node.text[:index]
                + replacement_text
                + parent_node.text[index + len(child_node.text) :]
            )
        elif f"See node_id {child_node.node_id}" in parent_node.text:
            print(f"Text already skeletonized for Child node ID: {child_node.node_id}")
        else:
            print(f"Error: Child text is not found in parent text.")
            print(f"Child Node ID: {child_node.node_id}")
            print(f"Child Text: {child_node.text}")
            print(f"Parent Text: {parent_node.text}")
            raise ValueError(f"The child text is not contained inside the parent text. Child node ID: {child_node.node_id}")

        if child_node.node_id not in (c.node_id for c in parent_node.relationships.get(NodeRelationship.CHILD, [])):
            raise ValueError("The child node is not a child of the parent node.")
            
    def _skeletonize_list(self, nodes: List[TextNode]) -> None:
        node_id_map = {n.node_id: n for n in nodes}

        def recur(node: TextNode) -> None:
            for child in node.relationships.get(NodeRelationship.CHILD, []):
                child_node = node_id_map[child.node_id]
                self._skeletonize(parent_node=node, child_node=child_node)
                recur(child_node)

        for n in nodes:
            if n.relationships.get(NodeRelationship.PARENT) is None:
                recur(n)


    def _chunk_node(
        self,
        parent: Node,
        text: str,
        _context_list: Optional[List[_ScopeItem]] = None,
        _root: bool = True,
    ) -> _ChunkNodeOutput:
        if _context_list is None:
            _context_list = []

        upstream_children_documents: List[TextNode] = []
        all_documents: List[TextNode] = []

        start_byte = parent.start_byte
        text_bytes = bytes(text, "utf-8")
        while start_byte > 0 and text_bytes[start_byte - 1 : start_byte] in (b" ", b"\t"):
            start_byte -= 1

        current_chunk = text_bytes[start_byte : parent.end_byte].decode()

        if len(current_chunk) < self.chunk_min_characters and not _root:
            return _ChunkNodeOutput(
                this_document=None, all_documents=[], upstream_children_documents=[]
            )

        # uncomment this to add more languages
        # print(parent.type)

        this_document = None
        if parent.type in self.signature_identifiers or _root:
            is_small_declaration = (
                (parent.type == "lexical_declaration" and len(parent.text.decode().split("\n")) < 5) or
                (parent.type == "function_declaration" and (self.language == "javascript" or self.language == "typescript") and len(parent.text.decode().split("\n")) < 3) or 
                (parent.type == "interface_declaration" and parent.text.decode().strip().startswith("interface ") and len(parent.text.decode().split("\n")) < 7) or
                (parent.type in [
                    "variable_declaration",
                    "export_statement",
                    "type_declaration",
                    "enum_declaration",
                    "annotation_type_declaration",
                    "union_specifier",
                    "namespace_definition",
                    "template_declaration",
                    "concept_definition"
                ] and len(parent.text.decode().split("\n")) < 5)
            )

            if not is_small_declaration:
                if not _root:
                    new_context = _ScopeItem(
                        name=self._get_node_name(parent),
                        type=parent.type,
                        signature=self._get_node_signature(text=text, node=parent),
                    )
                    _context_list.append(new_context)

                this_document = TextNode(
                    text=current_chunk,
                    metadata={
                        "inclusive_scopes": [cl.dict() for cl in _context_list],
                        "start_byte": start_byte,
                        "end_byte": parent.end_byte,
                    },
                    relationships={
                        NodeRelationship.CHILD: [],
                        NodeRelationship.PARENT: None,
                    },
                )
                all_documents.append(this_document)

        for child in parent.children:
            if child.children:
                next_chunks = self._chunk_node(
                    child, text, _context_list=_context_list.copy(), _root=False
                )

                if this_document is not None:
                    if next_chunks.this_document is not None:
                        # print(f"Adding child {next_chunks.this_document.node_id} to parent {this_document.node_id}")
                        this_document.relationships[
                            NodeRelationship.CHILD
                        ].append(next_chunks.this_document.as_related_node_info())
                        next_chunks.this_document.relationships[
                            NodeRelationship.PARENT
                        ] = this_document.as_related_node_info()
                    else:
                        for d in next_chunks.upstream_children_documents:
                            # print(f"Adding child {d.node_id} to parent {this_document.node_id}")
                            this_document.relationships[
                                NodeRelationship.CHILD
                            ].append(d.as_related_node_info())
                            d.relationships[
                                NodeRelationship.PARENT
                            ] = this_document.as_related_node_info()
                else:
                    if next_chunks.this_document is not None:
                        upstream_children_documents.append(next_chunks.this_document)
                    else:
                        upstream_children_documents.extend(
                            next_chunks.upstream_children_documents
                        )

                all_documents.extend(next_chunks.all_documents)

        return _ChunkNodeOutput(
            this_document=this_document,
            upstream_children_documents=upstream_children_documents,
            all_documents=all_documents,
        )
