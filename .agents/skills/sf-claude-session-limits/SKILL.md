---
name: sf-claude-session-limits
description: Reports this Claude Code session's usage against its Claude.ai Pro/Max limits, the rolling 5-hour session window and the 7-day weekly window. Use when the user types /sf-claude-session-limits or asks how much of their usage, session, rate limit, or weekly quota is left, or when it resets.
metadata:
  skillforge:
    version: 1.0.0
    source: ./skills/claude-session-limits
---

# Claude session limits

Claude Code writes the latest `anthropic-ratelimit-*` values to a per-session state file. Read the
two windows from it and report each as percent used and when it resets:

```bash
state="${CLAUDE_CONFIG_DIR:-$HOME/.claude}/session-state/${CLAUDE_CODE_SESSION_ID:?not set}.json"
now=$(date +%s)
for w in five_hour seven_day; do
  pct=$(jq -r ".rate_limits.$w.used_percentage" "$state")
  reset=$(jq -r ".rate_limits.$w.resets_at" "$state")
  when=$(date -d "@$reset" '+%Y-%m-%d %H:%M %Z' 2>/dev/null || date -r "$reset" '+%Y-%m-%d %H:%M %Z')
  printf '%-10s %s%% used, resets %s (in %dh %dm)\n' \
    "$w" "$pct" "$when" $(( (reset - now) / 3600 )) $(( ((reset - now) % 3600) / 60 ))
done
```

`resets_at` is Unix seconds; `date -d` is GNU, `date -r` covers BSD/macOS.
