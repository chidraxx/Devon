import uuid
import chromadb
import asyncio
import tiktoken
from devon_agent.semantic_search.graph_construction.core.graph_builder import GraphConstructor
from devon_agent.semantic_search.graph_traversal.encode_codegraph import (generate_doc_level_wise)
import chromadb.utils.embedding_functions as embedding_functions
import os
from  devon_agent.semantic_search.llm import run_model_completion, get_completion, agent_prompt, agent_prompt_v2, agent_prompt_v3
from devon_agent.semantic_search.constants import extension_to_language
import time
from devon_agent.semantic_search.llm import model_cost
from dotenv import load_dotenv
# from devon_agent.semantic_search.graph_construction.core.reranker import rerank_documents

class CodeGraphManager:
    def __init__(self, graph_storage_path, db_path, root_path, openai_api_key, api_key, model_name, collection_name):
        if not openai_api_key:
            raise ValueError("OpenAI API key is missing.")
        if not api_key:
            raise ValueError("API key is missing.")
        if model_name not in ["haiku", "groq", "gpt-4o-mini"]:
            raise ValueError("Unsupported model. Only 'haiku', 'gpt-4o-mini' and 'groq' are supported.")
        
        self.graph_storage_path = graph_storage_path
        self.db_path = db_path
        self.root_path = root_path
        self.openai_api_key = openai_api_key
        self.api_key = api_key
        self.model_name = model_name
        self.embedding_model_name = "text-embedding-3-small"
        self.openai_ef = embedding_functions.OpenAIEmbeddingFunction(
            api_key=self.openai_api_key,
            model_name= self.embedding_model_name
        )
        self.collection_name = collection_name
        self.languages = []
        self.ignore_dirs = []
        self.db_client = None
        

    def detect_languages(self):
        try:
            extensions = set()
            ignored_paths = set()

            def traverse_directory(path, ignored_paths):
                if not os.path.exists(path):
                    return
                gitignore_path = os.path.join(path, ".gitignore")
                if os.path.exists(gitignore_path):
                    with open(gitignore_path, "r") as gitignore_file:
                        for line in gitignore_file:
                            line = line.strip()
                            if line and not line.startswith("#"):
                                normalized_path = os.path.normpath(line)
                                absolute_path = os.path.abspath(os.path.join(path, normalized_path))
                                ignored_paths.add(absolute_path)

                for entry in os.scandir(path):
                    if entry.name.startswith(".") or os.path.abspath(entry.path) in ignored_paths:
                        continue
                    if entry.is_file():
                        ext = os.path.splitext(entry.name)[1]
                        if ext:
                            extensions.add(ext)
                    elif entry.is_dir():
                        traverse_directory(entry.path, ignored_paths)

            traverse_directory(self.root_path, ignored_paths)
            self.languages = list({extension_to_language.get(ext) for ext in extensions if extension_to_language.get(ext)})
            print("Detected languages:", self.languages)
        
        except Exception as e:
            print(f"An error occurred while detecting languages: {e}")
            raise

    def create_graph(self, create_new = False, progress_tracker=None, ctx = None):
        if not self.root_path:
            raise ValueError("Root path is not provided")

        # Ensure the database path exists
        if not os.path.exists(self.db_path):
            os.makedirs(self.db_path)
            print(f"Created database directory at {self.db_path}")

        # Initialize the database client
        if self.db_client is None:
            self.db_client = chromadb.PersistentClient(path=self.db_path)

        # self.detect_languages()

        graph_path = os.path.join(self.graph_storage_path, f"graph.pickle")
        hash_path = os.path.join(self.graph_storage_path, f"hashes.json")

        # Check if collection exists
        try:
            collection = self.db_client.get_collection(name=self.collection_name, embedding_function=self.openai_ef)
            collection_exists = True
            print("Number of documents in collections: ", collection.count())
        except ValueError:
            print("Vector Collection not found")
            # collection = self.db_client.create_collection(name=self.collection_name, embedding_function=self.openai_ef)
            collection_exists = False

        # Determine if we need to create a new graph or update the existing one
        graph_exists = os.path.exists(graph_path)
        hash_exists = os.path.exists(hash_path)
        create_new_graph = not collection_exists or not graph_exists or not hash_exists or create_new

        # If the collection exists but the graph or hash does not, clear the collection
        if collection_exists and create_new_graph:
            print(f"Creating a new graph. Clearing all the entries in the collection.")
            self.db_client.delete_collection(name=self.collection_name)
            self.db_client.create_collection(name=self.collection_name, embedding_function=self.openai_ef)
        

        # Initialize the graph constructor
        self.graph_constructor = GraphConstructor(
            # language,
            self.root_path,
            self.graph_storage_path,
            not create_new_graph,  # Pass False to create new graph if needed
            ignore_dirs=["__pycache__"]
        )

        # Build or update the graph and get the actions list
        actions, current_hashes = self.graph_constructor.build_or_update_graph(ctx = ctx)

        print(actions)



        # Generate documentation for the updated graph
        asyncio.run(generate_doc_level_wise(self.graph_constructor.graph, actions, api_key=self.api_key, model_name=self.model_name, progress_tracker=progress_tracker, ctx = ctx))

        # Update the collection
        self.update_collection(actions)

        

        # Save the updated graph and hashes
        self.graph_constructor.save_graph(graph_path)
        self.graph_constructor.save_hashes(hash_path, current_hashes)

        # collection = self.db_client.get_collection(name=self.collection_name, embedding_function=self.openai_ef)


            # except ValueError as e:
            #     print(f"Error: {e}. Language {language} is not supported.")
            # except Exception as e:
            #     print(f"An unexpected error occurred while building the graph for {language}: {e}")

    def estimate_cost(self):
        def find_node_id_by_file_path(dir_node_id, file_path):
            for child in self.graph_constructor.graph.successors(dir_node_id):
                if self.graph_constructor.graph.nodes[child].get("file_path") == file_path:
                    return child
            return None

        def collect_node_ids(node_id, collected_ids):
            collected_ids.add(node_id)
            for child in self.graph_constructor.graph.successors(node_id):
                collect_node_ids(child, collected_ids)
        
        
        self.graph_constructor = GraphConstructor(
            self.root_path,
            self.graph_storage_path,
            False,
            ignore_dirs=["__pycache__"]
        )

        actions, current_hashes = self.graph_constructor.build_or_update_graph(ctx = ctx)

        all_collected_node_ids = set()

        for file_path, dir_node_id in actions["add"] + actions["update"]:
            file_node_id = find_node_id_by_file_path(dir_node_id, file_path)
            if file_node_id:
                collected_ids = set()
                collect_node_ids(file_node_id, collected_ids)
                all_collected_node_ids.update(collected_ids)

        input_token = 0
        for node_id in all_collected_node_ids:
            try:
                text = self.graph_constructor.graph.nodes[node_id].get("text", " ")
                input_token += self.count_tokens(text)
            except Exception as e:
                print(f"Error calculating tokens for node {node_id}: {e}")
                print("File path:", self.graph_constructor.graph.nodes[node_id].get("file_path", ""))

        output_token = 0.5 * input_token  # Rough estimation

        cost = model_cost(self.model_name, input_token, output_token)
        cost += model_cost(self.embedding_model_name, input_token, output_token)

        return cost


        # for file_path in file_paths:
            

        # for file_path in file_paths:
            





    def update_collection(self, actions):
        try:
            collection_name = self.collection_name

            # Get or create the collection
            try:
                collection = self.db_client.get_collection(name=collection_name, embedding_function=self.openai_ef)
            except ValueError:
                print("Collection not found, creating a new one.")
                collection = self.db_client.create_collection(name=collection_name, embedding_function=self.openai_ef)
                print("Collection created.")

            def split_nodes(node_id, doc, code, node_data):
                combined_text = f"documentation - \n{doc} \n--code-- - \n{code}"
                combined_tokens = self.count_tokens(combined_text)
                if combined_tokens > 8000:
                    print("splitting nodes")

                    # Split the code part if the combined text exceeds 8000 tokens
                    code_tokens = self.count_tokens(code)
                    if code_tokens > 8000:
                        num_code_parts = (code_tokens // 8000) + 1
                        code_parts = [code[i * 8000:(i + 1) * 8000] for i in range(num_code_parts)]
                        code_part_ids = [f"{node_id}-code-{i}" for i in range(num_code_parts)]
                        code_part_metadatas = [{"split_type": "code", **node_data} for code_part_id in code_part_ids]
                    else:
                        # Add the entire code part
                        code_parts = [code]
                        code_part_ids = [f"{node_id}-code"]
                        code_part_metadatas = [{"split_type": "code", **node_data}]

                    # Create the final parts
                    doc_metadata = {"split_type": "documentation", **node_data}
                    doc_id = f"{node_id}-doc"
                    docs = [doc] + code_parts
                    ids = [doc_id] + code_part_ids
                    metadatas = [doc_metadata] + code_part_metadatas
                else:
                    docs = [combined_text]
                    ids = [node_id]
                    metadatas = [node_data]

                return ids, docs, metadatas   
                   
             # Helper function to find node_id by file_path using parent_node_id
            def find_node_id_by_file_path(parent_node_id, file_path):
                for child in self.graph_constructor.graph.successors(parent_node_id):
                    if self.graph_constructor.graph.nodes[child].get("file_path") == file_path:
                        return child
                return None

            # Helper function to process node and its children
            def process_node_recursively(node_id):
                # print("node getting added", node_id)
                node_data = self.graph_constructor.graph.nodes[node_id]
                code = node_data.get("text", "")
                doc = node_data.get("doc", "")
                metadata = {
                    "type": node_data.get("type", ""),
                    "name": node_data.get("name", ""),
                    "file_path": node_data.get("file_path", ""),
                    "start_line": node_data.get("start_line", ""),
                    "end_line": node_data.get("end_line", ""),
                    "node_id": node_data.get("node_id", ""),
                    "file_node_id": node_data.get("file_node_id", ""),
                    "signature": node_data.get("signature", ""),
                    "leaf": node_data.get("leaf", ""),
                    "lang": node_data.get("lang", ""),
                    "code": node_data.get("text", ""),
                    "doc": node_data.get("doc", "")
                }

                if metadata is None:
                    metadata = {}

                # print("node_id", node_id)
                ids, docs, metadatas = split_nodes(node_id, doc, code, metadata)
                # print(ids)
                all_ids.extend(ids)
                all_docs.extend(docs)
                all_metadatas.extend(metadatas)

                for child in self.graph_constructor.graph.successors(node_id):
                    process_node_recursively(child)

            # Process delete actions
            for file_path, parent_node_id in actions["delete"]:
                print("deleting nodes from", file_path)
                collection.delete(where={"file_path": file_path})

            # Delete nodes that are going to be updated
            for file_path, parent_node_id in actions["update"]:
                print("deleting nodes from", file_path)
                collection.delete(where={"file_path": file_path})

            # Collect all nodes to be added or updated
            all_ids = []
            all_docs = []
            all_metadatas = []

            # node_proccessed = set()

            for file_path, parent_node_id in actions["add"] + actions["update"]:
                node_id = find_node_id_by_file_path(parent_node_id, file_path)
                if not node_id:
                    print(f"No node found for file path: {file_path}")
                    continue

                # node_proccessed.add(node_id)

                process_node_recursively(node_id)

            # Generate embeddings for all documents at once
            # if all_docs:
            #     embeddings = self.openai_ef(all_docs)
            #     # Add all nodes to the collection
            #     # print(all_metadatas)
            #     collection.add(ids=all_ids, documents=all_docs, embeddings=embeddings, metadatas=all_metadatas)

            for doc_index in range(len(all_docs)):
                if all_docs[doc_index].strip() == "":
                    all_docs[doc_index] = "  "
                
                if self.count_tokens(all_docs[doc_index]) > 8000:
                    print("doc size exeeding 8000 tokens", all_docs[doc_index])
                    all_docs[doc_index] = all_docs[doc_index][0:(8000*3)]


            batch_size = 500
            num_docs = len(all_docs)
            max_retries = 10
            max_db_retries = 2
            for i in range(0, num_docs, batch_size):
                batch_ids = all_ids[i:i + batch_size]
                batch_docs = all_docs[i:i + batch_size]
                batch_metadatas = all_metadatas[i:i + batch_size]
                
                retries = 0
                embeddings=[]

                while retries < max_retries:
                    try:
                        embeddings = self.openai_ef(batch_docs)
                        break
                    except Exception as e:
                        print(f"Error: {e}. Retrying in 5 seconds...")
                        time.sleep(5)
                        retries += 1
                        
                if retries == max_retries:
                    print(f"Failed to add batch starting at index {i} after {max_retries} retries.")

                while retries < max_db_retries:
                    try:
                        collection.add(ids=batch_ids, documents=batch_docs, embeddings=embeddings, metadatas=batch_metadatas)
                        print("batch embedded and added")
                        break
                    except Exception as e:
                        print(f"Error: {e}. Retrying in 5 seconds...")
                        time.sleep(5)
                        retries += 1
                        
                if retries == max_retries:
                    print(f"Failed to add batch starting at index {i} after {max_retries} retries.")
                
                

        except Exception as e:
            print(f"An error occurred while updating the collection: {e}")
            raise


    def query_collection(self, query_text, top_n):
        # Helper function to combine split nodes
        processed_nodes=set()
        def combine_split_nodes(collection, documents, metadatas):
            combined_results = []

            for doc, metadata in zip(documents, metadatas):
                node_id = metadata.get("node_id")

                # print(metadata)

                if node_id in processed_nodes:
                    continue

                processed_nodes.add(node_id)

                # Check if the document is already combined or split
                if metadata.get("split_type") is None:
                    # Document is already combined
                    combined_results.append({
                        "doc": doc,
                        "code": "",
                        "metadata": metadata,
                        "combined_text": doc
                    })
                else:
                    # Fetch all parts of the split node
                    node_parts = collection.get(where={"node_id": node_id})
                    doc_part = ""
                    code_parts = []

                    # print(node_parts["ids"])
                    # print(node_parts["metadatas"])

                    for part_doc, part_metadata, part_id in zip(node_parts["documents"], node_parts["metadatas"], node_parts["ids"]):
                        if part_metadata.get("split_type") == "documentation":
                            doc_part = part_doc
                        elif part_metadata.get("split_type") == "code":
                            # Extract the index from the code part ID
                            index = int(part_id.split("-")[-1])
                            code_parts.append((index, part_doc))

                    # Combine the code parts in the correct order
                    code_parts.sort(key=lambda x: x[0])
                    code_part = "\n--code-- - \n".join([part[1] for part in code_parts])
                    # print(len(code_parts))

                    combined_text = f"documentation - \n{doc_part} \n{code_part}"
                    combined_results.append({
                        "doc": doc_part.get("doc", ""),
                        "code": metadata.get("text", ""),
                        "metadata": metadata,
                        "combined_text": combined_text
                    })

            return combined_results
        
        try:
            collection_name = self.collection_name

            collection = self.db_client.get_collection(name=collection_name, embedding_function=self.openai_ef)
            
            print("starting fetch")
            result = collection.query(query_texts=[query_text], n_results=top_n)
            print("finished fetch")

            documents = result["documents"][0]
            metadatas = result["metadatas"][0]

            combined_results = combine_split_nodes(collection, documents, metadatas)

            self.format_response_for_llm(combined_results)

            # print("===========")

            # reranked = rerank_documents(query_text, documents, metadatas, "/Users/arnav/Desktop/codegraph processed/devon/v1")

            # self.format_response_for_llm(reranked)

            return combined_results

        except Exception as e:
            print(f"An error occurred while querying the collection: {e}")
            raise

    @staticmethod
    def count_tokens(text: str) -> int:
        encoding = tiktoken.get_encoding("cl100k_base")
        try:
            num_tokens = len(encoding.encode(text, allowed_special={" "}, disallowed_special=(encoding.special_tokens_set - {" ", '<|endoftext|>'})))
        except Exception as e:
            print(f"Error encoding text: {e}")
            num_tokens = 0
        return num_tokens

    def query_and_run_agent(self, query_text):

        try:
            # Ensure the database path exists
            if not os.path.exists(self.db_path):
                raise ValueError(f"Database path '{self.db_path}' does not exist.")

            # Initialize the database client if it's not already initialized
            if self.db_client is None:
                self.db_client = chromadb.PersistentClient(path=self.db_path)

            # Check if the collection exists
            try:
                self.db_client.get_collection(name=self.collection_name, embedding_function=self.openai_ef)
            except ValueError:
                raise ValueError(f"Collection '{self.collection_name}' does not exist.")
                # print("collection not found, creating a collection")
                # self.db_client.create_collection(name=self.collection_name, embedding_function=self.openai_ef)

            # Step 1: Run the query method
            combined_results = self.query_collection(query_text, top_n = 35)
            # combined_results = []

            # for result in combined_results:
            #     print("here")
            # #     result["metadata"]["code"]=""
            # #     result["metadata"]["summary"]=""
            # #     result["metadata"]["doc"]=""
            #     print(result["metadata"])

            # Step 2: Format the response
            # print("code", combined_results[0]['metadata']['code'])
            formatted_response = self.format_response_for_llm(combined_results[:20])
            # print(formatted_response)


            # async def run_agents():

                

            #     # task1 = run_model_completion("groq-70b", self.api_key, agent_prompt(query_text, formatted_response))
            #     task2 = run_model_completion("sonnet", self.api_key, agent_prompt_v2(query_text, formatted_response))
            #     results = await asyncio.gather(task2, task2)
            #     return results
            

            # agent_response1, agent_response2 = asyncio.run(run_agents())

            # Step 3: Run the agent with the formatted response
            agent_response=""
            agent_response = asyncio.run(
                run_model_completion("sonnet", self.api_key, agent_prompt_v2(query_text, formatted_response))
            )

            # agent_
            # response = asyncio.run(
            #      get_completion(agent_prompt(query_text, formatted_response), self.api_key, size = "medium" )
            # )
            print()
            print()
            print("=============================")

            return agent_response

        except Exception as e:
            print(f"An error occurred while running the query and agent: {e}")
            raise

    def format_response_for_llm(self, response):
        try:
            formatted_string = ""
            for item in range(len(response)):
                metadata = response[item]["metadata"]
                print(metadata.get('file_path'))
                print(metadata.get('signature'))
                # print(metadata.get('start_line'))
                # print(metadata.get('end_line'))
                # print(metadata.get('doc'))

            for item in response:
                metadata = item["metadata"]
                formatted_string += f"path: {metadata.get('file_path')}\n"
                formatted_string += f"signature: {metadata.get('signature')}\n"
                formatted_string += f"start line: {metadata.get('start_line')}\n"
                formatted_string += f"end line: {metadata.get('end_line')}\n"
                formatted_string += f"code: \n{metadata.get('code')}\n\n"
            return formatted_string
        except Exception as e:
            print(f"An error occurred while formatting the response: {e}")
        raise


    def generate_embeddings(self, docs):
        try:
            return self.openai_ef(docs)
        except Exception as e:
            print(f"An error occurred while generating embeddings: {e}")
            raise

    def load_graph(self):
        try:
            self.graph_constructor.load_graph(self.graph_storage_path)
        except FileNotFoundError as e:
            print(f"Graph file not found: {e}")
            raise
        except Exception as e:
            print(f"An error occurred while loading the graph: {e}")
            raise



if __name__ == "__main__":

        load_dotenv()

    # try:
        # Initialize the CodeGraphManager
        root_path = "/Users/arnav/Desktop/pytest/pytest"
        root_path = "/Users/arnav/Desktop/devon/Devon"
        

        graph_storage_path = os.path.join(root_path, "graph")
        db_path = os.path.join(root_path, "vectorDB")

        openai_api_key = os.getenv("OPENAI_API_KEY")
        anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        collection_name = "collection"

        root_path = "/Users/arnav/Desktop/pytest/pytest"
        root_path = "/Users/arnav/Desktop/devon/Devon"
        manager = CodeGraphManager(graph_storage_path, db_path, root_path, openai_api_key, anthropic_api_key, "gpt-4o-mini", collection_name)
        # manager.create_graph(create_new=False)
        # result = (manager.query_and_run_agent("how to create an integrate tools"))
        # # result = (manager.query_and_run_agent("Is the codebase using jupiter notebooks"))
        # result = (manager.query_and_run_agent("How to integrate a tools"))
        # result = (manager.query_and_run_agent("how to create an agent environment for juipter notebook"))
        # result = (manager.query_and_run_agent("how do I update the tracking of the indexing process"))
        # result = (manager.query_and_run_agent("Show me the code for the is_rewrite_disabled method in the assertion rewrite mechanism of pytest."))
        # print(result)

        # print(manager.estimate_cost())

        # root_path = "/Users/arnav/Desktop/codegraph processed/devon/v3"

        # graph_storage_path = os.path.join(root_path, "graph")
        # db_path = os.path.join(root_path, "vectorDB")

        # openai_api_key = os.getenv("OPENAI_API_KEY")
        # anthropic_api_key = os.getenv("ANTHROPIC_API_KEY")
        # collection_name = "collection"

        # root_path = "/Users/arnav/Desktop/devon/Devon"
        # manager = CodeGraphManager(graph_storage_path, db_path, root_path, openai_api_key, anthropic_api_key, "haiku", collection_name)
        # # manager.create_graph(create_new=False)

        # result = (manager.query_and_run_agent("show me all the files that have llm prompts"))
        # print(result)
        

        # root_path = "/Users/arnav/Desktop/codegraph_processed/devon/v3"

        # graph_storage_path = os.path.join(root_path, "graph")
        # db_path = os.path.join(root_path, "vectorDB")

        # openai_api_key = os.getenv("OPENAI_API_KEY")
        # collection_name = "collection"

        # root_path = "/Users/arnav/Desktop/devon/Devon"
        # manager = CodeGraphManager(graph_storage_path, db_path, root_path, openai_api_key, anthropic_api_key, "gpt-4o-mini", collection_name)
        # # manager.create_graph(create_new=True)

        # # result = (manager.query_and_run_agent("which tool is responsible for opening files"))
        # # result = (manager.query_and_run_agent("What are environments"))
        # result = (manager.query_and_run_agent("how to create an agent environment for juipter notebook"))
        # print(result)

        # print(openai_ef([" "]))

        # graph = GraphConstructor()
        # graph.build_graph(path = "/Users/arnav/Desktop/codegraph/code-base-agent")

        # Create the graph
        # manager.create_graph(create_new=False)
        # manager.query_collection("what about the app")
        # result = (manager.query_and_run_agent("what is the app about"))

        
        # for i in results:
        # Uncomment to perform operations on the graph
        # query_text = "How do I call an llm model in the tool class"
        # collection_name = "code-graph-14"
        # response = manager.load_graph_and_perform_operations(query_text, collection_name)
        # print(response)
        
    # except Exception as e:
    #     (f"An error occurred in the main execution: {e}")


