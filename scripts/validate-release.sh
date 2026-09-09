#!/usr/bin/env bash

set -euo pipefail

release_root="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$release_root"

python3 -m json.tool .claude-plugin/plugin.json >/dev/null
python3 -m json.tool .claude-plugin/marketplace.json >/dev/null
python3 -m json.tool skills.sh.json >/dev/null

if command -v agentskills >/dev/null 2>&1; then
  skill_validator=(agentskills)
elif command -v uvx >/dev/null 2>&1; then
  skill_validator=(uvx --from skills-ref==0.1.1 agentskills)
else
  echo "Install skills-ref 0.1.1 or uv before validating the Agent Skills schema." >&2
  exit 1
fi

for skill_dir in skills/*; do
  "${skill_validator[@]}" validate "$skill_dir"
done

skills_output="$(npx --yes skills@1.5.23 add . --agent codex --list 2>&1)"
printf '%s\n' "$skills_output"
grep -Fq "Found 4 skills" <<<"$skills_output"

for skill_name in \
  remote-training-monitor \
  remote-job-watchdog \
  remote-job-phase-gate \
  remote-job-watch-and-fix; do
  grep -Fq "$skill_name" <<<"$skills_output"
done

npx --yes @anthropic-ai/claude-code@2.1.237 plugin validate --strict .
git diff --check

printf '%s\n' "Release validation passed."
