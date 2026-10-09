from hashlib import sha256

CHUNK_VERSION = "characters-1200-overlap-160-v1"


def chunk_document(document_id: str, text: str, *, size=1200, overlap=160) -> list[dict]:
    if size < 1 or not 0 <= overlap < size:
        raise ValueError("invalid chunk configuration")
    chunks = []
    for start in range(0, len(text), size - overlap):
        end = min(start + size, len(text))
        part = text[start:end]
        digest = sha256(part.encode("utf-8")).hexdigest()
        identity = sha256(f"{document_id}:{CHUNK_VERSION}:{start}:{digest}".encode()).hexdigest()
        chunks.append(
            {"chunk_id": identity, "content_hash": digest, "text": part, "start": start, "end": end}
        )
        if end == len(text):
            break
    return chunks
