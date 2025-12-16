#!/usr/bin/env python3
"""
ingest.py - Data ingestion for sp-violence-heatmap

Features:
- Copies local files into data/raw/
- Optionally downloads datasets from URLs
- Reads CSV / JSON / Excel and writes standardized Parquet outputs
- Adds minimal provenance columns (source_file, ingested_at)

Usage examples:
  python src/ingest.py --input data_sources/ssp.csv
  python src/ingest.py --url "https://example.com/data.csv" --name ssp.csv
  python src/ingest.py --input data_sources/ssp.xlsx data_sources/other.csv
  python src/ingest.py --skip-parquet
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import pandas as pd

try:
    import requests
except Exception:  # requests is optional if you only ingest local files
    requests = None


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
RAW_DIR = DATA_DIR / "raw"
PROC_DIR = DATA_DIR / "processed" / "ingested"


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 1024), b""):
            h.update(chunk)
    return h.hexdigest()


def ensure_dirs() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    PROC_DIR.mkdir(parents=True, exist_ok=True)


def download_file(url: str, dest: Path, timeout: int = 60) -> None:
    if requests is None:
        raise RuntimeError("requests is not installed. Install it or use --input local files.")
    dest.parent.mkdir(parents=True, exist_ok=True)
    with requests.get(url, stream=True, timeout=timeout) as r:
        r.raise_for_status()
        with dest.open("wb") as f:
            for chunk in r.iter_content(chunk_size=1024 * 256):
                if chunk:
                    f.write(chunk)


def sniff_format(path: Path) -> str:
    ext = path.suffix.lower()
    if ext in [".csv"]:
        return "csv"
    if ext in [".json", ".geojson"]:
        return "json"
    if ext in [".xlsx", ".xls"]:
        return "excel"
    if ext in [".parquet"]:
        return "parquet"
    return "unknown"


def read_any(path: Path, excel_sheet: Optional[str] = None) -> pd.DataFrame:
    fmt = sniff_format(path)
    if fmt == "csv":
        # safer defaults for messy CSVs
        return pd.read_csv(path, dtype_backend="numpy_nullable", low_memory=False)
    if fmt == "json":
        # supports array-of-objects JSON; for nested JSON you may need custom parsing later
        return pd.read_json(path)
    if fmt == "excel":
        return pd.read_excel(path, sheet_name=excel_sheet)
    if fmt == "parquet":
        return pd.read_parquet(path)
    raise ValueError(f"Unsupported file format: {path.name} ({path.suffix})")


def write_parquet(df: pd.DataFrame, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    df.to_parquet(out_path, index=False)


def write_metadata(meta: dict, out_path: Path) -> None:
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


def ingest_one(
    source_path: Path,
    raw_name: Optional[str],
    excel_sheet: Optional[str],
    skip_parquet: bool,
) -> dict:
    ensure_dirs()

    if not source_path.exists():
        raise FileNotFoundError(str(source_path))

    # Copy to raw with chosen name (or keep original)
    target_name = raw_name or source_path.name
    raw_path = RAW_DIR / target_name

    if source_path.resolve() != raw_path.resolve():
        raw_path.write_bytes(source_path.read_bytes())

    meta = {
        "raw_file": str(raw_path.relative_to(ROOT)),
        "original_path": str(source_path),
        "format": sniff_format(raw_path),
        "sha256": sha256_file(raw_path),
        "ingested_at": utc_now_iso(),
    }

    if not skip_parquet:
        df = read_any(raw_path, excel_sheet=excel_sheet)
        # minimal provenance columns
        df = df.copy()
        df["source_file"] = raw_path.name
        df["ingested_at"] = meta["ingested_at"]

        out_parquet = PROC_DIR / f"{raw_path.stem}.parquet"
        write_parquet(df, out_parquet)
        meta["parquet"] = str(out_parquet.relative_to(ROOT))
        meta["rows"] = int(len(df))
        meta["columns"] = list(map(str, df.columns))

    meta_path = PROC_DIR / f"{raw_path.stem}.meta.json"
    write_metadata(meta, meta_path)
    meta["metadata"] = str(meta_path.relative_to(ROOT))
    return meta


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest datasets into data/raw and standardized parquet outputs.")
    parser.add_argument("--input", nargs="*", default=[], help="Local file paths to ingest (CSV/JSON/XLSX/Parquet).")
    parser.add_argument("--url", action="append", default=[], help="URL to download and ingest (repeatable).")
    parser.add_argument("--name", action="append", default=[], help="Filename for each --url (repeatable, same count).")
    parser.add_argument("--excel-sheet", default=None, help="Excel sheet name (if ingesting .xlsx).")
    parser.add_argument("--skip-parquet", action="store_true", help="Only store raw + metadata; do not create parquet.")
    args = parser.parse_args()

    ensure_dirs()

    # Handle downloads
    if args.url:
        if args.name and len(args.name) != len(args.url):
            print("ERROR: --name must be provided the same number of times as --url (or not used).", file=sys.stderr)
            return 2

        for i, url in enumerate(args.url):
            fname = args.name[i] if args.name else Path(url.split("?")[0]).name or f"download_{i}"
            dest = RAW_DIR / fname
            print(f"Downloading: {url} -> {dest}")
            download_file(url, dest)
            # ingest downloaded raw file (already in RAW_DIR)
            meta = ingest_one(dest, raw_name=fname, excel_sheet=args.excel_sheet, skip_parquet=args.skip_parquet)
            print(f"✓ Ingested {fname} (meta: {meta['metadata']})")

    # Handle local files
    for p in args.input:
        path = Path(p).expanduser()
        print(f"Ingesting local file: {path}")
        meta = ingest_one(path, raw_name=None, excel_sheet=args.excel_sheet, skip_parquet=args.skip_parquet)
        print(f"✓ Ingested {path.name} (meta: {meta['metadata']})")

    if not args.url and not args.input:
        print("Nothing to ingest. Use --input <file> or --url <link>.", file=sys.stderr)
        return 2

    print(f"\nDone.\n- Raw: {RAW_DIR}\n- Processed: {PROC_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
