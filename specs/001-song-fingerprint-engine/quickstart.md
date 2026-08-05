# Quickstart & Validation Guide: Song Fingerprint Engine

## Prerequisites

- Python 3.11+
- PostgreSQL database running locally
- Virtual environment with dependencies (`django`, `sqlalchemy`, `psycopg2-binary`, `librosa`, `numpy`, `scipy`, `httpx`, `pytest`)

## Setup

```bash
# Set environment variable for PostgreSQL connection
export DATABASE_URL="postgresql://postgres:postgres@localhost:5432/genreguru"

# Run database migrations / table creation script
python -m src.core.db.init_db
```

## Running the Application

```bash
# Start Django dev server
python frontend/manage.py runserver 0.0.0.0:8000
```

Open browser to `http://localhost:8000`.

## Validation Workflows

### Scenario 1: Search & 2-Click Confirmation
1. Type `Daft Punk` in text field and click **Search**.
2. Verify top 5 candidate matches appear in list.
3. Click match once → verifies UI item enters "Selected" state.
4. Click match second time → confirms selection; initiates Deezer audio fetch + librosa DSP fingerprinting.
5. Verify success response and fingerprint metrics displayed.
6. Re-submit the same song and confirm again → verify the existing fingerprint is reused (matched by ISRC) without creating duplicate database records.

### Scenario 2: Automated Integration Tests

```bash
# Run test suite
pytest tests/
```
