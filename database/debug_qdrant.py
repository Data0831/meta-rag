from qdrant_client import QdrantClient
import inspect

def main():
    print("Inspecting QdrantClient...")
    try:
        client = QdrantClient(location=":memory:") # Use in-memory for quick test
        print(f"Client type: {type(client)}")
        
        methods = [m for m in dir(client) if not m.startswith("_")]
        print(f"Available methods: {methods}")
        
        if 'search' in methods:
            print("Method 'search' exists.")
        else:
            print("Method 'search' DOES NOT exist.")
            
        if 'query_points' in methods:
            print("Method 'query_points' exists.")

    except Exception as e:
        print(f"Error initializing client: {e}")

if __name__ == "__main__":
    main()
