import re
from src.prototype.wave_graph_grammar_core import (
    Lexicon, Morphology, Grammar, SentenceGenerator
)

def test_lexicon_add():
    lex = Lexicon()
    assert "scientist" not in lex.words_for_pos("NOUN")
    lex.add("scientist", "NOUN", 0.3)
    assert "scientist" in lex.words_for_pos("NOUN")

def test_morphology():
    assert Morphology.pluralize("cat") == "cats"
    assert Morphology.pluralize("box") == "boxes"
    assert Morphology.third_person_singular("chase") == "chases"
    assert Morphology.past_tense("like") == "liked"

def test_grammar_core_rules_exist():
    g = Grammar()
    for nt in ["S", "CLAUSE", "NP", "VP", "Q", "IMP"]:
        assert g.has(nt)

def test_generation_outputs_sentence_and_valence():
    lex = Lexicon()
    lex.add("scientist", "NOUN", 0.6)
    lex.add("discover", "VERB", 0.7)
    lex.add("beautiful", "ADJ", 0.8)
    g = Grammar()
    gen = SentenceGenerator(g, lex, seed=42)
    sent, tree, field = gen.generate()
    assert isinstance(sent, str) and len(sent) > 0
    assert sent[0].isupper()
    assert sent.endswith(('.', '?', '!'))
    assert -1.0 <= field.valence <= 1.0
    pretty = tree.pretty()
    assert "S" in pretty or "CLAUSE" in pretty