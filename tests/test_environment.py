import json
import threading
from http.server import ThreadingHTTPServer
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import pytest
from conftest import batch

from luxrisk.api import make_handler
from luxrisk.cli import doctor


def test_doctor_checks_resources_without_creating_ledger(store):
    assert doctor()["ok"] is True
    assert not store.path.exists()


def test_local_http_uses_same_report_and_rejects_untrusted_host(store):
    store.publish((batch(),), "demo", "two-row HTTP fixture")
    with ThreadingHTTPServer(("127.0.0.1", 0), make_handler(store)) as server:
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        try:
            root = f"http://127.0.0.1:{server.server_port}"
            with urlopen(
                root + "/api/report?country=DE&indicator=inflation&mode=demo", timeout=5
            ) as response:
                assert json.load(response)["summary"]["value"] == 2.0
                assert response.headers["X-Content-Type-Options"] == "nosniff"
            with urlopen(root, timeout=5) as response:
                assert b"Read the movement" in response.read()
            with pytest.raises(HTTPError) as exc:
                urlopen(Request(root, headers={"Host": "external.invalid"}), timeout=5)
            assert exc.value.code == 403
        finally:
            server.shutdown()
            thread.join(timeout=5)
