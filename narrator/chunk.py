import re
from dataclasses import dataclass

@dataclass
class Chunk:
    text: str
    index: int
    paragraph_index: int
    is_paragraph_start: bool

_PROTECT = {"e.g.": "e<dot>g<dot>", "i.e.": "i<dot>e<dot>", "etc.": "etc<dot>"}

def split_sentences(paragraph: str) -> list:
    s = paragraph
    for k, v in _PROTECT.items():
        s = s.replace(k, v)
    s = re.sub(r"\b([A-Z])\.", r"\1<dot>", s)            # initials
    parts = re.findall(r".+?(?:[.!?]+(?=\s|$)|$)", s)
    out = []
    for p in parts:
        p = p.strip()
        if not p:
            continue
        for k, v in _PROTECT.items():
            p = p.replace(v, k)
        p = p.replace("<dot>", ".")
        out.append(p)
    return out

def _hard_split(piece: str, max_chars: int) -> list:
    # Final fallback: split an over-long clause on word boundaries so no emitted
    # piece exceeds max_chars; a single over-long token is sliced mid-word.
    if len(piece) <= max_chars:
        return [piece]
    out, buf = [], ""
    for word in piece.split():
        if len(word) > max_chars:                 # over-long single token
            if buf:
                out.append(buf); buf = ""
            for i in range(0, len(word), max_chars):
                out.append(word[i:i + max_chars])
            continue
        cand = (buf + " " + word).strip() if buf else word
        if len(cand) <= max_chars:
            buf = cand
        else:
            if buf:
                out.append(buf)
            buf = word
    if buf:
        out.append(buf)
    return out

def _clause_split(sentence: str, max_chars: int) -> list:
    pieces = re.split(r"(?<=[;,])\s+|\s+--\s+", sentence)
    out, buf = [], ""
    for piece in pieces:
        cand = (buf + " " + piece).strip() if buf else piece
        if len(cand) <= max_chars:
            buf = cand
        else:
            if buf:
                out.append(buf)
            buf = piece
    if buf:
        out.append(buf)
    # Guarantee no emitted piece exceeds max_chars (clause with no internal
    # punctuation can still overflow), splitting on word boundaries.
    final = []
    for p in out:
        final.extend(_hard_split(p, max_chars))
    return final

def chunk_paragraphs(paragraphs: list, max_chars: int = 250) -> list:
    chunks, idx = [], 0
    for p_i, para in enumerate(paragraphs):
        sentences = split_sentences(para)
        buf, first = "", True
        def flush(buf, first):
            nonlocal idx
            if not buf:
                return first
            chunks.append(Chunk(buf, idx, p_i, first))
            idx += 1
            return False
        for sent in sentences:
            if len(sent) > max_chars:
                first = flush(buf, first); buf = ""
                for piece in _clause_split(sent, max_chars):
                    first = flush(piece, first)
                continue
            cand = (buf + " " + sent).strip() if buf else sent
            if len(cand) <= max_chars:
                buf = cand
            else:
                first = flush(buf, first); buf = sent
        flush(buf, first)
    return chunks
