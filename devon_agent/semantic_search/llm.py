from dotenv import load_dotenv
import os
from litellm import acompletion
import asyncio

    
def config_text_explainer_and_summary_prompt(text, file_path):
    user_prompt = f"File Path: {file_path}\n" + str(text)

    message = [{"content": f"""You are an expert software engineer. You will receive either a text, json, markdown, yaml, or config file from a codebase. Your job is to quickly explain the purpose of the file and mention only the most important details,

Also give a summary. Summarize the file purpose and maybe its content in 1 line

wrap the description in <description> tag and summary in <summary> tag

""", "role": "system"},
                {"content": f"{user_prompt}", "role": "user"}]
    
    return message

def code_explainer_and_summary_prompt(function_code, children_summaries):
    user_prompt = str(function_code) + "\n" + "Here are the summaries for all the definitions:" + "\n" + str(children_summaries)

    message = [{"content": f"""You are a code explainer, given a piece of code and summaries of its child functions or classes, you need to explain what the code is doing and is trying to achieve. Use code symbols, like variable names, function names, etc whenever you can while explaining. We purposely omitted some code If the code has the comment '# Code replaced for brevity. See node_id ..... ', so give us your best guess on what the whole code is trying to do using the summaries given of the definitions. Don't repeat the summaries.

Also give a summary. Mention what the code contains and what is the purpose. Use the summary of definitions if given. Have maximum of 3 lines

wrap the description in <description> tag and summary in <summary> tag
""", "role": "system"},
                {"content": f"{user_prompt}", "role": "user"}]
    
    return message

def config_text_explainer_prompt_groq(text, file_path):
    user_prompt = f"File Path: {file_path}\n" + str(text)

    message = [{"content": f"""You are an expert software engineer. You will receive either a text, json, markdown, yaml, or config file from a codebase. Your job is to quickly explain the purpose of the file and mention only the most important details,
""", "role": "system"},
                {"content": f"{user_prompt}", "role": "user"}]
    
    return message

def config_text_summary_prompt_groq(text, file_path):
    user_prompt = f"File Path: {file_path}\n" + str(text)

    message = [{"content": f"""You are an expert software engineer. You will receive either a text, json, markdown, yaml, or config file from a codebase. Your job is to quickly summarize the purpose of the file and maybe mention only the most important details in MAX 1 line

""", "role": "system"},
                {"content": f"{user_prompt}", "role": "user"}]
    
    return message

def code_explainer_prompt_groq(function_code, children_summaries):
    user_prompt = str(function_code) + "\n" + "Here are the summaries for all the definitions:" + "\n" + str(children_summaries)

    message = [{"content": f"""You are a code explainer, given a piece of code and summaries of its child functions or classes, you need to explain what the code is doing and is trying to achieve. Use code symbols, like variable names, function names, etc whenever you can while explaining. We purposely omitted some code If the code has the comment '# Code replaced for brevity. See node_id ..... ', so give us your best guess on what the whole code is trying to do using the summaries given of the definitions. Don't repeat the summaries.""", "role": "system"},
                {"content": f"{user_prompt}", "role": "user"}]
    
    return message
# def file_summary_prompt(function_code):
#     message = [{"content": f"Mention the main class or functions and say what their purpose is. Dont mention about commented code. Have maximum of 3  Be as concise as possible", "role": "system"},
#                {"content": f"{function_code}", "role": "user"}]
    
#     return message    

