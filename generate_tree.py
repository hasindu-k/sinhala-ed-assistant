import os

def print_tree(start_path='.', prefix='', exclude_dirs=None):
    if exclude_dirs is None:
        exclude_dirs = {'.git', '__pycache__', 'venv', '.idea', '.vscode'}
    
    items = os.listdir(start_path)
    items = [i for i in items if i not in exclude_dirs]
    items.sort()
    
    for i, item in enumerate(items):
        path = os.path.join(start_path, item)
        is_last = i == len(items) - 1
        
        if os.path.isdir(path):
            print(f"{prefix}{'└── ' if is_last else '├── '}📁 {item}/")
            extension = "    " if is_last else "│   "
            print_tree(path, prefix + extension, exclude_dirs)
        else:
            print(f"{prefix}{'└── ' if is_last else '├── '}📄 {item}")

if __name__ == "__main__":
    print("📁 sinhala-ed-assistant/")
    print_tree()