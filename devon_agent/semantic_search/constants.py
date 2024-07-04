extension_to_language = {
            '.py': 'python',
            '.js': 'javascript',
            '.jsx': 'javascript',
            '.ts': 'typescript',
            '.tsx': 'typescript',
            '.java': 'java',
            '.cpp': 'c++',
            '.c': 'c',
            '.cs': 'c#',
            '.rb': 'ruby',
            '.php': 'php',
            '.html': 'html',
            '.css': 'css',
            '.m': 'objective-c',
            '.mm': 'objective-c++',
            '.sh': 'shell',
            '.go': 'go',
            '.rs': 'rust',
            '.sql': 'sql',
            '.json': 'json',
            '.yaml': 'yaml',
            '.yml': 'yaml',
            '.xml': 'xml'
        }

supported_noncode_extentions = [".md", ".json", ".sh", ".cargo", ".toml", ".config", ".yaml", ".yml", ".properties", "Dockerfile", ".dockerignore"]

RELATIONS_TYPES_MAP = {
            "function_definition": "FUNCTION_DEFINITION",
            "class_definition": "CLASS_DEFINITION",
            "function_declaration" : "FUNCTION_DEFINITION",

            # js / ts
            "interface_declaration": "INTERFACE_DEFINITION",
            "lexical_declaration" : "FUNCTION_DEFINITION",
            "method_definition": "METHOD_DEFINITION",
            

            #CPP
            "class_specifier" : "CLASS_DEFINITION",
            "template_declaration" : "TEMPLATE_DEFINITION",
            "concept_definition" : "CONCEPT_DEFINITION",
            "struct_specifier" : "STRUCT_DEFINITION",
            "function_definition": "FUNCTION_DEFINITION",
            "namespace_definition": "NAMESPACE_DEFINITION",
            "enum_specifier": "ENUM_DEFINITION",
            "union_specifier": "UNION_DEFINITION",

            #java
            "class_declaration" : "CLASS_DEFINITION",
            "enum_declaration" : "ENUM_DEFINITION",
            "interface_declaration" : "INTERFACE_DEFINITION",
            "constructor_declaration": "CONSTRUCTOR_DEFINITION",
            "method_declaration": "METHOD_DEFINITION",
            "annotation_type_declaration": "ANNOTATION_DEFINITION",
            "record_declaration": "ROCORD_DEFINITION",

            # Go
            "type_declaration": "TYPE_DEFINITION",
            "method_declaration": "METHOD_DEFINITION",
            "function_declaration": "FUNCTION_DEFINITION",
            "interface_type": "INTERFACE_DEFINITION",
            "struct_type": "STRUCT_DEFINITION",
        }