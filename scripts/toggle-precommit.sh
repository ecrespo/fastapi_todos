#!/bin/bash
# Script to toggle pre-commit hooks on/off

HOOK_FILE=".git/hooks/pre-commit"

if [ -f "$HOOK_FILE" ]; then
    # Hooks are installed, disable them
    mv "$HOOK_FILE" "$HOOK_FILE.disabled"
    echo "✓ Pre-commit hooks disabled"
    echo "  To re-enable: ./scripts/toggle-precommit.sh"
else
    if [ -f "$HOOK_FILE.disabled" ]; then
        # Hooks were disabled, re-enable them
        mv "$HOOK_FILE.disabled" "$HOOK_FILE"
        echo "✓ Pre-commit hooks enabled"
        echo "  To disable: ./scripts/toggle-precommit.sh"
    else
        # Hooks not installed
        echo "Pre-commit hooks not found."
        echo "Install them with: uv run pre-commit install"
    fi
fi