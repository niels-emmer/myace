---
name: App Store Readiness
description: Privacy manifest, code signing, capability declarations, screenshot automation, and review guideline checks.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, amazon-q, copilot-cli]
tags: [ios, app-store, release]
---
## Purpose

Avoid App Store rejections by checking every submission requirement before shipping.

## Checklist

- **Privacy manifest**: `PrivacyInfo.xcprivacy` complete with all collected data types and reasons declared.
- **Code signing**: valid distribution certificate and provisioning profile for the target environment.
- **Capabilities**: all required capabilities declared in the app's entitlements file and Apple Developer portal.
- **Screenshot automation**: screenshots for the sizes App Store Connect currently requires. The 6.9" iPhone set (1320 x 2868) is the baseline that scales down to smaller iPhones; a 6.5" set is only needed when no 6.9" set is supplied. Check Apple's Screenshot Specifications page before exporting, the list changes with each iPhone generation.
- **Review credentials**: no hardcoded test accounts or review-mode flags in the production build.
- **Guideline check**: review current App Store Review Guidelines for any changes affecting the app's category or features.
- **Metadata**: app description, keywords, and privacy URL updated to match the current release.

## Expected output

A build that passes all pre-submission checks and is ready for App Store upload without expected rejections.
