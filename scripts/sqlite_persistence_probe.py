from __future__ import annotations

import argparse
import os
import sqlite3
from pathlib import Path

MARKER = "trm-persistence-probe-v1"


def database_path() -> Path:
    return Path(os.getenv("DATABASE_PATH", "/app/data/trading_risk.db"))


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    return sqlite3.connect(path, timeout=10)


def write_marker() -> None:
    with connect() as connection:
        connection.execute(
            "CREATE TABLE IF NOT EXISTS runtime_persistence_probe (marker TEXT PRIMARY KEY)"
        )
        connection.execute(
            "INSERT OR REPLACE INTO runtime_persistence_probe(marker) VALUES (?)",
            (MARKER,),
        )
        connection.commit()
    print(f"sqlite persistence marker written: {database_path()}")


def read_clean() -> None:
    with connect() as connection:
        row = connection.execute(
            "SELECT marker FROM runtime_persistence_probe WHERE marker = ?",
            (MARKER,),
        ).fetchone()
        if row is None:
            raise SystemExit("sqlite persistence marker was lost")
        connection.execute(
            "DELETE FROM runtime_persistence_probe WHERE marker = ?",
            (MARKER,),
        )
        connection.commit()
    print("sqlite persistence marker survived restart/down-up cycle")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["write", "read-clean"])
    args = parser.parse_args()
    if args.mode == "write":
        write_marker()
    else:
        read_clean()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
