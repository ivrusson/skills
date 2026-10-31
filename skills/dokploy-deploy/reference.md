# Dokploy zip and lookup

Generic helpers. Substitute the real application name, Dockerfile paths, and domain from **this** repo.

## Resolve the app

1. `dokploy_search` for applications / projects.
2. List apps in the intended project.
3. Match by **name**. Treat stored IDs as a cache, not as truth.

## Zip from git (repo root)

Example: one service whose Dockerfile lives at `apps/web/Dockerfile` and `COPY`s `apps/web` plus root lockfiles:

```bash
git archive --format=zip HEAD \
  Dockerfile \
  apps/web \
  package.json package-lock.json \
  -o /tmp/app.zip
```

Drop paths you do not need; **add every path the Dockerfile copies**. For a context that is the app directory, archive that directory as `.` only if Dokploy’s context is that folder.

Uncommitted files: stage a tree and `zip -r` from the repo root so relative paths stay `apps/…`, not `/Users/…`.

## dropDeployment via curl

If MCP cannot upload:

```bash
curl -sS -X POST "$DOKPLOY_URL/api/trpc/application.dropDeployment" \
  -H "x-api-key: $DOKPLOY_API_KEY" \
  -F "applicationId=<id>" \
  -F "file=@/tmp/app.zip;type=application/zip"
```

`DOKPLOY_URL` must **not** end with `/api` if the client already appends `/api`.

Skip REST `/api/drop-deployment` when it 413s or 500s; tRPC multipart is the working path.

## Health paths

Use whatever the app actually exposes (`/healthz`, `/`, `/api/health`). For HTTP-only hosts, inspect response **headers** for `Location: https://`.

## Cloudflare / DNS

HTTP-only hostname: DNS A to the VPS, proxy **off**. HTTPS hostname: proxy optional; Let’s Encrypt on Dokploy needs the host to reach the VPS on 80/443 as the certificate flow requires.
