Run these two commands, in this order. If your server is still running, either open a second terminal in the project folder, or press Ctrl+C to stop the server, run the commands, then start it again with `uv run python manage.py runserver`.

```bash
uv run python manage.py makemigrations   # write the migration from your model changes
uv run python manage.py migrate          # apply it to the database
```

You'll know it worked when `makemigrations` lists your changes and `migrate` prints `OK` next to each migration it applies. If you see `No changes detected`, check that you saved `models.py`, then run both commands again.

??? tip "What do these two commands do?"
    Changing a model changes the shape your database needs to be. `makemigrations` works
    out what changed and writes it down as a migration file; `migrate` applies that file to
    the database. You need both, every time you change a model.

    The migration file is code, so commit it alongside the model change. That's what makes
    your database schema travel with the project.
