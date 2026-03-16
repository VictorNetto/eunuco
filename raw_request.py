import httpx
from pathlib import Path
import io

def parse_raw_request(raw_bytes: bytes):
    """
    Parses raw bytes into componets fot httpx
    """
    # 1. Split headers and body (separeted by double CRLF)
    parts = raw_bytes.split(b"\r\n\r\n", 1)
    headers_section = parts[0].decode("utf-8")
    body = parts[1] if len(parts) > 0 else b""

    lines = headers_section.splitlines()
    if not lines:
        return None
    
    # 2. Parse the Request Line: "GET https://example.com:443/path HTTP/2.0"
    request_line_parts = lines[0].split()
    if len(request_line_parts) < 2:
        return None
    method, raw_path, _ = request_line_parts  # raw path may be a path or a full URL

    # 3. Parse Headers into a dict
    headers = {}
    for line in lines[1:]:
        if ':' in line:
            k, v = line.split(':', 1)
            headers[k.strip()] = v.strip()
    
    # 4. Determine the Final URL
    # If the path is an absolute URL (contains ://), use it directly
    if "://" in raw_path:
        url = raw_path
    else:
        # Fallback to Host header if the path was just "/path"
        host = headers.get("Host") or headers.get(":authority")
        if not host:
            raise ValueError("No destination found in request line or Host header.")
        
        # Assume HTTPS if not specified, as per your previous requirement
        url = f"https://{host.strip()}{raw_path}"

    return method, url, headers, body

def show_raw_request(flow_dir: str, request_file: str):
    dir_path = Path(flow_dir)
    req_path = dir_path / request_file
    print(req_path)

    # if not req_path.exists():
    #     print(f"Skipping: {req_path} not found.")
    #     return

    raw_request_data = req_path.read_bytes()
    method, url, headers, body = parse_raw_request(raw_request_data)
    print(method)
    print(url)
    print(headers)
    print(body)

def send_request(flow_dir: str, request_file: str):
    dir_path = Path(flow_dir)
    req_path = dir_path / request_file
    raw_request_data = req_path.read_bytes()
    method, url, headers, body = parse_raw_request(raw_request_data)

    # httpx.Client handles the ALPN (HTTP/1.1 vs HTTP/2 negotiation)
    with httpx.Client(http2=True, verify=False) as client:
        print(f"[*] Sending {method} to {url}")
        response = client.request(
            method=method,
            url=url,
            headers=headers,
            content=body
        )

        return response

def save_response(flow_dir: str, response_file: str, response: httpx.Response):
    dir_path = Path(flow_dir)
    req_path = dir_path / response_file
    with open(req_path, "wb") as f:
        # HTTP/2 doesn't have 'Reason Phrases' (like "OK"), so we default to ""
        version = "HTTP/2" if response.http_version == "HTTP/2" else "HTTP/1.1"
        reason = getattr(response, 'reason_phrase', 'OK')
        
        f.write(f"{version} {response.status_code} {reason}\r\n".encode())
        for k, v in response.headers.items():
            f.write(f"{k}: {v}\r\n".encode())
        f.write(b"\r\n")
        f.write(response.content)

if __name__ == "__main__":
    show_raw_request("flows/flow-0", "original_request.raw")
    res = send_request("flows/flow-0", "original_request.raw")
    save_response("flows/flow-0", "original_response.raw", res)