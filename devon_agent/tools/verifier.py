import os

from devon_agent.tool import Tool, ToolContext
import code_nav_devon
import tempfile


class CodeSearch(Tool):
    def __init__(self):
        self.temp_file_path = None

    @property
    def name(self):
        return "code_search"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, ctx):
        self.base_path = ctx["session"].base_path

        self.temp_dir = tempfile.TemporaryDirectory()
        self.temp_dir_path = self.temp_dir.name

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
            output = code_nav_devon.text_search(self.base_path, self.temp_dir_path, text, True)
            return output
        except Exception as e:
            ctx["session"].logger.error(f"Search failed for text: {text}. Error: {str(e)}")
            return f"Search failed for text: {text}. Error: {str(e)}"
        
