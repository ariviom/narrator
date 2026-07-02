import re
from dataclasses import dataclass
from num2words import num2words

# Front-matter markers. If the text opens with a metadata block that ends in a
# horizontal rule (a line of dashes) within the first several lines AND one of
# these markers appears near the top, the block is dropped and the first line is
# kept as the title. Plain chapter text (no such block) passes through untouched.
_HEADER_MARKERS = ("Published:", "Author:", "http")

def strip_metadata_header(raw: str) -> tuple[str, str]:
    lines = raw.splitlines()
    if not lines:
        return "", raw
    title = lines[0].strip()
    # find the separator rule line ("----...") that ends a front-matter block
    sep_idx = next((i for i, ln in enumerate(lines[:12]) if set(ln.strip()) == {"-"} and len(ln.strip()) >= 8), None)
    looks_like_header = any(m in raw[:400] for m in _HEADER_MARKERS)
    if sep_idx is not None and looks_like_header:
        body = "\n".join(lines[sep_idx + 1:])
        return title, body.lstrip("\n")
    return "", raw

def clean_text(s: str) -> str:
    s = (s.replace("“", '"').replace("”", '"')
           .replace("‘", "'").replace("’", "'")
           .replace("—", "--").replace("–", "-").replace("…", "..."))
    s = re.sub(r"[ \t]+", " ", s)
    s = re.sub(r"\n{3,}", "\n\n", s)
    return "\n".join(line.strip() for line in s.split("\n")).strip()

def _year_to_words(n: int) -> str:
    if 1000 <= n <= 2099 and n % 1000 != 0:
        return num2words(n, to="year")
    return num2words(n)

def expand_numbers(s: str) -> str:
    s = re.sub(r"\b(\d+)(st|nd|rd|th)\b",
               lambda m: num2words(int(m.group(1)), to="ordinal"), s)
    s = re.sub(r"\b\d{4}\b", lambda m: _year_to_words(int(m.group(0))), s)
    s = re.sub(r"\b\d+\b", lambda m: num2words(int(m.group(0))), s)
    return s

_ABBR = [(r"\bSt\.\s+", "Saint "), (r"\bNo\.\s*(?=\d)", "Number "),
         (r"\bMr\.\s+", "Mister "), (r"\bMrs\.\s+", "Missus "),
         (r"\bMs\.\s+", "Miss "), (r"\bDr\.\s+", "Doctor ")]

def expand_abbreviations(s: str) -> str:
    for pat, rep in _ABBR:
        s = re.sub(pat, rep, s)
    return s

@dataclass
class NormalizedStory:
    title: str
    paragraphs: list

def apply_pronunciation(s: str, pron) -> str:
    for pat, rep in pron.replacements:
        s = re.sub(pat, rep, s)
    for word, say in pron.respellings.items():
        s = re.sub(rf"\b{re.escape(word)}\b", say, s, flags=re.IGNORECASE)
    return s

_FN_DEF = re.compile(r"^\[(\d+)\]\s+(.+)$")

def _is_divider(line: str) -> bool:
    s = line.strip()
    return bool(s) and set(s) <= set("-—–*·_ ")

def restructure_footnotes(body: str) -> str:
    """Read footnotes inline for audio: replace each [N] reference in the prose
    with the spoken footnote 'Footnote N. <text> End footnote.' right where it
    occurs, then drop the trailing footnote-definition block and its divider rule.
    A footnote whose inline reference is missing is appended at the end as a
    fallback so no content is lost. The source text keeps its footnotes as
    footnotes; only the spoken version inlines them. No-op when there are no
    footnote definitions."""
    lines = body.split("\n")
    defs, first_def, j = {}, None, len(lines) - 1
    while j >= 0:
        s = lines[j].strip()
        if not s:
            j -= 1; continue
        m = _FN_DEF.match(s)
        if not m:
            break
        defs[m.group(1)] = m.group(2).strip()
        first_def = j
        j -= 1
    if first_def is None:
        return body
    story_lines = lines[:first_def]
    while story_lines and (not story_lines[-1].strip() or _is_divider(story_lines[-1])):
        story_lines.pop()
    story = "\n".join(story_lines)

    used = set()
    def _inline(m):
        n = m.group(1)
        if n not in defs:
            return ""
        used.add(n)
        return f" Footnote {n}. {defs[n]} End footnote."
    story = re.sub(r"\[(\d+)\]", _inline, story)
    story = re.sub(r"[ \t]{2,}", " ", story).strip()
    tail = [f"Footnote {n}. {defs[str(n)]} End footnote."
            for n in sorted(int(k) for k in defs if k not in used)]
    return "\n\n".join([story] + tail) if tail else story

def normalize_story(raw: str, pron, *, speak_subtitle: bool = False) -> NormalizedStory:
    title, body = strip_metadata_header(raw)
    body = clean_text(body)
    body = restructure_footnotes(body)
    body = expand_abbreviations(body)
    body = expand_numbers(body)
    body = apply_pronunciation(body, pron)
    paragraphs = [p.strip() for p in re.split(r"\n{2,}", body) if p.strip()]
    return NormalizedStory(title=title, paragraphs=paragraphs)
