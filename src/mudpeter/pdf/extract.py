from pathlib import Path
import requests
import fitz


class PdfExtractError(Exception):
    pass


def download_pdf(url: str, *, timeout: int = 20) -> bytes: # btw the timeout is in seconds
    """ 
    `download_pdf` downloads a pdf using a url.
    It returns bytes to be processed by `extract_text_from_pdf_bytes` - via wrapper `extract_text_from_pdf_url` - below.
    """
    if not url:
        raise ValueError("url must be provided")
    r = requests.get(url, timeout=timeout)
    if not r.ok:
        raise PdfExtractError(f"Failed to download PDF ({r.status_code}): {r.text[:200]}")
    return r.content


def extract_text_from_pdf_bytes(data: bytes, *, max_chars: int | None = None) -> str:
    """ 
    `extract_text_from_pdf_bytes` accepts bytes (passed from `download_pdf` above or a path, see below)
    and attempts to extract text via pymupdf (fitz).
    It returns a string.
    If max_chars is set (it can be None, i.e. unset) then only the characters up to max_chars are returned.
    """
    if not data:
        raise ValueError("data must be non-empty PDF bytes")
    try:
        doc = fitz.open(stream=data, filetype="pdf")
    except Exception as e:
        raise PdfExtractError(f"Could not open PDF bytes: {e}") from e

    chunks: list[str] = [] # chunks here are a convenience container that are joined below
    try:
        for page in doc:
            txt = page.get_text("text") or ""
            if txt.strip():
                chunks.append(txt)
            if max_chars is not None and sum(len(c) for c in chunks) >= max_chars:
                break
    finally:
        doc.close()

    text = "\n\n".join(chunks).strip()
    if max_chars is not None:
        text = text[:max_chars]
    return text


def extract_text_from_pdf_path(path: str | Path, *, max_chars: int | None = None) -> str:
    """ 
    Instead of downloading the pdf, it can be presented as a file.
    The bytes are then forwarded to `extract_text_from_pdf_bytes` above.
    """
    p = Path(path)
    if not p.exists():
        raise FileNotFoundError(str(p))
    return extract_text_from_pdf_bytes(p.read_bytes(), max_chars=max_chars)


def extract_text_from_pdf_url(url: str, *, timeout: int = 20, max_chars: int | None = None) -> str:
    """ 
    This is a wrapper for `download_pdf` above.
    """
    return extract_text_from_pdf_bytes(download_pdf(url, timeout=timeout), max_chars=max_chars)


# TODO: Lets also include a call to docling-serve as an alternative way to extract full text, yes?