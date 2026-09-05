.PHONY: serve test refresh migrate

serve:  ## Run the Django dev server
	uv run python manage.py runserver

migrate:  ## Apply database migrations
	uv run python manage.py migrate

test:  ## Run the test suite
	uv run python manage.py test

refresh:  ## Regenerate tutorial screenshots (run on each Django/jsPsych bump – see PLAN §9e)
	uv run python scripts/screenshots.py
