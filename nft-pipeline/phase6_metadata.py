#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Zohar Token — Master Edition  ·  PHASE 6
Emit metadata.json from the real pipeline stats. Local only.
    python phase6_metadata.py
"""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def main():
    stats = json.loads((HERE / "phase1_stats.json").read_text(encoding="utf-8"))
    mmeta = json.loads((HERE / "temple_map.json").read_text(encoding="utf-8"))["meta"]
    total_words = stats["total_words_clean"]

    metadata = {
        "name": "Zohar Token — Master Edition",
        "symbol": "ZOHAR",
        "description": (
            "The Third Temple, built word by word from the complete Aramaic Zohar. "
            "Every word of the corpus is present as its own illuminated micro-artwork. "
            "Zoom in — the Zohar reveals itself. "
            "LightVessel DAO LLC — Master Edition 2026."
        ),
        "image": "zohar_token_master_final.png",
        "attributes": [
            {"trait_type": "Edition", "value": "Master Edition"},
            {"trait_type": "Year", "value": "2026"},
            {"trait_type": "Language", "value": "Aramaic"},
            {"trait_type": "Sections", "value": str(stats["sections_seen"])},
            {"trait_type": "Words", "value": str(total_words)},
            {"trait_type": "Unique Words", "value": str(stats["unique_consonantal"])},
            {"trait_type": "Word Cells", "value": str(mmeta["cell_count"])},
            {"trait_type": "Temple", "value": "Third Temple"},
            {"trait_type": "DAO", "value": "LightVessel DAO LLC — Wyoming"},
        ],
        "properties": {
            "previews": ["zoom_full.png", "zoom_10.png", "zoom_01.png"],
            "grid": f"{mmeta['grid_cols']}x{mmeta['grid_rows']}",
        },
        "seller_fee_basis_points": 500,
        "creators": [
            {"address": "GkC43uAwn8RvxgnJQKxowVgZ9VFaWvUqhyJXouMfwoFs", "share": 100}
        ],
    }
    out = HERE / "metadata.json"
    out.write_text(json.dumps(metadata, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"Wrote {out}\nWords: {total_words:,} | Cells: {mmeta['cell_count']:,}")


if __name__ == "__main__":
    main()
