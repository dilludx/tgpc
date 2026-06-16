.PHONY: scrape sync enrich

scrape:
	python3 -m tgpc update

sync:
	python3 -m tgpc sync

enrich:
	python3 -m tgpc enrich
