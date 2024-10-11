#!/usr/bin/env python

import os
import json
import pathlib

import requests
from rich.console import Console

console = Console()


API_BASE = os.getenv('KURVE_API_ENDPOINT', 'https://demo.kurve.ai')
API_VERSION = 'v1'


def _load_tokens ():
    home = pathlib.Path.home()
    if pathlib.Path(home / '.kurve' / 'config.json').exists():
        console.print('[green]Found tokens[/green]')
        return json.loads(open(pathlib.Path(home / '.kurve' / 'config.json'), 'r').read())
    console.print('[red]User not authenticated! Must run[/red][green]kurveclient auth[/green][red] to continue[/red]')


def whoami():
    tokens = _load_tokens()
    resp = requests.get(f'{API_BASE}/{API_VERSION}/whoami',
                        cookies={
                            'jwt_access_cookie':tokens['access_token'],
                            'jwt_refresh_cookie':tokens['refresh_token']
                            })
    return json.loads(resp.text)


def list_providers():
    resp = requests.get(f'{API_BASE}/{API_VERSION}/providers')
    return json.loads(resp.text)


def list_sources():
    # Load up the cookies
    tokens = _load_tokens()
    resp = requests.get(f'{API_BASE}/{API_VERSION}/sources',
                        cookies={
                            'jwt_access_cookie': tokens['access_token'],
                            'jwt_refresh_cookie': tokens['refresh_token']
                            }
                        )
    return json.loads(resp.text)


def list_entities(source_id: int):
    tokens = _load_tokens()
    endpoint = f'{API_BASE}/{API_VERSION}/sources/{source_id}/entities'
    resp = requests.get(
            endpoint,
            cookies={
                'jwt_access_cookie':tokens['access_token'],
                'jwt_refresh_cookie':tokens['refresh_token']
                }
            )
    return json.loads(resp.text)


def list_graphs():
    tokens = _load_tokens()
    resp = requests.get(f'{API_BASE}/{API_VERSION}/graphs',
                        cookies={
                            'jwt_access_cookie': tokens['access_token'],
                            'jwt_refresh_cookie': tokens['refresh_token']
                            })
    return json.loads(resp.text)


def create_graph(source_id: int):
    tokens = _load_tokens()
    payload = {'source_id': source_id}
    resp = requests.post(f'{API_BASE}/{API_VERSION}/create_graph',
                         json=payload,
                         cookies={
                            'jwt_access_cookie': tokens['access_token'],
                            'jwt_refresh_cookie': tokens['refresh_token']
                             })
    return json.loads(resp.text)


def list_nodes(graph_id: int):
    tokens = _load_tokens()
    resp = requests.get(f'{API_BASE}/{API_VERSION}/graphs/{graph_id}/nodes',
                        cookies={
                            'jwt_access_cookie': tokens['access_token'],
                            'jwt_refresh_cookie': tokens['refresh_token']
                            })
    return json.loads(resp.text)


def list_edges(graph_id: int):
    tokens = _load_tokens()
    resp = requests.get(f'{API_BASE}/{API_VERSION}/graphs/{graph_id}/edges',
                        cookies={
                            'jwt_access_cookie': tokens['access_token'],
                            'jwt_refresh_cookie': tokens['refresh_token']
                            })
    return json.loads(resp.text)