def code_summary_prompt_groq(function_code):
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
            elif size == "medium":
                response = await acompletion(
                    model="claude-3-5-sonnet-20240620",
                    messages=messages,
                    temperature=0.5,
                    max_tokens=4096,
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
    
def model_cost(model_name, input, output):
    #per million tokens
    model_cost = {
        "haiku": {
            "input": "0.25",
            "output": "1.25"
        },
        "sonnet": {
            "input": "3",
            "output": "15"
        },
        "opus": {
            "input": "15",
            "output": "75"
        },
        "gpt-4o": {
            "input": "5.00",
            "output": "15.00"
        },
        "gpt-4o-2024-05-13": {
            "input": "5.00",
            "output": "15.00"
        },
        "gpt-3.5-turbo-0125": {
            "input": "0.50",
            "output": "1.50"
        },
        "gpt-3.5-turbo-instruct": {
            "input": "1.50",
            "output": "2.00"
        },
        "text-embedding-3-small": {
            "input": "0.02",
            "output": "0"
        },
        "text-embedding-3-large": {
            "input": "0.13",
            "output": "0"
        },
        "text-embedding-ada-002": {
            "input": "0.10",
            "output": "0"
        },
        "groq": {
            "input": str((0.05)*2), #It requires two different prompts for a node, one for summary and one for description
            "output": "0.08",
        }
    }

    # if model_name == "haiku":
    #     return cost["haiku"]
    # elif model_name == "groq":
    #     return cost["groq"]
    # elif model_name == "text-embedding-3-small":
    #     return cost["text-embedding-3-small"]
    # else:
    #     return 

    if model_name not in model_cost:
        raise ValueError(f"model name is invalid, {model_name}")

    return (input * float(model_cost[model_name]["input"]) + output * float(model_cost[model_name]["output"]))/ 1000000
    



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
    # api_key = os.getenv("GROQ_API_KEY")
    api_key = os.getenv("ANTHROPIC_API_KEY")
    code = """
<!-- PROJECT LOGO -->
<div align="center">
  <h1 align="center">Devon: An open-source pair programmer</h1>
</div>
<div align="center">
  <a href="https://github.com/entropy-research/Devon/graphs/contributors"><img src="https://img.shields.io/github/contributors/entropy-research/devon?style=for-the-badge&color=lime" alt="Contributors"></a>
  <a href="https://github.com/entropy-research/Devon/network/members"><img src="https://img.shields.io/github/forks/entropy-research/devon?style=for-the-badge&color=orange" alt="Forks"></a>
  <a href="https://github.com/entropy-research/Devon/stargazers"><img src="https://img.shields.io/github/stars/entropy-research/devon?style=for-the-badge&color=yellow" alt="Stargazers"></a>
  <a href="https://github.com/entropy-research/Devon/issues"><img src="https://img.shields.io/github/issues/entropy-research/devon?style=for-the-badge&color=red" alt="Issues"></a>
  <br/>
  <a href="https://github.com/entropy-research/Devon/blob/main/LICENSE"><img src="https://img.shields.io/github/license/entropy-research/devon?style=for-the-badge&color=blue" alt="Apache 2.0 License"></a>
  <a href="https://discord.gg/p5YpZ5vjd9"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a>
  <br/>


https://github.com/entropy-research/Devon/assets/61808204/f3197a56-3d6d-479f-bc0e-9cffe69f159b
</div>

### How do y'all ship so quickly?
<a href="https://discord.gg/p5YpZ5vjd9"><img src="https://img.shields.io/badge/Discord-Join%20Us-purple?logo=discord&logoColor=white&style=for-the-badge" alt="Join our Discord community"></a> 
← We have a __**community-driven Dev Team**__ for this repo. Come join us! It's great.
  
# Installation

## Prerequisites

1. `node.js` and `npm`
2. `pipx`, if you don't have this go [here](https://pipx.pypa.io/stable/installation/)
3. API Key <samp>(just one is required)</samp>
   - [**Anthropic**](https://console.anthropic.com/settings/keys)
    - [**OpenAI**](https://platform.openai.com/api-keys)
    - [**Groq**](https://console.groq.com/keys) (not released in package yet, run locally)
> We're currently working on supporting Windows! (Let us know if you can help)


"""
    # doc = await run_model_completion("groq", api_key, config_text_explainer_prompt_groq(code, "Devon/Readme.md"))
    # summary = await run_model_completion("groq", api_key, config_text_summary_prompt_groq(code, "Devon/Readme.md"))

    print(await get_completion(config_text_explainer_and_summary_prompt(code, ""), api_key, size = "medium" ))
    # print(doc)
    # print()
    # print(summary)

if __name__ == "__main__":
    asyncio.run(main())


# message = [{'content': "You are a code explainer, given a piece of code, you need to explain what the code is doing and is trying to achieve. Use code symbols, like variable names, function names, etc whenever you can while explaining. We purposely omitted some code If the code has the comment '# Code replaced for brevity. See node_id ..... '.", 'role': 'system'}, {'content': 'import os\nimport uuid\n\nimport networkx as nx\nfrom blar_graph.graph_construction.languages.python.python_parser import PythonParser\nfrom blar_graph.graph_construction.utils import format_nodes\n\n\nclass GraphConstructor:\n    # Code replaced for brevity. See node_id 63e540a1-91b3-4f17-b687-f0b263eeebc2', 'role': 'user'}]
# async def main():
#     doc = await get_completion(message, model = "anthropic")
#     print(doc)

# asyncio.run(main())
