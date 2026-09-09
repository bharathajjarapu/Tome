# Security

## Reporting

Report vulnerabilities privately through GitHub: **Security → Report a vulnerability** on this
repository. Do not open a public issue. Expect a reply within a week.

## Model

| Concern | Control |
| --- | --- |
| Tenant isolation | Every route checks team membership. Every vector query filters on team and project, and the retriever cannot be built without both |
| Probing | Another team's project, document or conversation answers 404, never 403 |
| Passwords | bcrypt; 8 to 72 bytes; emails compared case-insensitively |
| Login timing | An unknown email still costs one bcrypt check |
| Brute force | nginx limits `/api/auth/` to 10 requests a minute per address |
| Tokens | HS256 JWT, 60 minute expiry, sent as a header, never in a URL |
| Uploads | Extension allowlist, size cap at nginx and API, stored under random names outside any served path |
| Prompt injection | Answers render without images, so injected text cannot leak context through an image URL |
| Errors | One JSON shape; stack traces and internals stay in the server log |
| Secrets | Environment only. `.env` is ignored by git |
| Network | Postgres and Qdrant bind to localhost; only nginx is published |

## Known limits

- The JWT lives in `localStorage`, so an XSS bug would expose it. Markdown is rendered by Streamdown with images disabled, which closes the main injection path.
- Uploaded documents are untrusted. Their text reaches the model, which may follow instructions planted in them; answers cite their sources so a reader can check.
- Answers come from an external LLM: retrieved passages leave the machine on every question.

## Deploying

- Set a random `JWT_SECRET` (`openssl rand -hex 32`) and a real `POSTGRES_PASSWORD`.
- Terminate TLS in front of nginx.
- Keep the images and the lockfiles current.
