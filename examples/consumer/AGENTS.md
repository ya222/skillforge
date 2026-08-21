# Example app

A fictional TypeScript and React frontend, used to show what a consumer repository looks like
after `skillforge build`. This paragraph is hand-written and survives every rebuild; the
generated index below is replaced wholesale each time.

## Stack

- TypeScript, React, Tailwind
- `pnpm test` for tests, `pnpm bench` for benchmarks

<!-- skillforge:begin -->
## Agent skills

Read the linked file in full before acting on a skill. Load a skill when its description matches the task at hand.

- [`code-simplification`](.agents/skills/code-simplification/SKILL.md) — Simplifies code for clarity. Use when refactoring code for clarity without changing behavior. Use when code works but is harder to read, maintain, or extend than it should be. Use when reviewing code that has accumulated unnecessary complexity.
- [`frontend-ui-engineering`](.agents/skills/frontend-ui-engineering/SKILL.md) — Builds production-quality, accessible, responsive user-facing UIs. Use when building or modifying interfaces and pages, creating components, implementing layouts, meeting WCAG accessibility requirements, managing state, or when the output needs to look and feel production-quality rather than AI-generated.
- [`perf`](.agents/skills/perf/SKILL.md) — Optimizes application performance across frontend, backend, queries, and databases. Use when performance requirements exist, when you suspect performance regressions, when Core Web Vitals or load times need improvement, when N+1 query patterns need fixing, or when profiling reveals bottlenecks.
<!-- skillforge:end -->
