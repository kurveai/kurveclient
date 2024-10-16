# Welcome to the Kurve Client documentation.

For full documentation visit [kurve.ai/docs](https://kurve.ai/docs).

## Quickstart

### Installation
```bash
pip install kurveclient
```

### Authenticate
```python
from kurveclient.auth import do_auth

do_auth()
```

### List open data sources
```python
import pprint
from kurveclient.interaction import list_sources

sources = list_sources()
pprint.pprint(sources)
```

### Create a graph from a source
```python
from kurveclient.interaction import create_graph, list_sources, list_graphs, list_edges

source_id = list_sources()['data'][0]['id']
create_graph(source_id)
```

### Get nodes and edges from an existing graph
```python
# We previously built a graph in the above snippet
# If the graph is done building it should be in `list_graphs`

from kurveclient.interaction import list_graphs, list_nodes, list_edges

source_id = list_sources()['data'][0]['id']
graphs = list_graphs()

# Find the graph that was just built
graph = [g for g in graphs['data'] if g['source_id'] == source_id][0]

graph_id = graph['id']

# Get the graph nodes
node_df = list_nodes(graph_id, to_df=True)
edge_df = list_edges(graph_id, to_df=True)
```
