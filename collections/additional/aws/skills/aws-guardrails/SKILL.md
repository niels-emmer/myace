---
name: AWS Guardrails
description: Catalogue and rollout method for preventive guardrails in AWS Organizations using service control policies, resource control policies and declarative policies. Use when designing or changing organisation-wide controls.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [aws, governance, guardrails, scp]
---
## Purpose

Choose the right organisation-level control for each invariant and roll it out without breaking workloads.

## When to use it

When adding, changing or reviewing an SCP, RCP or declarative policy, or when deciding how to enforce an invariant across accounts.

## Checklist

- **Pick the layer**: SCPs cap what principals in member accounts can do; resource control policies (RCPs, launched November 2024) cap what can be done to resources, such as who outside your organisation can access them; declarative policies set a service's baseline configuration in the service's control plane. None of them grants permissions: effective access is the intersection with identity and resource policies.
- **Typical SCP guardrails**: deny leaving the organisation, deny disabling or altering the organisation trail, GuardDuty, Config and Security Hub, deny root-user actions in member accounts, deny unapproved regions with an exemption list for global services, deny creating IAM users and long-lived access keys where federation is the standard.
- **Typical RCP guardrails**: restrict access to S3, KMS, SQS and similar resources to your organisation with `aws:PrincipalOrgID`, require TLS with `aws:SecureTransport`, with documented exceptions for intentional public or partner access.
- **Management account**: SCPs and RCPs do not restrict it, so keep workloads out of it and protect it with other controls.
- **Break-glass**: exempt a named emergency role through a condition on the role ARN, alarm on its use, and test it.
- **Roll out safely**: author in code, attach first to a test OU, review CloudTrail and IAM Access Analyzer for would-be denials, then widen one OU at a time. Deny policies can block services in surprising ways, which AWS documentation warns about.
- **Keep it small**: policy size and attachment quotas apply (check current quotas), so use few, well-named policies with documented purpose rather than many narrow ones.
- **Record**: each guardrail has an owner, the invariant it enforces, the exception process and a link to the exception register.

## Expected output

A guardrail set mapped to named invariants with an owner for each, tested on a non-production OU before wide attachment, and a tested break-glass path.
