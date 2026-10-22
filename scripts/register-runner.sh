#!/usr/bin/env bash
# register-runner.sh — Bootstrap ein self-hosted github Runner fuer prototypen.
#
# AKTIVIERUNG des Live-Gates (ci-live.yml). DEFAULT: DRY-RUN.
# Real-Aktion (--apply) ist ein NICHT-UMKEHREBARER INFRASTRUKTUR-SCHLITT
# (laedt github actions/setup-runner, erzeugt ein GitHub token,
# meldet den Runner beim GitHub-Runner-Server). Dient als Blueprint.
#
# Voraussetzungen:
#   - ein Linux-Machine (VM/server), die 24/7 erreichbar ist
#   - Ollama installiert + ein Embedding-Modell (default: nomic-embed-text)
#   - ein `github_pat` mit scope `workflow` + `repo`
#   - ein Repo-Secret `GW_INFER_URL` + `GW_INFER_EMBED`
#
# Ablauf (3 Schritte fuer einen vollstandigen Aktivierung):
#
#   1. AUF DEM RUNNER:
#        - Ollama installiert
#        - `actions/runner`-Agenten installiert und als service geladen
#        - `actions/runner` meldet sich beim GitHub Actions Server mit
#          einem feingranulierten PAT (scope workflow)
#        - Label `gw-ollama` wird beim Register-Call gesetzt
#
#   2. REPO SECRETS (via GitHub web UI oder `gh secret set`):
#        GH_PAT="<PAT>" ./scripts/register-runner.sh --token ${GH_PAT} \
#          --owner GRADweight --repo prototypen --label gw-ollama
#      Dann:
#        gh secret set GW_INFER_URL  --repo GRADweight/prototypen --body "http://runner:11434"
#        gh secret set GW_INFER_EMBED --repo GRADweight/prototypen --body "nomic-embed-text"
#
#   3. AKTIVIERUNG:
#        in .github/workflows/ci-live.yml unter "on:" die
#        `workflow_dispatch:` Zeile auf `push:` / `pull_request:` umstellen
#        (im CI-live.yml ist das als Kommentar hinterlegt)
#
# DRY-RUN (DEFAULT --apply nicht gesetzt): nur die Befehle ausgeben,
# NICHTS AUF DEM SYSTEM AENDERN.
#
# Beispiel:
#   ./scripts/register-runner.sh --apply            # real register (NEIN default)
#   ./scripts/register-runner.sh                    # DRY-RUN
#

set -euo pipefail

# --- Args ---
OWNER="${OWNER:-GRADweight}"
REPO="${REPO:-prototypen}"
LABEL="${LABEL:-gw-ollama}"
APPLY="${APPLY:-0}"
RUNNER_URL="${RUNNER_URL:-https://github.com/${OWNER}/${REPO}/settings/actions/runners/new}"
GH_PAT="${GH_PAT:-}"

DRY=1
[[ "${APPLY}" = "1" ]] && DRY=0
[[ -f /dev/stdin && -t 0 ]] && echo "[INFO] interactive terminal detected. Use --apply for real registration."

# --- Pre-Checks ---
echo "=== pre-flight ==="
for dep in curl ollama; do
  if command -v "$dep" >/dev/null 2>&1; then
    version=$("$dep" --version 2>/dev/null | head -1 || echo "installed")
    echo "  [OK]  $dep: $version"
  else
    echo "  [WARN] $dep not found in \$PATH"
  fi
done

# Ollama: check that at least one model exists
echo "=== Ollama check ==="
if curl -fsS --max-time 5 http://localhost:11434/api/tags >/dev/null 2>&1; then
  echo "  [OK]  Ollama reachable at localhost:11434"
  echo "  Models:"
  curl -fsS http://localhost:11434/api/tags 2>/dev/null | \
    python3 -c "import sys,json; d=json.load(sys.stdin); [print('   -',m.get('name')) for m in d.get('models',[])]" 2>/dev/null || \
    echo "   (parse failed or no models installed)"
else
  echo "  [WARN] Ollama not reachable at localhost:11434. Start it:  ollama serve"
fi

# Check for embedding model
if [[ "${GW_INFER_EMBED:-nomic-embed-text}" != "nomic-embed-text" ]]; then
  echo "  [WARN] GW_INFER_EMBED=$GW_INFER_EMBED. Default is nomic-embed-text."
fi

