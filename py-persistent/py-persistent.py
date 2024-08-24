import hashlib
import random

import functools
import json
import os
import time

def cache_with_hash(dictionary_json):
    def decorator(func):
        # Load the cache from the JSON file if it exists
        if os.path.exists(dictionary_json):
            with open(dictionary_json, 'r') as f:
                try:
                    cache = json.load(f)
                except json.JSONDecodeError:
                    cache = {}
        else:
            cache = {}

        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            # Generate the hash key based on arguments
            hash_input = str(args) + str(kwargs)
            hash_key = hashlib.md5(hash_input.encode()).hexdigest()
            
            if hash_key in cache:
                return cache[hash_key]
            
            # Calculate the result and update the cache
            result = func(*args, **kwargs)
            cache[hash_key] = result
            return result

        # Attach the cache to the wrapper so it can be accessed externally
        wrapper.cache = cache

        # Function to save the cache back to the JSON file
        def save_cache():
            with open(dictionary_json, 'w') as f:
                json.dump(cache, f)

        # Register the save_cache function to be called when the program exits
        import atexit
        atexit.register(save_cache)

        return wrapper
    return decorator

def save_cache_with_hash(func, json_file):
    # Manually save the cache to the JSON file if needed
    with open(json_file, 'w') as f:
        json.dump(func.cache, f)

# Example usage
@cache_with_hash("add.json")
def add(x, y):
    return x + y


def test_main():
    for _ in range(100):
        a = random.randint(1, 5)
        b = random.randint(1, 5)
        result = add(a, b)

    print(add.cache)
    print(len(add.cache))

    # Manually save the cache if needed
    save_cache_with_hash(add, "add.json")


if __name__ == "__main__":
    test_main()
