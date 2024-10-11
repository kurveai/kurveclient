#!/usr/bin/env python

import os
import json
import time
from pathlib import Path
import subprocess
import signal

# third party
import requests
from rich.console import Console
from structlog import get_logger
import typer


auth_cli= typer.Typer(name="auth", help="Kurve client cli", no_args_is_help=True)
console = Console()
logger = get_logger(__name__)


API_BASE = os.getenv('KURVE_API_ENDPOINT', 'https://demo.kurve.ai')


def _auth ():
    home = Path.home()
    if Path(home / '.kurve' / 'config.json').exists():
        # read the current config
        config_path = Path(home / '.kurve' / 'config.json')
        tokens = None
        with open(config_path, 'r') as f:
            tokens = json.loads(f.read())
        # Check the status of the tokens.
        endpoint = f'{API_BASE}/tokenstatus'
        resp = requests.post(
                endpoint,
                json=tokens
                )
        if resp.status_code == 200:
            token_status = json.loads(resp.text)
            if token_status['access_expired'] or token_status['refresh_expired']:
                console.print("[yellow]Access token or refresh token expired![/yellow]")
            else:
                console.print("[green]Tokens not expired![/green]")
    else:
        web_url = f'{API_BASE}/login_auth0?client_callback=true'
        pid = _start_app()
        console.print(f"Please visit the following link on a browser to finish authenticating: \n[link={web_url}]{web_url}[/link]\n")
        finished = False
        i = 0
        max_waits = 10
        with console.status("Waiting for user to authenticate...", spinner="dots"):
            token_path = Path(home / '.kurve' / 'config.json')
            while not finished and i < max_waits:
                time.sleep(10)
                i += 1
                if token_path.exists():
                    _teardown_app(pid)
                    finished = True                
        console.print(f"[green]Authentication is complete![/green]\nTokens can be found at [yellow]{token_path}[/yellow]")


fbase = os.path.abspath(__file__)
app_path = '/'.join(fbase.split('/')[0:-1]) + '/app.py'
def _start_app () -> int:
    command = ["nohup", "fastapi", "run", app_path, "--port", "9843"]
    process = subprocess.Popen(command, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    return process.pid


def _teardown_app (pid) -> bool:    
    os.kill(pid, signal.SIGTERM)
    return bool


if __name__ == '__main__':
    _auth()
