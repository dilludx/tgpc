.PHONY: scrape sync

scrape:
	python3 -m tgpc update

sync:
	python3 -m tgpc sync
