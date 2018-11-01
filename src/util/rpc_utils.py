import json
import subprocess


def send_request(cmd):

    # execute client
    process = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)

    bytes=[]
    for b in process.stdout:
        bytes.append(b)

    process.wait()

    buffer = b''.join(bytes).decode('utf-8')
    print(buffer)

    process.wait()

    return buffer

def parse_response(client_response):
    # because of disclaimer header; find beginning of response
    idx = client_response.find("{")
    if idx < 0:
        idx = client_response.find("[")
    if idx < 0:
        idx = client_response.find("\"")
    if idx < 0:
        raise Exception("Unknown client response format")

    response_str = client_response[idx:]

    print(response_str)

    response_json = json.loads(response_str)
    return response_json
