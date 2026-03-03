#!/usr/bin/env bash
# block-dangerous-commands.sh — PreToolUse hook for Bash tool calls
#
# Reads the tool input JSON from stdin, extracts the command string,
# and checks it against blocked patterns. Prints a warning to stderr
# for any match.
#
# Behavior: SOFT WARNING (exit 0 always — command still runs)
# To switch to hard block, change "exit 0" to "exit 2" in the block()
# function below.

set -euo pipefail

# ── Read tool input ──────────────────────────────────────────────────
INPUT=$(cat)
CMD=$(echo "$INPUT" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data.get('tool_input', {}).get('command', ''))
" 2>/dev/null || echo "")

if [[ -z "$CMD" ]]; then
  exit 0
fi

# ── Warning handler ──────────────────────────────────────────────────
# Change "exit 0" to "exit 2" below to hard-block instead of warn.
block() {
  echo "⚠️  DANGEROUS COMMAND DETECTED: $1" >&2
  echo "    Command: $CMD" >&2
  exit 0
}

# ── 1. Destructive git operations ────────────────────────────────────

# Force push (--force or -f flag on push)
if echo "$CMD" | grep -qE 'git\s+push\b' && echo "$CMD" | grep -qE '(--force\b|-f\b)'; then
  block "git force push can overwrite remote history"
fi

# Hard reset
if echo "$CMD" | grep -qE 'git\s+reset\s+--hard'; then
  block "git reset --hard discards all uncommitted changes"
fi

# Branch delete (-D or -d)
if echo "$CMD" | grep -qE 'git\s+branch\s+-[dD]'; then
  block "git branch delete"
fi

# Checkout discard (git checkout -- . or git restore .)
if echo "$CMD" | grep -qE 'git\s+checkout\s+--\s+\.' ; then
  block "git checkout -- . discards all working tree changes"
fi
if echo "$CMD" | grep -qE 'git\s+restore\s+\.' ; then
  block "git restore . discards all working tree changes"
fi

# Clean untracked files
if echo "$CMD" | grep -qE 'git\s+clean\s+-[a-zA-Z]*f'; then
  block "git clean -f deletes untracked files permanently"
fi

# ── 2. Push to main/master ───────────────────────────────────────────

if echo "$CMD" | grep -qE 'git\s+push\b' && echo "$CMD" | grep -qE '\b(main|master)\b'; then
  block "direct push to main/master — use a feature branch + PR"
fi

# ── 3. Destructive file operations ───────────────────────────────────

# Any recursive rm (rm -r, rm -rf, rm -fr, etc.)
if echo "$CMD" | grep -qE '\brm\s+-[a-zA-Z]*(r|R)[a-zA-Z]*\b'; then
  block "recursive rm can delete entire directory trees"
fi

# rm with broad glob patterns
if echo "$CMD" | grep -qE '\brm\s+.*\*\.\w+'; then
  block "rm with glob wildcard can delete many files at once"
fi

# ── 4. Pipe-to-shell (remote code execution) ─────────────────────────

if echo "$CMD" | grep -qE '(curl|wget)\s+.*\|\s*(bash|sh|zsh|python|perl)'; then
  block "piping remote content to shell executes untrusted code"
fi

# ── 5. Package publishing ────────────────────────────────────────────

if echo "$CMD" | grep -qE '(pip|twine)\s+upload'; then
  block "package publishing to PyPI"
fi
if echo "$CMD" | grep -qE 'npm\s+publish'; then
  block "package publishing to npm"
fi

# ── 6. Reading secrets / sensitive files ─────────────────────────────

if echo "$CMD" | grep -qE '(cat|less|more|head|tail|bat)\s+.*\.(env|pem|key)\b'; then
  block "reading potentially sensitive file (.env / .pem / .key)"
fi
if echo "$CMD" | grep -qiE '(cat|less|more|head|tail|bat)\s+.*(credentials|secret|token|password)'; then
  block "reading file with sensitive name (credentials/secret/token)"
fi

# ── 7. System-level commands ─────────────────────────────────────────

if echo "$CMD" | grep -qE '\bchmod\b'; then
  block "chmod modifies file permissions"
fi
if echo "$CMD" | grep -qE '\bchown\b'; then
  block "chown modifies file ownership"
fi
if echo "$CMD" | grep -qE '\b(kill|pkill|killall)\b'; then
  block "kill/pkill can terminate running processes"
fi
if echo "$CMD" | grep -qE '\bmkfs\b'; then
  block "mkfs creates a filesystem (destructive)"
fi
if echo "$CMD" | grep -qE '\bdd\b\s+'; then
  block "dd can overwrite disks and devices"
fi
if echo "$CMD" | grep -qE '\bsudo\b'; then
  block "sudo runs commands with elevated privileges"
fi

# ── All clear ─────────────────────────────────────────────────────────
exit 0
