import os
import tempfile

import code_nav_devon
from pydantic import Field

from devon_agent.tool import Tool, ToolContext
from devon_agent.tools.retrieval.regex.query_regex import regex_search
from devon_agent.tools.utils import cwd_normalize_path

class RegexSearch(Tool):
    base_path: str = Field(default=None)
    temp_dir: tempfile.TemporaryDirectory = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    @property
    def name(self):
        return "code_search"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, ctx):
        self.base_path = ctx["environment"].path

    def cleanup(self, ctx):
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
    CODE_SEARCH(1)                   General Commands Manual                  CODE_SEARCH(1)

    NAME
            code_search - perform regex search within Python files in the project

    SYNOPSIS
            code_search PATTERN [DIR_PATH]

    DESCRIPTION
            The code_search command performs a regex search for the specified pattern within all Python files in the project.

    OPTIONS
            PATTERN
                    The regex pattern to search for within the project files. This pattern follows Python's re module syntax.
            
            DIR_PATH
                    The path of the directory or file whose content you want to search in.
                    If not given, it will take the base path of the codebase

    RETURN VALUE
            A string containing all the match with their context.

    EXAMPLES
           1. Search for a specific function definition:
               code_search "def\\s+process_data\\s*\\(" 3

            2. Search for a specific class definition:
               code_search "class\\s+UserProfile\\s*\\(" 2

            3. Search for calls to a specific method on a particular object:
               code_search "request\\.user\\.is_authenticated\\s*\\(" 2

            4. Search for imports from a specific module:
               code_search "from\\s+django\\.shortcuts\\s+import\\s+" 1

            5. Search for assignments to a specific variable:
               code_search "^\\s*MAX_RETRIES\\s*=" 1

            basically feel free to use the full potential of regex

    NOTE: When using the command line, you may need to escape backslashes and quotes according to your shell's rules. For example:
          code_search "def\\\\s+[a-zA-Z_][a-zA-Z0-9_]*\\\\s*\\\\(" 3
    """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, ctx: ToolContext, pattern: str, dir_path: str | None = None) -> str:
        """
        command_name: code_search
        description: Performs a regex search in Python files. Accepts a regex pattern and an optional directory or file path. Returns matches with context as a string. Uses Python's re syntax. Useful for finding functions, classes, or specific code patterns.
        signature: code_search PATTERN [DIR_PATH]
        example: `code_search "def process_data\\s*\\(" /path/to/project`
        """
        try:
            window = 1
            path = None
            if dir_path is None:
                path = self.base_path  
            else:
                path = cwd_normalize_path(ctx, dir_path)

            results = regex_search(path, pattern, window)
            num_matches = len(results)

            if num_matches == 0:
                return f'No matches found for "{pattern}" in {path}'
            elif num_matches < 10:
                window = 20
                results = regex_search(path, pattern, window)

            elif num_matches < 20:
                window = 10
                results = regex_search(path, pattern, window)
                results = results

            elif num_matches < 50:
                window = 5
                results = regex_search(path, pattern, window)
                results = results
                
            elif num_matches > 50:
                return f'More than 50 lines matched for "{pattern}" in {path}. Please narrow your search either though your regex pattern or through limitting it to a smaller directory or file.'

            output = ""
            
            output += f'Found {num_matches} matches for "{pattern}" in {path}:\n'
            output = "\n".join(results)
            return output
        
        except Exception as e:
            ctx["config"].logger.error(
                f"Regex search failed for pattern: {pattern}. Error: {str(e)}"
            )
            return f"Regex search failed for pattern: {pattern}. Error: {str(e)}"


class CodeSearch(Tool):
    base_path: str = Field(default=None)
    temp_dir: tempfile.TemporaryDirectory = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    @property
    def name(self):
        return "code_search"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, ctx):
        self.base_path = ctx["environment"].path

        self.temp_dir = tempfile.TemporaryDirectory()

    def cleanup(self, ctx):
        # Clean up the temporary directory
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
    CODE_SEARCH(1)                   General Commands Manual                  CODE_SEARCH(1)

    NAME
            code_search - case-sensitive search for text within all the project files

    SYNOPSIS
            code_search TEXT

    DESCRIPTION
            The code_search command does case-sensitive search for the specified text within all the project files.

    OPTIONS
            TEXT
                    The text to search within the project files.

    RETURN VALUE
.

    EXAMPLES
            To search for the text "def my_function":

                    code_search "def my_function"
    """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, ctx: ToolContext, text: str) -> str:
        """
        command_name: code_search
        description: Searches for the specified text within the code base.
        signature: code_search [TEXT]
        example: `code_search "def my_function"`
        """
        try:
            # Run the text_search function
            output = code_nav_devon.text_search(
                self.base_path, self.temp_dir.name, text, True
            )
            return output
        except Exception as e:
            ctx["config"].logger.error(
                f"Search failed for text: {text}. Error: {str(e)}"
            )
            return f"Search failed for text: {text}. Error: {str(e)}"


