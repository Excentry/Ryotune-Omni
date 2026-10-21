<!--
Title format: refactor|test|build|ci|chore|revert(scope): short description. See CONTRIBUTING.md#title-format.
-->

## What changed

<!-- What was restructured, added or removed, and why. For reverts: which commit/PR is reverted and why. -->

## Behaviour preservation

<!-- For refactors and test/CI changes: how behaviour was proven unchanged (same tests, same outputs). For build/chore: what stays identical for users. Write "Not applicable" for pure reverts. -->

## Scope and impact

- **Areas:** <!-- e.g. playback, provider, UI, CI, packaging, docs -->
- **Platforms affected and tested:** <!-- Include OS/version, or say not runtime-tested. -->

## Validation

- **Checks/scenarios run:** <!-- Include commands and results. -->
- **Not run:** <!-- Explain why, or write "None." -->

## Risks and follow-up

<!-- Note dependencies, deferred cleanup, or rollback needs. Write "None" if not applicable. -->

## Checklist

- [ ] Existing checks still pass, or skipped ones are explained above.
- [ ] No user-facing behaviour changed (or the change is declared in "What changed").
- [ ] No secrets or unrelated changes are included.
