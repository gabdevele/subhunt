# How it works

```
handle ─▶ scope ─▶ apexes ─▶ enumerate ─▶ filter ─▶ alive ─▶ enrich ─▶ output
```

Custom attribution headers (`-H/--header`, `--h1-header`) are attached to
enumeration and target requests; they are not sent to the HackerOne API.

## 1. HackerOne scope

subhunt reads the program's **structured scopes** and **scope exclusions** from
the HackerOne Hacker API (with a local cache, see
[Configuration](configuration.md#cache)).

Each asset becomes either an in-scope or an out-of-scope pattern:

- **In scope**: `eligible_for_submission` is true and, unless
  `--include-non-bounty` is set, `eligible_for_bounty` is true.
- **Out of scope**: `eligible_for_submission` is false.

Only host-like assets are kept. Wildcards are detected from the `*` character
in the identifier, **not** from the asset type, because HackerOne marks wildcards
inconsistently:

| Identifier | Type | Treated as |
| --- | --- | --- |
| `*.shopify.com` | `WILDCARD` | wildcard |
| `*.coinbase.com` | `URL` | wildcard |
| `*.base.org` | `OTHER` | wildcard |
| `api.example.com` | `URL` | host |
| `https://*.content.example.com/` | `URL` | wildcard |
| `54.175.255.192/27` | `CIDR` | ignored |
| `https://github.com/org/repo` | `SOURCE_CODE` | ignored |
| `com.example.android` | `GOOGLE_PLAY_APP_ID` | ignored |
| `Shopify Third Party Apps` | `OTHER` | ignored (not a host) |

Types `URL`, `DOMAIN` and `WILDCARD` are always considered; `OTHER` only when
its identifier contains a `*`. CIDR, IP addresses, source code, mobile app IDs,
hardware, smart contracts and similar non-host assets are ignored.

`scope_exclusions` are report **categories** (for example "Subdomain takeover
without POC"), not hosts. They are surfaced by `subhunt scope` as notes but do
not affect host filtering. Host-level exclusions live in the structured scopes
as assets with `eligible_for_submission: false`.

## 2. Apex derivation

For each in-scope pattern, subhunt derives the registrable domain to enumerate
using `tldextract`. Wildcards are handled by taking the part after the last `*`:

| Pattern | Apex enumerated |
| --- | --- |
| `*.shopify.com` | `shopify.com` |
| `api.hackerone.com` | `hackerone.com` |
| `*ubereats.com` | `ubereats.com` |
| `scaledsolutions*.uber.com` | `uber.com` |
| `status.*.coinbase.com` | `coinbase.com` |

## 3. Enumeration

subhunt is **hybrid**: it uses the best available backend automatically.

- If `subfinder` is on the `PATH`, it runs `subfinder -d <apex> -silent`.
- Otherwise it queries free Certificate Transparency sources concurrently:
  `crt.sh`, `crt.name`, `agniops` and `jsmon`.

Source calls are isolated: a slow or failing source is skipped without aborting
the run. Results are lower-cased, de-duplicated, wildcard prefixes stripped, and
restricted to the apex being enumerated.

## 4. Filtering

A host is kept if it matches at least one in-scope pattern **and** no
out-of-scope pattern.

Pattern matching:

- A `*` matches any characters, at any depth: `*.example.com` matches
  `a.example.com` and `a.b.example.com`, but not `example.com`.
- A bare host matches itself and its subdomains: `example.com` matches
  `example.com` and `api.example.com`.

Out-of-scope patterns are subtracted even when they fall under an in-scope
wildcard, so explicitly excluded hosts never reach the liveness stage.

## 5. Liveness

Candidates are resolved and probed:

1. **DNS**: `A` and `AAAA` records via `dnspython`, concurrently. Hosts that do
   not resolve are dropped.
2. **HTTP**: `https://<host>` then `http://<host>` via `httpx`, following
   redirects, concurrently. Only hosts that answer are reported, with their
   status code, page title and `Server` header.

`--dns-only` stops after step 1. TLS certificate verification is disabled during
probing because recon must survive broken/expired certificates; no response body
is trusted beyond extracting the `<title>`.

## 6. Enrichment and probes

When `--enrich` or `--takeover` is set, each live host is enriched in the same
concurrent pass:

- **`--enrich`**: security headers, technology fingerprints (headers, cookies,
  body and `Server`), the TLS certificate (issuer, expiry, SANs) and a favicon
  hash for clustering identical applications.
- **`--takeover`**: resolves the host's CNAME and flags it when it points to a
  known service (GitHub Pages, Heroku, S3, Azure, ...) that is not claimed,
  matching the service's "unclaimed" response.

All enrichment is bounded by the same concurrency and timeout as probing, and
results land in the `enrichment` object of each host.

## 7. Output

Findings are streamed as each host becomes live (see
[Usage](usage.md#live-progress)), then emitted as a table, JSON, CSV or Markdown.
With structured output, progress goes to stderr and the data to stdout.

### Result fields

| Field | Description |
| --- | --- |
| `host` | The live subdomain. The reachable URL is `https://<host>`. |
| `ips` | Resolved IPv4/IPv6 addresses. |
| `status` | HTTP status code (`null` with `--dns-only`). |
| `title` | Page `<title>`, if any. |
| `server` | `Server` response header, if present. |
| `enrichment` | Optional object with technology, headers, TLS, favicon and takeover data (see [Enrichment](usage.md#enrichment-and-probes)). |

---

See also: [Usage](usage.md) · [FAQ](faq.md)
