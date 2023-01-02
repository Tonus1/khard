#!/bin/bash
# This add the bash completion for khard.
# To enable it copy this file in /etc/bash_completion.d/

_khard()
{
 
# local variables for current text and previous word 
    local cur prev
    COMPREPLY=()
    cur="${COMP_WORDS[COMP_CWORD]}"
    prev="${COMP_WORDS[COMP_CWORD-1]}"

# variables to use for completion
    opts="-a"

#  Complete the arguments to some of the basic commands.
    case "${prev}" in
        -a)
            COMPREPLY=( $(compgen -W "$( khard abooks )" -- ${cur}) )
            return 0
            ;;
        -A)
            COMPREPLY=( $(compgen -W "$( khard abooks )" -- ${cur}) )
            return 0
            ;;
         copy)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
         move)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
         merge)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
         edit)
            COMPREPLY=( $(compgen -W "${opts}" -- ${cur}) )
            return 0
            ;;
	*)
        ;;
    esac

# first the commands to be run after khard invocation
    COMPREPLY=( $( compgen -W 'add-email adddressbooks abooks birthdays bdays copy cp details show email filename file list ls merge modify edit ed move mv new add phone postaddress postaddr post remove rm del delete
            ' -- "$cur" ) ) 
    return 0
} &&
complete -F _khard khard
