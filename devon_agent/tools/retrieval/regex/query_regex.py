import os
import re

def regex_search(directory, pattern, window=2):
    regex = re.compile(pattern)
    results = []
    
    for root, _, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
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