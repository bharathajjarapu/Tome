# Security

Report vulnerabilities privately through GitHub **Security → Report a vulnerability**.
Include the affected commit and reproduction steps. Do not disclose vulnerabilities in public issues.

## Controls

- bcrypt passwords; HS256 bearer JWTs expire after 60 minutes by default.
- API access checks team membership; vector queries filter by team and project.
- Uploads use an extension allowlist, size limits and generated storage names.
- nginx rate-limits authentication. Compose publishes Postgres and Qdrant on loopback only.

## Limits

- JWTs in `localStorage` are exposed if XSS occurs.
- Untrusted documents can contain prompt injection; citations do not guarantee correct answers.
- Retrieved passages are sent to the configured LLM endpoint.

## Deployment

Set a strong `JWT_SECRET` and `POSTGRES_PASSWORD`, terminate TLS before nginx,
and keep dependencies and container images updated.
