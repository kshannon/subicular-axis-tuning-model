#!/usr/bin/env bash
# Create a new experiment folder under experiments/ from the templates in templates/.
#
#   pixi run new-experiment --description "block building proposals"
#
# makes experiments/<YYYY-MM-DD-HHMM>-<slug>/ holding labnote.md, notebook.ipynb and figures/,
# with the front matter and the notebook's first cell filled in from the description,
# the clock and the git state.

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
EXPERIMENTS_DIR="$REPO_ROOT/experiments"
TEMPLATES_DIR="$REPO_ROOT/templates"

usage() {
    cat <<USAGE
usage: pixi run new-experiment --description "TEXT"

Create experiments/<YYYY-MM-DD-HHMM>-<slug>/ with labnote.md, notebook.ipynb and figures/.
The slug is the description in lower case with runs of other characters as hyphens.

  -d, --description TEXT   what the experiment is about (required)
  -h, --help               show this help
USAGE
}

description=""
while [ $# -gt 0 ]; do
    case "$1" in
        -d|--description)
            [ $# -ge 2 ] || { echo "error: $1 needs a value" >&2; usage >&2; exit 2; }
            description="$2"
            shift 2
            ;;
        --description=*)
            description="${1#--description=}"
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "error: unknown argument: $1" >&2
            usage >&2
            exit 2
            ;;
    esac
done

# Trim surrounding whitespace and collapse inner runs of it.
description="$(printf '%s' "$description" | tr -s '[:space:]' ' ' | sed -e 's/^ //' -e 's/ $//')"
if [ -z "$description" ]; then
    echo "error: --description is required" >&2
    usage >&2
    exit 2
fi

slug="$(printf '%s' "$description" | tr '[:upper:]' '[:lower:]' | tr -cs 'a-z0-9' '-' | sed -e 's/^-//' -e 's/-$//')"
if [ -z "$slug" ]; then
    echo "error: the description has no letters or digits to name the folder with" >&2
    exit 2
fi

stamp="$(date +%Y-%m-%d-%H%M)"
created="$(date +%Y-%m-%dT%H:%M:%S%z)"
name="$stamp-$slug"
target="$EXPERIMENTS_DIR/$name"

author="$(git -C "$REPO_ROOT" config user.name 2>/dev/null || true)"
[ -n "$author" ] || author="${USER:-unknown}"
commit="$(git -C "$REPO_ROOT" rev-parse --short HEAD 2>/dev/null || echo none)"
branch="$(git -C "$REPO_ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || echo none)"

for template in labnote.md notebook.ipynb; do
    [ -f "$TEMPLATES_DIR/$template" ] || { echo "error: missing template $TEMPLATES_DIR/$template" >&2; exit 1; }
done
if [ -e "$target" ]; then
    echo "error: $target already exists" >&2
    exit 1
fi

# Escape a value for the replacement side of sed with | as the delimiter.
sed_escape() {
    printf '%s' "$1" | sed -e 's/[\\&|]/\\&/g'
}

# Escape a value for the inside of a JSON string.
json_escape() {
    printf '%s' "$1" | sed -e 's/\\/\\\\/g' -e 's/"/\\"/g'
}

# render SOURCE DEST TITLE: substitute every {{FIELD}} in SOURCE and write DEST.
render() {
    sed \
        -e "s|{{TITLE}}|$(sed_escape "$3")|g" \
        -e "s|{{NAME}}|$(sed_escape "$name")|g" \
        -e "s|{{SLUG}}|$(sed_escape "$slug")|g" \
        -e "s|{{CREATED}}|$(sed_escape "$created")|g" \
        -e "s|{{DATE}}|$(sed_escape "${stamp%-*}")|g" \
        -e "s|{{AUTHOR}}|$(sed_escape "$4")|g" \
        -e "s|{{COMMIT}}|$(sed_escape "$commit")|g" \
        -e "s|{{BRANCH}}|$(sed_escape "$branch")|g" \
        "$1" > "$2"
}

mkdir -p "$target/figures"
touch "$target/figures/.gitkeep"
render "$TEMPLATES_DIR/labnote.md" "$target/labnote.md" "$description" "$author"
render "$TEMPLATES_DIR/notebook.ipynb" "$target/notebook.ipynb" "$(json_escape "$description")" "$(json_escape "$author")"

echo "created experiments/$name"
echo "  labnote.md"
echo "  notebook.ipynb"
echo "  figures/"
