#!/usr/bin/env python

import os
import json
import pathlib
import typing
import subprocess
import time
import signal

import requests
from rich.console import Console
import pandas as pd

from kurveclient.auth import _signed_request

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


def _create_source_from_dir (
        path: typing.Union[str, pathlib.Path],
        storage_format: typing.Optional[str] = None
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

    console.print(f'[green]creating source from directory {path}[/green]')
    if isinstance(path, str):
        path = pathlib.Path(path)
    if not path.exists():
        raise Exception(f'{path} does not exist')
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


def _get_source_from_dir (
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
    source_data = _create_source_from_dir(path)
    if 'error' in source_data:
        source_data = _get_source_from_dir(path)

    graph_data = create_graph(source_data['data']['id'])
    return graph_data
