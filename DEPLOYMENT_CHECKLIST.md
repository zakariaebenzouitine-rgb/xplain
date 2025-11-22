# XPLAIN – First Deployment Checklist (Cloud Run)

This document is a **repeatable, one-path** sequence for deploying XPLAIN
into **any** GCP account.

**Important rules (project design):**
- No training happens here.
- No credentials live in this repo.
- The deployer authenticates with gcloud **outside** the repo.

---

## 0) Preconditions (deployer machine)

The deployer must have:
- Docker installed
- gcloud CLI installed
- Access to their GCP project
- A Cloud Run–capable region (example: europe-west1)

---

## 1) Authenticate with GCP (outside repo)

```bash
gcloud auth login
