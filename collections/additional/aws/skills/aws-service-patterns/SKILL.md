---
name: AWS Service Patterns
description: Service-selection and configuration patterns for common AWS workloads covering compute, data, networking and storage defaults. Use when choosing or configuring AWS services in IaC.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [aws, architecture, services]
---
## Purpose

Give AWS-specific defaults and trade-offs that the generic IaC and landing-zone skills cannot, so service choices are deliberate and safe.

## When to use it

When selecting compute, a data store or a network path for a new workload, or reviewing IaC that provisions them. Verify current service limits, SKUs and defaults against the provider's documentation before relying on them.

## Checklist

- **Compute**: Lambda for event-driven or spiky work, ECS on Fargate for containers without cluster management, EKS when Kubernetes is a requirement, EC2 when you need control of the instance; say which and why. Run containers and functions with a dedicated task or execution role, not a shared one.
- **Network**: private subnets for workloads, public ones only for load balancers. Use gateway endpoints for S3 and DynamoDB (no hourly charge) and interface endpoints (PrivateLink) for other services you call heavily; NAT gateways carry hourly and per-GB charges, so a design that sends large traffic through them needs a cost note.
- **S3**: keep Block Public Access on at account and bucket level, ACLs disabled (bucket-owner enforced), default encryption with SSE-KMS where key control matters, versioning for important data, a lifecycle rule for retention, and a bucket policy that denies non-TLS requests.
- **Databases**: RDS or Aurora in private subnets with encryption, automated backups, deletion protection and a Multi-AZ choice that matches the availability target; DynamoDB with point-in-time recovery for important tables.
- **Secrets and config**: Secrets Manager for credentials that rotate, SSM Parameter Store for plain configuration, referenced by ARN.
- **Load balancing and edge**: ALB for HTTP, NLB for TCP or static IPs; terminate TLS with ACM certificates; put CloudFront and AWS WAF in front of internet-facing apps that need them.
- **Observability**: CloudTrail organisation trail, Config recorder, CloudWatch log groups with retention set (the default is never expire), alarms with an owner.
- **Regions**: pick regions for latency, data residency and service availability, and block the rest with the guardrails skill.
- **Cost levers**: right-size, use Savings Plans only for stable baseline, delete unattached volumes and idle load balancers, and tag for cost allocation.

## Expected output

A design note naming the chosen services with reasons, the private-networking path, storage and database protections, and the cost drivers.
