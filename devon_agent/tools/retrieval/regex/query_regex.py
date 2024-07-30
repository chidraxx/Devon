import os
import re

def regex_search(path, pattern, window=2):
    regex = re.compile(pattern)
    results = []
    
    def process_file(file_path):
        with open(file_path, 'r') as f:
            lines = f.readlines()
        
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
        # If path is a directory, walk through it
        for root, _, files in os.walk(path):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    process_file(file_path)
    else:
        raise ValueError(f"Invalid path: {path}. Must be a file or directory.")
    
    return results

if __name__ == "__main__":
    directory = "/Users/arnav/Desktop/pytest/pytest"
    pattern = r"\ball\("
    window = 5
    
    results = regex_search(directory, pattern, window)
    
    for result in results:
        print(result)
        print("=" * 50)

    print(f"Total matches: {len(results)}")