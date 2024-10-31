#!/usr/bin/env python

import os
import json
import pathlib
import typing
import subprocess
import time
import signal
import datetime

import requests
from rich.console import Console
import pandas as pd

from kurveclient.auth import _signed_request
from kurveclient.models import LocalPayload, RestCatalogPayload, S3Payload

console = Console()


API_BASE = os.getenv('KURVE_API_ENDPOINT', 'https://demo.kurve.ai')
API_VERSION = 'v1'


def _todf (
        response: dict
        ) -> pd.DataFrame:
    if 'data' in response:
        return pd.DataFrame(response['data'])
    return None


def whoami():
    endpoint = f'{API_BASE}/{API_VERSION}/whoami'    
    resp = _signed_request(endpoint, 'get')
    return json.loads(resp.text)


def list_providers():
    resp = requests.get(f'{API_BASE}/{API_VERSION}/providers')
    return json.loads(resp.text)


def list_sources (
        include_open: bool = True,
        to_df: bool = False
    ) -> typing.Union[dict, pd.DataFrame]:
    """
List the data sources.

    Parameters
    ----------
    include_open: bool whether to include open datasets
    to_df: bool whether or not to return as `pandas.DataFrame`

    Returns
    ----------
    sources: dict or dataframe of sources
    """
    endpoint = f'{API_BASE}/{API_VERSION}/sources'
    resp = _signed_request(endpoint, 'get')
    sources = json.loads(resp.text)
    if not include_open:
        sources['data'] = [x for x in sources['data'] if x['is_open'] == False]
    if to_df:
        return _todf(sources)
    return sources


def create_source (
        payload: typing.Union[LocalPayload, RestCatalogPayload, S3Payload],
        ) -> dict:
    """
Create a data source.

    Parameters
    -----------
    payload: pydantic model representing the data source

    Returns
    -----------
    source: dict of the created source
    """
    endpoint = f'{API_BASE}/{API_VERSION}/add_source'
    resp = _signed_request(endpoint, method='post', payload=payload.dict())
    return json.loads(resp.text)


def list_entities (
        source_id: int,
        to_df: bool = False
        ) -> typing.Union[dict, pd.DataFrame]:
    """
List the source entities.

    Parameters
    ----------
    source_id: int id of the source
    to_df: bool whether or not to return as `pandas.DataFrame`

    Returns
    ----------
    entities: dict or dataframe of entities
    """
    endpoint = f'{API_BASE}/{API_VERSION}/sources/{source_id}/entities'
    resp = _signed_request(endpoint, 'get')
    entities = json.loads(resp.text)
    if to_df:
        return _todf(entities)
    return entities


def list_graphs():
    endpoint = f'{API_BASE}/{API_VERSION}/graphs'
    resp = _signed_request(endpoint, 'get')
    return json.loads(resp.text)


def create_graph(source_id: int):
    payload = {'source_id': source_id}
    endpoint = f'{API_BASE}/{API_VERSION}/create_graph'
    resp = _signed_request(endpoint, 'post', payload=payload)
    return json.loads(resp.text)


def get_graph(source_id: int):
    endpoint = f'{API_BASE}/{API_VERSION}/graphs?source_id={source_id}'
    resp = _signed_request(endpoint, 'get')
    return json.loads(resp.text)


def list_nodes (
        graph_id: int,
        to_df: bool = False
        ) -> typing.Union[dict, pd.DataFrame]:
    """
List the graph nodes.

    Parameters
    ----------
    graph_id: int id of the graph
    to_df: bool whether or not to return as `pandas.DataFrame`

    Returns
    ----------
    nodes: dict or dataframe of nodes
    """
    endpoint = f'{API_BASE}/{API_VERSION}/graphs/{graph_id}/nodes'
    resp = _signed_request(endpoint, 'get')
    nodes = json.loads(resp.text)
    if to_df:
        return _todf(nodes)
    return nodes


def get_node (
        graph_id: int,
        node_id: int
        ) -> dict:
    """
Get a single node.
   
    Parameters
    ----------
    graph_id: int id of graph
    node_id: int id of node

    Returns
    ---------
    node: dict of node
    """
    endpoint = f'{API_BASE}/{API_VERSION}/graphs/{graph_id}/nodes/{node_id}'
    resp = _signed_request(endpoint, 'get')
    return json.loads(resp.text)


def list_edges (
        graph_id: int,
        to_df: bool = False
        ) -> typing.Union[dict, pd.DataFrame]:
    """
List the graph edges.

    Parameters
    ----------
    graph_id: int id of the graph
    to_df: bool whether or not to return as `pandas.DataFrame`

    Returns
    ----------
    edges: dict or dataframe of edges
    """
    endpoint = f'{API_BASE}/{API_VERSION}/graphs/{graph_id}/edges'
    resp = _signed_request(endpoint, 'get')
    edges = json.loads(resp.text)
    if to_df:
        return _todf(edges)
    return edges


