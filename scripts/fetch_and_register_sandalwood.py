"""
fetch_and_register_sandalwood.py
─────────────────────────────────────────────────────────────────────────────
Full pipeline:  GBIF + iNaturalist  →  normalize  →  deduplicate  →  register
into the project's SQLite / Postgres database (same DB the FastAPI app uses).

Usage
─────
  python scripts/fetch_and_register_sandalwood.py              # dry-run preview
  python scripts/fetch_and_register_sandalwood.py --commit     # actually insert
  python scripts/fetch_and_register_sandalwood.py --commit --limit 50

Options
  --commit        Write records to the database (default: dry-run only)
  --limit N       Max occurrences to fetch from *each* source (default: 100)
  --fallback-region REG-KA-SHIVAMOGGA
                  region_id to use when no polygon matches (default: first active region)
  --export csv    Also export all fetched (pre-DB) records to datasets/ as CSV
  --export json   Same, but as JSON
"""

import argparse
import csv
import json
import sys
import time
from dataclasses import dataclass, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

import requests

# ── Make the project root importable ─────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sqlalchemy import select, func
from app.database.database import SessionLocal, init_db
from app.database.models.tree import Tree, TreeStatus
from app.database.models.region import Region


# ── Import Occurrence models and harvesting functions from service layer ───────
from app.services.gbif_service import (
    Occurrence,
    fetch_gbif,
    fetch_inaturalist,
    deduplicate,
    match_region,
    _bbox_of_polygon,
    _point_in_bbox,
)


# ─────────────────────────────────────────────────────────────────────────────
# 6.  UID generator (continues SW-KA-XXXXX sequence)
# ─────────────────────────────────────────────────────────────────────────────

def next_tree_uid(db):
    """Return next available SW-KA-XXXXX uid based on current DB max."""
    max_uid = db.execute(
        select(func.max(Tree.tree_uid)).where(Tree.tree_uid.like("SW-KA-%"))
    ).scalar()

    if max_uid:
        try:
            num = int(max_uid.replace("SW-KA-", "")) + 1
        except ValueError:
            num = 1
    else:
        num = 1
    return f"SW-KA-{num:05d}"


# ─────────────────────────────────────────────────────────────────────────────
# 7.  Registration
# ─────────────────────────────────────────────────────────────────────────────

def register_occurrences(occurrences: list, commit: bool, fallback_region_id: Optional[str]) -> dict:
    """Insert new occurrences as Tree records. Skip those already in DB."""

    init_db()   # ensure tables exist

    stats = {"inserted": 0, "skipped_duplicate": 0, "skipped_no_region": 0, "errors": 0}

    with SessionLocal() as db:
        # Load all regions once
        regions = db.execute(select(Region)).scalars().all()
        if not regions:
            print("[DB]  No regions found. Seed the database first: python run.py")
            return stats

        # Resolve fallback region
        fallback = None
        if fallback_region_id:
            fallback = db.execute(
                select(Region).where(Region.region_id == fallback_region_id)
            ).scalar_one_or_none()
        if fallback is None:
            fallback = regions[0]

        print(f"\n[DB] {len(regions)} region(s) loaded. Fallback -> '{fallback.name}'")
        print(f"[DB] Mode: {'WRITE (--commit)' if commit else 'DRY-RUN (pass --commit to write)'}\n")

        # Pre-load existing coords to skip duplicates efficiently
        existing_coords = set()
        for tree in db.execute(select(Tree)).scalars():
            key = f"{round(tree.latitude, 5):.5f},{round(tree.longitude, 5):.5f}"
            existing_coords.add(key)

        for occ in occurrences:
            if occ.dedupe_key in existing_coords:
                stats["skipped_duplicate"] += 1
                print(f"  SKIP (already in DB)  [{occ.source}] ({occ.latitude:.5f}, {occ.longitude:.5f})")
                continue

            region = match_region(occ.latitude, occ.longitude, regions, fallback)
            if region is None:
                stats["skipped_no_region"] += 1
                print(f"  SKIP (no region)      [{occ.source}] ({occ.latitude:.5f}, {occ.longitude:.5f})")
                continue

            uid = next_tree_uid(db)
            notes = (
                f"Source: {occ.source} | ID: {occ.source_id} | "
                f"Observed: {occ.observed_on or 'unknown'} | "
                f"Observer: {occ.observer or 'unknown'} | "
                f"Place: {occ.place_name or 'unknown'} | "
                + occ.notes
            )[:1000]

            tree = Tree(
                tree_uid=uid,
                region_id=region.id,
                species=occ.species or "Santalum album",
                latitude=occ.latitude,
                longitude=occ.longitude,
                gps_accuracy=occ.coordinate_uncertainty_m,
                status=TreeStatus.HEALTHY,
                notes=notes,
            )

            action = "INSERT" if commit else "WOULD INSERT"
            print(
                f"  {action}  {uid}  [{occ.source}]  "
                f"({occ.latitude:.5f}, {occ.longitude:.5f})  "
                f"-> region='{region.region_id}'"
            )

            if commit:
                try:
                    db.add(tree)
                    db.flush()
                    existing_coords.add(occ.dedupe_key)   # prevent intra-batch dupes
                    stats["inserted"] += 1
                except Exception as exc:
                    db.rollback()
                    stats["errors"] += 1
                    print(f"    ERROR: {exc}")
            else:
                stats["inserted"] += 1   # dry-run count

        if commit:
            db.commit()

    return stats


