# Certificate monitoring

Phase 7 turns certificate discovery into monitoring and alerting. Automatic renewal is **not** implemented.

## Model

All sources share one `acm_certificates` table (historical name):

- AWS ACM
- Alibaba CAS
- Kubernetes TLS secrets (EKS and ACK)
- Ingress TLS metadata (attached as `in_use_by`)
- External HTTPS endpoints (`certificate_endpoints`)

Private keys, `tls.key`, and full secret payloads are never persisted.

Operational expiry class is computed only in `classify_expiry()`:

| Status | Days remaining |
| --- | --- |
| HEALTHY | > 60 |
| WARNING | 31–60 |
| CRITICAL | 8–30 |
| URGENT | 1–7 |
| EXPIRED | ≤ 0 |
| UNKNOWN | expiration missing |

Catalog `renewalStatus` (`OK` / `Expiring` / `Renewing` / `Expired`) is derived from that class.

## Celery (configurable)

Intervals come from settings, not business logic:

| Job | Setting | Default |
| --- | --- | --- |
| `certificate-discovery` | `CLOUDOPS_CERTIFICATE_DISCOVERY_INTERVAL_SECONDS` | 6 hours |
| `certificate-expiry-scan` | `CLOUDOPS_CERTIFICATE_EXPIRY_INTERVAL_SECONDS` | 1 hour |
| `certificate-endpoint-validation` | `CLOUDOPS_CERTIFICATE_ENDPOINT_INTERVAL_SECONDS` | 6 hours |
| `certificate-alert-evaluation` | `CLOUDOPS_CERTIFICATE_ALERT_INTERVAL_SECONDS` | 1 hour |

Manual enqueue: `POST /api/v1/certificates/scan` (discovery) and `POST /api/v1/certificates/{id}/validate`. FastAPI does not scan providers synchronously.

Per-account failures are isolated. Environments store last successful scan, last attempted scan, and last error class.

## Alerts and notifications

Kinds: `CERTIFICATE_WARNING`, `CERTIFICATE_CRITICAL`, `CERTIFICATE_URGENT`, `CERTIFICATE_EXPIRED`.

Lifecycle: `OPEN` → `ACKNOWLEDGED` → `RESOLVED`. One active alert per certificate. Renewal auto-resolves the open alert.

Severity mapping (configurable):

- WARNING → `CLOUDOPS_CERTIFICATE_ALERT_SEVERITY_WARNING` (default MEDIUM)
- CRITICAL → HIGH
- URGENT → CRITICAL
- EXPIRED → CRITICAL

`NotificationProvider` implementations: `log` (default), `slack`, `email` (stub), `teams` (stub). Cooldown: `CLOUDOPS_CERTIFICATE_NOTIFICATION_COOLDOWN_SECONDS`.

## HTTPS / SSRF

Only HTTPS. Private, loopback, link-local, and metadata addresses are blocked. An empty allow-list (`CLOUDOPS_CERTIFICATE_HTTPS_ALLOWLIST`) rejects unregistered hosts; rows in `certificate_endpoints` are treated as registered.

## API

- `GET /api/v1/certificates` (`provider`, `region`, `environment`, `status`, `expires_within_days`, `sort`)
- `GET /api/v1/certificates/{id}`
- `GET /api/v1/certificates/{id}/history`
- `GET /api/v1/certificates/{id}/alerts`
- `POST /api/v1/certificates/scan`
- `POST /api/v1/certificates/{id}/validate`
- `POST /api/v1/certificates/{id}/alerts/{alert_id}/acknowledge`
- `GET /metrics`

RBAC: `certificate:read|scan|validate|ack`.

## Known limitations

- Ingress TLS is derived from Kubernetes Ingress objects when the API is reachable; otherwise only TLS secret metadata is stored.
- HTTPS probes require an allow-list or a registered endpoint row.
- Metrics are in-process counters/gauges, not a Prometheus client library.
- ACM/CAS auto-renew is inferred from provider eligibility fields, not a live renewal API.
- Header RBAC is not SSO.
- Local/dev uses eager Celery (`CLOUDOPS_CELERY_EAGER=true`).
