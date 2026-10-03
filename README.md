# RealBeauty

[![CI/CD](https://github.com/unibo-dtm-se-2526-RealBeauty/artifact/actions/workflows/check.yml/badge.svg)](https://github.com/unibo-dtm-se-2526-RealBeauty/artifact/actions/workflows/check.yml)
[![PyPI](https://img.shields.io/pypi/v/realbeauty)](https://pypi.org/project/realbeauty/)

**Know what's really inside your personal care products.**

RealBeauty is a small Flask web application that analyses the ingredient list of a cosmetic or personal care product. It returns a safety score, flags concerning ingredients with a severity level, and highlights beneficial ones.

It was developed as the project work for the Software Engineering course (University of Bologna, DTM, 2025/26). The full process description (requirements, design, validation, release, etc.) is in the report, which lives in the `report` repository of this GitHub organization.

## Features

- **Three ways to provide input**
  - a product **barcode**, looked up on [Open Beauty Facts](https://world.openbeautyfacts.org/);
  - an **ingredient list** pasted manually (also the fallback when a barcode is not found);
  - a **photo of the label**, from which the ingredient list is extracted by a vision model.
- **AI-based analysis** (through [OpenRouter](https://openrouter.ai/)): a score from 0 to 100, a short summary, flagged ingredients (high / medium / low severity) and safe highlights.
- **History**: every analysis is stored in a local SQLite database and can be listed through the API.
- **Versioned HTTP API** under `/api/v1`.

### How the score works

The AI model is instructed to start from 100, subtract 20 for each high-severity ingredient, 10 for each medium one and 3 for each low one, add 2 for each beneficial ingredient, and keep the result between 0 and 100.

> RealBeauty is an educational project. Its output comes from an AI model, can be wrong, and is **not** medical or dermatological advice.

## Tech stack and architecture

- **Language and framework:** Python 3.10+, Flask
- **Data:** SQLite through SQLAlchemy; Open Beauty Facts for product lookup
- **AI:** OpenRouter (text analysis and label-photo reading)
- **Tooling:** Poetry, pytest, coverage, ruff, mypy, GitHub Actions, semantic-release

The code is split by responsibility: `beauty_api.py` talks to Open Beauty Facts, `analyzer.py` talks to the AI service, `database.py` handles persistence, and `app.py` exposes the Flask routes (versioned under `/api/v1`). The user interface is a single HTML page with vanilla JavaScript.

## Project structure

```
<root directory>
├── artifact/               # main Python package
│   ├── __init__.py
│   ├── __main__.py
│   ├── app.py              # Flask application and HTTP routes
│   ├── analyzer.py         # AI analysis and label-photo reading (OpenRouter)
│   ├── beauty_api.py       # Open Beauty Facts client
│   └── database.py         # SQLite persistence (SQLAlchemy)
├── templates/
│   └── index.html          # web interface
├── tests/                  # automated tests
├── .github/workflows/      # CI/CD: check.yml (checks and tests), deploy.yml (release)
├── pyproject.toml          # project configuration and dependencies (Poetry)
├── release.config.mjs      # semantic-release configuration
├── CHANGELOG.md            # generated automatically at each release
└── LICENSE                 # Apache License 2.0
```

## Requirements

- Python 3.10 or newer
- [Poetry](https://python-poetry.org/)
- An OpenRouter API key

## Getting started

```bash
git clone https://github.com/unibo-dtm-se-2526-RealBeauty/artifact.git
cd artifact
poetry install
```

Create a file named `.env` in the project root (it is git-ignored) containing your OpenRouter key. The variable is called `GEMINI_API_KEY` for historical reasons, but it holds an OpenRouter key:

```
GEMINI_API_KEY=your-openrouter-api-key
```

Start the application:

```bash
poetry run flask --app artifact.app run
```

and open <http://127.0.0.1:5000>. On macOS, port 5000 is sometimes used by AirPlay; in that case run it with `--port 5001`.

The SQLite database (`realbeauty.db`) is created automatically in the project root on first start.

> The package is also published on [PyPI](https://pypi.org/project/realbeauty/) as `realbeauty`, but the HTML templates live outside the Python package, so running from a source checkout as described above is the supported way to use the web application.

## Using the application

1. Type a barcode, **or** paste the ingredient list, **or** upload a photo of the label.
2. Press **Analyze** (or **Analyze Photo**).
3. Wait for the result. Free AI models can be slow: an analysis may take up to about two minutes.

If a barcode is not found (or has no ingredient list in Open Beauty Facts), the application asks you to enter the ingredients manually.

## HTTP API

| Method | Path | Body | Description |
|--------|------|------|-------------|
| `GET` | `/` | – | Web interface |
| `POST` | `/api/v1/analyze` | JSON: `barcode` and/or `ingredients` | Analyse a product |
| `POST` | `/api/v1/analyze-photo` | multipart form: `photo` | Extract the ingredients from a label photo and analyse them |
| `GET` | `/api/v1/history` | – | List previous analyses |

Example:

```bash
curl -X POST http://127.0.0.1:5000/api/v1/analyze \
  -H "Content-Type: application/json" \
  -d '{"ingredients": "Aqua, Glycerin"}'
```

A successful analysis returns:

```json
{
  "product_name": "Manual Entry",
  "brand": "Unknown",
  "score": 100,
  "summary": "…",
  "flagged": [{"name": "…", "reason": "…", "severity": "low"}],
  "safe_highlights": ["Glycerin"]
}
```

Error responses carry an `error` field: `400` (no input), `404` (`not_found`, barcode unknown), `422` (ingredients could not be read from the photo), `503` (`ai_failed`, the AI service did not answer correctly).

## Configuration

- The AI models and the request timeout (120 seconds) are set in `artifact/analyzer.py`. The project uses free OpenRouter models, which may change or become unavailable.
- The database location is set in `artifact/database.py`.

## Development

Useful commands (all through Poetry):

```bash
poetry run poe format           # format the code with ruff
poetry run poe static-checks    # ruff lint + mypy
poetry run poe test             # run the tests
poetry run poe coverage         # run the tests under coverage
poetry run poe coverage-report  # print the coverage report
```

Tests live in `tests/`. The AI and the database calls are mocked, so the tests need neither an API key nor network access.

### Commit convention and releases

Commit messages follow [Conventional Commits](https://www.conventionalcommits.org/) (`feat:`, `fix:`, `docs:`, `test:`, `ci:`, `build:`, `refactor:`). Releases are fully automated by [semantic-release](https://semantic-release.gitbook.io/): `feat` produces a minor version, `fix` a patch version.

### CI/CD

On every push, GitHub Actions runs the syntax check, ruff, mypy, the format check and the tests with coverage, then runs the tests on Python 3.10–3.13 on Linux, Windows and macOS. On `master`, semantic-release computes the next version from the commit messages, updates `CHANGELOG.md`, creates the tag and the GitHub release, and publishes the package to PyPI.

To enable releases on a new repository, add two repository secrets: `RELEASE_TOKEN` (a GitHub personal access token allowed to push to the repository) and `PYPI_TOKEN` (a PyPI API token).

## Validation summary

- **Automated tests:** pytest tests for the web routes, with the AI and the database mocked; line coverage is over 80%, measured with `coverage`.
- **Manual acceptance testing:** the application was exercised through the web interface with real ingredient lists, including error cases such as an unknown barcode and an unavailable AI service.

## Known limitations

- Open Beauty Facts is community-maintained: many products, or their ingredient lists, are missing, and the same product has different barcodes in different countries.
- The free AI models are slow and sometimes unreliable; photo analysis can occasionally fail with an empty answer from the vision model.
- Results are AI-generated and depend on the model used.

## License

Released under the Apache License 2.0. See [LICENSE](LICENSE).
