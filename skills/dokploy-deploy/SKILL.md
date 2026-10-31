---
name: dokploy-deploy
description: >-
  Publishes any app to a self-hosted Dokploy (Hostinger or elsewhere) using git
  or zip-drop. Use when the user asks to desplegar, deploy, publish, rebuild, or
  set up Dokploy, Traefik domains, SSL, or a first production ship with no git
  remote.
---

# Dokploy deploy (generic)

How to put **any** project on Dokploy. Do not assume a specific stack, backend or domain.

MCP namespace `dokploy`: `dokploy_search` → `dokploy_describe` → `dokploy_call` (read) / `dokploy_mutate` (write). If MCP cannot upload a zip, `curl` the same tRPC route.

Zip/git recipes: [reference.md](reference.md).

## 1. Pick the ship path

| Situation | Path |
| --- | --- |
| Repo has `origin` and Dokploy already tracks that repo | Git deploy / rebuild of the existing application |
| No git remote, or Dokploy must not see the whole git history | **Zip-drop** (`application.dropDeployment`) |
| Only backend-as-a-service changed (Convex, Supabase, …) | Ship **there**, not Dokploy, unless this app’s image embeds that URL at **build** time |

One Dokploy **application** = one running service (one Dockerfile or compose). Split frontend, HTTP gateway, workers into **sibling apps** in the **same product project**. Never deploy into someone else’s project.

## 2. Isolate the product

Before mutating anything:

1. Resolve **organization → project → environment → application** by **name**.
2. Confirm the application id against that name. Do not reuse an id from another product.
3. **Do not** rebuild, restage, or edit domains of unrelated projects on the same VPS.

If the user is starting a **new** product: create a new Dokploy project (and apps) instead of stuffing it into an existing one.

## 3. HTTP vs HTTPS (do this before the first deploy)

Ask how clients will talk to the service.

**Normal websites / APIs in browsers:** HTTPS on, Let’s Encrypt (or the instance’s certificate type). `https://` public URL.

**HTTP-only clients** (old `wget`, IoT, devices that follow redirects and cannot do modern TLS):

- Domain HTTPS **off**
- `certificateType: none`
- **No** `redirect-to-https` (Traefik/Dokploy middleware)
- DNS **A** to the VPS. If Cloudflare: **DNS only** (grey cloud). Orange proxy terminates TLS and breaks those clients.
- Verify with **curl**, not Chrome (browsers force HTTPS).

A 301 to `https://` is as fatal as TLS for those clients.

## 4. Docker layout

Match the Dokploy app settings to the repo:

- **Dockerfile path** (e.g. `apps/web/Dockerfile` or `Dockerfile`)
- **Build context** (often **repository root**, not the app folder)
- **Port** the process listens on (`PORT`, `EXPOSE`, Traefik entrypoint). Mismatch = 502.

The zip or git tree must contain every path the Dockerfile `COPY`s. Monorepos: include workspace `package.json` files the install step needs.

**Runtime env** (secrets, API URLs the server reads): set on the Dokploy application, survive rebuilds.

**Build-time env** (`VITE_*`, `NEXT_PUBLIC_*`, baked into a SPA): pass as **build-args** on **every** image build. Changing them ⇒ rebuild. A runtime env var does not update a baked client bundle.

## 5. Zip-drop (no git remote)

REST `POST /api/drop-deployment` has failed here with **413/500**. Prefer tRPC:

`POST /api/trpc/application.dropDeployment`

Multipart: `applicationId` + zip. Auth: `x-api-key`.

Wait until the new deployment is **done** before saying it is live.

Zip from the **repo root**, preserving paths. Do not put `.env`, credentials, or huge `node_modules` in the zip (the image build installs deps).

If MCP cannot send multipart, use `curl` against the same tRPC URL. Still do not invent a git remote.

## 6. Git deploy

When `origin` exists and the Dokploy app is connected to it: push the branch Dokploy tracks, then trigger that application’s deploy. Do not zip-drop unless the user wants a one-off override.

## 7. Verify

After status **done**:

```bash
# HTTPS app
curl -sS -o /dev/null -w "%{http_code}\n" https://<host>/

# HTTP-only app (expect no Location: https://)
curl -sS -D- http://<host>/<health-path>
```

Hit the real health/login/API route this app documents. 502 → port, context, or crash logs in Dokploy.

## 8. New project checklist

```
- [ ] New Dokploy project (or explicit reuse of the same product)
- [ ] Application + Dockerfile path + context + PORT
- [ ] Domain + HTTP/HTTPS policy (section 3)
- [ ] Runtime env + build-args
- [ ] First ship (git or zip-drop)
- [ ] curl checks
```

## 9. Talk to the user

Use their language. State which **application** went out, HTTP vs HTTPS, and what to curl. Never dump API keys, deploy tokens, or env secret values.
