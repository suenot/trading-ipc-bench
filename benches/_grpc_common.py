"""Shared gRPC setup: proto compilation + servicer definition.

Both bench_grpc_tcp.py and bench_grpc_uds.py import from here.
On first call, compiles echo.proto → echo_pb2.py + echo_pb2_grpc.py.
Requires: pip install grpcio grpcio-tools
"""
import subprocess
import sys
import time
import threading
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).parent.parent
PROTO_DIR = ROOT / "benches" / "proto"

sys.path.insert(0, str(ROOT))


def _ensure_stubs() -> bool:
    if (PROTO_DIR / "echo_pb2.py").exists():
        return True
    try:
        result = subprocess.run(
            [
                sys.executable, "-m", "grpc_tools.protoc",
                f"-I{PROTO_DIR}",
                f"--python_out={PROTO_DIR}",
                f"--grpc_python_out={PROTO_DIR}",
                str(PROTO_DIR / "echo.proto"),  # absolute path required by protoc
            ],
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  protoc failed:\n{result.stderr}")
            return False
        return True
    except Exception as e:
        print(f"  grpcio-tools not available: {e}\n  Run: pip install grpcio grpcio-tools")
        return False


def load_grpc():
    """Return (grpc, echo_pb2, echo_pb2_grpc) or None."""
    if not _ensure_stubs():
        return None
    # The generated echo_pb2_grpc.py uses `import echo_pb2` (non-relative),
    # so the proto directory itself must be in sys.path.
    if str(PROTO_DIR) not in sys.path:
        sys.path.insert(0, str(PROTO_DIR))
    try:
        import grpc
        import echo_pb2
        import echo_pb2_grpc
        return grpc, echo_pb2, echo_pb2_grpc
    except ImportError as e:
        print(f"  grpcio not installed: {e}\n  Run: pip install grpcio grpcio-tools")
        return None


def make_servicer(echo_pb2, echo_pb2_grpc):
    class _Servicer(echo_pb2_grpc.EchoServiceServicer):
        def Echo(self, request, context):
            return echo_pb2.EchoReply(data=request.data)
    return _Servicer()


def start_server(grpc, echo_pb2, echo_pb2_grpc, address: str):
    """Start a gRPC server on `address`. Returns (server, ready_event)."""
    ready = threading.Event()
    server = grpc.server(ThreadPoolExecutor(max_workers=2))
    echo_pb2_grpc.add_EchoServiceServicer_to_server(
        make_servicer(echo_pb2, echo_pb2_grpc), server
    )
    server.add_insecure_port(address)

    def _run():
        server.start()
        ready.set()
        server.wait_for_termination()

    t = threading.Thread(target=_run, daemon=True)
    t.start()
    ready.wait(timeout=5)
    return server
