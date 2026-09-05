??? tip "Remind me — how do I run a migration?"
    Changing a model changes the shape your database needs to be. `makemigrations` works
    out what changed and writes it down as a migration file; `migrate` applies that file to
    the database. Two commands, every time, in that order:

    ```bash
    uv run python manage.py makemigrations   # write the migration from your model changes
    uv run python manage.py migrate          # apply it to the database
    ```

    The migration file is code, so commit it alongside the model change — that's what makes
    your database schema travel with the project.
