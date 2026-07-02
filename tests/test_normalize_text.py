from narrator.normalize import (strip_metadata_header, clean_text, expand_numbers, expand_abbreviations)

def test_strip_header_returns_title_and_body():
    raw = ("Chapter One\n"
           "A quiet beginning\n\n"
           "Author: A. Writer\n"
           "Published: 2024\n"
           "https://example.com/x\n\n"
           "------------------------------------------------------------\n"
           "First body line.\n\nSecond paragraph.\n")
    title, body = strip_metadata_header(raw)
    assert title == "Chapter One"
    assert body.strip().startswith("First body line.")
    assert "Published:" not in body and "http" not in body

def test_strip_header_noop_without_frontmatter():
    raw = "Chapter One\n\nThe story starts right here.\n"
    title, body = strip_metadata_header(raw)
    assert title == "" and body == raw

def test_clean_text_normalizes_punctuation():
    assert clean_text("“Hi”—there…") == '"Hi"--there...'
    assert clean_text("a   b\n\n\n c") == "a b\n\nc"  # collapse spaces, cap blank lines

def test_expand_numbers_ordinal_year_cardinal():
    assert expand_numbers("the 23rd of June") == "the twenty-third of June"
    assert expand_numbers("in 1880 and 1883") == "in eighteen eighty and eighteen eighty-three"
    assert expand_numbers("page 7") == "page seven"

def test_expand_abbreviations_saint_and_number():
    assert expand_abbreviations("St. Mary's") == "Saint Mary's"
    assert expand_abbreviations("No. 23") == "Number 23"
    assert expand_abbreviations("Mr. Smith and Mrs. Jones") == "Mister Smith and Missus Jones"
