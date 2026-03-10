import cv2
import os
import pytesseract
import numpy as np
import shutil
from typing import Optional, List

try:
    import easyocr
except ImportError:
    easyocr = None


_easyocr_reader: Optional["easyocr.Reader"] = None


def _ensure_tesseract_available():
    if shutil.which("tesseract"):
        return

    common_windows_paths = [
        r"C:\Program Files\Tesseract-OCR\tesseract.exe",
        r"C:\Program Files (x86)\Tesseract-OCR\tesseract.exe",
    ]

    for path in common_windows_paths:
        if os.path.exists(path):
            pytesseract.pytesseract.tesseract_cmd = path
            return

    raise RuntimeError(
        "Tesseract OCR is not installed or not found in PATH. "
        "Windows default install path: C:\\Program Files\\Tesseract-OCR\\tesseract.exe"
    )


def _get_easyocr_reader():
    if easyocr is None:
        raise RuntimeError("EasyOCR is not installed.")

    global _easyocr_reader
    if _easyocr_reader is None:
        _easyocr_reader = easyocr.Reader(["en"], gpu=False)
    return _easyocr_reader


def _to_rgb(image):
    if len(image.shape) == 2:
        return cv2.cvtColor(image, cv2.COLOR_GRAY2RGB)
    return cv2.cvtColor(image, cv2.COLOR_BGR2RGB)


def _dedupe_preserve_order(lines: List[str]) -> List[str]:
    seen = set()
    out = []
    for line in lines:
        key = " ".join(line.split()).strip()
        if not key:
            continue
        if key not in seen:
            seen.add(key)
            out.append(key)
    return out

def preprocess_image(image):
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Noise removal
    blur = cv2.GaussianBlur(gray, (5,5), 0)
    
    # Adaptive threshold
    thresh = cv2.adaptiveThreshold(
        blur,
        255,
        cv2.ADAPTIVE_THRESH_MEAN_C,
        cv2.THRESH_BINARY,
        11,
        2
    )
    
    return thresh


def extract_text(image, processed_image=None):
    variants = [image]
    if processed_image is not None:
        variants.append(processed_image)
    else:
        variants.append(preprocess_image(image))

    # Preferred path: pytesseract if local Tesseract exists.
    try:
        _ensure_tesseract_available()
        outputs = []
        for variant in variants:
            for psm in (6, 11):
                config = f"--oem 3 --psm {psm}"
                text = pytesseract.image_to_string(variant, config=config)
                outputs.extend(text.splitlines())
        return "\n".join(_dedupe_preserve_order(outputs))
    except Exception:
        pass

    # Fallback path: EasyOCR (no separate Tesseract install needed).
    try:
        reader = _get_easyocr_reader()
        outputs = []
        for variant in variants:
            image_rgb = _to_rgb(variant)
            chunks = reader.readtext(image_rgb, detail=0, paragraph=False)
            outputs.extend(chunks)
        return "\n".join(_dedupe_preserve_order(outputs))
    except Exception as exc:
        raise RuntimeError(
            "OCR engine unavailable. Install either:\n"
            "1) Tesseract OCR system package, or\n"
            "2) Python package easyocr."
        ) from exc
