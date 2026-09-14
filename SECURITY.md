# Security Policy

## Reporting a Vulnerability

**Please do not open a public issue for security problems.** Report in private
so the issue can be fixed before it is exposed.

Preferred — GitHub Security Advisory ("Report a vulnerability" button on this
repository's *Security* tab). Draft a private advisory; it stays private until
a patch is ready and you decide to publish.

Please include:

- The affected module/endpoint and a minimal reproducer
- Impact — what an attacker can do, and under what conditions
- Any affected branch/commit if you know one
- Suggested fix if you have one

You will get an acknowledgement promptly; the maintainer will work with you to
confirm the issue and plan a fix. Please keep the issue private until a fix is
released, unless you need to coordinate elsewhere (coordinated disclosure is
welcome).

## Supported Versions

No tagged releases exist yet. The only supported "version" is the latest
commit on `main` and the code under current development. Security fixes land
on `main` and are back-ported only if an existing release is affected and a
release-based fix is warranted.

## Security Model & Practices

GenreGuru's security baseline, as designed in the architecture decision records
(`docs/adr/0008`–`0012`) and implemented in the Django config tree:

- **Secrets never live in source.** All secrets resolve at load time through
  Hydra `${oc.env:...}` interpolation: `DJANGO_SECRET_KEY`, `DJANGO_ALLOWED_HOSTS`,
  and the `DB_*` connection set. Prod config has **no defaults** for these —
  load fails fast when a variable is missing (fail-closed). `.env.example`
  documents which variables are required and ships placeholders only.
- **Django production hardening** (`config/django/prod.yaml`,
  `genreguru_web/settings/production`): `debug: false`, `SECURE_SSL_REDIRECT`,
  `SESSION_COOKIE_SECURE`, `CSRF_COOKIE_SECURE`, `X_FRAME_OPTIONS: DENY`. Cross-site
  forgery protection is on for the `search`/`confirm` API.
- **Dependency scanning.** `bandit` is a dev dependency; run locally with
  `uv run bandit -r src web`. A CI-gated bandit scan is not wired yet.
- **Known deferred item — rate limiting.** The internal search API does not yet
  enforce rate limiting / abuse prevention (tracked as CHK024 in the specs).
  Treat the service as trusted-network-only until that lands.

## Reporting a Non-Vulnerability

Bugs, feature requests, and questions go to the issue tracker or
[`docs/ROADMAP.md`](docs/ROADMAP.md) — not this file.