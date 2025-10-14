#!/bin/bash
# Poe the Poet bash completion for Watchtower project
# Source this file to enable tab completion for poetry run poe commands

# Enhanced completion function that works with both "poe" and "poetry run poe"
_poe_complete_enhanced() {
    local cur prev words
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    
    # Find the position of "poe" in the command line
    local poe_pos=-1
    for ((i=0; i < ${#COMP_WORDS[@]}; i++)); do
        if [[ "${COMP_WORDS[i]}" == "poe" ]]; then
            poe_pos=$i
            break
        fi
    done
    
    # If we found "poe" and we're at the task name position
    if [[ $poe_pos -ne -1 && $COMP_CWORD -eq $((poe_pos + 1)) ]]; then
        # Get task list from poe (need to be in the right directory)
        local tasks
        if command -v poetry >/dev/null 2>&1; then
            # Try with poetry first (for poetry run poe)
            tasks=$(cd "$(pwd)" && poetry run poe _list_tasks '' 2>/dev/null)
        fi
        
        # Fallback to direct poe if poetry didn't work
        if [[ -z "$tasks" ]] && command -v poe >/dev/null 2>&1; then
            tasks=$(poe _list_tasks '' 2>/dev/null)
        fi
        
        # Use hardcoded list as final fallback
        if [[ -z "$tasks" ]]; then
            tasks="lint fmt typecheck test cz commit-flow quick-commit"
        fi
        
        COMPREPLY=($(compgen -W "${tasks}" -- ${cur}))
        return 0
    fi
    
    # Handle global options if current word starts with -
    if [[ ${cur} == -* ]]; then
        local opts="--help --version --verbose --quiet --dry-run --directory --executor --ansi --no-ansi"
        COMPREPLY=($(compgen -W "${opts}" -- ${cur}))
        return 0
    fi
    
    return 0
}

# Register the completion function
complete -F _poe_complete_enhanced poe

# Also handle "poetry run poe" by completing after "poetry"
_poetry_complete_enhanced() {
    local cur prev
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"
    
    # If previous word was "poetry" and current starts with "run"
    if [[ "$prev" == "poetry" && "$cur" == "run"* ]]; then
        COMPREPLY=($(compgen -W "run" -- ${cur}))
        return 0
    fi
    
    # If we're in a "poetry run" context, delegate to poe completion
    if [[ "${COMP_WORDS[1]}" == "run" && "${COMP_WORDS[2]}" == "poe" ]]; then
        _poe_complete_enhanced
        return 0
    fi
    
    # Default poetry completion (if any)
    return 1
}

# Register poetry completion
complete -F _poetry_complete_enhanced poetry

echo "✅ Poe bash completion enabled!"
echo "Now you can use tab completion with:"
echo "  - poe q<TAB> → quick-commit"
echo "  - poetry run poe c<TAB> → commit-flow, cz"
echo "  - poetry run poe --<TAB> → --help, --version, etc."