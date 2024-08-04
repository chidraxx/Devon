import json
import time
from typing import Dict, List
from devon_agent.config import Checkpoint
from devon_agent.environment import EnvironmentModule
from devon_agent.tool import Tool, ToolContext
import xml.etree.ElementTree as ET

from devon_agent.tools.utils import cwd_normalize_path, read_file


def waitForEvent(event_log: List[Dict], event):
    while True:
        if event_log[-1] == event:
            return event_log[-1]
        time.sleep(1)

class AskUserTool(Tool):
    @property
    def name(self):
        return "AskUserTool"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, context: ToolContext):
        pass

    def cleanup(self, context: ToolContext):
        pass

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
                NAME
                    ask_user - ask the user for their input

                SYNOPSIS
                    ask_user

                DESCRIPTION
                    The ask_user command asks the user for their input

                RETURN VALUE
                    The ask_user command returns a string indicating the user's input.

                EXAMPLES
                    To ask the user for their input, run the following command:

                        ask_user
                """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, context: ToolContext, question: str, **kwargs):
        """
        command_name: ask_user
        description: The ask_user command asks the user for their input
        signature: ask_user "Some question here"
        example: `ask_user "What would you like me to do?"`
        """
        return context["environment"].execute(input=question)

class AskUserToolWithCommit(Tool):
    @property
    def name(self):
        return "AskUserTool"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, context: ToolContext):
        pass

    def cleanup(self, context: ToolContext):
        pass

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
                NAME
                    ask_user - ask the user for their input and provide commit message for changes

                SYNOPSIS
                    ask_user "Some question here" "Some commit message here"

                DESCRIPTION
                    The ask_user command asks the user for their input. Also add a commit message. The commit message should be relavent to the changes you did since the latest user requestion / task

                RETURN VALUE
                    The ask_user command returns a string indicating the user's input.

                EXAMPLES
                    To ask the user for their input, run the following command:

                        ask_user "What would you like me to do?" "Added a new feature ..."
                """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, context: ToolContext, question: str, commit_message: str, **kwargs):
        """
        command_name: ask_user
        description: The ask_user command asks the user for their input and provide a commit message for changes. The commit message should be relavent to the changes you did since the latest user requestion / task
        signature: ask_user "Some question here" "Some commit message here"
        example: `ask_user "What would you like me to do?" "Added a new feature ..."`
        """            
        return context["environment"].execute(input=question)


def parse_xml_tags_to_xml(start_tag, end_tag, xml_string):
    start_index = xml_string.rfind(start_tag)
    end_index = xml_string.rfind(end_tag)

    if start_index != -1 and end_index != -1:
        xml_string = xml_string[start_index:end_index + len(end_tag)]
    else:
        return "Error: Invalid XML structure. Missing graph_commands tags."

    # Clean the string
    xml_string = ''.join(char for char in xml_string if ord(char) >= 32)
    xml_string = xml_string.strip()

    return ET.fromstring(xml_string)

def _safe_read_file(ctx, file_path):
    abs_path = cwd_normalize_path(ctx, file_path)

    try:
        # Check if file exists to avoid reading from non-existent files
        content, _ = ctx["environment"].execute(f"cat '{abs_path}'")
        return content
    except Exception as e:
        ctx["config"].logger.error(
            f"Failed to read file: {file_path}. Error: {str(e)}"
        )
        return f"Failed to read file: {file_path}. Error: {str(e)}"

def json_to_markdown(data):
    try:
        
        # Start building the Markdown string
        markdown = "# Code Blocks\n\n"
        
        for block in data.get("codeblocks", []):
            location = block.get("location", "Unknown location")
            content = block.get("content", "No content available")
            
            # Add the location as a subheading
            markdown += f"## Location: {location}\n\n"
            
            # Add the content as a TypeScript code block
            markdown += "```\n"
            markdown += f"// Content of {location}\n"
            markdown += f"{content.strip()}\n"
            markdown += "```\n\n"
        
        return markdown.strip()
    except json.JSONDecodeError:
        return "Error: Invalid JSON input"

class SurfaceContextTool(Tool):
    shell_env: EnvironmentModule = None

    @property
    def name(self):
        return "SurfaceContextTool"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, context: ToolContext):
        pass

    def cleanup(self, context: ToolContext):
        pass

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
                NAME
                    surface_context - surfaces POTENTIALLY relevant context to the user and asks them to approve its use as part of this task

                SYNOPSIS
                    surface_context "<codeblocks><codeblock><location>[location]</location></codeblock>...</codeblocks>"

                DESCRIPTION
                    The surface_context command asks the user for their input on potentially relevant code blocks and asks them to approve them for use in the task.

                RETURN VALUE
                    The surface_context command returns which context blocks are relevant to the task

                EXAMPLES
                    To surface context about a particular for loop, run the following command:

                        surface_context "<codeblocks><codeblock><location>sample/path/file.py</location></codeblock>...</codeblocks>"
                """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, context: ToolContext, codeblocks: str, **kwargs):
        """
        command_name: surface_context
        description: The surface_context command asks the user for their input on potentially relevant code blocks and asks them to approve them for use in the task.
        signature: surface_context "<codeblocks><codeblock><location>[location]</location></codeblock></codeblocks>"
        example: `surface_context "<codeblocks><codeblock><location>sample/path/file.py</location></codeblocks>"`
        """

        # Remove any leading/trailing whitespace and add a root element if not present
        codeblock_xml = parse_xml_tags_to_xml("<codeblocks>", "</codeblocks>", codeblocks)

        locations = []

        for child in codeblock_xml:
            if child.tag == "codeblock":
                for element in child:
                    if element.tag == "location":

                        code = _safe_read_file({"environment": self.shell_env, "config": context["config"]}, element.text)
                        locations.append({
                            "location": element.text,
                            "content": code
                        })

        locations = {"codeblocks": locations}

        return context["environment"].execute(input=json_to_markdown(locations))

class SetTaskTool(Tool):
    @property
    def name(self):
        return "SetTaskTool"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, context: ToolContext):
        pass

    def cleanup(self, context: ToolContext):
        pass

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
                NAME
                    set_task - asks the user for the task and persists it

                SYNOPSIS
                    set_task

                DESCRIPTION
                    The set_task command asks the user for their specified task

                RETURN VALUE
                    The set_task command returns a string indicating the user's input.

                EXAMPLES
                    To ask the user for their input, run the following command:

                        set_task
                """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, context: ToolContext, **kwargs):
        """
        command_name: set_task
        description: The set_task command asks the user for the next task to perform
        signature: set_task
        example: `set_task`
        """
        context["session"].state.task = context["environment"].execute(
            input="what is my next task?"
        )
        return context["session"].state.task


class RespondUserTool(Tool):
    @property
    def name(self):
        return "RespondUserTool"

    def setup(self, context: ToolContext):
        pass

    def cleanup(self, context: ToolContext):
        pass

    def supported_formats(self):
        return ["docstring", "manpage"]

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
                NAME
                    respond - respond to the user

                SYNOPSIS
                    respond "Some response here"

                DESCRIPTION
                    The respond command responds to the user

                RETURN VALUE
                    The user may respond back to you

                EXAMPLES
                    To ask the user for their input, run the following command:

                        respond "I did this, what do you think?"
                """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, context: ToolContext, response: str, **kwargs):
        """
        command_name: respond
        description: The respond command responds to the user
        signature: respond "Some response here"
        example: `respond "I did this, what do you think?"`
        """
        return context["environment"].execute(input=response)
