---
name: DevSecOps Checklist
description: A structured PASS / FAIL / N/A checklist for reviewing infrastructure changes for security issues before merge — identity, secrets, network, data, and supply chain.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [security, devsecops, review, checklist]
---
## Purpose

A security review without a structure tends to catch whatever the reviewer happens to think of that day and miss whatever they don't. This checklist gives a repeatable set of categories to walk through explicitly for any infrastructure change, so coverage doesn't depend on what's top of mind. It's the working tool behind the `security-auditor` agent, but it's usable by anyone reviewing an IaC or pipeline diff.

## When to use it

For any change touching: identity and access, secrets, network configuration, data storage, container images, dependencies, or CI/CD pipeline definitions. Skip it for changes with none of the above (e.g., a pure documentation change) — mark the whole review N/A rather than force-fitting categories that don't apply.

## The checklist

Walk each category and mark it PASS (verified, no issue), FAIL (issue found — blocking), or N/A (doesn't apply to this diff), with a one-line note for anything not PASS/N/A:

1. **Identity** — Does the change use managed identity (Azure Managed Identity, AWS IAM roles, GCP Workload Identity Federation) over long-lived keys? Are IAM roles scoped to least privilege (no `*` actions, no `*` resources where avoidable)? Is the blast radius of each grant proportionate to what it's for?
2. **Secrets** — Are there any hardcoded credentials, API keys, or tokens in this diff? Are secrets injected at deploy time from a secrets manager, never baked into artifacts, config files, or logs? Is there a rotation path for any new secret?
3. **Network exposure** — Are resources private by default? Any public IP, `0.0.0.0/0` ingress, or open bucket ACL? Is ingress restricted to the sources that actually need it (security groups, NSGs, WAF rules)?
4. **Data protection** — Is data encrypted at rest and in transit? Are encryption keys managed (KMS/Key Vault) rather than defaulting to provider-managed where the data warrants it? Is backup/retention configured for stateful data?
5. **Supply chain** — Are container images scanned for CVEs? Are base images minimal and pinned? Are dependencies pinned and from trusted sources? Is there an SBOM for production images?
6. **Pipeline integrity** — Are CI/CD secrets scoped to the jobs that need them? Are pipeline definitions protected from untrusted PRs (no secret exposure on `pull_request` from forks)? Is the pipeline itself reviewed like code?
7. **Compliance mapping** — Does the change touch regulated data or workloads (PCI, HIPAA, GDPR, CIS benchmarks)? Is the mapping to the relevant standard explicit rather than assumed?

## Expected output

A short report listing each applicable category with its verdict and a one-line justification, e.g. `Network exposure: FAIL — security group allows 0.0.0.0/0 on port 5432`. Blocking (FAIL) items should be specific enough that the fix is obvious without re-deriving the finding. Ground findings in OWASP, CIS Benchmarks, or NIST where the mapping is genuinely clear — it makes the finding checkable against an external standard rather than a matter of opinion.