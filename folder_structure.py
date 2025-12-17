import os

def write_tree(start_path='.', prefix='', exclude_dirs=None, file=None):
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', '.venv', 'venv', '.idea', '.vscode'}
    
    items = os.listdir(start_path)
    items = [i for i in items if i not in exclude_dirs]
    items.sort()
    
    for i, item in enumerate(items):
        path = os.path.join(start_path, item)
        is_last = i == len(items) - 1
        
        if os.path.isdir(path):
            file.write(f"{prefix}{'└── ' if is_last else '├── '}📁 {item}/\n")
            extension = "    " if is_last else "│   "
            write_tree(path, prefix + extension, exclude_dirs, file)
        else:
            file.write(f"{prefix}{'└── ' if is_last else '├── '}📄 {item}\n")

if __name__ == "__main__":
    # Open the text file for writing
    with open("directory_tree.txt", "w") as file:
        file.write("📁 sinhala-ed-assistant/\n")
        write_tree(file=file)
    
    print("Directory tree has been written to 'directory_tree.txt'")