class CodeGoTo(Tool):
    base_path: str = Field(default=None)
    temp_dir: tempfile.TemporaryDirectory = Field(default=None)

    class Config:
        arbitrary_types_allowed = True

    @property
    def name(self):
        return "go_to_definition_or_references"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, ctx):
        self.base_path = ctx["environment"].path

        self.temp_dir = tempfile.TemporaryDirectory()

    def cleanup(self, ctx):
        # Clean up the temporary directory
        if self.temp_dir:
            self.temp_dir.cleanup()
            self.temp_dir = None

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
    GO_TO_DEFINITION_OR_REFERENCES(1)                   General Commands Manual                  GO_TO_DEFINITION_OR_REFERENCES(1)

    NAME
            go_to_definition_or_references - find symbol's definition or all references and get a list of all the positions within the codebase

    SYNOPSIS
            go_to_definition_or_references FILE_PATH LINE_NUMBER SYMBOL_STRING

    DESCRIPTION
            The go_to_definition_or_references command navigates to the specified symbol's definition or reference within the project files by using ast tree
            and returns a lists all positions of the symbol in the rest of the codebase. To find reference, use it on a definition. To find definition, use it on reference.
            This is not a simple string matching. If you want to see the definition of a function or a class, use this. If you want to see references of a function or class, use this.
            Use it to find all the function calls.

    OPTIONS
            FILE_PATH
                    The path of the file containing the symbol.

            LINE_NUMBER
                    The line number where the symbol is located.

            SYMBOL_STRING
                    The symbol string to navigate to and search for within the project files.

    RETURN VALUE
            The go_to_definition_or_references command returns a string of all positions of the symbol in the rest of the codebase.

    EXAMPLES
            To navigate to a symbol "my_function" in file "example.py" at line 42 and find its positions:

                    go_to_definition_or_references "example.py" 42 "my_function"
    """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(
        self, ctx: ToolContext, file_path: str, line_number: int, symbol_string: str
    ) -> str:
        """
        command_name: go_to_definition_or_references
        description: Navigates to the specified symbol's definition or reference within the code base
                    and lists all positions of the symbol in the rest of the codebase.
                    Use it to find all the locations where the function or class is being called.
                    If you want to see the definition of a function or a class, use this. If you want to see references of a function or class, use this.
        signature: go_to_definition_or_references [FILE_PATH] [LINE_NUMBER] [SYMBOL_STRING]
        example: `go_to_definition_or_references "example.py" 42 "my_function"`
        """
        try:
            # to tell the agent whether fuzzy search was enabled
            fuzzy_search_text = ""

            line_number = int(line_number)
            abs_file_path = os.path.abspath(os.path.normpath(file_path))
            with open(abs_file_path, "r") as file:
                lines = file.readlines()

            if int(line_number) - 1 >= len(lines):
                raise ValueError(
                    f"Line number {line_number} is out of range in file {file_path}"
                )

            base_path = ctx["environment"].path

            # Check the specified line for the symbol
            line_content = lines[line_number - 1]
            start_index = line_content.find(symbol_string)
            if start_index != -1:
                end_index = start_index + len(symbol_string)
            else:
                # Perform fuzzy search within ±4 lines if symbol is not found in the specified line
                start_line = max(0, line_number - 5)  # 1 lines above
                end_line = min(len(lines), line_number + 4)  # 2 lines below

                old_line_number = line_number

                # Initialize variables for line content and symbol indices
                line_content = None
                start_index = -1
                end_index = -1

                # Search for the symbol in the lines within ±4 lines
                for i in range(start_line, end_line):
                    line_content = lines[i]
                    start_index = line_content.find(symbol_string)
                    if start_index != -1:
                        line_number = i + 1  # Adjust line number to the found line
                        end_index = start_index + len(symbol_string)
                        break

                fuzzy_search_text = f"{symbol_string} is not found in line number {old_line_number} but found in line number {line_number} \n\n"

                # If symbol is not found, raise an error
                if start_index == -1:
                    raise ValueError(
                        f"Symbol '{symbol_string}' not found in line {line_number} or within ±4 lines of it in file {file_path}"
                    )

            # Run the go_to function
            output = code_nav_devon.go_to(
                base_path,
                self.temp_dir.name,
                abs_file_path,
                line_number,
                start_index,
                end_index,
            )
            return fuzzy_search_text + output
        except Exception as e:
            ctx["config"].logger.error(
                f"Navigation failed for symbol: {symbol_string} at line: {line_number} in file: {file_path}. Error: {str(e)}"
            )
            return f"Navigation failed for symbol: {symbol_string} at line: {line_number} in file: {file_path}. Error: {str(e)}"


# Create a temporary directory
# temp_dir = tempfile.TemporaryDirectory()
# temp_file_dir = temp_dir.name
# print(f"Temporary directory created at: {temp_dir}")

# try:
#     # Use the temporary directory with the package function
#     result = code_nav_devon.go_to("/Users/arnav/Desktop/devon/Devon", temp_file_dir, "/Users/arnav/Desktop/devon/Devon/devon_agent/session.py", 34, 6, 22)
#     print(result)
# except Exception as e:
#     print(f"Error: {e}")
# finally:
#     # Manually delete the temporary directory and its contents
#     temp_dir.cleanup()
#     temp_dir = None
