---
name: Image Build
description: Multi-stage Docker builds, minimal base images, image scanning, and SBOMs — so container images are small, secure, and reproducible.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [docker, containers, images, security]
---
## Purpose

A container image is the unit of deployment — its size, contents, and provenance determine how fast deploys are and how big the attack surface is. This skill is the checklist for building images that are small, secure, and reproducible.

## When to use it

When writing or modifying a Dockerfile, adding a new service image, or reviewing image builds for security or size.

## Steps / checklist

1. **Multi-stage builds.** Build in a fat stage (compilers, dev dependencies), copy only the runtime artifacts into a minimal final stage. The final image contains what runs, nothing more.
2. **Minimal base images.** Prefer distroless or slim base images over full distributions. Fewer packages means fewer CVEs and a smaller attack surface.
3. **Run as non-root.** The container runs as a non-root user with the least privileges it needs. No `USER root` in the final stage.
4. **Pin base images.** Pin base image tags (ideally by digest) so builds are reproducible. Unpinned `latest` makes today's build differ from last week's.
5. **Scan images.** Scan images for CVEs in CI (Trivy, Grype, etc.) and fail on critical/high findings. Scanning after deploy is too late.
6. **SBOM and provenance.** Generate an SBOM for production images so you can answer "what's in this image and where did it come from" during an incident or audit.
7. **Layer hygiene.** Order layers by change frequency (dependencies first, code last) to maximize cache reuse. Don't copy secrets or build args into layers that ship.
8. **Tag immutably.** Tag images with a unique, immutable identifier (commit SHA or digest) and promote that tag through environments — never retag a mutable `latest` and call it a release.

## Expected output

An image that is small enough to deploy fast, minimal enough to have a small attack surface, and reproducible enough that today's build equals last week's. If the image contains a compiler, a root user, or an unpinned base, it isn't done.