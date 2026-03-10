import streamlit as st
import cv2
import numpy as np
import html
from PIL import Image

from ocr_utils import preprocess_image, extract_text
from extractor import extract_pan_number, extract_dob, extract_names

st.set_page_config(page_title="PAN Card Extractor", page_icon="ID", layout="wide")

CUSTOM_CSS = """
    @import url('https://fonts.googleapis.com/css2?family=Space+Grotesk:wght@400;500;700&family=Source+Sans+3:wght@400;600&display=swap');

    :root {
        --bg-a: #0c2d48;
        --bg-b: #145da0;
        --card: #f4f9ff;
        --ink: #0d1b2a;
        --accent: #ff9f1c;
        --mint: #2ec4b6;
        --danger: #d62828;
    }

    .stApp {
        background:
            radial-gradient(circle at 20% 10%, #2ec4b633 0%, transparent 35%),
            radial-gradient(circle at 80% 0%, #ff9f1c2b 0%, transparent 30%),
            linear-gradient(135deg, var(--bg-a), var(--bg-b));
        color: #f9fbff;
        font-family: "Source Sans 3", sans-serif;
    }

    .main-title {
        font-family: "Space Grotesk", sans-serif;
        font-size: 2.1rem;
        font-weight: 700;
        margin: 0;
    }

    .hero {
        border: 1px solid #ffffff33;
        background: linear-gradient(135deg, #ffffff1c, #ffffff0d);
        border-radius: 18px;
        padding: 1.1rem 1.2rem;
        margin: 0.3rem 0 1rem 0;
        backdrop-filter: blur(6px);
    }

    .hero p {
        margin: 0.3rem 0 0 0;
        opacity: 0.95;
        font-size: 1rem;
    }

    .section-head {
        font-family: "Space Grotesk", sans-serif;
        font-size: 1.25rem;
        font-weight: 700;
        margin: 0.8rem 0 0.3rem 0;
        color: #fff7e6;
    }

    .field-card {
        background: var(--card);
        color: var(--ink);
        border-radius: 14px;
        padding: 0.9rem 1rem;
        border-left: 7px solid var(--mint);
        box-shadow: 0 10px 20px #00000025;
        transition: transform .2s ease, box-shadow .2s ease;
        margin-bottom: 0.7rem;
    }

    .field-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 14px 24px #00000030;
    }

    .field-label {
        font-size: 0.82rem;
        opacity: .75;
        letter-spacing: .03em;
        text-transform: uppercase;
        margin-bottom: 0.2rem;
    }

    .field-value {
        font-family: "Space Grotesk", sans-serif;
        font-size: 1.3rem;
        font-weight: 700;
        margin: 0;
        word-break: break-word;
    }

    .text-box {
        background: #061522cc;
        border: 1px solid #ffffff22;
        color: #f8fcff;
        border-radius: 12px;
        padding: 0.8rem 0.9rem;
        max-height: 240px;
        overflow-y: auto;
        white-space: pre-wrap;
        box-shadow: inset 0 0 0 1px #ffffff10;
    }

    .footer {
        margin-top: 1.2rem;
        margin-bottom: 0.4rem;
        text-align: center;
        color: #ffffffd9;
        font-size: 0.9rem;
        border-top: 1px solid #ffffff2e;
        padding-top: 0.7rem;
    }

    .scroll-top {
        position: fixed;
        right: 18px;
        bottom: 18px;
        z-index: 99999;
        text-decoration: none;
        background: linear-gradient(135deg, #ff9f1c, #ffbf69);
        color: #072b3a;
        border-radius: 999px;
        border: 2px solid #ffffff99;
        padding: 0.45rem 0.8rem;
        font-weight: 700;
        box-shadow: 0 10px 20px #0000003b;
        transition: transform .2s ease, box-shadow .2s ease;
    }

    .scroll-top:hover {
        transform: translateY(-2px) scale(1.03);
        box-shadow: 0 14px 26px #0000004a;
    }

    [data-testid="stFileUploader"] {
        background: #ffffff14;
        border-radius: 14px;
        border: 1px solid #ffffff3a;
        padding: 0.5rem 0.7rem;
    }
"""

st.markdown('<div id="top-anchor"></div>', unsafe_allow_html=True)
st.markdown(f"<style>{CUSTOM_CSS}</style>", unsafe_allow_html=True)

st.markdown(
    """
    <div class="hero">
      <h1 class="main-title">PAN Card Smart Extractor</h1>
      <p>Upload a PAN image and extract PAN number, name, father name and date of birth.</p>
    </div>
    """,
    unsafe_allow_html=True,
)

uploaded_file = st.file_uploader("Upload PAN Card Image", type=["jpg", "png", "jpeg"])

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    image_np = np.array(image)
    image_np = cv2.cvtColor(image_np, cv2.COLOR_RGB2BGR)
    processed = preprocess_image(image_np)

    st.markdown('<div class="section-head">Image Preview</div>', unsafe_allow_html=True)
    col1, col2 = st.columns(2, gap="large")
    with col1:
        st.image(image, caption="Original Image", width="stretch")
    with col2:
        st.image(processed, caption="Processed Image", width="stretch")

    try:
        text = extract_text(image_np, processed)
    except RuntimeError as err:
        st.error(str(err))
        st.info(
            "Install option 1 (system): https://github.com/tesseract-ocr/tesseract\n"
            "Install option 2 (python): pip install easyocr"
        )
        st.stop()

    st.markdown('<div class="section-head">Extracted Text</div>', unsafe_allow_html=True)
    st.markdown(f"<div class='text-box'>{html.escape(text)}</div>", unsafe_allow_html=True)

    pan_number = extract_pan_number(text)
    dob = extract_dob(text)
    name, father_name = extract_names(text)
    pan_display = html.escape(pan_number) if pan_number else "Not Found"
    name_display = html.escape(name) if name else "Not Found"
    father_display = html.escape(father_name) if father_name else "Not Found"
    dob_display = html.escape(dob) if dob else "Not Found"

    st.markdown('<div class="section-head">Extracted Fields</div>', unsafe_allow_html=True)
    f1, f2 = st.columns(2, gap="large")
    with f1:
        st.markdown(
            f"""
            <div class="field-card">
              <div class="field-label">PAN Number</div>
              <p class="field-value">{pan_display}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="field-card">
              <div class="field-label">Card Holder Name</div>
              <p class="field-value">{name_display}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
    with f2:
        st.markdown(
            f"""
            <div class="field-card">
              <div class="field-label">Father Name</div>
              <p class="field-value">{father_display}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )
        st.markdown(
            f"""
            <div class="field-card">
              <div class="field-label">Date of Birth</div>
              <p class="field-value">{dob_display}</p>
            </div>
            """,
            unsafe_allow_html=True,
        )

st.markdown('<a href="#top-anchor" class="scroll-top">Top ^</a>', unsafe_allow_html=True)

st.markdown(
    """
    <div class="footer">
      Built for fast PAN verification | OCR + Smart Parsing
    </div>
    """,
    unsafe_allow_html=True,
)
