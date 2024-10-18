# kurveclient
Kurve Open Source client

# installation
```python
pip install kurveclient
```

# usage
```python
from kurveclient.auth import do_auth
from kurveclient.interaction import map_local_source

do_auth()

map_local_source('/path/to/csv_directory')
# magic
```
