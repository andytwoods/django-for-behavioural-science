# Sharing page layout: template inheritance

By chapter 5 you have two researcher-facing pages, the studies list and the dashboard, and they share a header, a footer and CSS. To save you the effort of entering the same piece of text multiple times, we use
 **template inheritance**, with shared code held in `base.html`.

## The base template

`base.html` stores everything the pages have in common, `{% block %}` marking
the gaps each page can fill (if desired):

<!-- source: study/templates/study/base.html -->
```html
<!DOCTYPE html>
<html lang="en">
<head>
  <title>{% block title %}Study platform{% endblock title %}</title>
  <style>/* the shared styling lives here, once */</style>
</head>
<body>
  {% include "study/menu.html" %}
  {% block content %}{% endblock content %}
  {% include "study/footer.html" %}
</body>
</html>
```

There are 2 mechanisms:

- `{% block %}` marks a region a child page can override. `base.html` gives each block a
  default (the title falls back to "Study platform"), and a child page replaces it.
- `{% include %}` pulls in a smaller partial. The header and footer live in their own
  little `menu.html` and `footer.html` files, so they're easy to find and reuse.

## A page that extends it

Each page now extends base.html:

<!-- source: study/templates/study/study_list.html -->
```html
{% extends "study/base.html" %}
{% block title %}Studies{% endblock title %}
{% block content %}
  <h1>Studies</h1>
  ...the list of studies...
{% endblock content %}
```
