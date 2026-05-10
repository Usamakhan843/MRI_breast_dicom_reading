# MRI Breast DICOM Metadata

A Python-based pipeline for extracting, auditing, and summarizing DICOM metadata from breast MRI datasets. Built and tested on the publicly available **QIN-BREAST-02** collection from The Cancer Imaging Archive (TCIA), which contains Dynamic Contrast-Enhanced (DCE) MRI data from 13 subjects acquired on a Philips Achieva 3T scanner.

This project serves both as a portfolio demonstration of clinical imaging pipeline design and as a reusable research utility for anyone working with breast MRI DICOM data.

---

## Background

Medical imaging research begins long before any model is trained. Before a single pixel enters a deep learning pipeline, a researcher must understand the dataset: how many patients, what scanner was used, which acquisition sequences exist, whether PHI has been properly removed, and what the image intensity distributions look like. This pipeline automates that audit step.

DICOM (Digital Imaging and Communications in Medicine) is the universal standard for storing and transmitting medical images. Each `.dcm` file contains both the image pixel data and a rich header of structured metadata: patient demographics, scanner parameters, acquisition settings, and more. Reading and interpreting this header is a fundamental skill in medical AI research, yet it is rarely taught explicitly.

This project addresses that gap.

---

## Dataset

**QIN-BREAST-02**, The Cancer Imaging Archive (TCIA)

