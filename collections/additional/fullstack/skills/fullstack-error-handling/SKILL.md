---
name: Full-Stack Error Handling
description: Error propagation patterns — backend error shape to API response to frontend fetch wrapper to UI state.
version: "1.0.0"
priority: 50
compatibility: [opencode, claude-code, cursor]
tags: [fullstack, errors, error-handling]
---
## Purpose

Ensure every backend error reaches the frontend UI correctly, with no unhandled error states.

## When to use it

Designing or reviewing any feature that involves frontend-backend communication.

## Checklist

- **Backend error envelope**: standardize on `{ "error": { "code": "...", "message": "...", "details": [...] } }`.
- **Frontend fetch wrapper**: parse the error envelope and throw typed errors, not generic exceptions.
- **Component-level handling**: map `error.code` to specific UI treatment — validation errors show field messages, not-found redirects, server errors show retry option.
- **No unhandled states**: every data-fetching component has loading, empty, error, and success states.
- **Consistency**: same error shape across all endpoints; same error handling pattern across all components.

## Expected output

A consistent error propagation chain where every backend failure mode has a corresponding frontend UI treatment.
