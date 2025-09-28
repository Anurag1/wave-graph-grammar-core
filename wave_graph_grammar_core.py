"""
Wave-Graph Grammar-Core — minimal runnable prototype

This single-file starter gives you:
  • A tiny CFG-like grammar with expansion
  • A morphology module (very small, demonstrative)
  • A lexicon with POS + polarity (emotion valence)
  • A sentence generator that emits (text, grammar_tree, emotion_score)
  • A CLI demo and simple unit-style checks

Drop this file into: src/prototype/wave_graph_grammar_core.py
Then run:  python src/prototype/wave_graph_grammar_core.py --demo

No external dependencies.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Union
import random
import math

# ------------------------------
# Lexicon: word → (POS, polarity)
# polarity ∈ [-1.0, 1.0] (negative to positive)
# ------------------------------

@dataclass(frozen=True)
class LexEntry:
    pos: str
    polarity: float = 0.0


class Lexicon:
    def __init__(self) -> None:
        # Minimal seed lexicon; extend at runtime (Phase 2 style)
        self.entries: Dict[str, LexEntry] = {
            # determiners
            "the": LexEntry("DET", 0.0),
            "a": LexEntry("DET", 0.0),
            "an": LexEntry("DET", 0.0),

            # nouns
            "cat": LexEntry("NOUN", 0.2),
            "dog": LexEntry("NOUN", 0.3),
            "child": LexEntry("NOUN", 0.4),
            "war": LexEntry("NOUN", -0.9),
            "love": LexEntry("NOUN", 0.9),

            # verbs (base)
            "see": LexEntry("VERB", 0.0),
            "like": LexEntry("VERB", 0.6),
            "chase": LexEntry("VERB", -0.1),
            "hate": LexEntry("VERB", -0.7),
            "adore": LexEntry("VERB", 0.8),

            # adjectives
            "happy": LexEntry("ADJ", 0.8),
            "sad": LexEntry("ADJ", -0.6),
            "brave": LexEntry("ADJ", 0.5),
            "angry": LexEntry("ADJ", -0.5),
        }

    def add(self, word: str, pos: str, polarity: float = 0.0) -> None:
        self.entries[word.lower()] = LexEntry(pos.upper(), float(polarity))

    def get(self, word: str) -> Optional[LexEntry]:
        return self.entries.get(word.lower())

    def words_for_pos(self, pos: str) -> List[str]:
        p = pos.upper()
        return [w for w, e in self.entries.items() if e.pos == p]


# ------------------------------
# Morphology — tiny demonstrator
# ------------------------------

class Morphology:
    VOWELS = set("aeiou")

    @staticmethod
    def pluralize(noun: str) -> str:
        # very rough English pluralization
        if noun.endswith("y") and len(noun) > 1 and noun[-2] not in Morphology.VOWELS:
            return noun[:-1] + "ies"
        if noun.endswith(("s", "x", "z", "ch", "sh")):
            return noun + "es"
        return noun + "s"

    @staticmethod
    def third_person_singular(verb_base: str) -> str:
        if verb_base.endswith("y") and len(verb_base) > 1 and verb_base[-2] not in Morphology.VOWELS:
            return verb_base[:-1] + "ies"
        if verb_base.endswith(("s", "x", "z", "ch", "sh")):
            return verb_base + "es"
        return verb_base + "s"

    @staticmethod
    def past_tense(verb_base: str) -> str:
        if verb_base.endswith("e"):
            return verb_base + "d"
        if verb_base.endswith("y") and len(verb_base) > 1 and verb_base[-2] not in Morphology.VOWELS:
            return verb_base[:-1] + "ied"
        return verb_base + "ed"


# ------------------------------
# CFG-like Grammar
# Nonterminals in UPPERCASE; terminals are quoted strings or POS slots
# Rules: LHS → list of alternatives; each alternative is a list of symbols
# POS slots are like <NOUN>, <VERB>, etc. and draw from the lexicon
# ------------------------------

Symbol = Union[str, Tuple[str, dict]]  # e.g., "NP" or ("<NOUN>", {"num":"PL"})

@dataclass
class Rule:
    lhs: str
    rhs: List[List[Symbol]]


class Grammar:
    def __init__(self) -> None:
        self.rules: Dict[str, Rule] = {}
        self.start: str = "S"
        self._seed_rules()

    def _seed_rules(self) -> None:
        self.add_rule("S", [["CLAUSE"], ["Q"], ["IMP"]])

        # Declaratives / simple clause
        self.add_rule("CLAUSE", [["NP", "VP"], ["NP", "VP", "PP"]])
        self.add_rule("NP", [["DET", "N"], ["DET", "ADJ", "N"], ["N"]])
        self.add_rule("VP", [["V", "NP"], ["V"], ["V", "ADJ"]])
        self.add_rule("PP", [["P", "NP"]])

        # Questions
        self.add_rule("Q", [["AUX", "NP", "V", "NP", "?"], ["WH", "V", "NP", "?"]])

        # Imperatives
        self.add_rule("IMP", [["V", "NP"], ["V"]])

        # Preterminals → POS slots
        self.add_rule("DET", [[("<DET>", {})]])
        self.add_rule("N", [[("<NOUN>", {})]])
        self.add_rule("V", [[("<VERB>", {})]])
        self.add_rule("ADJ", [[("<ADJ>", {})]])
        self.add_rule("P", [[("<P>", {})]])
        self.add_rule("AUX", [[("<AUX>", {})]])
        self.add_rule("WH", [[("<WH>", {})]])
        self.add_rule("?", [["?"]])

    def add_rule(self, lhs: str, rhs: List[List[Symbol]]) -> None:
        self.rules[lhs] = Rule(lhs, rhs)

    def has(self, nonterminal: str) -> bool:
        return nonterminal in self.rules


# ------------------------------
# Emotion / Behavior field
# For a sentence, aggregate word-level polarity with simple compositionality
# ------------------------------

@dataclass
class EmotionField:
    valence: float  # [-1, 1]

    def combine(self, other: "EmotionField") -> "EmotionField":
        # Smooth averaging with diminishing returns
        v = math.tanh(self.valence + other.valence)
        return EmotionField(v)

    @staticmethod
    def from_word(word: str, lex: Lexicon) -> "EmotionField":
        e = lex.get(word)
        return EmotionField(e.polarity if e else 0.0)


# ------------------------------
# Generator
# ------------------------------

@dataclass
class DerivationNode:
    symbol: str
    children: List["DerivationNode"]
    token: Optional[str] = None  # for terminals/POS resolutions

    def pretty(self, indent: int = 0) -> str:
        pad = "  " * indent
        if self.token is not None:
            return f"{pad}{self.symbol} → '{self.token}'\n"
        out = f"{pad}{self.symbol}\n"
        for ch in self.children:
            out += ch.pretty(indent + 1)
        return out


class SentenceGenerator:
    def __init__(self, grammar: Grammar, lexicon: Lexicon, seed: Optional[int] = None) -> None:
        self.g = grammar
        self.lex = lexicon
        if seed is not None:
            random.seed(seed)

        # expand functional slots like <P>, <AUX>, <WH>
        self.functional_words = {
            "<P>": ["with", "without", "near", "against"],
            "<AUX>": ["does", "did", "will"],
            "<WH>": ["why", "how", "what", "who"],
        }

    def generate(self) -> Tuple[str, DerivationNode, EmotionField]:
        tree, tokens = self._expand(self.g.start)
        tokens = self._postprocess(tokens)
        field = EmotionField(0.0)
        for t in tokens:
            field = field.combine(EmotionField.from_word(t.lower(), self.lex))
        sent = self._linearize(tokens)
        return sent, tree, field

    def _expand(self, symbol: str) -> Tuple[DerivationNode, List[str]]:
        if not self.g.has(symbol):  # terminal literal
            return DerivationNode(symbol, [], token=symbol), [symbol]

        rule = self.g.rules[symbol]
        choice = random.choice(rule.rhs)
        children: List[DerivationNode] = []
        tokens: List[str] = []

        for sym in choice:
            if isinstance(sym, tuple):  # POS slot like ("<NOUN>", {...})
                word = self._choose_for_pos(sym[0])
                node = DerivationNode(sym[0], [], token=word)
                children.append(node)
                tokens.append(word)
            elif isinstance(sym, str):
                node, toks = self._expand(sym)
                children.append(node)
                tokens.extend(toks)
            else:
                raise ValueError("Unknown symbol type")
        return DerivationNode(symbol, children), tokens

    def _choose_for_pos(self, slot: str) -> str:
        if slot in self.functional_words:
            return random.choice(self.functional_words[slot])
        if slot == "<DET>":
            return random.choice(["the", "a", "an"])
        if slot == "<NOUN>":
            return random.choice(self.lex.words_for_pos("NOUN") or ["cat"])
        if slot == "<VERB>":
            return random.choice(self.lex.words_for_pos("VERB") or ["see"])
        if slot == "<ADJ>":
            return random.choice(self.lex.words_for_pos("ADJ") or ["happy"])
        return ""  # fallback

    def _postprocess(self, tokens: List[str]) -> List[str]:
        out: List[str] = []
        i = 0
        while i < len(tokens):
            tok = tokens[i]
            # fix 'a/an'
            if tok.lower() == "a" and i + 1 < len(tokens):
                nxt = tokens[i + 1].lower()
                if nxt and nxt[0] in "aeiou":
                    tok = "an"
            # leave AUX handling simple for now
            out.append(tok)
            i += 1
        return out

    @staticmethod
    def _linearize(tokens: List[str]) -> str:
        if not tokens:
            return ""
        s = " ".join(tokens)
        s = s.replace(" ?", "?").replace(" ,", ",")
        s = s[0].upper() + s[1:]
        if not s.endswith(('.', '?', '!')):
            s += "."
        return s


# ------------------------------
# Simple tests / demo
# ------------------------------

def _demo(seed: int = 7, n: int = 5) -> None:
    lex = Lexicon()
    # Example of Phase 2: add new vocab at runtime (no retrain)
    lex.add("scientist", "NOUN", 0.6)
    lex.add("discover", "VERB", 0.7)
    lex.add("beautiful", "ADJ", 0.8)

    g = Grammar()
    gen = SentenceGenerator(g, lex, seed=seed)

    for i in range(n):
        sent, tree, field = gen.generate()
        print(f"[{i+1}] {sent}  \t(valence={field.valence:.2f})")
        print(tree.pretty())


def _mini_checks() -> None:
    # Ensure lexicon expansion is instant
    lex = Lexicon()
    assert "scientist" not in lex.words_for_pos("NOUN")
    lex.add("scientist", "NOUN", 0.3)
    assert "scientist" in lex.words_for_pos("NOUN")

    # Morphology sanity
    assert Morphology.pluralize("cat") == "cats"
    assert Morphology.pluralize("box") == "boxes"
    assert Morphology.third_person_singular("chase") == "chases"
    assert Morphology.past_tense("like") == "liked"

    # Grammar has core categories
    g = Grammar()
    for nt in ["S", "CLAUSE", "NP", "VP", "Q", "IMP"]:
        assert g.has(nt)

    print("Mini checks passed.")


if __name__ == "__main__":
    import argparse
    p = argparse.ArgumentParser(description="Wave-Graph Grammar-Core prototype")
    p.add_argument("--demo", action="store_true", help="run demo sentences")
    p.add_argument("--seed", type=int, default=7)
    p.add_argument("--n", type=int, default=5)
    args = p.parse_args()

    _mini_checks()
    if args.demo:
        _demo(seed=args.seed, n=args.n)