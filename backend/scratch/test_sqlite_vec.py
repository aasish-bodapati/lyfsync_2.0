import os
import sys
import sqlite3
import json
import sqlite_vec

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DB_PATH = os.path.join(BACKEND_DIR, "local_db.db")

def test():
    conn = sqlite3.connect(DB_PATH)
    conn.enable_load_extension(True)
    sqlite_vec.load(conn)
    conn.enable_load_extension(False)

    # Print sqlite-vec version
    vec_version, = conn.execute("select vec_version()").fetchone()
    print(f"sqlite-vec version: {vec_version}")

    # Fetch one food item to see if we can do vec_distance_cosine
    row = conn.execute("SELECT fdc_id, description, vector_embedding FROM food_nutrition WHERE vector_embedding IS NOT NULL LIMIT 1").fetchone()
    if not row:
        print("No foods found with embeddings.")
        return
    
    fdc_id, description, vector_embedding_json = row
    print(f"Found sample: {fdc_id} - {description}")
    
    # Parse vector
    vec_list = json.loads(vector_embedding_json)
    
    # Serialize to float32 blob
    vec_blob = sqlite_vec.serialize_float32(vec_list)
    
    # Let's try passing JSON string or blob
    try:
        # Pass a serialized float32 blob as query, and see if we can compare it to another blob
        # Wait, the database vector_embedding column contains JSON text!
        # If the column has JSON text, we might need to convert it using vec_distance_cosine(vector_embedding, ?)
        # Let's see if we can pass JSON string to vec_distance_cosine:
        distance = conn.execute("SELECT vec_distance_cosine(?, ?)", (vector_embedding_json, vector_embedding_json)).fetchone()[0]
        print(f"Distance between JSON strings: {distance}")
    except Exception as e:
        print(f"Failed to compare JSON strings directly: {e}")
        
    try:
        # Compare blobs
        distance_blob = conn.execute("SELECT vec_distance_cosine(?, ?)", (vec_blob, vec_blob)).fetchone()[0]
        print(f"Distance between blobs: {distance_blob}")
    except Exception as e:
        print(f"Failed to compare blobs: {e}")

if __name__ == "__main__":
    test()
