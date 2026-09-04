import asyncio
from main import app

async def test_asgi_request(path: str, accept_header: str = "*/*"):
    response_headers = []
    response_body = []
    status_code = None

    scope = {
        "type": "http",
        "asgi": {"version": "3.0"},
        "http_version": "1.1",
        "method": "GET",
        "scheme": "http",
        "path": path,
        "raw_path": path.encode("latin1"),
        "query_string": b"",
        "headers": [
            (b"host", b"localhost:8000"),
            (b"accept", accept_header.encode("latin1"))
        ],
        "client": ("127.0.0.1", 12345),
        "server": ("127.0.0.1", 8000),
    }

    async def receive():
        return {"type": "http.request", "body": b"", "more_body": False}

    async def send(message):
        nonlocal status_code
        if message["type"] == "http.response.start":
            status_code = message["status"]
            response_headers.extend(message.get("headers", []))
        elif message["type"] == "http.response.body":
            response_body.append(message.get("body", b""))

    await app(scope, receive, send)
    body_text = b"".join(response_body).decode("utf-8")
    headers_dict = {k.decode("latin1").lower(): v.decode("latin1") for k, v in response_headers}
    return status_code, headers_dict, body_text

async def main():
    print("--- 1. Testing /some-path-that-does-not-exist (404) ---")
    status, headers, body = await test_asgi_request("/some-path-that-does-not-exist")
    print(f"Status: {status}")
    print(f"Content-Type: {headers.get('content-type')}")
    print(f"Vary Header: {headers.get('vary')}")
    assert status == 404, f"Expected 404, got {status}"
    assert "Accept" in headers.get("vary", ""), "Expected 'Accept' in Vary header"
    assert "sitemap" in body.lower()
    print("-> 404 test with Vary header PASSED!")

    print("\n--- 2. Testing Homepage / with Accept: text/html ---")
    status, headers, body_html = await test_asgi_request("/", accept_header="text/html")
    print(f"Status: {status}")
    print(f"Content-Type: {headers.get('content-type')}")
    print(f"Vary Header: {headers.get('vary')}")
    assert status == 200
    assert "text/html" in headers.get("content-type", "")
    assert "Accept" in headers.get("vary", ""), "Expected 'Accept' in Vary header for HTML response"
    print("-> HTML negotiation with Vary header PASSED!")

    print("\n--- 3. Testing Homepage / with Accept: text/markdown ---")
    status, headers, body = await test_asgi_request("/", accept_header="text/markdown")
    print(f"Status: {status}")
    print(f"Content-Type: {headers.get('content-type')}")
    print(f"Vary Header: {headers.get('vary')}")
    assert status == 200
    assert "text/markdown" in headers.get("content-type", "")
    assert "Accept" in headers.get("vary", ""), "Expected 'Accept' in Vary header for Markdown response"
    assert "FraudLens — Real-Time ML Fraud Intelligence" in body
    print("-> Markdown negotiation with Vary header PASSED!")

    print("\n--- 4. Validating JSON-LD Structured Data in HTML Homepage ---")
    import json, re
    match = re.search(r'<script type="application/ld\+json">\s*(\{.*?\})\s*</script>', body_html, re.DOTALL)
    assert match is not None, "JSON-LD script tag not found in HTML response"
    json_ld = json.loads(match.group(1))
    print("Parsed JSON-LD:")
    print(f"  @context: {json_ld.get('@context')}")
    print(f"  @type: {json_ld.get('@type')}")
    print(f"  name: {json_ld.get('name')}")
    print(f"  url: {json_ld.get('url')}")
    print(f"  author: {json_ld.get('author')}")
    print(f"  offers: {json_ld.get('offers')}")
    print(f"  sameAs: {json_ld.get('sameAs')}")

    assert json_ld.get("@context") == "https://schema.org"
    assert json_ld.get("@type") == "SoftwareApplication"
    assert json_ld.get("name") == "FraudLens"
    assert json_ld.get("description")
    assert json_ld.get("url")
    assert "name" in json_ld.get("author", {})
    assert "price" in json_ld.get("offers", {})
    assert len(json_ld.get("sameAs", [])) > 0
    print("-> JSON-LD Structured Data validation PASSED!")

    print("\n--- 5. Validating 'When to Use' Guidance in /llms.txt ---")
    status_llms, headers_llms, body_llms = await test_asgi_request("/llms.txt")
    assert status_llms == 200
    assert "When to Use FraudLens" in body_llms
    assert "When NOT to Use" in body_llms
    assert "How an Agent Should Call" in body_llms
    assert "POST /api/evaluate" in body_llms
    print("-> /llms.txt Guidance validation PASSED!")

    print("\n--- 6. Validating /agent-instructions.md ---")
    status_ai, headers_ai, body_ai = await test_asgi_request("/agent-instructions.md")
    assert status_ai == 200
    assert "When to Use FraudLens" in body_ai
    assert "Agent Adjudication Workflow" in body_ai
    print("-> /agent-instructions.md validation PASSED!")

    print("\nALL ACCEPT NEGOTIATION, VARY, JSON-LD, AND AGENT GUIDANCE TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(main())