# ─────────────────────────────────────────────────────────────────────────────
# 8.  Export helpers
# ─────────────────────────────────────────────────────────────────────────────

def export_to_csv(occurrences: list, path: str) -> None:
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(asdict(occurrences[0]).keys()))
        writer.writeheader()
        writer.writerows(asdict(o) for o in occurrences)
    print(f"[Export] CSV written -> {path}")


def export_to_json(occurrences: list, path: str) -> None:
    with open(path, "w", encoding="utf-8") as f:
        json.dump([asdict(o) for o in occurrences], f, indent=2, ensure_ascii=False)
    print(f"[Export] JSON written -> {path}")


# ─────────────────────────────────────────────────────────────────────────────
# 9.  CLI entry point
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="Fetch Santalum album from GBIF + iNaturalist and register in the project DB."
    )
    parser.add_argument("--commit", action="store_true",
                        help="Write records to DB. Without this, runs as dry-run.")
    parser.add_argument("--limit", type=int, default=100,
                        help="Max occurrences to fetch from each source (default: 100).")
    parser.add_argument("--fallback-region", type=str, default=None,
                        help="region_id to use when no polygon matches.")
    parser.add_argument("--export", type=str, choices=["csv", "json"], default=None,
                        help="Export deduplicated occurrences to datasets/ before registering.")
    args = parser.parse_args()

    print("=" * 65)
    print("  Sandalwood Occurrence Pipeline")
    print("  GBIF + iNaturalist  -->  Deduplicate  -->  Register")
    print("=" * 65)

    # Step 1: Fetch
    gbif_records = fetch_gbif(limit=args.limit)
    inat_records = fetch_inaturalist(limit=args.limit)
    all_records  = gbif_records + inat_records

    if not all_records:
        print("\n[Pipeline] No records fetched. Check internet connectivity.")
        sys.exit(1)

    # Step 2: Deduplicate
    unique_records = deduplicate(all_records)

    # Step 3: Export (optional)
    if args.export and unique_records:
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_dir = ROOT / "datasets"
        out_dir.mkdir(exist_ok=True)
        out_path = str(out_dir / f"sandalwood_occurrences_{ts}.{args.export}")
        if args.export == "csv":
            export_to_csv(unique_records, out_path)
        else:
            export_to_json(unique_records, out_path)

    # Step 4: Register
    print("\n[Pipeline] Starting registration ...")
    stats = register_occurrences(
        occurrences=unique_records,
        commit=args.commit,
        fallback_region_id=args.fallback_region,
    )

    # Summary
    print("\n" + "=" * 65)
    print("  Pipeline Summary")
    print("=" * 65)
    print(f"  Records fetched (total)    : {len(all_records)}")
    print(f"  Unique after deduplicate   : {len(unique_records)}")
    label = "Inserted into DB" if args.commit else "Would insert (dry-run)"
    print(f"  {label:<27}: {stats['inserted']}")
    print(f"  Skipped (already in DB)    : {stats['skipped_duplicate']}")
    print(f"  Skipped (no region match)  : {stats['skipped_no_region']}")
    print(f"  Errors                     : {stats['errors']}")
    print("=" * 65)

    if not args.commit:
        print("\n  This was a DRY-RUN. Re-run with --commit to write to DB.")


if __name__ == "__main__":
    main()
