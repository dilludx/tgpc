.PHONY: scrape sync

scrape:  # Scrape TGPC website → save rph.json → sync all destinations
	python3 -m tgpc update

sync:  # Sync existing rph.json to Supabase, R2, GDrive, Release, Email
	python3 -m tgpc sync
