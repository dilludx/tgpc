.PHONY: scrape sync enrich retry quota

scrape:  # Scrape TGPC website → save rph.json → sync all destinations
	python3 -m tgpc update

sync:  # Sync existing rph.json to Supabase, R2, GDrive, Release, Email
	python3 -m tgpc sync

enrich:  # Upload photos for new records from last scrape
	python3 -m tgpc enrich

retry:  # Retry uploading failed photos from data/webp/ to R2
	python3 -m tgpc retry-photos

quota:  # Show free quota usage for all services
	python3 -m tgpc quota
