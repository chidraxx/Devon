from dotenv import load_dotenv
import os
from litellm import acompletion
import asyncio

    
def code_explainer_and_summary_prompt(function_code, children_summaries):
    user_prompt = str(function_code) + "\n" + "Here are the summaries for all the definitions:" + "\n" + str(children_summaries)

    message = [{"content": f"""You are a code explainer, given a piece of code and summaries of its child functions or classes, you need to explain what the code is doing and is trying to achieve. Use code symbols, like variable names, function names, etc whenever you can while explaining. We purposely omitted some code If the code has the comment '# Code replaced for brevity. See node_id ..... ', so give us your best guess on what the whole code is trying to do using the summaries given of the definitions. Don't repeat the summaries.

Also give a summary. Mention what the code contains and what is the purpose. Use the summary of definitions if given. Have maximum of 3 lines

wrap the description in <description> tag and summary in <summary> tag
""", "role": "system"},
                {"content": f"{user_prompt}", "role": "user"}]
    
    return message

def code_explainer_and_summary_prompt_groq(function_code, children_summaries):
    user_prompt = str(function_code) + "\n" + "Here are the summaries for all the definitions:" + "\n" + str(children_summaries)

    message = [{"content": f"""You are a code explainer, given a piece of code and summaries of its child functions or classes, you need to explain what the code is doing and is trying to achieve. Use code symbols, like variable names, function names, etc whenever you can while explaining. We purposely omitted some code If the code has the comment '# Code replaced for brevity. See node_id ..... ', so give us your best guess on what the whole code is trying to do using the summaries given of the definitions. Don't repeat the summaries.""", "role": "system"},
                {"content": f"{user_prompt}", "role": "user"}]
    
    return message
# def file_summary_prompt(function_code):
#     message = [{"content": f"Mention the main class or functions and say what their purpose is. Dont mention about commented code. Have maximum of 3  Be as concise as possible", "role": "system"},
#                {"content": f"{function_code}", "role": "user"}]
    
#     return message    

def code_summary_prompt(function_code):
    message = [{"content": f"summarize what does the code trying to do. Dont mention about commented code. Do not have a summary more than 3 lines, but try to keep is less than 3. Be as concise as posible", "role": "system"},
               {"content": f"{str(function_code)}", "role": "user"}]
    
    return message 

def directory_summary_prompt(directory_content):
    message = [{"content": f"""In a really concise way, describe the role of the directory. Highlight the main functionalities according to you, no matter its hierarchy. Don't have bullet points.

start with- The directory [name of the directory]""", "role": "system"},
               {"content": f"{directory_content}", "role": "user"}]
    
    return message

def directory_summary_prompt_groq(directory_content):
    message = [{"content": f"""In a really concise way, describe the role of the directory. Highlight the main functionalities according to you, no matter its hierarchy. Don't have bullet points. ONLY 4 SENTENCES maximum. Try to mention everything in few words and focus on most important aspects

start with- The directory [name of the directory]""", "role": "system"},
               {"content": f"{directory_content}", "role": "user"}]
    
    return message


def agent_prompt(question, tool_response):
    message = [{"content": f"You are a senior software engineer who is expert in understanding large codebases. You are serving a user who asked a question about a codebase they have no idea about. We did semantic search with their question on the codebase through our tool and we are giving you the output of the tool. The tool's response will not be fully accurate. Only choose the code that looks right to you while formulating the answer. Your job is to frame the answer properly by looking at all the different code blocks and give a final answer. Your job is to make the user understand the new codebase, so whenever you are talking about an important part of the codebase mention the full file path and codesnippet, like the whole code of a small function or the relavent section of a large function, which will be given along with the code in the tool output", "role": "system"},
                {"content": f"The user's question: {question}\n\nOur tool's response: {tool_response} \n\n Remember, be sure to give us relavent code snippets along with file path while formulating an answer", "role": "user"}]
    
    return message

async def get_completion(messages, api_key, size = "small", model="anthropic"):
    try:
        # Retrieve API keys from environment variables
        # openai_api_key = os.getenv("OPENAI_API_KEY")
        # anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")

        # Determine the model to use based on available API keys
        # if model == "openai" and not openai_api_key:
        #     model = "anthropic" if anthropic_api_key else None
        # elif model == "anthropic" and not anthropic_api_key:
        #     model = "openai" if openai_api_key else None

        if model == "openai":
            # os.environ["OPENAI_API_KEY"] = api_key
            response = await acompletion(
                model="gpt-4o",
                messages=messages,
                api_key=api_key
            )
        elif model == "anthropic":
            # os.environ["ANTHROPIC_API_KEY"] = api_key
            if size == "small":
                response = await acompletion(
                    model="claude-3-haiku-20240307",
                    messages=messages,
                    temperature=0.5,
                    api_key=api_key
                )
            else:
                response = await acompletion(
                    model="claude-3-opus-20240229",
                    messages=messages,
                    temperature=0.5,
                    max_tokens=4096,
                    api_key=api_key
                )
        else:
            raise ValueError("Invalid model specified and no valid API keys found.")

        # Return the API response
        return response.choices[0].message['content']

    except Exception as e:
        # Handle errors that occur during the API request or processing
        # return {"error": str(e)}
        raise e
    
