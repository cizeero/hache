# Hache: Persistent Cache Manager

Hache is a one-file library that allows you to have persistent cacheing for
function return values. We map the hash (`md5`) of the input parameters
in-order to the output value. In order to avoid bugs, any change in the
function description or the docstring will clear the function cache and start
afresh.


## Example
```py
# database name that will create the file for database
DATABASE_NAME = "function.db"

@hache(blob_type=np.ndarray, max_size=1000)
def multiply_matrix(a, b):
    return a @ b
```

### Requirements

Package requirements:
- `numpy`

Development requirements:
- `pytest`
