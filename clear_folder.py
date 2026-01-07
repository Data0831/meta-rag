import os
import shutil

path_to_clear = [
    "data_logs",
    "data_update/data_logs",
    "data_update/data",
    "data_update/sync_output",
]

def clear_folders(paths):
    for path in paths:
        if os.path.exists(path):
            print(f"Clearing contents of: {path}")
            for filename in os.listdir(path):
                file_path = os.path.join(path, filename)
                try:
                    if os.path.isfile(file_path) or os.path.islink(file_path):
                        os.unlink(file_path)
                    elif os.path.isdir(file_path):
                        shutil.rmtree(file_path)
                except Exception as e:
                    print(f'Failed to delete {file_path}. Reason: {e}')
        else:
            print(f"Path does not exist: {path}")

if __name__ == "__main__":
    clear_folders(path_to_clear)
