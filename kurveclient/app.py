import os
import json

from fastapi import FastAPI
from starlette.responses import RedirectResponse
from fastapi import Request

app = FastAPI()

@app.get("/data/")
async def api_data(request: Request):
    params = request.query_params
    url = f'http://some.other.api/?{params}'
    response = RedirectResponse(url=url)
    return response


app = FastAPI()


@app.get("/")
def read_root():
    return {"Hello": "World"}


@app.get("/client_callback")
def callback(request: Request):
    params = request.query_params
    # get the access token
    # and refresh token
    # and save it locally.
    upath = os.path.expanduser('~')
    if not os.path.isdir(os.path.join(upath, '.kurve')):
        os.mkdir(os.path.join(upath, '.kurve'))

    print(params)

    with open(os.path.join(upath, '.kurve/config.json'), 'w') as f:
        f.write(json.dumps({'access_token':params['access_token'],'refresh_token':params['refresh_token']}))
    path = os.path.join(upath, '.kurve/config.json')
    return {'msg': f'saved at {path}'}, 200

