import base64
import logging
import re
import sys
from typing import Any, TypedDict

LOGGER_NAME = "devon"

logger = logging.getLogger(LOGGER_NAME)

stdout_handler = logging.StreamHandler(sys.stdout)
stdout_handler.setLevel(logging.DEBUG)
logger.addHandler(stdout_handler)

logger.setLevel(logging.DEBUG)

import hashlib
import json
import os

def encode_path(path, mapper_path):
    # Calculate the SHA-256 hash of the path
    hashed = hashlib.sha256(path.encode()).hexdigest()
    
    # Save the mapping in the mapper JSON file
    if not os.path.exists(mapper_path):
        with open(mapper_path, 'w') as f:
            json.dump({}, f)
    
    with open(mapper_path, 'r+') as f:
        mapper = json.load(f)
        if path not in mapper:
            mapper[path] = hashed
            f.seek(0)
            json.dump(mapper, f, indent=4)
    
    # print(hashed)
    return hashed

def decode_path(encoded_path, mapper_path):
    # Load the mapping from the mapper JSON file
    try:
        with open(mapper_path, 'r') as f:
            mapper = json.load(f)
        
        # Find the original path based on the encoded value
        for original_path, hashed in mapper.items():
            if encoded_path.endswith(hashed):
                return original_path
    except:
        return None
    
    return None



class DotDict:
    """
    Wrapper class for accessing dictionary keys as attributes
    """

    def __init__(self, data):
        self.data = data

    def __getattr__(self, key):
        return self.data.get(key)

    def to_dict(self):
        return self.__dict__


class Event(TypedDict):
    type: str  # types: ModelResponse, ToolResponse, UserRequest, Interrupt, Stop
    content: Any
    producer: str | None
    consumer: str | None
