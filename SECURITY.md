# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 2.0.x | Yes |
| 1.x | No (legacy; replaced by 2.0) |

## What TempCleaner is

TempCleaner is a **local Windows utility** that permanently deletes files under a fixed set of allowlisted temp/cache paths. It is not a network service and does not sync data to the cloud.

## Threat model (local delete)

| Area | Behavior |
|------|----------|
| Destructive action | Permanent delete of children under allowlisted roots (not Recycle Bin) |
| Guardrails | GUI confirm + acknowledgment; CLI requires `--yes`; path allowlists; forbidden roots |
| Scheduled clean | Trusted path with no interactive confirm; only when enabled in settings; heavily logged |
| Privileges | Optional UAC elevation for system locations; elevation is explicit |
| Network | Optional GitHub Releases API check only; **no telemetry**, no auto-download of updates |
| Logging | Local log files under `%AppData%\TempCleaner\logs\` may contain paths |

### Residual risks (users should understand)

- Permanent delete cannot be undone via Recycle Bin.
- Running elevated increases what can be deleted under system targets.
- Enabling scheduled clean + elevated targets without reviewing selection can delete caches unattended.
- Malicious modification of `settings.json` or the scheduled task command could change what runs — protect your user account and review Task Scheduler entries named **TempCleaner Scheduled Clean**.
- Locked files fail with skip/error rather than elevating automatically mid-clean.

### What we intentionally do not claim

- Secure multi-user isolation beyond normal Windows ACLs
- Protection if an attacker already has full control of your user session
- Soft-delete recovery paths

## Reporting a vulnerability

Please **do not** open a public issue for security vulnerabilities that could enable unexpected mass deletion, privilege abuse, or path-escape beyond allowlists.

Prefer one of:

1. Private contact via the maintainer channels listed on [GitHub](https://github.com/Rulesmash/TempCleaner) (profile / security advisory if enabled).
2. If a private channel is unavailable, open a GitHub issue **without** exploit detail and request a private follow-up.

Include:

- TempCleaner version
- Windows version
- Description of the issue and impact
- Minimal reproduction steps
- Whether admin elevation is required

We will acknowledge reports as capacity allows and coordinate a fix before public disclosure when practical.

## Safe testing

- Use disposable directories and pytest `tmp_path` fixtures.
- Never aim automated tests at real `C:\Windows\*` contents.
- Prefer `--scan` / `--dry-run` when exploring on a real machine.
