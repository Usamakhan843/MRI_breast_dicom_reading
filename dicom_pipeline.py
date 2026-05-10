"""
DICOM Batch Metadata Pipeline — QIN-BREAST-02 (DCE Breast MRI)
===============================================================
Recursively reads all .dcm files, extracts MRI metadata and
optional pixel statistics, and produces:
  1. metadata_all.csv     — one row per DICOM file
  2. summary_report.txt   — dataset-level statistics

Usage:
    python dicom_pipeline.py                          # uses default paths
    python dicom_pipeline.py --pixel-stats            # also compute pixel stats (slower)
    python dicom_pipeline.py -d /custom/path -o ./out # override paths

Author: Usama
"""

import argparse
import csv
import logging
import numpy as np
from collections import defaultdict
from datetime import datetime
from pathlib import Path

import pydicom

# ---------------------------------------------------------------------------
# DEFAULT PATHS — edit these once, never type them again
# ---------------------------------------------------------------------------
DEFAULT_DATA_DIR   = "/home/usama/dicom_learning/data/qin_breast_02"
DEFAULT_OUTPUT_DIR = "/home/usama/dicom_learning/output"

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Tags to extract — tailored to QIN-BREAST-02 (Philips 3T DCE-MRI)
# ---------------------------------------------------------------------------
TAGS = {
    # Patient
    "PatientID":                  "Patient ID",
    "PatientSex":                 "Sex",
    "PatientAge":                 "Age",

    # Study / Series
    "StudyDate":                  "Study Date",
    "SeriesDescription":          "Series Description",
    "SeriesNumber":               "Series Number",
    "InstanceNumber":             "Instance Number",
    "Modality":                   "Modality",

    # Scanner
    "Manufacturer":               "Manufacturer",
    "ManufacturerModelName":      "Scanner Model",
    "MagneticFieldStrength":      "Field Strength (T)",
    "ReceiveCoilName":            "Receive Coil",

    # MRI Sequence
    "PulseSequenceName":          "Pulse Sequence",
    "ScanningSequence":           "Scanning Sequence",
    "MRAcquisitionType":          "MR Acquisition Type",
    "RepetitionTime":             "TR (ms)",
    "EchoTime":                   "TE (ms)",
    "FlipAngle":                  "Flip Angle (deg)",
    "InversionTime":              "TI (ms)",
    "ProtocolName":               "Protocol Name",

    # DCE-specific
    "TemporalPositionIdentifier": "Temporal Position",
    "NumberOfTemporalPositions":  "Total Temporal Positions",

    # Image geometry
    "SliceThickness":             "Slice Thickness (mm)",
    "PixelSpacing":               "Pixel Spacing (mm)",
    "Rows":                       "Rows",
    "Columns":                    "Columns",

    # De-identification
    "PatientIdentityRemoved":     "PHI Removed",
}


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def get_tag(ds: pydicom.Dataset, keyword: str) -> str:
    """Safely read a DICOM tag, return 'N/A' if absent."""
    if not hasattr(ds, keyword):
        return "N/A"
    val = getattr(ds, keyword)
    if isinstance(val, pydicom.multival.MultiValue):
        return " x ".join(str(v) for v in val)
    return str(val)


def compute_pixel_stats(ds: pydicom.Dataset) -> dict:
    """
    Compute basic pixel statistics from the image.
    Applies RescaleSlope and RescaleIntercept if present.
    """
    try:
        pixels    = ds.pixel_array.astype(np.float32)
        slope     = float(getattr(ds, "RescaleSlope",     1))
        intercept = float(getattr(ds, "RescaleIntercept", 0))
        pixels    = pixels * slope + intercept

        return {
            "Pixel Mean":    f"{pixels.mean():.2f}",
            "Pixel Std":     f"{pixels.std():.2f}",
            "Pixel Min":     f"{pixels.min():.2f}",
            "Pixel Max":     f"{pixels.max():.2f}",
            "Dynamic Range": f"{pixels.max() - pixels.min():.2f}",
        }
    except Exception as e:
        logger.warning(f"Pixel stats failed: {e}")
        return {k: "N/A" for k in
                ["Pixel Mean", "Pixel Std", "Pixel Min", "Pixel Max", "Dynamic Range"]}


# ---------------------------------------------------------------------------
# Process one file
# ---------------------------------------------------------------------------
def process_file(filepath: str, pixel_stats: bool = False) -> dict | None:
    """Read one DICOM file and return a metadata dict."""
    try:
        ds  = pydicom.dcmread(filepath, stop_before_pixels=not pixel_stats)
        row = {"Filepath": str(filepath)}
        for keyword, label in TAGS.items():
            row[label] = get_tag(ds, keyword)
        if pixel_stats:
            row.update(compute_pixel_stats(ds))
        return row
    except Exception as e:
        logger.warning(f"Skipped {filepath}: {e}")
        return None