def _start_ngrok (
        path: typing.Union[str, pathlib.Path],
        ) -> str:
    """
Starts ngrok file serving at a path.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    if not path.exists():
        raise Exception(f'{path} does not exist')
    command = ['nohup', 'ngrok', 'http', f'file://{path}']
    proc = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    time.sleep(5)
    # now call the API and get the endpoint
    ngrok_local = 'http://localhost:4040/api/tunnels'
    resp = json.loads(requests.get(ngrok_local).text)
    return {'endpoint': resp['tunnels'][0]['public_url'], 'pid': proc.pid}


def _expose_directory (
        path: typing.Union[str, pathlib.Path],
        ) -> dict:
    """
Expose a directory to the internet.

    Parameters
    -----------
    path: str or `pathlib.Path` of the directory

    Returns
    -----------
    files: returns a list of files in the directory
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    if not path.exists():
        raise Exception(f'{path} does not exist')
    # ngrok link
    # files
    # format
    files = []
    # This will not work for partitioned
    # columnar format directories.
    for f in path.iterdir():
        if f.is_file():
            files.append(f.name)
    # Start the ngrok server.
    ngrok_data = _start_ngrok(path)
    return {
            'endpoint': ngrok_data['endpoint'],
            'files': files,
            'directory': str(path),
            'pid': ngrok_data['pid']
            }


def _enumerate_directory (
        path: typing.Union[str, pathlib.Path],
        file_format: str,
        n_rows: int = 5,
        ) -> dict:
    """
Enumerate a directory.
    """
    if isinstance(path, str):
        path = pathlib.Path(path)
    if not path.exists():
        raise Exception(f'{path} does not exist')
    files = []
    # This will not work for partitioned
    # columnar format directories.
    for f in path.iterdir():
        if f.is_file() and (file_format in f.suffix or file_format == f.suffix):
            files.append(f.name)
    # For each file in the directory 
    # read in a sample of `n` rows
    # and create dictionaries.
    data_samples = {}
    for f in path.iterdir():
        if f.name in files:
            df = getattr(pd, f'read_{file_format}')(str(f))
            samp = [{c:r[c] for c in df.columns} for ix, r in df.head(n_rows).iterrows()]
            data_samples[f.name] = samp
    return {
            'files': files,
            'directory': str(path),
            'data_samples': data_samples,
            'storage_format': file_format
            }


def create_source_from_dir (
        path: typing.Union[str, pathlib.Path],
        storage_format: typing.Optional[str] = None,
        n_rows: int = 5,
        ) -> dict:
    """
Given a directory path create a source.

    Parameters
    -----------
    path: typing.Union[str, pathlib.Path] directory path to data
    storage_format (optional): str of the storage format options: 'csv','parquet','json','excel','tsv'

    Returns
    -----------
    source_record: dict source record
    """

    if 'error' not in get_source_from_dir(path):
        return get_source_from_dir(path)

    console.print(f'[green]creating source from directory {path}[/green]')
    if isinstance(path, str):
        path = pathlib.Path(path)
    if not path.exists():
        raise Exception(f'{path} does not exist')

    dirdata = _enumerate_directory(path, storage_format, n_rows=n_rows)
    # POST to the kurve backend for source
    # creation.
    endpoint = f'{API_BASE}/{API_VERSION}/stored_source'
    # Creates the source or gets
    # a pre-existing source.
    resp = _signed_request(endpoint, 'post', payload=dirdata)
    return json.loads(resp.text)
    

    ######### ORIGINAL IMPLEMENTATION ##############
    file_map = _expose_directory(path)
    # Check the response html for all of the files.
    ngrok_endpoint = file_map['endpoint']
    files = file_map['files']
    # TODO: refactor this is brittle
    if not storage_format:
        storage_format = files[0].split('.')[-1]
    file_map['storage_format'] = storage_format
    directory = file_map['directory']
    ngrok_pid = file_map['pid']
    # POST to the kurve backend for source
    # creation.
    endpoint = f'{API_BASE}/{API_VERSION}/stored_source'
    # Creates the source or gets
    # a pre-existing source.
    resp = _signed_request(endpoint, 'post', payload=file_map)
    os.kill(ngrok_pid, signal.SIGTERM)
    return json.loads(resp.text)


def get_source_from_dir (
        path: typing.Union[str, pathlib.Path] = None,
        ) -> dict:
    """
Given a directory path get a source if it exists.

    Parameters
    -----------
    path: typing.Union[str, pathlib.Path] directory path to data

    Returns
    -----------
    source_record: dict source record
    """
    endpoint = f'{API_BASE}/{API_VERSION}/stored_source?directory={path}'
    resp = _signed_request(endpoint, 'get')
    return json.loads(resp.text)


def map_local_source (
        path: typing.Union[str, pathlib.Path],
        storage_format: typing.Optional[str] = None,
        n_rows: int = 100,
        ) -> dict:
    """
Given a directory path map the data.

    Parameters
    -----------
    path: typing.Union[str, pathlib.Path] directory path to data
    storage_format (optional): str of the storage format options: 'csv','parquet','json','excel','tsv'

    Returns
    -----------
    graph_record: dict graph record
    """

    if isinstance(path, str):
        path = pathlib.Path(path)
    if not path.exists():
        raise Exception(f'{path} does not exist')

    # Take a look at the files in
    # the path and find out their formats.
    source_data = create_source_from_dir(path, storage_format=storage_format, n_rows=n_rows)
    if 'error' in source_data:
        source_data = get_source_from_dir(path)

    graph_data = create_graph(source_data['data']['id'])
    return graph_data


