#!/usr/bin/env sh
set -eu

repo_root() {
    pwd
}

run_git() {
    git -c "safe.directory=$(repo_root)" "$@"
}

hook_dir() {
    case "$0" in
        */*) printf "%s\n" "${0%/*}" ;;
        *) printf ".\n" ;;
    esac
}

find_python() {
    if command -v python >/dev/null 2>&1 && python --version >/dev/null 2>&1; then
        printf "%s\n" "python"
        return 0
    fi

    if command -v python3 >/dev/null 2>&1 && python3 --version >/dev/null 2>&1; then
        printf "%s\n" "python3"
        return 0
    fi

    if command -v py >/dev/null 2>&1 && py -3 --version >/dev/null 2>&1; then
        printf "%s\n" "py -3"
        return 0
    fi

    return 1
}

run_python_checks_if_possible() {
    python_cmd=$(find_python || true)
    if [ -z "${python_cmd}" ]; then
        echo "Skipping Python checks: no runnable Python was found." >&2
        echo "GitHub Actions still runs the full strict quality gate." >&2
        return 0
    fi

    # Local hooks run the portable subset. CI enforces Python 3.14, uv 0.8,
    # Ruff 0.15, and the full formatter/linter checks.
    $python_cmd scripts/check_all.py --skip-tool-versions --skip-commits --skip-ruff
}

run_ruff_if_possible() {
    if ! command -v ruff >/dev/null 2>&1; then
        echo "Skipping Ruff checks: ruff is not on PATH." >&2
        echo "GitHub Actions still runs pinned ruff==0.15.20." >&2
        return 0
    fi

    ruff format --check .
    ruff check .
}

validate_conventional_subject() {
    subject=$1

    case "${subject}" in
        *": "*) ;;
        *) return 1 ;;
    esac

    prefix=${subject%%: *}
    description=${subject#*: }

    if [ -z "${prefix}" ] || [ -z "${description}" ]; then
        return 1
    fi

    case "${prefix}" in
        *!)
            prefix=${prefix%!}
            ;;
    esac

    type=${prefix}
    scope=
    case "${prefix}" in
        *"("*")")
            type=${prefix%%(*}
            scope=${prefix#*(}
            scope=${scope%)}
            if [ -z "${scope}" ]; then
                return 1
            fi
            case "${scope}" in
                *[!abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._/-]*)
                    return 1
                    ;;
            esac
            ;;
        *"("* | *")"*)
            return 1
            ;;
    esac

    case "${type}" in
        [abcdefghijklmnopqrstuvwxyz]*) ;;
        *) return 1 ;;
    esac

    case "${type}" in
        *[!abcdefghijklmnopqrstuvwxyz0123456789-]*) return 1 ;;
    esac

    return 0
}

validate_commit_message_file() {
    message_file=$1
    subject=

    while IFS= read -r line || [ -n "${line}" ]; do
        case "${line}" in
            "" | \#*) continue ;;
            *)
                subject=${line}
                break
                ;;
        esac
    done <"${message_file}"

    if validate_conventional_subject "${subject}"; then
        return 0
    fi

    echo "Commit message must follow Conventional Commits v1.0.0." >&2
    echo "Expected: <type>[optional scope][optional !]: <description>" >&2
    echo "Example: feat(search): add catalog indexing" >&2
    echo "Actual: ${subject}" >&2
    return 1
}
