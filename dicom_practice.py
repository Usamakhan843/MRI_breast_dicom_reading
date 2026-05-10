"""
DICOM Practice Script — QIN-BREAST-02 (DCE Breast MRI)
=======================================================
Explore a single DICOM file:
  1. Print all tags
  2. Print key MRI tags cleanly
  3. Show DCE temporal info
  4. Visualize the image slice

Usage:
    python dicom_practice.py --file /path/to/file.dcm
"""

import argparse
import glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pydicom
from pathlib import Path


def find_first_dcm(data_dir: str) -> str:
    """Find the first .dcm file in a directory."""
    files = glob.glob(f"{data_dir}/**/*.dcm", recursive=True)
    if not files:
        raise FileNotFoundError(f"No .dcm files found in {data_dir}")
    return files[0]


def print_all_tags(ds: pydicom.Dataset) -> None:
    """Print every tag in the DICOM file."""
    print("\n" + "=" * 60)
    print("  ALL DICOM TAGS")
    print("=" * 60)
    print(ds)


def print_key_tags(ds: pydicom.Dataset) -> None:
    """Print the most clinically relevant MRI tags."""
    tags = {
        "Patient ID":           "PatientID",
        "Sex":                  "PatientSex",
        "Age":                  "PatientAge",
        "Modality":             "Modality",
        "Study Date":           "StudyDate",
        "Series Description":   "SeriesDescription",
        "Scanner":              "ManufacturerModelName",
        "Field Strength (T)":   "MagneticFieldStrength",
        "Receive Coil":         "ReceiveCoilName",
        "Pulse Sequence":       "PulseSequenceName",
        "MR Acquisition Type":  "MRAcquisitionType",
        "TR (ms)":              "RepetitionTime",
        "TE (ms)":              "EchoTime",
        "Flip Angle (deg)":     "FlipAngle",
        "Slice Thickness (mm)": "SliceThickness",
        "Pixel Spacing (mm)":   "PixelSpacing",
        "Rows x Columns":       None,   # computed
        "Temporal Position":    "TemporalPositionIdentifier",
        "Total Dynamics":       "NumberOfTemporalPositions",
        "PHI Removed":          "PatientIdentityRemoved",
    }

    print("\n" + "=" * 60)
    print("  KEY MRI TAGS")
    print("=" * 60)
    for label, keyword in tags.items():
        if keyword is None:
            val = f"{getattr(ds, 'Rows', '?')} x {getattr(ds, 'Columns', '?')}"
        elif hasattr(ds, keyword):
            raw = getattr(ds, keyword)
            val = " x ".join(str(v) for v in raw) if isinstance(raw, pydicom.multival.MultiValue) else str(raw)
        else:
            val = "N/A"
        print(f"  {label:<25} {val}")
    print("=" * 60)


def explain_dce(ds: pydicom.Dataset) -> None:
    """Explain DCE temporal structure of this file."""
    print("\n  DCE TEMPORAL INFO")
    print("-" * 60)
    tp    = getattr(ds, "TemporalPositionIdentifier", "N/A")
    total = getattr(ds, "NumberOfTemporalPositions",  "N/A")
    print(f"  This slice is time point {tp} of {total} dynamics.")
    print(f"  In DCE-MRI, each dynamic = one full 3D volume of the breast.")
    print(f"  Contrast agent uptake is tracked across these {total} time points.")
    print("-" * 60)


def visualize(ds: pydicom.Dataset, output_path: str) -> None:
    """Visualize the MRI slice and save as PNG."""
    pixels = ds.pixel_array.astype(np.float32)

    # Apply rescale slope/intercept if present
    slope     = float(getattr(ds, "RescaleSlope",     1))
    intercept = float(getattr(ds, "RescaleIntercept", 0))
    pixels    = pixels * slope + intercept

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(pixels, cmap="gray")
    ax.set_title(
        f"{getattr(ds, 'SeriesDescription', 'MRI Slice')} | "
        f"TP: {getattr(ds, 'TemporalPositionIdentifier', '?')}/"
        f"{getattr(ds, 'NumberOfTemporalPositions', '?')} | "
        f"{getattr(ds, 'Rows', '?')}x{getattr(ds, 'Columns', '?')} px",
        fontsize=9
    )
    ax.axis("off")
    plt.tight_layout()
    plt.savefig(output_path, dpi=150, bbox_inches="tight")
    print(f"\n  Image saved → {output_path}")


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------
def parse_args():
    parser = argparse.ArgumentParser(
        description="Explore a single DICOM file from QIN-BREAST-02."
    )
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--file",     "-f", help="Path to a single .dcm file")
    group.add_argument("--data-dir", "-d", help="Auto-pick first .dcm from this directory")
    parser.add_argument("--output",  "-o", default="./mri_slice.png",
                        help="Output path for the visualization (default: ./mri_slice.png)")
    parser.add_argument("--all-tags", action="store_true",
                        help="Also print all DICOM tags (verbose)")
    return parser.parse_args()


def main():
    args = parse_args()

    filepath = args.file if args.file else find_first_dcm(args.data_dir)
    print(f"\n  Reading: {filepath}")

    ds = pydicom.dcmread(filepath)

    if args.all_tags:
        print_all_tags(ds)

    print_key_tags(ds)
    explain_dce(ds)
    visualize(ds, args.output)


if __name__ == "__main__":
    main()
