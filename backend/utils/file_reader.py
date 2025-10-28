import os

def read_text_file(file_path: str) -> str:
    """
    Reads a text file and returns its content.
    """
    try:
        # Ensure the path is relative to this file's directory if needed
        # This assumes `main.py` is in the parent directory
        base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        full_path = os.path.join(base_dir, file_path)

        if not os.path.exists(full_path):
            print(f"Warning: File not found at {full_path}")
            return ""

        with open(full_path, 'r', encoding='utf-8') as f:
            return f.read()
            
    except Exception as e:
        print(f"Error reading file {file_path}: {e}")
        return ""
