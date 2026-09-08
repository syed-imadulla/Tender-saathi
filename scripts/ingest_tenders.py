"""CLI script for discovering, ingesting, and processing tender PDFs repeatably."""

import os
import sys
import argparse
import shutil
import glob
from generate_dataset import run_pipeline


def main():
    parser = argparse.ArgumentParser(
        description="Ingest tender PDFs and run the SIH26108 technical feasibility spike extraction pipeline."
    )
    parser.add_argument(
        "--source-dir",
        default="tenders/raw",
        help="Directory containing raw tender PDFs (default: tenders/raw)"
    )
    parser.add_argument(
        "--output-dir",
        default="dataset",
        help="Directory to write dataset outputs (default: dataset)"
    )
    parser.add_argument(
        "--reports-dir",
        default="reports/feasibility",
        help="Directory to write feasibility reports (default: reports/feasibility)"
    )
    parser.add_argument(
        "--import-from",
        default=None,
        help="Optional external folder from which to copy new PDFs into tenders/raw without overwriting"
    )

    args = parser.parse_args()

    # If --import-from specified, safely copy PDFs into tenders/raw without overwriting
    if args.import_from and os.path.exists(args.import_from):
        os.makedirs(args.source_dir, exist_ok=True)
        imported_files = glob.glob(os.path.join(args.import_from, "*.pdf"))
        print(f"Importing {len(imported_files)} PDFs from {args.import_from} into {args.source_dir}...")
        for src_pdf in imported_files:
            dst_pdf = os.path.join(args.source_dir, os.path.basename(src_pdf))
            if not os.path.exists(dst_pdf):
                shutil.copy2(src_pdf, dst_pdf)
                print(f"  + Added: {os.path.basename(src_pdf)}")
            else:
                print(f"  = Exists: {os.path.basename(src_pdf)}")

    print("=" * 60)
    print("SIH26108: INGESTING TENDERS & RUNNING EXTRACTION PIPELINE")
    print("=" * 60)
    run_pipeline(
        tenders_dir=args.source_dir,
        output_dir=args.output_dir,
        reports_dir=args.reports_dir
    )
    print("=" * 60)
    print("INGESTION & EXTRACTION PIPELINE COMPLETED SUCCESSFULLY!")
    print("=" * 60)


if __name__ == "__main__":
    main()
