# ADL — npm publishing under foomakers

**Date:** 2026-10-29
**Status:** Accepted
**Type:** Non-architectural (ADL)
**Scope:** npm package names, release pipeline (#56, #28)

## Context

ADR-0002 named the content package `@gilberto/vault-bootstrap`. The npm org `gilberto` is not owned by the maintainer. pair is already published under `@foomakers`.

## Decision

| Artifact      | npm name                                          | Owner                 |
| ------------- | ------------------------------------------------- | --------------------- |
| CLI           | `gilberto` (unscoped, free; `npx gilberto` works) | foomakers org account |
| Vault content | `@foomakers/gilberto-vault-bootstrap`             | foomakers org         |

- Workspace `packages/vault-bootstrap` renames its `name` accordingly; imports and docs follow.
- Publish token: foomakers automation token as repo secret `NPM_TOKEN`.

## References

- [ADR-0002](../tech/adr/0002-distribution-and-dual-entry-bootstrap.md) — content package naming superseded here
