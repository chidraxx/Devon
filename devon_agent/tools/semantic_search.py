from devon_agent.semantic_search.code_graph_manager import CodeGraphManager
from devon_agent.semantic_search.code_graph_manager import CodeGraphManager
from devon_agent.tool import Tool, ToolContext

# import chromadb.utils.embedding_functions as embedding_functions
import logging
import os

from devon_agent.tools.utils import encode_path
from devon_agent.config import AgentConfig
import time
import traceback
from typing import List, Any
from pydantic import Field
from litellm import APIConnectionError

class SemanticSearch(Tool):
    db_path:str = Field(default=None)
    mapper:str = Field(default=None)
    storage_path:str = Field(default=None)
    vectorDB_path:str = Field(default=None)
    graph_path:str = Field(default=None)
    graph_path:str = Field(default=None)
    collection_name:str = Field(default=None)
    manager:Any = Field(default=None)

    @property
    def name(self):
        return "semantic_search"

    @property
    def supported_formats(self):
        return ["docstring", "manpage"]

    def setup(self, ctx):
        try:
            self.db_path = ctx["config"].db_path
            self.mapper = os.path.join(self.db_path, "project_mapper.json")
            self.storage_path = os.path.join(self.db_path, encode_path(ctx["config"].path, self.mapper))
            self.vectorDB_path = os.path.join(self.storage_path, "vectorDB")
            self.graph_path = os.path.join(self.storage_path, "graph")
            self.collection_name = "collection"

            ctx["config"].logger.info(f"storage_path {self.storage_path}")
            # print(self.vectorDB_path)
            # print("storage_path", self.storage_path)

            # self.db_path = ctx["config"].db_path
            # self.mapper = os.path.join(self.db_path, "project_mapper.json")
            # self.storage_path = "/Users/arnav/Desktop/pytest/pytest"
            # self.vectorDB_path = os.path.join(self.storage_path, "vectorDB")
            # self.graph_path = os.path.join(self.storage_path, "graph")
            # self.collection_name = "collection"
            # # print(self.vectorDB_path)
            # print("storage_path", self.storage_path)

            
            api_key = os.getenv("ANTHROPIC_API_KEY")
            openai_api_key=os.getenv("OPENAI_API_KEY")


            # configs:List[AgentConfig] = ctx["config"].agent_configs
            # for config in configs:
            #     if config.agent_name == "Devon":
            #         print()
            #         # api_key = config.api_key

            #     if config.agent_name == "Embedding":
            #         print()
            #         # openai_api_key = config.api_key


            self.manager = CodeGraphManager(
                graph_storage_path=self.graph_path, 
                db_path=self.vectorDB_path, 
                root_path=ctx["config"].path, 
                openai_api_key=openai_api_key, 
                api_key=openai_api_key, 
                model_name="gpt-4o-mini", 
                collection_name=self.collection_name
            )
            print("here")
            def progress_tracker(val):
                ctx["config"].logger.info(f"progress {val}")

            self.manager.create_graph(create_new=False, progress_tracker=progress_tracker)
            print("aaaaa")
            
        except:
            ctx["config"].logger.info(f"error in semantic search {traceback.print_exc()}")
            pass
        
    def cleanup(self, ctx):
        try:
            self.manager.delete_collection(self.collection_name)
        except Exception:
            pass
        pass

    def documentation(self, format="docstring"):
        match format:
            case "docstring":
                return self.function.__doc__
            case "manpage":
                return """
    SEMANTIC_SEARCH(1)               General Commands Manual               SEMANTIC_SEARCH(1)

    NAME
            semantic_search - Ask a qustion regarding the codebase and get an answer. Use this especially when you want to understand how the codebase works.

    SYNOPSIS
            semantic_search QUERY_TEXT

    DESCRIPTION
            The ask_codebase command executes a semantic search within the codebase for the given query. It then sends relevant code snippets to a language model, which generates a comprehensive answer.
            Utilize this tool to enhance your understanding of the codebase prior to task execution. Pose general inquiries that broaden your comprehension of the codebase, such as "What are...", "How does... function", "How to integrate ... to ...", or "Where does... occur". 
            Limit your query to a SINGLE QUESTION OR SENTENCE, avoiding conjunctions like "and" or "or". Refrain from using terms such as "files" in your query. 
            IMPORTANT: Do not accept the provided answer at face value. Always verify the information by examining each file path referenced in the response.

    OPTIONS
            QUERY_TEXT
                    The query text to search within the code base. Limit your query to a SINGLE QUESTION AND SENTENCE, avoiding conjunctions like "and" or "or". Refrain from using terms such as "files" or start with "show me" in your query.

    RETURN VALUE
            A string containing the final answer from the llm along with the paths to the code snippets

    EXAMPLES
            To search for how to create a new tool for the agent:

                    semantic_search "How do I create a new tool for the agent"
    """
            case _:
                raise ValueError(f"Invalid format: {format}")

    def function(self, ctx: ToolContext, query_text: str) -> str:
        """
        command_name: semantic_search
        description: Performs a semantic search for the specified query within the code base.
        signature: semantic_search [QUERY_TEXT]
        example: `semantic_search "How do I create a new tool for the agent"`
        """

        def query_with_retry(query_text):
            max_attempts = 3
            wait_time = 2  # in seconds
            api_key = os.getenv("ANTHROPIC_API_KEY")

            for attempt in range(max_attempts):
                try:
                    self.manager.api_key = api_key
                    result = self.manager.query_and_run_agent(query_text)
                    return result
                except APIConnectionError as e:
                    print(f"API Connection Error on attempt {attempt + 1}: {e}")
                    if attempt < max_attempts - 1:
                        time.sleep(wait_time)  # Wait before retrying
                    else:
                        raise

        # def format_response_for_llm(response):
        #     formatted_string = ""
        #     ids = response["ids"]
        #     documents = response["documents"]
        #     metadatas = response["metadatas"]
        #     for i in range(len(ids[0])):
        #         metadata = metadatas[0][i]
        #         document = documents[0][i]
        #         code = document.split("--code-- - \n")[1]
        #         formatted_string += f"path: {metadata.get('file_path')}\n"
        #         formatted_string += f"signature: {metadata.get('signature')}\n"
        #         formatted_string += f"start line: {metadata.get('start_line')}\n"
        #         formatted_string += f"end line: {metadata.get('end_line')}\n"
        #         formatted_string += f"code: \n{code}\n\n"
        #     return formatted_string

        try:
            # agent : TaskAgent = ctx["session"].agent
            # agent : TaskAgent = ctx["session"].agent
            # model_args = ModelArguments(
            #     model_name=agent.args.model,
            #     temperature=0.5,
            #     api_key=agent.args.api_key
            # )
            # opus = agent.current_model



            # Run the semantic search function
            # openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            #     api_key=os.environ.get("OPENAI_API_KEY"),
            #     model_name="text-embedding-ada-002"
            # )

            result = query_with_retry(query_text)

            result = f"""
**IMPORTANT: Please consider verify the answer by opening the relavent file paths and exploring around by using go_to_definition_or_references, if required, to see how it is connected to rest of the codebase. Feel free to ask another question to fully get the context to execute the user request and follow the CONSTRAINTS givent to you**
{result}
**IMPORTANT: Please consider verify the answer by opening the relavent file paths and exploring around by using go_to_definition_or_references, if required, to see how it is connected to rest of the codebase. Feel free to ask another question to fully get the context to execute the user request and follow the CONSTRAINTS givent to you**
"""
            # print(result)

            
            # collection_name = "devon-5"

            # response = self.manager.query(query_text)
            # response = self.manager.query(query_text)
            # print(response)
            # print(asyncio.run(get_completion(agent_prompt(query_text, (response)), size="large")))

            # collection = self.vectorDB.get_collection("devon-5", openai_ef)
            # result = collection.query(query_texts=[query_text], n_results=10)

            # print(result)

            # formated_response = format_response_for_llm(result)

            # Add the new query and response to the messages
            # self.messages.append({"content": f"The user's question: {query_text}\n\nOur tool's response: {response} \n\n Remember, be sure to give me relavent code snippets along with absolute file path while formulating an answer", "role": "user"})
            # self.messages.append({"content": f"The user's question: {query_text}\n\nOur tool's response: {response} \n\n Remember, be sure to give me relavent code snippets along with absolute file path while formulating an answer", "role": "user"})

            # # Use all the messages in the LLM call
            # response = opus.query(
            #     messages=self.messages,
            #     system_message="You are a senior software engineer who is expert in understanding large codebases. You are serving a user who asked a question about a codebase they have no idea about. We did semantic search with their question on the codebase through our tool and we are giving you the output of the tool. The tool's response will not be fully accurate. Only choose the code that looks right to you while formulating the answer. Your job is to frame the answer properly by looking at all the different code blocks and give a final answer. Your job is to make the user understand the new codebase, so whenever you are talking about an important part of the codebase mention the full file path and codesnippet, like the whole code of a small function or the relavent section of a large function, which will be given along with the code in the tool output"
            # )
            # # Use all the messages in the LLM call
            # response = opus.query(
            #     messages=self.messages,
            #     system_message="You are a senior software engineer who is expert in understanding large codebases. You are serving a user who asked a question about a codebase they have no idea about. We did semantic search with their question on the codebase through our tool and we are giving you the output of the tool. The tool's response will not be fully accurate. Only choose the code that looks right to you while formulating the answer. Your job is to frame the answer properly by looking at all the different code blocks and give a final answer. Your job is to make the user understand the new codebase, so whenever you are talking about an important part of the codebase mention the full file path and codesnippet, like the whole code of a small function or the relavent section of a large function, which will be given along with the code in the tool output"
            # )

            # Append the assistant's response to the messages
            # self.messages.append({"content": response, "role": "assistant"})
            
            return result
        
        except Exception as e:
            return str(e)
