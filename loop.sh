#!/bin/bash
# Ralphus - Autonomous Coding Loop for OpenCode
# Usage: ./loop.sh [plan] [ultrawork|ulw] [max_iterations]
# Examples:
#   ./loop.sh                  # Build mode, unlimited iterations
#   ./loop.sh 20               # Build mode, max 20 iterations
#   ./loop.sh plan             # Plan mode, unlimited iterations
#   ./loop.sh plan 5           # Plan mode, max 5 iterations
#   ./loop.sh ultrawork        # Build mode with ultrawork
#   ./loop.sh ulw 10           # Ultrawork build, max 10 iterations
#   ./loop.sh plan ultrawork   # Plan mode with ultrawork
#   ./loop.sh plan ulw 5       # Ultrawork plan, max 5 iterations

set -euo pipefail

# Configuration (override via environment variables)
AGENT="${RALPH_AGENT:-Sisyphus}"
OPENCODE="${OPENCODE_BIN:-opencode}"
ULTRAWORK=0

# Parse arguments
MODE="build"
PROMPT_FILE="PROMPT_build.md"
MAX_ITERATIONS=0

for arg in "$@"; do
    if [ "$arg" = "plan" ]; then
        MODE="plan"
        PROMPT_FILE="PROMPT_plan.md"
    elif [ "$arg" = "ultrawork" ] || [ "$arg" = "ulw" ]; then
        ULTRAWORK=1
    elif [[ "$arg" =~ ^[0-9]+$ ]]; then
        MAX_ITERATIONS=$arg
    fi
done

ITERATION=0
CURRENT_BRANCH=$(git branch --show-current 2>/dev/null || echo "unknown")

# Header
echo "=== RALPHUS: $MODE mode | $AGENT | $CURRENT_BRANCH ==="
[ "$ULTRAWORK" -eq 1 ] && echo "Ultrawork: enabled"
[ "$MAX_ITERATIONS" -gt 0 ] && echo "Max iterations: $MAX_ITERATIONS"

# Verify prompt file exists
if [ ! -f "$PROMPT_FILE" ]; then
    echo "Error: $PROMPT_FILE not found"
    exit 1
fi

# Build mode requires IMPLEMENTATION_PLAN.md
if [ "$MODE" = "build" ] && [ ! -f "IMPLEMENTATION_PLAN.md" ]; then
    echo "Error: IMPLEMENTATION_PLAN.md not found."
    echo "Run planning mode first: ./loop.sh plan"
    exit 1
fi

# Archive previous run if branch changed
LAST_BRANCH_FILE=".last-branch"
if [ -f "$LAST_BRANCH_FILE" ]; then
    LAST_BRANCH=$(cat "$LAST_BRANCH_FILE")
    if [ "$LAST_BRANCH" != "$CURRENT_BRANCH" ]; then
        ARCHIVE_DIR="archive/$(date +%Y-%m-%d)-$LAST_BRANCH"
        mkdir -p "$ARCHIVE_DIR"
        cp IMPLEMENTATION_PLAN.md "$ARCHIVE_DIR/" 2>/dev/null || true
        cp AGENTS.md "$ARCHIVE_DIR/" 2>/dev/null || true
        echo "Archived previous run to $ARCHIVE_DIR"
    fi
fi
echo "$CURRENT_BRANCH" > "$LAST_BRANCH_FILE"

# Graceful shutdown handler
SHUTDOWN=0
trap 'SHUTDOWN=1; echo -e "\n⚠ Shutdown requested. Finishing current iteration..."' INT TERM

# Main loop
while true; do
    # Check for shutdown request
    if [ "$SHUTDOWN" -eq 1 ]; then
        echo "Shutting down gracefully."
        exit 0
    fi

    # Check iteration limit
    if [ "$MAX_ITERATIONS" -gt 0 ] && [ "$ITERATION" -ge "$MAX_ITERATIONS" ]; then
        echo "Reached max iterations: $MAX_ITERATIONS"
        break
    fi

    ITERATION=$((ITERATION + 1))
    echo -e "\n======================== ITERATION $ITERATION ========================\n"

    if [ "$ULTRAWORK" -eq 1 ]; then
        MESSAGE="Read the attached prompt file and execute the instructions. ulw"
    else
        MESSAGE="Read the attached prompt file and execute the instructions"
    fi

    # Run OpenCode with the prompt file
    OUTPUT=$("$OPENCODE" run --agent "$AGENT" -f "$PROMPT_FILE" -- "$MESSAGE" 2>&1 | tee /dev/stderr) || true

    # Check completion signals
    if echo "$OUTPUT" | grep -q "<promise>PHASE_COMPLETE</promise>"; then
        if [ "$MODE" = "plan" ]; then
            echo "=== PLANNING COMPLETE ===" && exit 0
        else
            echo "=== PHASE COMPLETE - next iteration ==="
        fi
    fi
    if echo "$OUTPUT" | grep -q "<promise>COMPLETE</promise>"; then
        echo "=== ALL TASKS COMPLETE ===" && exit 0
    fi
    if echo "$OUTPUT" | grep -q "<promise>BLOCKED:"; then
        echo "=== BLOCKED ===" && echo "$OUTPUT" | grep -o "<promise>BLOCKED:[^<]*</promise>" && exit 1
    fi

    # Push changes after each iteration (if in a git repo)
    if git rev-parse --git-dir > /dev/null 2>&1; then
        git push origin "$CURRENT_BRANCH" 2>/dev/null || {
            echo "Note: Failed to push. Creating remote branch..."
            git push -u origin "$CURRENT_BRANCH" 2>/dev/null || echo "Warning: Could not push to remote"
        }
    fi
done

echo "=== Loop finished after $ITERATION iterations ==="