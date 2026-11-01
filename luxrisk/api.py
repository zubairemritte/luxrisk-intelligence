"""Loopback-only, read-only report viewer using the Python standard library."""

import json
import mimetypes
from dataclasses import asdict
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import cast
from urllib.parse import parse_qs, urlsplit

from luxrisk.analysis import exposure_scenario
from luxrisk.catalog import COUNTRIES, INDICATORS
from luxrisk.models import JsonObject, Mode
from luxrisk.reporting import compare_countries, series_report
from luxrisk.warehouse import Warehouse


def make_handler(store: Warehouse, default_mode: Mode = "demo") -> type[BaseHTTPRequestHandler]:
    """Bind a ledger to one HTTP handler type without starting a listener.

    Args:
        store: Local ledger owner. Handlers make independent read-only SQLite connections.
        default_mode: Initial viewer cohort; request mode is still validated explicitly.

    Returns:
        Handler class accepted by ThreadingHTTPServer.

    Side effects:
        None; no network or source collection until the caller starts the local viewer.

    """

    class Handler(BaseHTTPRequestHandler):
        """Serve whitelisted assets and read-only JSON calculations on loopback."""

        def do_GET(self) -> None:
            """Route a single safe local read, returning visible empty/error states.

            Returns:
                None; writes a JSON or static-file HTTP response.

            Side effects:
                Reads known assets/ledger; never collects, exports or mutates user data.
                Rejects nonlocal Host headers and disallows cross-origin embedding/scripts.

            """
            host: str = self.headers.get("Host", "").split(":")[0]
            if host not in {"127.0.0.1", "localhost"}:
                self.respond(403, b"Local host required", "text/plain")
                return
            parsed = urlsplit(self.path)
            params: dict[str, list[str]] = parse_qs(parsed.query)
            mode_text: str = params.get("mode", [default_mode])[0]
            try:
                if mode_text not in {"demo", "live"}:
                    raise ValueError("Choose demo or live")
                mode: Mode = cast(Mode, mode_text)
                data: JsonObject | list[JsonObject]
                if parsed.path == "/api/catalog":
                    data = {
                        "countries": COUNTRIES,
                        "indicators": {key: asdict(spec) for key, spec in INDICATORS.items()},
                        "default_mode": default_mode,
                    }
                elif parsed.path == "/api/coverage":
                    data = store.coverage(mode)
                elif parsed.path == "/api/report":
                    run: str | None = params.get("run_id", [None])[0]
                    data = series_report(
                        store,
                        params.get("country", ["DE"])[0],
                        params.get("indicator", ["inflation"])[0],
                        mode,
                        int(run) if run else None,
                    )
                elif parsed.path == "/api/compare":
                    data = compare_countries(
                        store,
                        params.get("countries", ["DE,FR"])[0].split(","),
                        params.get("indicator", ["inflation"])[0],
                        mode,
                    )
                elif parsed.path == "/api/scenario":
                    data = exposure_scenario(
                        float(params.get("imports", ["100000"])[0]),
                        float(params.get("fx", ["1.1"])[0]),
                        float(params.get("shock", ["-10"])[0]),
                        float(params.get("debt", ["500000"])[0]),
                        float(params.get("bps", ["100"])[0]),
                    )
                elif parsed.path in {"/", "/app.js", "/style.css"}:
                    name: str = "index.html" if parsed.path == "/" else parsed.path[1:]
                    asset: Path = Path(__file__).with_name("static") / name
                    self.respond(
                        200, asset.read_bytes(), mimetypes.guess_type(name)[0] or "text/plain"
                    )
                    return
                else:
                    self.respond(404, b"Not found", "text/plain")
                    return
                self.respond(200, json.dumps(data, allow_nan=False).encode(), "application/json")
            except (ValueError, FileNotFoundError) as exc:
                self.respond(400, json.dumps({"error": str(exc)}).encode(), "application/json")

        def respond(self, status: int, body: bytes, content_type: str) -> None:
            """Send a length-delimited response with conservative local-viewer headers.

            Args:
                status: HTTP status code.
                body: Already-encoded response bytes.
                content_type: MIME type of this whitelisted resource.

            Returns:
                None; completes the HTTP response.

            Side effects:
                Writes headers and bytes to the connected local client.

            """
            self.send_response(status)
            self.send_header("Content-Type", content_type + "; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header(
                "Content-Security-Policy",
                "default-src 'self'; style-src 'self'; script-src 'self'; frame-ancestors 'none'; base-uri 'none'",
            )
            self.end_headers()
            self.wfile.write(body)

    return Handler


def serve(store: Warehouse, port: int = 8010, mode: Mode = "demo") -> None:
    """Start the explicit local viewer until Ctrl+C.

    Args:
        store: Ledger used for read-only reports.
        port: Unprivileged local TCP port, 1024..65535.
        mode: Initial cohort selected by the UI.

    Returns:
        None after a keyboard interrupt.

    Raises:
        ValueError: Port is outside the supported range.
        OSError: The port is already occupied or cannot be bound.

    Side effects:
        Listens only on 127.0.0.1; no public deployment, database mutation or automatic collection.
        Python's local server is intentionally not a production internet hosting stack.

    """
    if not 1024 <= port <= 65535:
        raise ValueError("Use a local port between 1024 and 65535")
    with ThreadingHTTPServer(("127.0.0.1", port), make_handler(store, mode)) as server:
        print(f"LuxRisk viewer: http://127.0.0.1:{port} | initial mode={mode}")
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            return
