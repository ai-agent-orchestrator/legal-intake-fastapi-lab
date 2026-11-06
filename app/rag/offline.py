"""Python network guard; native networking is not an OS firewall guarantee."""
import os
import socket
from contextlib import contextmanager
from unittest.mock import patch


@contextmanager
def offline():
    os.environ.update(HF_HUB_OFFLINE="1", HF_HUB_DISABLE_TELEMETRY="1", MEMVID_TELEMETRY="0",
                      TOKENIZERS_PARALLELISM="false")
    def denied(*args, **kwargs):
        raise AssertionError("Network forbidden during offline RAG execution")
    with patch.object(socket.socket, "connect", denied), patch.object(socket.socket, "connect_ex", denied), \
         patch.object(socket, "create_connection", denied), patch.object(socket, "getaddrinfo", denied):
        yield