# --- Registration ---
echo
echo "=== github-runner registration ==="
echo "  Target:    $RUNNER_URL"
echo "  Owner/Repo: $OWNER/$REPO"
echo "  Label:     $LABEL"
if [ -z "${GH_PAT:-}" ]; then echo "  PAT:       (unset)"; else echo "  PAT:       (set, len $(printf '%s' "$GH_PAT" | wc -c))"; fi
echo "  APPLY:     $APPLY  (DRY-RUN: $DRY)"

if [[ "${DRY}" = "1" || ! "$APPLY" = "1" ]]; then
  echo
  echo "=== DRY-RUN -- no system modification ==="
  echo
  cat <<'EOF'
Aktionen im REAL-Ablauf (nicht ausgefuehrt):

  1. GitHub PAT mit scope workflow + repo pruefen:
       curl -sf https://api.github.com/repos/${OWNER}/${REPO} \
        -H "Authorization: Bearer ${GH_PAT}" >/dev/null \
        && echo "PAT OK"

  2. Runner-Tokens vom GitHub API auslesen:
       TOKEN_B64=$( \
         curl -fsS "https://api.github.com/repos/${OWNER}/${REPO}/actions/runners/registration-token" \
           -H "Authorization: Bearer ${GH_PAT}" \
         | python3 -c "import sys,json; print(json.load(sys.stdin)['token'])"
       )

  3. Runner-Agent installieren und als service starten:
       ./config.sh --url "https://github.com/${OWNER}/${REPO}" \
                   --token "$TOKEN_B64" \
                   --labels "$LABEL" \
                   --run-name "gw-ollama" &
       ./run.sh &
       # Fuer Ubuntu/Debian:
       # sudo ./svc-installer.sh --user $(whoami)  # als systemctl

  4. Repo secrets fuer den Live-Gate setzen:
       gh secret set GW_INFER_URL  --repo ${OWNER}/${REPO} --body "http://localhost:11434"
       gh secret set GW_INFER_EMBED --repo ${OWNER}/${REPO} --body "nomic-embed-text"
       # Falls der Runner NICHT localhost ist:
       #   http://runner:11434  (oder die runner-IP/Hostname)

  5. Aktivierung:
       - im .github/workflows/ci-live.yml unter "on:" von workflow_dispatch
         auf push/pull_request umstellen (Kommentar im ci-live.yml)

  6. Test-Ausfuehrung:
       gh workflow run protypen-live-gate --repo ${OWNER}/${REPO}
       gh run list --repo ${OWNER}/${REPO} --workflow protypen-live-gate --limit 5

EOF
  exit 0
fi

# --- REAL (nicht default) ---
echo "!!! APPLY MODE: this WILL register a self-hosted runner !!!"
read -r -p "Type CONFIRM to proceed: " CONFIRM
[ "$CONFIRM" = "CONFIRM" ] || { echo "aborted."; exit 1; }

[ -z "$GH_PAT" ] && { echo "::error::GH_PAT not set"; exit 1; }

echo "=== step 1: check PAT ==="
curl -fsS "https://api.github.com/repos/${OWNER}/${REPO}" \
  -H "Authorization: Bearer $GH_PAT" >/dev/null && echo "  PAT OK"

echo "=== step 2: get runner-registration token ==="
TOKEN_B64=$(curl -fsS "https://api.github.com/repos/${OWNER}/${REPO}/actions/runners/registration-token" \
  -H "Authorization: Bearer $GH_PAT" \
  | python3 -c "import sys, json; print(json.load(sys.stdin)['token'])")
echo "  runner-token: ${TOKEN_B64:0:12}..."

echo "=== step 3: install & register runner agent ==="
# This is the REAL point of execution.
DIR="./actions-runner"
[ ! -d "$DIR" ] && {
  echo "  cloning github runner..."
  git clone https://github.com/actions/runner $DIR
}
cd "$DIR"
./config.sh --url "https://github.com/${OWNER}/${REPO}" \
            --token "$TOKEN_B64" \
            --labels "$LABEL" \
            --run-name "gw-ollama"
echo "!! runner config done. Start with: ./run.sh or ./svc-installer.sh"
echo "!! do NOT start it without confirming it is reachable on the same network"
echo
echo "!!! SETUP COMPLETE. !!!"
echo "Next: activate on:push in .github/workflows/ci-live.yml"
echo "     test: gh workflow run protypen-live-gate --repo ${OWNER}/${REPO}"
