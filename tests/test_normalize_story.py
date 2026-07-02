from narrator.config import Pronunciation
from narrator.normalize import (
    apply_pronunciation, normalize_story, restructure_footnotes,
)

PRON = Pronunciation(respellings={"Siobhan": "Shiv-awn"},
                     replacements=[(r"\bNo\.\s*(?=\d)", "Number ")])

EMPTY_PRON = Pronunciation(respellings={}, replacements=[])

def test_apply_pronunciation_replacements_then_respellings():
    out = apply_pronunciation("No. 23, Ms Siobhan", PRON)
    assert out == "Number 23, Ms Shiv-awn"

def test_apply_pronunciation_is_word_bounded_caseinsensitive():
    out = apply_pronunciation("SIOBHAN Siobhans", PRON)
    assert out == "Shiv-awn Siobhans"   # whole word only

def test_normalize_story_splits_paragraphs_and_expands():
    raw = ("Chapter Nine\n\n"
           "Author: A. Writer\nPublished: 2024\n\n"
           "------------------------------------------------------------\n"
           "On the 23rd, St. Mary's stirred.\n\nNo. 4 followed.\n")
    ns = normalize_story(raw, PRON)
    assert ns.title == "Chapter Nine"
    assert len(ns.paragraphs) == 2
    assert "twenty-third" in ns.paragraphs[0]
    assert ns.paragraphs[0].startswith("On the twenty-third, Saint Mary")
    assert ns.paragraphs[1].startswith("Number four")

def test_normalize_story_without_frontmatter_keeps_all_text():
    # Plain chapter text (no metadata block) passes through untouched.
    raw = "A short tale.\n\nIt simply ends with narration."
    ns = normalize_story(raw, EMPTY_PRON)
    assert ns.title == ""
    assert ns.paragraphs == ["A short tale.", "It simply ends with narration."]

def test_restructure_footnotes_inline_at_reference():
    body = ("The boy ran[1] down the street.\n\n"
            "He paused[2] at the door.\n\n"
            "------------------------------\n\n"
            "[1] He was fast.\n\n"
            "[2] Then he stopped.")
    out = restructure_footnotes(body)
    assert "[1]" not in out and "[2]" not in out          # inline refs gone
    assert "----" not in out                               # divider gone
    # each footnote is read at its reference point, then the sentence resumes
    assert "The boy ran Footnote 1. He was fast. End footnote. down the street." in out
    assert "He paused Footnote 2. Then he stopped. End footnote. at the door." in out

def test_restructure_footnotes_noop_without_footnotes():
    body = "Just a plain story.\n\nIt simply ends."
    assert restructure_footnotes(body) == body

def test_normalize_story_reads_footnotes_inline():
    raw = ("The Boy\n\n"
           "Author: A. Writer\nPublished: 2024\n\n"
           "------------------------------------------------------------\n"
           "He had 3 reasons[1] for it.\n\n"
           "——————————————\n\n"
           "[1] One might even say meagre.")
    ns = normalize_story(raw, EMPTY_PRON)
    joined = " ".join(ns.paragraphs)
    assert "[1]" not in joined
    # the footnote is read where it is referenced, numbers expanded to words
    assert ("He had three reasons Footnote one. One might even say meagre. "
            "End footnote. for it.") in joined

def test_normalize_story_abbr_then_number_order():
    # Documents the (correct) call order: expand_abbreviations runs before
    # expand_numbers, so "No. 3rd" -> "Number 3rd" -> "Number third".
    raw = ("Chapter One\n\n"
           "Author: A. Writer\n\n"
           "------------------------------------------------------------\n"
           "No. 3rd of the lot.")
    ns = normalize_story(raw, EMPTY_PRON)
    assert "Number third" in ns.paragraphs[0]
