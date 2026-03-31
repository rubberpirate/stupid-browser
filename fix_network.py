import re

with open('/home/rubberpirate/stupid-browser/browser/stupid_browser_scratch/stupid_browser_scratch/network.py', 'r') as f:
    code = f.read()

fixed = re.sub(
    r"    def _request_http.*?def resolve",
    """    def _request_http(self) -> tuple[dict[str, str], str, URL]:
        req = request.Request(
            str(self),
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        ctx = ssl._create_unverified_context()
        with request.urlopen(req, timeout=20, context=ctx) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            try:
                text = body.decode(charset, errors="replace")
            except LookupError:
                text = body.decode("utf-8", errors="replace")

            headers = {key.lower(): value for key, value in response.headers.items()}
            final_url = URL(response.geturl())
            return (headers, text, final_url)

    def resolve""",
    code,
    flags=re.DOTALL
)

with open('/home/rubberpirate/stupid-browser/browser/stupid_browser_scratch/stupid_browser_scratch/network.py', 'w') as f:
    f.write(fixed)
