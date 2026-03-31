from __future__ import annotations

import base64
import ssl
from urllib import parse, request


class URL:
    def __init__(self, raw: str):
        raw = raw.strip()
        if not raw:
            raise ValueError("URL cannot be empty")

        self.raw = raw
        self.parsed = parse.urlparse(raw)

        if not self.parsed.scheme:
            raise ValueError("URL must include a scheme")

        if self.parsed.scheme not in {"http", "https", "file", "data"}:
            raise ValueError(f"Unsupported URL scheme: {self.parsed.scheme}")

    def request(self) -> tuple[dict[str, str], str, URL]:
        scheme = self.parsed.scheme
        if scheme == "file":
            return self._request_file()
        if scheme == "data":
            return self._request_data_url()
        return self._request_http()

    def _request_file(self) -> tuple[dict[str, str], str, URL]:
        if self.parsed.path:
            path_part = self.parsed.path
        else:
            path_part = self.parsed.netloc

        local_path = request.url2pathname(path_part)
        with open(local_path, "rb") as file:
            data = file.read()

        text = data.decode("utf-8", errors="replace")
        return ({"content-type": "text/html"}, text, self)

    def _request_data_url(self) -> tuple[dict[str, str], str, URL]:
        if "," not in self.raw:
            raise ValueError("Malformed data URL")

        header, data = self.raw.split(",", 1)
        meta = header[5:] if header.startswith("data:") else ""
        parts = [part.strip().lower() for part in meta.split(";") if part.strip()]

        charset = "utf-8"
        media_type = "text/plain"
        is_base64 = False

        if parts:
            if "/" in parts[0]:
                media_type = parts[0]
                parts = parts[1:]

            for part in parts:
                if part == "base64":
                    is_base64 = True
                elif part.startswith("charset="):
                    charset = part.split("=", 1)[1] or charset

        if is_base64:
            payload = base64.b64decode(data)
        else:
            payload = parse.unquote_to_bytes(data)

        text = payload.decode(charset, errors="replace")
        return ({"content-type": media_type}, text, self)

    def _request_http(self) -> tuple[dict[str, str], str, URL]:
        req = request.Request(
            str(self),
            headers={Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )

        ctx = ssl._create_unverified_context()
        with request.urlopen(req, timeout=20, context=ctx
        with request.urlopen(req, timeout=20) as response:
            body = response.read()
            charset = response.headers.get_content_charset() or "utf-8"
            try:
                text = body.decode(charset, errors="replace")
            except LookupError:
                text = body.decode("utf-8", errors="replace")

            headers = {key.lower(): value for key, value in response.headers.items()}
            final_url = URL(response.geturl())
            return (headers, text, final_url)

    def resolve(self, reference: str) -> URL:
        return URL(parse.urljoin(str(self), reference))

    def __str__(self) -> str:
        return parse.urlunparse(self.parsed)

    def __repr__(self) -> str:
        return f"URL({str(self)!r})"
