.PHONY: scrape sync quota

scrape:  # Scrape TGPC → sync all destinations → enrich new records
	python3 -m tgpc update

sync:  # Full manual sync of rph.json to all cloud destinations
	python3 -m tgpc sync

quota:  # Show free quota usage for all services
	python3 -m tgpc quota
