import asyncio
from collections import deque
from devon_agent.semantic_search.llm import config_text_summary_prompt_groq, config_text_explainer_prompt_groq, config_text_explainer_and_summary_prompt, run_model_completion, code_explainer_and_summary_prompt, code_explainer_prompt_groq, code_summary_prompt_groq, directory_summary_prompt
import asyncio
from collections import deque
import openai
import os
import pickle
import yaml
import tiktoken

def count_tokens(text: str) -> int:
    encoding = tiktoken.get_encoding("cl100k_base")
    try:
        num_tokens = len(encoding.encode(text, allowed_special={" "}, disallowed_special=(encoding.special_tokens_set - {" ", '<|endoftext|>'})))
    except Exception as e:
        print(f"Error encoding text: {e}")
        num_tokens = 0
    return num_tokens



async def process_code_node(graph, node, model_name, api_key):
    node_data = graph.nodes[node]
    code = node_data.get("text", "")
    lang = node_data.get("lang", "")
    retries = 8
    wait_time = 10  # seconds
    max_retries_no_status = 3  # max retries if exception does not have status_code attribute
    rate_limit_encountered = False
    doc = None
    summary = None
    file_path = node_data.get("file_path")

    # Gather child summaries and signatures
    child_nodes = [target for _, target in graph.out_edges(node)]
    children_summaries = []
    for child in child_nodes:
        child_data = graph.nodes[child]
        child_summary = child_data.get("summary", "")
        child_signature = child_data.get("signature", "")
        if child_summary and child_signature:
            children_summaries.append(f"{child_signature}\n{child_summary}")
    children_summaries_text = "\n".join(children_summaries)

    if count_tokens(code) > 8000:
        tokens = count_tokens(code)
        factor = tokens / 8000
        code = code[ : (int((len(code)//factor)) - 500)]
        if count_tokens(code) > 8000:
            return 1, ""

    for attempt in range(retries):
        try:
            if model_name == "groq":
                if lang == "no_code":
                    doc = await run_model_completion(model_name, api_key, config_text_explainer_prompt_groq(code, file_path))
                    summary = await run_model_completion(model_name, api_key, config_text_summary_prompt_groq(code, file_path))
                else:
                    doc = await run_model_completion(model_name, api_key, code_explainer_prompt_groq(code, children_summaries_text))
                    summary = await run_model_completion(model_name, api_key, code_summary_prompt_groq(code))
            else:
                if lang == "no_code":
                    result = await run_model_completion(model_name, api_key, config_text_explainer_and_summary_prompt(code, file_path))
                else:
                    result = await run_model_completion(model_name, api_key, code_explainer_and_summary_prompt(code, children_summaries_text))
                doc_start = result.find("<description>") + len("<description>")
                doc_end = result.find("</description>")
                summary_start = result.find("<summary>") + len("<summary>")
                summary_end = result.find("</summary>")
                
                doc = result[doc_start:doc_end].strip()
                summary = result[summary_start:summary_end].strip()

            break  # If the call succeeds, exit the loop
        except Exception as e:
            if isinstance(e, openai.OpenAIError):
                if hasattr(e, 'status_code'):
                    status_code = e.status_code
                    rate_limit_encountered=True
                    if status_code == 429:
                        if attempt < retries - 1:
                            print(f"Rate limit exceeded. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{retries})")
                            await asyncio.sleep(wait_time)
                        else:
                            raise e  # Raise the exception after the last attempt
                    elif status_code >= 500:
                        await asyncio.sleep(wait_time)
                    else:
                        raise e
                else:
                    if attempt < max_retries_no_status - 1:
                        print(f"Exception without status_code. Retrying in {wait_time} seconds... (Attempt {attempt + 1}/{max_retries_no_status})")
                        await asyncio.sleep(wait_time)
                    else:
                        raise e  # Raise the exception after the max retries
            else:
                raise e
            
    # print("==========")
    # print(f"Codeblock name: {node_data.get('signature')}, {node_data.get('type')}")
    # print("Level:", node_data.get("level"))
    # print("Path:", node_data.get("file_path"))
    # # print(code)
    # print(doc)
    # print()

    doc += "\n\n" + summary
    graph.nodes[node]["doc"] = doc
    if summary is not None:
        graph.nodes[node]["summary"] = summary

    return rate_limit_encountered, doc

async def process_level_async(graph, nodes, level, batch_size, model_name, api_key):
    rate_limits = 0
    successful_completions = 0

    for i in range(0, len(nodes), batch_size):
        batch = nodes[i:i + batch_size]
        tasks = []
        for node in batch:
            node_type = graph.nodes[node].get("type", "")
            if node_type == "directory":
                # tasks.append(process_directory_node(graph, node, model_name))
                pass
            else:
                tasks.append(process_code_node(graph, node, model_name, api_key))
        results = await asyncio.gather(*tasks)

        print("done max batch_size,", batch_size)
        
        for node, result in zip(batch, results):
            if isinstance(result, tuple) and result[0]:  # Check if rate_limit_encountered is True
                rate_limits += 1
            else:
                successful_completions += 1

    return rate_limits, successful_completions



async def generate_doc_level_wise(graph, actions, api_key, model_name="groq", edge_types=["FUNCTION_DEFINITION", "CLASS_DEFINITION", "CONTAINS", "INTERFACE_DECLARATION", "METHOD_DEFINITION", "UNKNOWN"], batch_size=50, minimum_batch = 4):
    files_to_process = actions["add"] + actions["update"]
    file_file_paths = list(map(lambda x: x[0], files_to_process))

    root_node = graph.graph["root_id"]

    queue = deque([(root_node, 0)])
    visited = set()
    node_levels = {}

    while queue:
        node, level = queue.popleft()
        if node not in visited:
            visited.add(node)
            node_levels[node] = level
            child_nodes = [target for _, target, data in graph.out_edges(node, data=True) if data['type'] in edge_types]
            for child_node in child_nodes:
                queue.append((child_node, level + 1))

    max_level = max(node_levels.values())

    current_batch_size = batch_size
    for level in range(max_level, -1, -1):
        nodes_to_process = [
            node for node, node_level in node_levels.items()
            if node_level == level and (graph.nodes[node].get("file_path") in file_file_paths and graph.nodes[node].get("type") != "directory")
        ]

        if nodes_to_process:
            current_batch_size = max(current_batch_size, minimum_batch)
            rate_limits, successful_completions = (await process_level_async(graph, nodes_to_process, level, batch_size=current_batch_size, model_name=model_name, api_key=api_key))
            if rate_limits > len(nodes_to_process) * 0.2:  # More than 20% rate limits
                current_batch_size = max(1, current_batch_size // 2)
            elif rate_limits == 0:
                current_batch_size = min(current_batch_size + (current_batch_size // 10), 150)  # Increase batch size by 10% up to a max of 100

            print(f"Processed level {level} with batch size {current_batch_size}: {successful_completions} successful, {rate_limits} rate limits")
    
    # Process the root directory node after all file nodes have been processed
    await process_directory_node(graph, root_node, model_name, api_key)
    print(f"Processed root directory: {graph.nodes[root_node].get('file_path', '')}")



async def process_directory_node(graph, node, model_name, api_key, threshold=25):
    async def process_recursive(current_node):
        node_data = graph.nodes[current_node]

        # print(node_data.get("file_path"))
        
        # Process child directories first
        if node_data.get("type") == "directory":
            for _, child_node in graph.out_edges(current_node):
                child_data = graph.nodes[child_node]
                if child_data.get("type") == "directory":
                    await process_recursive(child_node)

        # Now process the current directory
        directory_structure = traverse_directory(graph, current_node)
        file_count = directory_structure["file_count"]

        if file_count > threshold:
            # For larger directories, generate a summary using LLM
            # root_id = graph.graph['root_id']
            # yaml_structure = generate_summary_from_json(directory_structure, graph.nodes[root_id]["file_path"])
            yaml_structure = json_to_yaml(directory_structure)
            llm_summary = await run_model_completion(model_name, api_key, directory_summary_prompt(yaml_structure))
            # print(yaml_structure)
            # print("llm_summary", llm_summary)
            # print("here")
            summary_json = {
                "name": directory_structure["name"],
                "path": directory_structure["path"],
                "type": "directory",
                "file_count": 0,
                "summary": llm_summary,
                "is_llm_summary": True
            }
        else:
            # For smaller directories, use the structure as is
            summary_json = directory_structure

        # Update the node's summary_json
        graph.nodes[current_node]["summary_json"] = summary_json

        return summary_json

    # Start the recursive processing from the given node
    return await process_recursive(node)


def traverse_directory(graph, node):
    node_data = graph.nodes[node]
    
    # If this node has a pre-computed summary_json, use it
    if "summary_json" in node_data:
        return node_data["summary_json"]
    
    result = {
        "name": os.path.basename(node_data.get("file_path", "")),
        "path": node_data.get("file_path", ""),
        "type": node_data.get("type", ""),
    }
    
    # For files or directories with summaries
    if "summary" in node_data:
        result["summary"] = node_data["summary"]
    
    # Calculate file count
    if result["type"] == "file":
        result["file_count"] = 1
    else:  # For directories
        result["children"] = []
        file_count = 1  # Count the directory itself
        for _, child in graph.out_edges(node):
            child_result = traverse_directory(graph, child)
            if child_result:
                result["children"].append(child_result)
                file_count += child_result["file_count"]
        result["file_count"] = file_count
    
    # Save the computed result in the graph node
    graph.nodes[node]["summary_json"] = result
    
    return result


def json_to_yaml(json_data):
    def convert_node(node):
        if isinstance(node, dict):
            if 'type' in node and 'name' in node:
                if node['type'] == 'file':
                    return {node['name']: node.get('summary', '')}
                elif node['type'] == 'directory':
                    content = {}
                    if 'summary' in node:
                        content['summary'] = node['summary']
                    for child in node.get('children', []):
                        child_content = convert_node(child)
                        content.update(child_content)
                    return {node['name']: content}
            else:
                return {k: convert_node(v) for k, v in node.items()}
        elif isinstance(node, list):
            return [convert_node(item) for item in node]
        else:
            return node

    def represent_dict(dumper, data):
        return dumper.represent_dict(data.items())

    yaml.add_representer(dict, represent_dict)

    # Convert JSON data to nested dictionary
    yaml_data = convert_node(json_data)

    # Convert nested dictionary to YAML string
    yaml_string = yaml.dump(yaml_data, default_flow_style=False, sort_keys=False, indent=2)

    # Post-process the YAML string to add dashes
    lines = yaml_string.split('\n')
    processed_lines = []
    for line in lines:
        stripped = line.lstrip()
        if stripped and ':' in stripped and not stripped.startswith('- '):
            indent = len(line) - len(stripped)
            processed_lines.append(' ' * indent + '- ' + stripped)
        else:
            processed_lines.append(line)

    return ('\n'.join(processed_lines)[2:])
    

def generate_summary_from_json(json_data, root_dir):
    # Check if it's an LLM-generated summary
    if json_data.get("is_llm_summary", False) and "summary" in json_data:
        return json_data["summary"]


    # Convert JSON to YAML
    yaml_structure = json_to_yaml(json_data)
    directory_name = os.path.basename(os.path.dirname(json_data['path']))
    if os.path.relpath(json_data['path'], start=root_dir) == ".":
        yaml_string = f"\"{directory_name}\" is the root of the codebase:"
    else:
        yaml_string = f"relative directory path of \"{directory_name}\" from the root of the codebase: {os.path.relpath(json_data['path'], start=root_dir)}\n"
    return (yaml_string + yaml_structure)

# print(os.path.relpath("/Users/arnav/Desktop/codegraph/core", "/Users/arnav/Desktop/codegraph/core"))


def reset_directory_summaries(graph):
    """
    Resets the summaries of all directory nodes in the graph.
    
    Args:
    graph: The graph object containing the nodes.
    
    Returns:
    int: The number of directory summaries reset.
    """
    reset_count = 0
    for node, data in graph.nodes(data=True):
        if data.get("type") == "directory":
            if "summary_json" in data:
                del graph.nodes[node]["summary_json"]
                reset_count += 1
            if "summary" in data:
                del graph.nodes[node]["summary"]
                reset_count += 1
            if "is_llm_summary" in data:
                del graph.nodes[node]["is_llm_summary"]
                reset_count += 1
    
    print(f"Reset {reset_count} directory summaries.")
    return reset_count


async def create_advanced_directory_summary(graph, root_id, model_name, api_key):
    """
    Creates an advanced directory summary starting from the root_id.
    Goes down two levels if direct children are <= 3, otherwise one level.
    Processes directories at these levels and generates a summary using a new LLM prompt.

    Args:
    graph: The graph object containing the nodes.
    root_id: The ID of the root directory node.
    model_name: The name of the model to use for processing.

    Returns:
    str: The generated summary.
    """
    async def process_level(nodes):
        tasks = [process_directory_node(graph, node, model_name, api_key) for node in nodes]
        await asyncio.gather(*tasks)

    # Get direct children of the root
    direct_children = [target for _, target, data in graph.out_edges(root_id, data=True) 
                       if data['type'] == 'CONTAINS' and graph.nodes[target].get('type') == 'directory']
    
    # Determine depth based on number of direct children
    max_depth = 2 if len(direct_children) <= 3 else 1

    # BFS to get nodes up to max_depth
    queue = deque([(root_id, 0)])
    visited = set()
    nodes_to_process = []

    while queue:
        node, depth = queue.popleft()
        if node not in visited:
            visited.add(node)
            if depth > 0:  # Don't process the root node yet
                nodes_to_process.append(node)

            if depth < max_depth:
                children = [target for _, target, data in graph.out_edges(node, data=True) 
                            if data['type'] == 'CONTAINS' and graph.nodes[target].get('type') == 'directory']
                for child in children:
                    queue.append((child, depth + 1))

    # Process the collected nodes
    await process_level(nodes_to_process)

    # Now generate the summary_json for the root node using traverse_directory
    root_summary_json = traverse_directory(graph, root_id)
    

    # Convert JSON to YAML using the existing function
    yaml_string = json_to_yaml(root_summary_json)

    # print(yaml_string)

    # Generate the final summary using the new LLM prompt
    # final_summary = await new_llm_directory_summary_prompt(yaml_string, model_name)

    return "final_summary"



def load_graph(graph_path):
    with open(graph_path, 'rb') as f:
        return pickle.load(f)
    
def save_graph(graph, graph_path):
    with open(graph_path, 'wb') as f:
        pickle.dump(graph, f)

# graph = load_graph("/Users/arnav/Desktop/devon/Devon/graph/graph.pickle")
# # asyncio.run(process_directory_node(graph, graph.graph["root_id"], 'haiku'))
# reset_directory_summaries(graph)
# root_id = graph.graph["root_id"]
# asyncio.run(create_advanced_directory_summary(graph, root_id, "haiku"))
# save_graph(graph, "/Users/arnav/Desktop/devon/Devon/graph/graph.pickle")
# # reset_directory_summaries()
        

# import tree_sitter_languages
