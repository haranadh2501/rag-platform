# Claude Code Token Usage — Admin UI

Date: 2026-06-02
Module: M8 Admin UI
Branch: feature/admin-UI

## Usage Summary


  Session

  Total cost:            $5.95
  Total duration (API):  26m 13s
  Total duration (wall): 19h 8m 20s
  Total code changes:    1865 lines added, 104 lines removed
  Usage by model:
     claude-sonnet-4-6:  10.8k input, 74.4k output, 12.9m cache read, 251.0k cache write ($5.95)

  Current session
  ████                                               8% used
  Resets 9pm (Asia/Calcutta)

  Current week (all models)
  ██                                                 4% used
  Resets Jun 6 at 12:30am (Asia/Calcutta)

  What's contributing to your limits usage?
  Approximate, based on local sessions on this machine — does not include other devices or claude.ai

  Last 24h · these are independent characteristics of your usage, not a breakdown

  Skills                  % of usage
  /frontend-checks                3%
  /admin-ui-phase                 2%
  /claude-api                     1%

  d to day · w to week

  Usage credits
  Usage credits are off · /usage-credits to turn them on
  

## Notes

- Used Admin-specific SDD files.
- Used custom skills: admin-ui-phase, frontend-checks.
- Used phase-based prompts to reduce token usage.
- Verified with typecheck, lint, and build.