async def get_completion_groq(messages, size = "small", model="llama-3-8b"):
    try:

        # if size == "small":
        try:
            response = await acompletion(
                model="groq/llama3-8b-8192",
                messages=messages,
                temperature=0.5,
                )
        except Exception as e:
            # print(e)
            raise e
        # else:
        #     response = await acompletion(
        #         model="claude-3-opus-20240229",
        #         messages=messages,
        #         temperature=0.5,
        #         max_tokens=4096
        #     )
 
        # Return the API response
        return response.choices[0].message['content']

    except Exception as e:
        # Handle errors that occur during the API request or processing
        # return {"error": str(e)}
        raise e


async def run_model_completion(model_name, api_key, prompt):
    if model_name == "groq":
        return await get_completion_groq(prompt, model="anthropic")
    else:
        return await get_completion(prompt, api_key)


async def main():
    # print(await get_completion_groq(code_explainer_prompt("""def _relate_constructor_calls(self, node_view, imports):
    #     for node_id, node_attrs in node_view:
    #         function_calls = node_attrs.get("function_calls")
    #         inherits = node_attrs.get("inheritances")
    #         if function_calls:
    #             function_calls_relations = self.__relate_function_calls(node_attrs, function_calls, imports)
    #             for relation in function_calls_relations:
    #                 self.graph.add_edge(relation["sourceId"], relation["targetId"], type=relation["type"])
    #         if inherits:
    #             inheritances_relations = self.__relate_inheritances(node_attrs, inherits, imports)
    #             for relation in inheritances_relations:
    #                 self.graph.add_edge(relation["sourceId"], relation["targetId"], type=relation["type"])""")))
    # print(await get_completion(code_summary_prompt(""""""), size="small"))
#     print(await run_model_completion("haiku", directory_summary_prompt("""test:
#   test1.py: The code contains a set of functions that perform various code analysis
#     tasks, including removing non-ASCII characters, traversing a syntax tree, extracting
#     function names, decomposing function calls, and identifying function calls and
#     class inheritances. The purpose of this code is to provide a set of utilities
#     for analyzing and processing code.
#   new.py: The code defines a `hello()` function that adds two variables and prints
#     the result. The actual implementation of the function has been omitted for brevity.
#   idk.py: The code defines a function `idk` that removes non-ASCII characters from
#     the input text using a regular expression. The purpose i)s to clean up the text
#     by removing any non-standard characters.""")))
    print(await run_model_completion("groq", directory_summary_prompt("""code-base-agent:
  test: {}
  tests:
    test_graph_constructor.py: The code is a test suite for the `GraphConstructor`
      class, which is responsible for constructing a graph representation of a file
      system. The test suite sets up a temporary directory structure, verifies the
      graph structure, and tests the functionality of the `GraphConstructor` class.
  src:
    blar_graph:
      chromadb:
        graph_traversal:
          encode_codegraph.py: This code is part of a system that processes and generates
            documentation for code graphs. It includes functions for processing code
            nodes, directories, and generating summaries using AI models and directory
            traversal. The purpose is to provide concise and informative documentation
            for code repositories.
          value_extractor.py: The code is part of a system that processes and extracts
            information from a graph data structure. The `process_node` function processes
            data associated with a node, while the `extract_chromadb_values` function
            extracts node IDs, documents, metadata, and code from the graph using
            a BFS algorithm.
        db.py: The code defines a `ChromaDB` class that provides a persistent database
          for managing collections of documents, embeddings, and metadata. It allows
          for creating, retrieving, updating, and deleting collections, as well as
          adding, updating, and deleting documents within those collections.
        llm.py: The code provides a set of utilities for analyzing and processing
          code, including generating code explanations, summaries, and prompts for
          a language model. The main purpose is to facilitate the understanding and
          documentation of codebases.
      graph_construction:
        summary: The directory "graph_construction" contains the core components of
          a code analysis tool that constructs a graph representation of a codebase.
          It includes modules for parsing different file types, managing the graph
          data, and providing utility functions to analyze and extract information
          from the code structure.
      run.py: The code defines a `CodeGraphManager` class that manages a knowledge
        graph of programming languages, code, and documentation. It provides methods
        for creating, updating, and querying the graph, as well as generating responses
        using a language model. The main purpose of the code is to provide a comprehensive
        tool for managing and utilizing this knowledge graph.
      constants.py: The code contains a dictionary that maps file extensions to programming/markup
        languages. This can be used to determine the language of a file based on its
        extension.""")))

if __name__ == "__main__":
    asyncio.run(main())


# message = [{'content': "You are a code explainer, given a piece of code, you need to explain what the code is doing and is trying to achieve. Use code symbols, like variable names, function names, etc whenever you can while explaining. We purposely omitted some code If the code has the comment '# Code replaced for brevity. See node_id ..... '.", 'role': 'system'}, {'content': 'import os\nimport uuid\n\nimport networkx as nx\nfrom blar_graph.graph_construction.languages.python.python_parser import PythonParser\nfrom blar_graph.graph_construction.utils import format_nodes\n\n\nclass GraphConstructor:\n    # Code replaced for brevity. See node_id 63e540a1-91b3-4f17-b687-f0b263eeebc2', 'role': 'user'}]
# async def main():
#     doc = await get_completion(message, model = "anthropic")
#     print(doc)

# asyncio.run(main())
