"""A small MCP client for the image test, Python standard library only.

It runs in a container on the network of the test. Its argument is a JSON
object: url, token (or null), host (a Host header, or null), and calls, a
list of [method, params]. It opens one session, makes the calls in order,
and prints one JSON object: the HTTP status of the first request and the
result or error of each call. It prints no token.
"""

import json
import sys
import urllib.error
import urllib.request


def post(url, body, token, host, session):
    headers = {
        "Content-Type": "application/json",
        "Accept": "application/json, text/event-stream",
    }
    if token is not None:
        headers["Authorization"] = f"Bearer {token}"
    if host is not None:
        headers["Host"] = host
    if session:
        headers["Mcp-Session-Id"] = session
    req = urllib.request.Request(
        url, data=json.dumps(body).encode(), headers=headers, method="POST"
    )
    try:
        with urllib.request.urlopen(req, timeout=60) as res:
            text = res.read().decode()
            status, sid, kind = (
                res.status,
                res.headers.get("Mcp-Session-Id"),
                res.headers.get("Content-Type", ""),
            )
    except urllib.error.HTTPError as err:
        return err.code, None, None
    if not text:
        return status, sid, None
    if kind.startswith("text/event-stream"):
        data = [
            line[5:].strip() for line in text.splitlines() if line.startswith("data:")
        ]
        text = data[-1] if data else "null"
    return status, sid, json.loads(text)


def main():
    args = json.loads(sys.argv[1])
    url, token, host = args["url"], args.get("token"), args.get("host")
    init = {
        "jsonrpc": "2.0",
        "id": 1,
        "method": "initialize",
        "params": {
            "protocolVersion": "2025-06-18",
            "capabilities": {},
            "clientInfo": {"name": "image-test", "version": "1"},
        },
    }
    status, session, _ = post(url, init, token, host, None)
    out = {"status": status, "results": []}
    if status != 200:
        print(json.dumps(out))
        return
    post(
        url,
        {"jsonrpc": "2.0", "method": "notifications/initialized"},
        token,
        host,
        session,
    )
    for i, (method, params) in enumerate(args.get("calls", []), start=2):
        code, _, body = post(
            url,
            {"jsonrpc": "2.0", "id": i, "method": method, "params": params},
            token,
            host,
            session,
        )
        out["results"].append({"status": code, "body": body})
    print(json.dumps(out))


if __name__ == "__main__":
    main()