# ---------------------------------------------------------------------------
# Batch process directory
# ---------------------------------------------------------------------------
def process_directory(data_dir: str, pixel_stats: bool = False) -> list[dict]:
    """Recursively find and process all DICOM files."""
    dcm_files = list(Path(data_dir).rglob("*.dcm"))
    total     = len(dcm_files)
    logger.info(f"Found {total} DICOM files.")
    if pixel_stats:
        logger.info("Pixel statistics enabled — this will take longer.")

    records = []
    for i, filepath in enumerate(dcm_files, 1):
        if i % 1000 == 0 or i == total:
            logger.info(f"  Processing {i}/{total} ...")
        row = process_file(str(filepath), pixel_stats=pixel_stats)
        if row:
            records.append(row)

    logger.info(f"Successfully processed {len(records)}/{total} files.")
    return records


# ---------------------------------------------------------------------------
# Export CSV
# ---------------------------------------------------------------------------
def export_csv(records: list[dict], output_path: str) -> None:
    if not records:
        logger.warning("No records to export.")
        return
    fieldnames = list(records[0].keys())
    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(records)
    logger.info(f"CSV saved → {output_path}")


# ---------------------------------------------------------------------------
# Summary report
# ---------------------------------------------------------------------------
def write_summary(records: list[dict], data_dir: str, report_path: str,
                  pixel_stats: bool = False) -> None:

    def unique(field):
        return sorted(set(r[field] for r in records if r.get(field, "N/A") != "N/A"))

    patients        = unique("Patient ID")
    study_dates     = unique("Study Date")
    series_descs    = unique("Series Description")
    field_strengths = unique("Field Strength (T)")
    scanners        = unique("Scanner Model")
    total_dynamics  = unique("Total Temporal Positions")
    phi_removed     = unique("PHI Removed")

    per_patient = defaultdict(int)
    for r in records:
        per_patient[r["Patient ID"]] += 1

    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    lines = [
        "=" * 65,
        "  QIN-BREAST-02 — DATASET METADATA SUMMARY",
        "=" * 65,
        f"  Generated        : {now}",
        f"  Source dir       : {data_dir}",
        f"  Total files      : {len(records)}",
        f"  Pixel stats      : {'Yes' if pixel_stats else 'No  (run with --pixel-stats to enable)'}",
        "",
        "  PATIENTS",
        "-" * 65,
        f"  Total patients   : {len(patients)}",
        f"  IDs              : {', '.join(patients)}",
        "",
        "  FILES PER PATIENT",
        "-" * 65,
    ]
    for pid, count in sorted(per_patient.items()):
        lines.append(f"  {pid:<40} {count} files")

    lines += [
        "",
        "  SCANNER / ACQUISITION",
        "-" * 65,
        f"  Scanner          : {', '.join(scanners)}",
        f"  Field strength   : {', '.join(field_strengths)} T",
        f"  Study dates      : {', '.join(study_dates)}",
        f"  DCE dynamics     : {', '.join(total_dynamics)} time points",
        "",
        "  SERIES TYPES",
        "-" * 65,
    ]
    for s in series_descs:
        lines.append(f"  - {s}")

    if pixel_stats:
        def mean_of(field):
            vals = [float(r[field]) for r in records if r.get(field, "N/A") != "N/A"]
            return f"{np.mean(vals):.2f}" if vals else "N/A"

        lines += [
            "",
            "  PIXEL STATISTICS (averaged across all files)",
            "-" * 65,
            f"  Mean intensity   : {mean_of('Pixel Mean')}",
            f"  Mean std dev     : {mean_of('Pixel Std')}",
            f"  Mean min value   : {mean_of('Pixel Min')}",
            f"  Mean max value   : {mean_of('Pixel Max')}",
            f"  Mean dyn. range  : {mean_of('Dynamic Range')}",
        ]

    lines += [
        "",
        "  DE-IDENTIFICATION",
        "-" * 65,
        f"  PHI removed      : {', '.join(phi_removed)}",
        "=" * 65,
    ]

    with open(report_path, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    logger.info(f"Summary report saved → {report_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Batch DICOM metadata extractor for QIN-BREAST-02."
    )
    parser.add_argument("--data-dir",    "-d", default=DEFAULT_DATA_DIR,
                        help=f"Root DICOM directory (default: {DEFAULT_DATA_DIR})")
    parser.add_argument("--output-dir",  "-o", default=DEFAULT_OUTPUT_DIR,
                        help=f"Output directory (default: {DEFAULT_OUTPUT_DIR})")
    parser.add_argument("--pixel-stats", "-p", action="store_true",
                        help="Compute pixel statistics per file (slower)")
    return parser.parse_args()


def main():
    args    = parse_args()
    out_dir = Path(args.output_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    csv_path    = str(out_dir / "metadata_all.csv")
    report_path = str(out_dir / "summary_report.txt")

    records = process_directory(args.data_dir, pixel_stats=args.pixel_stats)
    export_csv(records, csv_path)
    write_summary(records, args.data_dir, report_path, pixel_stats=args.pixel_stats)

    print("\n✓ Pipeline complete.")
    print(f"  Metadata CSV    → {csv_path}")
    print(f"  Summary report  → {report_path}")


if __name__ == "__main__":
    main()
