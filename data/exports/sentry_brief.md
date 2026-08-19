# Vendor research brief — Sentry

> FIRST-PASS INTERNAL RESEARCH AID. Generated from public web pages only. This is not a vendor risk score, a security approval, or a procurement decision. Every field must be confirmed by a human reviewer before use.

**Overview (quoted from the vendor's own product page):** Application Performance Monitoring & Error Tracking Software | Sentry

**Category:** developer productivity tools _(curated, not extracted)_

**Generated:** 2026-08-19

## How to read this brief

| Measure | Value | What it answers |
|---|---|---|
| **Evidence** | 10/10 → High | how much quotable material was found |
| **Confidence** | Medium — 2 of 5 core fields High, 3 Medium, 0 Low | how good that evidence is, on the client's definition |
| **Coverage** | 5/5 core fields verified | how much we could actually check |

> **Read all three.** A vendor can score 10/10 on evidence while most of its primary documents were never readable. Confidence is the WEAKEST core field, not an average — a first-pass brief is only as trustworthy as the weakest field a reviewer will act on.

## Fields

### Security and trust information

- **Status:** FOUND · **Confidence:** High · **Extraction quality:** High
- **Why:** stated directly on the vendor's own security page, quoted in full, with no collection limitation

> Sentry has obtained the following compliance certifications: SOC2 Type I SOC2 Type II HIPAA Attestation ISO 27001 If you already use Sentry, you can access the report and certificate via your Sentry account.

- `security` — matched soc2, iso 27001, hipaa — [https://sentry.io/security/](https://sentry.io/security/)
- `security` — matched soc 2, iso 27001 — [https://sentry.io/security/](https://sentry.io/security/)
- `security` — matched saml, scim — [https://sentry.io/security/](https://sentry.io/security/)

### Privacy and data-handling references

- **Status:** FOUND · **Confidence:** Medium · **Extraction quality:** High
- **Why:** the top card cites terms its quoted text does not show

> Customer controls what Service Data (including what, if any, personal information) are sent to and processed by the Service by configuring SDKs and the Service.

- `terms` — matched personal information (+5 more term(s) on the page, outside this quote) — [https://sentry.io/terms](https://sentry.io/terms)
- `privacy` — matched personal information (+3 more term(s) on the page, outside this quote) — [https://sentry.io/privacy/](https://sentry.io/privacy/)
- `privacy` — matched privacy policy, personal information (+1 more term(s) on the page, outside this quote) — [https://sentry.io/privacy/](https://sentry.io/privacy/)

### Support and documentation availability

- **Status:** FOUND · **Confidence:** Medium · **Extraction quality:** High
- **Why:** evidence came from security, never from docs/product

> Sentry retains event data in production for the period set forth in our documentation based on data and plan type by default.

- `security` — matched documentation — [https://sentry.io/security/](https://sentry.io/security/)
- `security` — matched documentation — [https://sentry.io/security/](https://sentry.io/security/)
- `security` — matched 24/7 — [https://sentry.io/security/](https://sentry.io/security/)

### Integration or API availability

- **Status:** FOUND · **Confidence:** Medium · **Extraction quality:** High
- **Why:** evidence came from pricing, security, terms, never from docs/integrations/product; the top card cites terms its quoted text does not show

> …Third-Party Platforms (e.g., messaging services, code repositories and project management solutions) through supported integrations.

- `terms` — matched integrations (+1 more term(s) on the page, outside this quote) — [https://sentry.io/terms](https://sentry.io/terms)
- `security` — matched rest api — [https://sentry.io/security/](https://sentry.io/security/)
- `pricing` — matched sdk — [https://sentry.io/pricing/](https://sentry.io/pricing/)

### Pricing or plan availability

- **Status:** FOUND · **Confidence:** High · **Extraction quality:** High
- **Why:** stated directly on the vendor's own pricing page, quoted in full, with no collection limitation

> New users only: Get 5,000 free replays per month for your first 3 months.

- `pricing` — matched per month — [https://sentry.io/pricing/](https://sentry.io/pricing/)
- `terms` — matched pricing — [https://sentry.io/terms](https://sentry.io/terms)
- `pricing` — matched billed annually, pricing — [https://sentry.io/pricing/](https://sentry.io/pricing/)

### Data residency / storage location

- **Status:** PARTIAL · **Confidence:** Low · **Extraction quality:** Low
- **Why:** only a label, a fragment or an image — nothing quotable was written

> Data Residency

- `pricing` — matched data residency — [https://sentry.io/pricing/](https://sentry.io/pricing/)

### Encryption practices

- **Status:** FOUND · **Confidence:** High · **Extraction quality:** High
- **Why:** stated directly on the vendor's own security page, quoted in full, with no collection limitation

> All data is AES-256bit encrypted, both in transit and at rest.

- `security` — matched aes-256bit — [https://sentry.io/security/](https://sentry.io/security/)
- `security` — matched encrypted at rest — [https://sentry.io/security/](https://sentry.io/security/)

### Uptime, SLA and reliability

- **Status:** FOUND · **Confidence:** High · **Extraction quality:** High
- **Why:** stated directly on the vendor's own security page, quoted in full, with no collection limitation

> In the event of a region-wide outage, Sentry will bring up a duplicate environment in a different Google Cloud Platform region. The Sentry operations team has extensive experience performing full region migrations.

- `security` — matched disaster recovery — [https://sentry.io/security/](https://sentry.io/security/)
- `security` — matched business continuity — [https://sentry.io/security/](https://sentry.io/security/)
- `security` — matched high availability — [https://sentry.io/security/](https://sentry.io/security/)

## Missing or unclear

- Data residency / storage location: a heading or label only — the vendor named it but published no statement. Open the page.

## Review flags — a human must act on these

- Security and trust information: the vendor says the proof exists but does not publish it ("available to customers"). It cannot be closed from public sources alone.
- Support and documentation availability: evidence came only from security, never from docs/product. The match is real; the finding is weak.
- Integration or API availability: evidence came only from pricing, security, terms, never from docs/integrations/product. The match is real; the finding is weak.
- Data residency / storage location: evidence came only from pricing, never from security/privacy. The match is real; the finding is weak.
- Uptime, SLA and reliability: the confidence label was earned by a sentence that does not contain the matched term (longest term-carrying sentence is 17 characters). Read the quote before relying on the label.

## Sources read

- https://sentry.io/welcome/
- https://sentry.io/pricing/
- https://sentry.io/security/
- https://sentry.io/privacy/
- https://docs.sentry.io/
- https://status.sentry.io/
- https://sentry.io/terms
