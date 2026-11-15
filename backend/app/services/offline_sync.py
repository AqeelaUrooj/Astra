"""Small append-only store for the offline-sync hackathon demonstration.

The file is deliberately local to this prototype. A real mission system would
need approved storage, access controls, encryption, auditability, and validation.
"""

import json
from pathlib import Path
from typing import Any

STORE_PATH = Path(__file__).resolve().parents[2] / "data" / "synced_packets.jsonl"


def save_synced_packets(packets: list[dict[str, Any]]) -> dict[str, int]:
    """Append new packet IDs once and report how many were already present."""
    STORE_PATH.parent.mkdir(parents=True, exist_ok=True)
    known_packet_ids: set[str] = set()

    if STORE_PATH.exists():
        with STORE_PATH.open("r", encoding="utf-8") as store_file:
            for line in store_file:
                if not line.strip():
                    continue
                try:
                    stored_packet = json.loads(line)
                except json.JSONDecodeError:
                    # Keep a damaged historical line from blocking new samples.
                    continue
                packet_id = stored_packet.get("packet_id")
                if isinstance(packet_id, str):
                    known_packet_ids.add(packet_id)

    stored_count = 0
    duplicate_count = 0
    with STORE_PATH.open("a", encoding="utf-8") as store_file:
        for packet in packets:
            packet_id = packet["packet_id"]
            if packet_id in known_packet_ids:
                duplicate_count += 1
                continue
            store_file.write(json.dumps(packet, separators=(",", ":")) + "\n")
            known_packet_ids.add(packet_id)
            stored_count += 1

    return {
        "received_count": len(packets),
        "stored_count": stored_count,
        "duplicate_count": duplicate_count,
    }
