---
name: Play Store Readiness
description: App signing, keystore management, API level targeting, privacy policy, and review guideline checks.
version: "1.0.0"
priority: 55
compatibility: [opencode, claude-code, cursor, codex-cli, windsurf, aider, cline, continue-dev, goose, cody, amazon-q]
tags: [android, play-store, release]
---
## Purpose

Avoid Play Store rejections by checking every submission requirement before shipping.

## Checklist

- **App signing**: Play App Signing or upload key configured. Keystore backed up securely, not in the repo.
- **API level targeting**: `targetSdkVersion` and `compileSdkVersion` match current Play Store requirements (target latest API level within one year of release).
- **Privacy policy**: published and linked in the Play Store listing and within the app. Covers all data collection declared in the manifest.
- **Content rating**: completed Play Console content rating questionnaire for the current feature set.
- **Permissions**: only requested permissions are used. No overbroad permission declarations. Runtime permission requests are handled gracefully.
- **Review guidelines**: check current Play Store Developer Program Policies for changes affecting the app's category or monetization model.

## Expected output

A build that passes all pre-submission checks and is ready for Play Store upload without expected rejections.
