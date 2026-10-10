# Agent Instructions

## Process safety (Windows / PowerShell)

- **Do NOT run `Stop-Process` (or `taskkill`) against `node` (or `python`) processes without a specific target.**
  A bare `Get-Process node | Stop-Process -Force` will kill the DeepSeek Harness (`dsh`) web server and other tooling, because they are Node processes. This hangs the session and the tool result never comes back.
- If you need to free a port or stop a dev server:
  - Find the specific process first (`Get-NetTCPConnection -LocalPort <port>` or `Get-Process` with an explicit `-Id`).
  - Stop **only that exact PID**, never all `node`/`python` processes.
  - Never target `$PID` of the current shell, and never kill the process running `dsh`/`claude` (port 3080 / `node` hosting `dsh web`).
- When in doubt about whether a process is harness-owned, prefer stopping the specific port's listener rather than a blanket process kill.

## Long-running commands

- PowerShell commands get up to 5 minutes by default (15 min cap) before the harness times them out.
- For anything likely to run longer (builds, servers, long scripts), run it with `run_in_background: true` and poll with `job_output` instead of blocking.
