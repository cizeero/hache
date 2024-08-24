import hashlib
import time
import random

import functools
import atexit


import sqlite3

DATABASE_NAME = "function.db"

def initialize_db():
    """Initialize the SQLite database connection."""
    conn = sqlite3.connect(DATABASE_NAME)
    return conn

def create_table_if_not_exists(conn, func_name):
    """Create a table for the function if it does not already exist."""
    with conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS {func_name} (
                hash_key TEXT PRIMARY KEY,
                result BLOB
            )
        """)

def load_cache_with_hash(func_name):
    """Load the cache from the SQLite database into a dictionary."""
    conn = initialize_db()
    create_table_if_not_exists(conn, func_name)
    
    cache = {}
    cursor = conn.cursor()
    cursor.execute(f"SELECT hash_key, result FROM {func_name}")
    rows = cursor.fetchall()
    
    for row in rows:
        cache[row[0]] = row[1]
    
    conn.close()
    print(f"Cache loaded: {cache}")
    return cache

def save_cache_with_hash(func, func_name):
    """Save the function cache to the SQLite database."""
    conn = initialize_db()
    create_table_if_not_exists(conn, func_name)
    
    with conn:
        for hash_key, result in func.cache.items():
            conn.execute(f"""
                INSERT OR REPLACE INTO {func_name} (hash_key, result)
                VALUES (?, ?)
            """, (hash_key, result))
    
    conn.close()


def cache_with_hash(dictionary_json):
    def decorator(func):
        cache = load_cache_with_hash(dictionary_json)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            hash_input = str(args) + str(kwargs)
            hash_key = hashlib.md5(hash_input.encode()).hexdigest()
            
            if hash_key in cache:
                return cache[hash_key]
            
            # Cache missing, calculate and update
            result = func(*args, **kwargs)
            cache[hash_key] = result
            return result

        # Attach the cache to the wrapper so it can be accessed externally
        wrapper.cache = cache

        atexit.register(lambda : save_cache_with_hash(wrapper, dictionary_json))

        return wrapper
    return decorator

# Example usage
@cache_with_hash("add_custom")
def add_custom(x, y):
    return x + y

@cache_with_hash("multiply_custom")
def multiply_custom(x, y):
    time.sleep(1)
    return x * y


def test_main():
    for _ in range(100):
        a = random.randint(1, 5)
        b = random.randint(1, 5)
        result = multiply_custom(a, b)

    # Manually save the cache if needed
    save_cache_with_hash(multiply_custom, "multiply_custom")


if __name__ == "__main__":
    test_main()
