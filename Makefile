.PHONY: demo test lint

demo:
	python src/prototype/wave_graph_grammar_core.py --demo --n 3

test:
	pytest -q