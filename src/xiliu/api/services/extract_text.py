from __future__ import annotations

from io import BytesIO
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

MAX_TEXT_CHARS = 200_000
MAX_EXPANDED_BYTES = 40 * 1024 * 1024
TEXT_EXTENSIONS = {
    ".txt",
    ".md",
    ".markdown",
    ".csv",
    ".tsv",
    ".json",
    ".jsonl",
    ".yaml",
    ".yml",
    ".xml",
    ".html",
    ".log",
    ".py",
    ".js",
    ".ts",
    ".css",
    ".rst",
}


def extract_text(filename: str, data: bytes) -> tuple[str, str | None]:
    suffix = Path(filename).suffix.casefold()
    try:
        if suffix in TEXT_EXTENSIONS:
            for encoding in (
                "utf-8-sig",
                "utf-16" if data.startswith((b"\xff\xfe", b"\xfe\xff")) else "utf-8",
                "gb18030",
            ):
                try:
                    text = data.decode(encoding)
                    if "\x00" in text or sum(ord(c) < 32 and c not in "\n\r\t" for c in text) > max(
                        2, len(text) // 100
                    ):
                        continue
                    return text[:MAX_TEXT_CHARS], None
                except UnicodeError:
                    continue
            return "", "无法识别文字编码，已保留原件。"
        if suffix == ".pdf":
            from pypdf import PdfReader

            reader = PdfReader(BytesIO(data), strict=False)
            pieces = []
            size = 0
            for page in reader.pages[:200]:
                part = page.extract_text() or ""
                pieces.append(part[: MAX_TEXT_CHARS - size])
                size += len(pieces[-1])
                if size >= MAX_TEXT_CHARS:
                    break
            text = "\n".join(pieces)[:MAX_TEXT_CHARS]
            return text, None if text.strip() else "PDF 没有可提取文字，已保留原件；不支持 OCR。"
        if suffix == ".docx":
            with ZipFile(BytesIO(data)) as archive:
                if sum(item.file_size for item in archive.infolist()) > MAX_EXPANDED_BYTES:
                    return "", "DOCX 解压后过大，已保留原件。"
                source = archive.read("word/document.xml")
                if b"<!DOCTYPE" in source or b"<!ENTITY" in source:
                    return "", "DOCX 文档格式不受支持，已保留原件。"
                root = ElementTree.fromstring(source)
                text = "\n".join(
                    "".join(node.itertext())
                    for node in root.iter(
                        "{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p"
                    )
                )
                return text[:MAX_TEXT_CHARS], None
    except (ValueError, KeyError, BadZipFile, ElementTree.ParseError, ImportError, OSError):
        return "", "正文提取失败，已保留原件。"
    except Exception:
        return "", "正文提取失败，已保留原件。"
    return "", "此文件格式仅保留原件，尚未提取正文。"
