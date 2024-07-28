import hashlib
import json
import os
import time
from typing import Dict, Any
from pydantic import BaseModel
from devon_agent.semantic_search.code_graph_manager import CodeGraphManager

# Assuming the db_path is set elsewhere in your application
db_path = "/Users/arnav/Library/Application Support/Devon(Alpha)"  # Replace with actual db path

def encode_path(path: str, mapper_path: str) -> str:
    """Encode a path using SHA-256 and store the mapping along with metadata in a JSON file."""
    hashed = hashlib.sha256(path.encode()).hexdigest()
    
    if not os.path.exists(mapper_path):
        with open(mapper_path, 'w') as f:
            json.dump({}, f)
    
    with open(mapper_path, 'r+') as f:
        mapper = json.load(f)
        if path not in mapper:
            mapper[path] = {
                "hash": hashed,
                "last_updated_at": None  # Set to None initially
            }
        f.seek(0)
        json.dump(mapper, f, indent=4)
    
    return hashed

def update_mapper(path: str, mapper_path: str, update: Dict[str, Any]) -> None:
    """Update the mapping metadata in the JSON file."""
    if os.path.exists(mapper_path):
        with open(mapper_path, 'r+') as f:
            mapper = json.load(f)
            if path in mapper:
                mapper[path].update(update)
                f.seek(0)
                json.dump(mapper, f, indent=4)

class IndexCreationRequest(BaseModel):
    index: str
    model_api: str
    embedding_api: str

index_tasks: Dict[str, Dict[str, Any]] = {}

def create_index(request: IndexCreationRequest):
    try:
        def register_task(task, **kwargs):
            index_tasks[request.index] = {"status": "running", "percentage": "0"}
            
            def progress_tracker(progress: float):
                print(progress)
                if request.index not in index_tasks:
                    index_tasks[request.index] = {}
                if progress >= 1:
                    index_tasks[request.index]["percentage"] = 100
                else:
                    index_tasks[request.index]["percentage"] = int(progress * 100)

            task(progress_tracker=progress_tracker, **kwargs)
            
            # Update the last_updated_at after the task is complete
            mapper_path = os.path.join(db_path, "project_mapper.json")
            update_info = {"last_updated_at": time.strftime("%Y-%m-%d %H:%M:%S", time.gmtime())}
            update_mapper(request.index, mapper_path, update=update_info)
            print("task complete")
            index_tasks[request.index] = {"status": "done", "percentage": "100"}

        mapper_path = os.path.join(db_path, "project_mapper.json")
        encoded_index = encode_path(request.index, mapper_path)
        storage_path = os.path.join(db_path, encoded_index)
        vectorDB_path = os.path.join(storage_path, "vectorDB")
        graph_path = os.path.join(storage_path, "graph")
        collection_name = "collection"
        
        api_key = request.model_api
        openai_api_key = request.embedding_api

        manager = CodeGraphManager(
            graph_storage_path=graph_path, 
            db_path=vectorDB_path, 
            root_path=request.index, 
            openai_api_key=openai_api_key, 
            api_key=api_key, 
            model_name="haiku", 
            collection_name=collection_name
        )
        
        register_task(manager.create_graph)

        return {"message": "Index creation task started"}
    except Exception as e:
        raise Exception(f"Failed to create index: {str(e)}")

# Example usage
if __name__ == "__main__":

    api_key = os.getenv("ANTHROPIC_API_KEY")
    openai_api_key=os.getenv("OPENAI_API_KEY")
    # Replace these with actual test values
    test_request = IndexCreationRequest(
        index="/Users/arnav/Desktop/devon/Devon",
        model_api=api_key,
        embedding_api=openai_api_key
    )
    
    result = create_index(test_request)
    print(result)
    print(index_tasks)
