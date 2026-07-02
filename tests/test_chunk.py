from narrator.chunk import split_sentences, chunk_paragraphs

def test_split_sentences_basic_and_protected():
    s = "He left. She, e.g., stayed! Did he? Yes."
    assert split_sentences(s) == ["He left.", "She, e.g., stayed!", "Did he?", "Yes."]

def test_chunk_packs_to_budget_without_splitting_sentences():
    paras = ["Aaa aaa. Bbb bbb. Ccc ccc."]   # ~10 chars each sentence
    chunks = chunk_paragraphs(paras, max_chars=20)
    assert all(len(c.text) <= 22 for c in chunks)
    assert "".join(c.text.replace(" ", "") for c in chunks).count("Aaaaaa") == 1
    assert chunks[0].is_paragraph_start is True

def test_paragraph_boundaries_marked():
    chunks = chunk_paragraphs(["One. Two.", "Three."], max_chars=100)
    starts = [c.paragraph_index for c in chunks if c.is_paragraph_start]
    assert starts == [0, 1]

def test_overlong_sentence_falls_back_to_clause_split():
    long = "alpha, beta, gamma, delta, epsilon, zeta, eta, theta."
    chunks = chunk_paragraphs([long], max_chars=20)
    assert all(len(c.text) <= 25 for c in chunks)

def test_punctuationless_overlong_clause_is_hard_split():
    # A single clause with no internal punctuation that exceeds max_chars must
    # not be emitted whole; the word-level hard split caps every piece.
    para = ("alpha " * 60).strip() + "."
    chunks = chunk_paragraphs([para], max_chars=40)
    assert chunks, "expected at least one chunk"
    assert all(len(c.text) <= 40 for c in chunks)
    # No text is lost: every 'alpha' token survives.
    assert sum(c.text.count("alpha") for c in chunks) == 60
