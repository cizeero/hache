import hashlib
import time
import random

import functools
import json
import os
import atexit

def load_cache_with_hash(json_file):
    # Load the cache from the JSON file if it exists
    if os.path.exists(json_file):
        with open(json_file, 'r') as f:
            try:
                cache = json.load(f)
            except json.JSONDecodeError:
                cache = {}
    else:
        cache = {}

    return cache


def save_cache_with_hash(func, json_file):
    # Manually save the cache to the JSON file if needed
    with open(json_file, 'w') as f:
        json.dump(func.cache, f)


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
@cache_with_hash("add.json")
def add(x, y):
    return x + y

@cache_with_hash("multiply.json")
def multiply(x, y):
    time.sleep(1)
    return x * y


def test_main():
    for _ in range(100):
        a = random.randint(1, 5)
        b = random.randint(1, 5)
        result = multiply(a, b)

    # Manually save the cache if needed
    save_cache_with_hash(multiply, "multiply.json")


if __name__ == "__main__":
    test_main()