def prefix(ident: str):
    if len(ident.split('_')) > 1:
        parts = ident.split('_')
        return ''.join([_[0:2] for _ in parts])
    else:
        return ident[0:4]


def autofe_local_source (
        path: typing.Union[str, pathlib.Path],
        storage_format: typing.Optional[str] = None,
        parent_node: str = '',
        label_node: str = '',
        label_field: str = 'id',
        label_operation: str = 'count',
        compute_period: int = 365,
        label_period: int = 30,
        cut_date : datetime.datetime = datetime.datetime.now(),
        hops_front: int = 1,
        hops_back: int = 2,
        ) -> pd.DataFrame:
    """
Perform automatic feature engineering on a local
data source and return the results.
    """
    source_data = create_source_from_dir(path, storage_format=storage_format)
    source_id = source_data['data']['id']
    graphs = list_graphs()
    if len([x for x in graphs['data'] if x['source_id'] == source_id]):
        graph_id = [x for x in graphs['data'] if x['source_id'] == source_id][0]['id']
    else:
        create_graph(source_id)
        graph_id = None
    if not graph_id:
        start = time.time()
        while not graph_id:            
            console.print(f'[blue]Waiting on graph to finish inferring {path} passed[/blue]')
            time.sleep(20)
            graphs = list_graphs()
            if len([x for x in graphs['data'] if x['source_id'] == source_id]):
                graph_id = [x for x in graphs['data'] if x['source_id'] == source_id][0]['id']
                console.print(f'[green]Graph finished building![/green]')

    edges = list_edges(graph_id,to_df=True)
    edges['node_one_identifier'] = edges.apply(lambda x:
                f"{x['original_directory']}/{x['node_one_identifier'].split('/')[-1]}", axis=1)
    edges['node_two_identifier'] = edges.apply(lambda x:
                f"{x['original_directory']}/{x['node_two_identifier'].split('/')[-1]}", axis=1)
    # now we should have a graph id.
    from graphreduce.node import GraphReduceNode, DynamicNode
    from graphreduce.graph_reduce import GraphReduce
    from graphreduce.enum import PeriodUnit, ComputeLayerEnum
    gr_nodes = {}
    for ix, edge in edges.iterrows():
        n1id = edge['node_one_identifier']
        n2id = edge['node_two_identifier']
        if not gr_nodes.get(n1id):
            gr_nodes[n1id] = DynamicNode(
                fpath=n1id,
                fmt=n1id.split('.')[-1],
                compute_layer=ComputeLayerEnum.pandas,
                pk=edge['node_one_pk'],
                date_key=edge['node_one_date_key'],
                prefix=prefix(n1id.split('/')[-1])
                )
        if not gr_nodes.get(n2id):
            gr_nodes[n2id] = DynamicNode(
                    fpath=n2id,
                    fmt=n2id.split('.')[-1],
                    compute_layer=ComputeLayerEnum.pandas,
                    pk=edge['node_two_pk'],
                    date_key=edge['node_two_date_key'],
                    prefix=prefix(n2id.split('/')[-1])
                    )
    gr = GraphReduce(
            name='kurveclient',
            parent_node=gr_nodes[parent_node],
            compute_layer=ComputeLayerEnum.pandas,
            fmt=storage_format,
            compute_period_val=compute_period,
            compute_period_unit=PeriodUnit.day,
            cut_date=cut_date,
            label_period_val=label_period,
            label_period_unit=PeriodUnit.day,
            label_node=gr_nodes[label_node],
            label_field=label_field,
            label_operation=label_operation,
            auto_features=True,
            auto_features_hops_front=hops_front,
            auto_features_hops_back=hops_back
            )
    for key, node in gr_nodes.items():
        gr.add_node(node)
    for ix, edge in edges.iterrows():
        # get the node one node
        # get the node two node
        # add the edge directionally where the parent is always `node_two`
        node_one = gr_nodes[edge['node_one_identifier']]
        node_two = gr_nodes[edge['node_two_identifier']]
        gr.add_entity_edge(
            parent_node=node_two,
            relation_node=node_one,
            parent_key=edge['node_two_fields'],
            relation_key=edge['node_one_fields'],
            reduce=True,
            reduce_after_join=False
        )
    gr.do_transformations()
    return gr.parent_node.df



def autofe_catalog (
        source_id: int,
        parent_node: str = '',
        label_node: str = '',
        label_field: str = 'id',
        label_operation: str = 'count',
        compute_period: int = 365,
        label_period: int = 30,
        cut_date : datetime.datetime = datetime.datetime.now(), 
        ):
    pass


def autofe_remote_source (
        source_id: int,
        parent_entity: str,
        compute_period: int = 365,
        label_period: int = 30,
        ) -> str:
    """
Perform automatic feature engineering on a remote
source and return the table name.
    """
    pass
