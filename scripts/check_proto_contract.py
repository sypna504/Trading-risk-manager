from __future__ import annotations

import argparse
import importlib
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PROTO = ROOT / "app/proto/ml/v1/ml.proto"

EXPECTED_REQUEST = {
    "symbol": ("string", 1),
    "interval": ("string", 2),
    "strategy_name": ("string", 3),
    "candles": ("repeated Candle", 4),
}
EXPECTED_RESPONSE = {
    "prob_good_trade": ("double", 1),
    "risk_score": ("double", 2),
    "trade_allowed": ("bool", 3),
    "threshold": ("double", 4),
    "risk_level": ("string", 5),
    "model_version": ("string", 6),
    "raw_prob_good_trade": ("double", 7),
    "calibration_method": ("string", 8),
    "probability_bin": ("string", 9),
    "model_supported_interval": ("string", 10),
}


def _message_fields(text: str, name: str) -> dict[str, tuple[str, int]]:
    match = re.search(rf"message\s+{re.escape(name)}\s*\{{(.*?)\n\}}", text, re.S)
    if not match:
        raise AssertionError(f"message {name} not found")
    result: dict[str, tuple[str, int]] = {}
    for raw in match.group(1).splitlines():
        line = raw.strip()
        if not line or line.startswith("//"):
            continue
        field = re.fullmatch(r"(.+?)\s+(\w+)\s*=\s*(\d+)\s*;", line)
        if field:
            result[field.group(2)] = (field.group(1).strip(), int(field.group(3)))
    return result


def check_source() -> None:
    text = PROTO.read_text(encoding="utf-8")
    assert text.count("service MLService") == 1
    assert _message_fields(text, "PredictSignalQualityRequest") == EXPECTED_REQUEST
    assert _message_fields(text, "PredictSignalQualityResponse") == EXPECTED_RESPONSE


def check_generated() -> None:
    try:
        from generate_proto import generate
        import grpc_tools  # noqa: F401
    except ImportError as error:
        raise RuntimeError("grpcio-tools is not installed") from error

    with tempfile.TemporaryDirectory(prefix="trm_proto_") as tmp:
        output = Path(tmp)
        generate(output)
        sys.path.insert(0, str(output))
        try:
            ml_pb2 = importlib.import_module("ml.v1.ml_pb2")
            ml_pb2_grpc = importlib.import_module("ml.v1.ml_pb2_grpc")
            request_fields = {
                field.name: (field.type, field.number)
                for field in ml_pb2.PredictSignalQualityRequest.DESCRIPTOR.fields
            }
            response_fields = {
                field.name: (field.type, field.number)
                for field in ml_pb2.PredictSignalQualityResponse.DESCRIPTOR.fields
            }
            # Generated numeric protobuf types are intentionally checked only by
            # names/numbers here; source-level types are validated above.
            assert set(request_fields) == set(EXPECTED_REQUEST)
            assert {name: number for name, (_, number) in EXPECTED_REQUEST.items()} == {
                name: number for name, (_, number) in request_fields.items()
            }
            assert set(response_fields) == set(EXPECTED_RESPONSE)
            assert {name: number for name, (_, number) in EXPECTED_RESPONSE.items()} == {
                name: number for name, (_, number) in response_fields.items()
            }
            assert hasattr(ml_pb2_grpc, "MLServiceStub")
        finally:
            sys.path.pop(0)
            for name in list(sys.modules):
                if name == "ml" or name.startswith("ml."):
                    sys.modules.pop(name, None)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--strict-generated", action="store_true")
    args = parser.parse_args()

    check_source()
    print("protobuf source contract: OK")
    try:
        check_generated()
    except RuntimeError as error:
        if args.strict_generated:
            raise SystemExit(str(error)) from error
        print(f"protobuf generated contract: NOT RUN ({error})")
    else:
        print("protobuf generated contract: OK")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
