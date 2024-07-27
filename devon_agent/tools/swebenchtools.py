from devon_agent.tool import Tool, ToolContext


class SubmitTool(Tool):
    @property
    def name(self):
        return "submit"

    def supported_formats(self):
        return ["docstring", "manpage"]

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """NAME
            submit - submit your solution once you think you have resolved the issue
        
        SYNOPSIS
            submit
        
        DESCRIPTION
            The submit command submits your solution. It is used to indicate that you have resolved the issue and are ready to submit your
            solution.
        """
            case _:
                return "Unknown format"

    def setup(self, ctx):
        pass

    def function(self, ctx: ToolContext):
        
        return ctx["environment"].execute(f"""
    cd {ctx["environment"].base_path};

    # Check if the patch file exists and is non-empty
    if [ -s "/root/test.patch" ]; then
        # Apply the patch in reverse
        git apply -R < "/root/test.patch"
    fi;

    git add -A;
    git diff --cached > model.patch;
    echo "<<SUBMISSION||";
    cat model.patch;
    echo "||SUBMISSION>>";""")[0]

    def cleanup(self, ctx):
        pass
