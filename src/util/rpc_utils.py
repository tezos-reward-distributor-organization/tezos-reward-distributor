import json
import subprocess
import re

def send_request(cmd):

    # execute client
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    bytes=[]
    for b in process.stdout:
        bytes.append(b)

    process.wait()

    buffer = b''.join(bytes).decode('utf-8')
    print("buffer is '{}'".format(buffer))

    process.wait()

    return buffer

def parse_response(client_response):

    # get rid of special chars, terminal sequences
    ansi_escape = re.compile(r'\x1B\[[0-?]*[ -/]*[@-~]')
    client_response = ansi_escape.sub('', client_response)

    # because of disclaimer header; find beginning of response
    idx = client_response.find("{")
    if idx < 0:
        idx = client_response.find("[")
    if idx < 0:
        idx = client_response.find("\"")
    if idx < 0:
        raise Exception("Unknown client response format")

    response_str = client_response[idx:]

    print("response_str is '{}'".format(response_str))

    response_json = json.loads(response_str)
    return response_json
