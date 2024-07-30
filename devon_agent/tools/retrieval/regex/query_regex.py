import os
import re
import pathspec
from devon_agent.semantic_search.constants import (extension_to_language, json_config_files,
    supported_extensions, supported_noncode_extensions)

def regex_search(path, pattern, window=2):
    regex = re.compile(pattern)
    results = []
    
    def load_gitignore_specs(root_path):
        ignore_specs = []
        for dirpath, dirnames, filenames in os.walk(root_path, topdown=True):
            if '.gitignore' in filenames:
                gitignore_path = os.path.join(dirpath, '.gitignore')
                with open(gitignore_path, 'r') as gitignore_file:
                    spec = pathspec.PathSpec.from_lines('gitwildmatch', gitignore_file)
                    ignore_specs.append((dirpath, spec))
            
            # Don't traverse into ignored directories
            dirnames[:] = [d for d in dirnames if not is_ignored(os.path.join(dirpath, d), ignore_specs)]

        # Sort ignore_specs so that root comes first, then by path length (descending)
        ignore_specs.sort(key=lambda x: (x[0] != root_path, -len(x[0])))
        return ignore_specs

    def is_ignored(path, ignore_specs):
        path = os.path.abspath(path)
        
        for spec_path, spec in ignore_specs:
            if path.startswith(spec_path):
                # Get the path relative to the .gitignore file
                relative_path = os.path.relpath(path, spec_path)
                if spec.match_file(relative_path):
                    return True
        
        return False

    def process_file(file_path):
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            print(f"Error processing {file_path}: {str(e)}")
            return
        
        file_results = []
        last_end = -1
        for i, line in enumerate(lines):
            if regex.search(line):
                start = max(0, i - window)
                end = min(len(lines), i + window + 1)
                
                if start <= last_end:
                    # Overlap with previous match, extend the last result
                    file_results[-1] = (file_results[-1][0], end)
                else:
                    # New match
                    file_results.append((start, end))
                
                last_end = end
        
        # Create strings for each combined result
        for start, end in file_results:
            match_result = f"\nMatch in {file_path}:\n"
            match_result += "\n".join(f"{'>' if regex.search(lines[j]) else ' '} {lines[j].rstrip()}" for j in range(start, end))
            results.append(match_result)

    if os.path.isfile(path):
        # If path is a file, process only that file
        if path.endswith('.py'):
            process_file(path)
    elif os.path.isdir(path):
        # If path is a directory, load gitignore specs and walk through it
        ignore_specs = load_gitignore_specs(path)
        for root, dirs, files in os.walk(path):
            # Remove ignored directories
            dirs[:] = [d for d in dirs if not is_ignored(os.path.join(root, d), ignore_specs)]
            
            for file in files:
                file_path = os.path.join(root, file)
                file_extension = os.path.splitext(file_path)[-1]
                if file_extension in extension_to_language or (file_extension != '.json' and file_extension in supported_noncode_extensions) or (file_extension == '.json' and file_extension in json_config_files):
                    if not is_ignored(file_path, ignore_specs):
                        process_file(file_path)
    else:
        raise ValueError(f"Invalid path: {path}. Must be a file or directory.")
    
    return results

if __name__ == "__main__":
    directory = "/Users/arnav/Desktop/devon/Devon"
    pattern = r"electron-forge start"
    window = 5
    
    results = regex_search(directory, pattern, window)
    
    for result in results:
        print(result)
        print("=" * 50)

    print(f"Total matches: {len(results)}")