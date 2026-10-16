---
name: web-scraping-best-practices
description: Robust, ethical, and resilient scraping workflows for automotive platforms (Encar, Autoplus, Heydealer, etc.) with rate limiting, error mitigation, and snapshot integrity.
---

# Web Scraping & Data Pipeline Best Practices

## 1. Request Courtesy & Anti-Blocking
- **Rate Limiting**: Always enforce random delays (jitter) between consecutive external requests.
- **Header Uniformity**: Use consistent, modern User-Agent strings and appropriate `Referer` headers matching real browser navigation.
- **Fail-Stop on 403/429**: If external servers return HTTP 403 (Forbidden) or 429 (Too Many Requests), **never** increase retries. Immediately abort and report the status.

## 2. Automotive Listing State Tracking
- **Active vs Sold-Out Transition**:
  - Do not mark a vehicle as sold on a single missing fetch.
  - Require consecutive missing detections (`consecutive_misses >= 2`) or verified 404 response on vehicle detail endpoints before transitioning state.
- **Link Integrity**: Construct vehicle detail links exclusively using verified vehicle IDs (`Id` or `_carid`), never brittle text or old query parameters.

## 3. Data Ingestion & Sanitization
- **Schema Protection**: Never inject synthetic defaults (`0`, `""`, `null`) interchangeably. Treat missing fields as `"-"` and fetch errors as `"미확인"`.
- **Atomic File Writes**: Write new snapshots or synced ledgers safely to temporary files before replacing target data files to prevent corruption on sudden termination.
