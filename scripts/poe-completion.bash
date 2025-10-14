#!/bin/bash
# Poe the Poet bash completion script for Watchtower project

_poe_completion() {
    local cur prev opts
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

    # Check if we're completing after "poetry run poe" or just "poe"
    local poe_pos=-1
    for ((i=0; i < ${#COMP_WORDS[@]}; i++)); do
        if [[ "${COMP_WORDS[i]}" == "poe" ]]; then
            poe_pos=$i
            break
        fi
    done

    # If poe found and we're at the right position for task name
    if [[ $poe_pos -ne -1 && $COMP_CWORD -eq $((poe_pos + 1)) ]]; then
        # List of available Poe tasks for Watchtower
        opts="lint fmt typecheck test cz commit-flow quick-commit"
        COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
        return 0
    fi

    # Handle global options
    if [[ ${cur} == -* ]]; then
        opts="--help --version --verbose --quiet --dry-run --directory --executor --ansi --no-ansi"
        COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
        return 0
    fi
}

# Register completion for both "poe" and when used with poetry
complete -F _poe_completion poe
complete -F _poe_completion poetry