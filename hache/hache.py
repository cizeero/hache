import hashlib
import inspect
import numpy as np
import io
import functools
import atexit
import sqlite3
import collections

DATABASE_NAME = "function.db"
"""
# Hache: Persistent Cache Manager

Hache is a one-file library that allows you to have persistent cacheing for
function return values. We map the hash (`md5`) of the input parameters
in-order to the output value. In order to avoid bugs, any change in the
function description or the docstring will clear the function cache and start
afresh.
"""


"""
BLOB conversion: The function outputs are stored in terms of BLOBs, the library
currently treats numpy array as a special case and dumps the arrays in binary.
"""
def to_blob(result, blob_type):
    if blob_type == np.ndarray:
        with io.BytesIO() as output:
            np.save(output, result)
            return output.getvalue()
    else:
        return result

def from_blob(blob, blob_type):
    if blob_type == np.ndarray:
        with io.BytesIO(blob) as input_bytes:
            return np.load(input_bytes)
    else:
        return blob



def initialize_db():
    """Initialize the SQLite database connection, the entire DB is one file."""
    conn = sqlite3.connect(DATABASE_NAME)

    with conn:
        conn.execute(f"""
            CREATE TABLE IF NOT EXISTS Hashes (
                function TEXT PRIMARY KEY,
                descriptionHash TEXT
            )
        """)
    return conn

def function_setup(conn, func):
    """Set up the function table based on its current hash.
    
    The library supports the change of the function description. If there is a
    change then the old entries are deleted, we track these changes by storing
    a table of function name to code description hash.
    """
    
    source_plus_desc = inspect.getsource(func) 
    desc = inspect.getdoc(func)
    if desc is not None:
        source_plus_desc += desc
        
    current_hash = hashlib.md5(source_plus_desc.encode()).hexdigest()

    with conn:
        cursor = conn.execute("SELECT descriptionHash FROM Hashes WHERE function = ?", (func.__name__,))
        result = cursor.fetchone()

        if result is None:
            # New function addition, no previous hash entry found
            conn.execute(f"""
                CREATE TABLE IF NOT EXISTS {func.__name__} (
                    hashKey TEXT PRIMARY KEY,
                    result BLOB
                )
            """)
            conn.execute("INSERT INTO Hashes (function, descriptionHash) VALUES (?, ?)",
                         (func.__name__, current_hash))
        else:
            stored_hash = result[0]
            if stored_hash != current_hash:
                # Function code has been modified, clear entries
                conn.execute(f"DROP TABLE IF EXISTS {func.__name__}")
                conn.execute(f"""
                    CREATE TABLE {func.__name__} (
                        hashKey TEXT PRIMARY KEY,
                        result BLOB
                    )
                """)
                conn.execute("UPDATE Hashes SET descriptionHash = ? WHERE function = ?",
                             (current_hash, func.__name__))

def load_cache_with_hash(func, blob_type):
    """Load the cache from the SQLite database into a dictionary."""
    conn = initialize_db()
    function_setup(conn, func)
    
    cursor = conn.cursor()
    cursor.execute(f"SELECT hashKey, result FROM {func.__name__}")
    rows = cursor.fetchall()
    
    cache = collections.OrderedDict()
    for row in rows:
        cache[row[0]] = from_blob(row[1], blob_type)
    
    conn.close()
    return cache

def save_cache_with_hash(func, blob_type):
    """Save the function cache to the SQLite database."""
    conn = initialize_db()
    function_setup(conn, func)
    
    with conn:
        for hash_key, result in func.cache.items():
            conn.execute(f"""
                INSERT OR REPLACE INTO {func.__name__} (hashKey, result)
                VALUES (?, ?)
            """, (hash_key, to_blob(result, blob_type)))
    
    conn.close()

"""
A decorator function that can be applied to any function to make a persistent
cache. By default we use LRU caching mechanism to manage memory. This naturally
demands a maximum size of the cache.

Note that each runtime will start with a cache load from the persistent storage
and ends with the current cache being moved to the persistent storage. All the
entries from the persistent storage will load with the same recency. LRU does
not carry over from one runtime to the other.
"""
def hache(blob_type, max_size):
    def decorator(func):
        cache = load_cache_with_hash(func, blob_type)

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            hash_input = str(args) + str(kwargs)
            hash_key = hashlib.md5(hash_input.encode()).hexdigest()
            
            if hash_key in cache:
                cache.move_to_end(hash_key)
                return cache[hash_key]
            
            # Cache missing, calculate and update
            result = func(*args, **kwargs)

            if len(cache) >= max_size:
                # Remove the least recently used item (first item)
                cache.popitem(last=False)

            cache[hash_key] = result
            return result

        # Attach the cache to the wrapper so it can be accessed externally
        wrapper.cache = cache

        atexit.register(lambda : save_cache_with_hash(wrapper, blob_type))

        return wrapper
    return decorator


"""
###############################################################################
Below code is not part of the functionality but was made just for testing. Add
print statements in the above functionality for checking if the behaviour is as
expected.
###############################################################################
"""

import random

@hache(int, 1000)
def add_custom(x, y):
    return x + y

@hache(int, 1000)
def multiply_custom(x, y):
    return x * y


def test_multiply():
    for _ in range(100):
        a = random.randint(1, 5)
        b = random.randint(1, 5)
        result = multiply_custom(a, b)
        assert result == a * b

    # Manually save the cache if needed
    save_cache_with_hash(multiply_custom, np.ndarray)

@hache(np.ndarray, 1000)
def multiply_matrix(a, b):
    return a @ b

def test_matrix():
    for _ in range(100):
        matrix1 = np.random.randint(1, 6, size=(2, 2))
        # matrix2 = np.random.randint(1, 6, size=(2, 2))
        
        # Multiply the matrices
        result = multiply_matrix(matrix1, matrix1)
        answer = matrix1 @ matrix1
        assert np.allclose(result, answer)


    save_cache_with_hash(multiply_matrix, np.ndarray)


@hache(int, 2)
def add_lru_test(x, y):
    return x + y

def test_lru():
    add_lru_test(1, 2)
    # cache hit 1
    add_lru_test(1, 2)
    print("^^cache must hit")
    add_lru_test(2, 3)
    print("^^no cache hit")
    add_lru_test(3, 4)
    print("^^no cache hit")
    add_lru_test(1, 2)
    print("^^no cache hit")
    add_lru_test(1, 2)
    print("^^cache must hit")

    add_lru_test(4, 3)
    add_lru_test(6, 4)



def test_main():
    test_matrix()
    test_lru()

if __name__ == "__main__":
    test_main()