| Property | Value |
|---|---|
| Modality | MR (Dynamic Contrast-Enhanced) |
| Subjects | 13 |
| Studies | 34 |
| Series | 235 |
| Total Images | 31,790 |
| Scanner | Philips Achieva 3T |
| License | CC BY 4.0 |
| Access | [TCIA Collection Page](https://www.cancerimagingarchive.net/collection/qin-breast-02/) |

All files in this dataset have been de-identified by TCIA prior to release. The `PatientIdentityRemoved` tag is set to `YES` in every file, with de-identification performed per DICOM PS 3.15 Annex E.

---

## Features

- Recursively scans an entire DICOM directory and processes all `.dcm` files
- Extracts 20+ clinically relevant metadata tags per file including MRI sequence parameters, scanner specifications, and DCE temporal information
- Computes per-file pixel statistics (mean, std, min, max, dynamic range) when enabled
- Exports a structured CSV with one row per DICOM file, ready for pandas analysis
- Generates a plain-text dataset audit report with per-patient file counts, series types, scanner details, and aggregated pixel statistics
- Uses `stop_before_pixels=True` by default for fast metadata-only reading across large datasets
- Hardcoded default paths, no lengthy CLI arguments required for routine use

---

## Project Structure

```
MRI_breast_dicom_metadata/
├── dicom_pipeline.py      # Batch metadata extractor, processes all 31,790 files
├── dicom_practice.py      # Single-file explorer: tags, visualization, DCE info
├── requirements.txt
└── README.md
```

---

## Installation

```bash
git clone https://github.com/<Usamakhan843>/MRI_breast_dicom_metadata.git
cd MRI_breast_dicom_metadata
pip install -r requirements.txt
```

---

## Usage

### 1. Batch Metadata Pipeline

Processes all DICOM files in the dataset directory and writes a CSV and summary report.

```bash
# Metadata only, fast (skips pixel data)
python dicom_pipeline.py

# Metadata + pixel statistics, slower but more complete
python dicom_pipeline.py --pixel-stats

# Override paths if needed
python dicom_pipeline.py -d /path/to/dicoms -o ./output
```

**Outputs:**

| File | Description |
|---|---|
| `output/metadata_all.csv` | One row per DICOM file, all extracted tags |
| `output/summary_report.txt` | Dataset-level audit report |

### 2. Single-File Explorer

Useful for inspecting an individual file before running the full pipeline.

```bash
# Auto-select first .dcm file from directory
python dicom_practice.py --data-dir /path/to/qin_breast_02

# Specify a file directly
python dicom_practice.py --file /path/to/file.dcm

# Also print all raw DICOM tags
python dicom_practice.py --file /path/to/file.dcm --all-tags

# Specify output path for the visualization
python dicom_practice.py --file /path/to/file.dcm --output ./slice.png
```

---

## Extracted Metadata Tags

### Patient and Study
| Tag | Description |
|---|---|
| PatientID | De-identified subject identifier |
| PatientSex | Biological sex |
| PatientAge | Age at time of scan |
| StudyDate | Date of imaging visit |
| SeriesDescription | Name of the acquisition sequence |

### Scanner and Acquisition
| Tag | Description |
|---|---|
| ManufacturerModelName | Scanner model (Philips Achieva) |
| MagneticFieldStrength | Field strength in Tesla (3T) |
| ReceiveCoilName | Coil used (SENSE_BREAST_16) |
| PulseSequenceName | Sequence type (T1FFE, gradient echo) |
| MRAcquisitionType | 2D or 3D acquisition |

### MRI Sequence Parameters
| Tag | Description |
|---|---|
| RepetitionTime (TR) | Time between successive RF pulses (ms) |
| EchoTime (TE) | Time between RF pulse and signal echo (ms) |
| FlipAngle | Excitation angle (degrees) |
| InversionTime (TI) | Delay after inversion pulse (ms) |
| ProtocolName | Full acquisition protocol name |

### DCE-Specific
| Tag | Description |
|---|---|
| TemporalPositionIdentifier | Which dynamic time point this slice belongs to |
| NumberOfTemporalPositions | Total number of contrast dynamics acquired |

In DCE-MRI, contrast agent uptake is tracked across multiple 3D volumes acquired over time. Each volume is one temporal position. This dataset contains 10 temporal positions per series, allowing measurement of contrast enhancement kinetics, a key biomarker in breast cancer diagnosis.

### Image Geometry
| Tag | Description |
|---|---|
| Rows and Columns | Image dimensions in pixels (192 x 192) |
| PixelSpacing | In-plane resolution in mm |
| SliceThickness | Slice thickness in mm |

---

## Pixel Statistics (Optional)

When `--pixel-stats` is enabled, the following are computed per file after applying the DICOM rescale transformation (`pixel * RescaleSlope + RescaleIntercept`):

| Statistic | Meaning |
|---|---|
| Mean intensity | Average signal level across the slice |
| Std deviation | Spread of intensity values, reflects image contrast |
| Min and Max | Raw intensity range |
| Dynamic range | Max minus Min, indicates total signal dynamic range |

These statistics are written per file in the CSV and aggregated across the full dataset in the summary report.

---

## Example Summary Report Output

```
=================================================================
  QIN-BREAST-02: DATASET METADATA SUMMARY
=================================================================
  Generated        : 2026-05-09 14:32:10
  Source dir       : /home/usama/dicom_learning/data/qin_breast_02
  Total files      : 31790
  Pixel stats      : No  (run with --pixel-stats to enable)

  PATIENTS
-----------------------------------------------------------------
  Total patients   : 13
  IDs              : QIN-BREAST-02-0001, QIN-BREAST-02-0002, ...

  FILES PER PATIENT
-----------------------------------------------------------------
  QIN-BREAST-02-0001                       2430 files
  QIN-BREAST-02-0002                       2444 files
  ...

  SCANNER / ACQUISITION
-----------------------------------------------------------------
  Scanner          : Achieva
  Field strength   : 3 T
  DCE dynamics     : 10 time points

  SERIES TYPES
-----------------------------------------------------------------
  - multi-flip_T1-map
  - dce_T1_1_THRIVE
  - ...

  DE-IDENTIFICATION
-----------------------------------------------------------------
  PHI removed      : YES
=================================================================
```

---

## Requirements

```
pydicom>=2.4.0
numpy>=1.24.0
matplotlib>=3.7.0
```

---

## Clinical Context

Breast DCE-MRI is widely used for cancer screening in high-risk populations, treatment response monitoring, and surgical planning. The QIN-BREAST-02 dataset was collected as part of the Quantitative Imaging Network (QIN) initiative, which focuses on developing and validating quantitative imaging biomarkers for oncology.

Understanding the acquisition parameters, particularly TR, TE, flip angle, and the number of temporal positions, is essential for interpreting the signal characteristics of the images and for designing preprocessing pipelines that are physically meaningful.

---

## Author

**Usama Khan**, PhD, Industrial and Information Engineering
Specialization: Medical image analysis, breast ultrasound radiomics, deep learning pipelines, PyTorch

---

## License

This project is released under the MIT License.
The QIN-BREAST-02 dataset is licensed under CC BY 4.0 by The Cancer Imaging Archive.
