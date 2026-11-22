# Live-Gate: Einrichten eines self-hosted Ollama-Runners

**Ziel:** Die `.github/workflows/ci-live.yml` wird aktiv. In GitHub Actions
soll jeder push auf `main` das Live-Gate lausfen, mit echtem Ollama
Embedding (default: `nomic-embed-text`) und Sichtbarem DELTA. In der
CI (nicht lokal) soll ein echtes **GO** (nicht CONDITIONAL) sichtbar werden.

## Voraussetzungen

1. **Ein 24/7 erreichbarer Linux-Machine/Server**
   (VM, Droplet, oder ein dedizierter Raspberry Pi mit Ollama).
   Muss `actions/runner` laufen koennen.
2. **Ollama** installiert + ein Embedding-Modell (default `nomic-embed-text`).
3. **Ein fein-granularer GitHub PAT** mit scope `workflow` + `repo`.
4. **Ein Ollama-Endpoint** der von dem Runner aus erreichbar ist.

## Ablauf (3 Schritte)

### Schritt 1 — den self-hosted Runner registrieren
Auf dem **Runner-Host** ausfuehren:

```bash
export GH_PAT="<feingranuliertes-PAT>"
export OWNER="GRADweight" REPO="prototypen" LABEL="gw-ollama"
./scripts/register-runner.sh --apply
```

Der Skript defaultet zum DRY-RUN. `--apply` aktiviert die
Regele, aber mit einer `CONFIRM`-Abfrage. Fuer Automatisierung:
`export APPLY=1; ./scripts/register-runner.sh`.

### Schritt 2 — Repo-Secrets setzen (auf dem Mac, lokal)

```bash
gh auth login   # falls noch nicht
gh secret set GW_INFER_URL   --repo GRADweight/prototypen --body "http://runner:11434"
gh secret set GW_INFER_EMBED --repo GRADweight/prototypen --body "nomic-embed-text"
# Falls der Runner NICHT bei localhost ist:
#   GW_INFER_URL = "http://<runner-ip>:11434"  (oder ein Reverse-Proxy auf
#   port 80/443 auf den Runner-Host)
```

Fuer ein privat-lauffendes Ollama muss man einen Reverse-Proxy
(Varnish/traefik) vorschalten, damit das Secret
`GW_INFER_URL=http://proxy:8080` zeigt.

### Schritt 3 — den Workflow aktivieren
`.github/workflows/ci-live.yml` unter `on:`:

```yaml
on:
  # INAKTIV:
  # workflow_dispatch:
  # AKTIV:
  push:
    branches: [main]
  pull_request:
```

## Verifikation

### Nach dem ersten push:
```bash
gh run list --repo GRADweight/prototypen --workflow protypen-live-gate \
  --limit 5 --json conclusion,head_branch,display_title

# Erwartet:
#   live-gate: 01-rag-chatbot  ->  ✅ GO
#   live-gate: 02-rechnungs-extraktion  ->  ✅ GO
#   live-gate: 03-email-triage  ->  ✅ GO
#
# Delta Report (im Log):
#   recall@3 demo=50%  prod=100%  Δ=+50 pts  -> RAG semantic win
#   recall@3 demo=100% prod=100% Δ=+0 pts  -> klassifiziert, kein LLM-lift noetig
#
# In der CI-Console sieht man:
#   → 01-rag-chatbot  VERDICT: ✅ GO  Δ=+50.0 pts
```

## Notizen

- **shared-lib ist oeffentlich.** Fuer den Live-Gate ist `vendor/` byte-identical
  v0.1.1 und reicht. Ein `SHARED_LIB_TOKEN` ist NICHT erforderlich.
- **Fail-loud:** falls Ollama nicht erreichbar ist, der Job rotiert
  (kein vorgetaucht GO).
- **Nur 5 min timeout** pro Job: ein Runner muss innerhalb von 5
  Minuten die Ollama-Warmup + 3 Prototypen durchlaufen
  (mit nomic-embed-text ~3 min, mit groesseren Modellen laenger).

## Kritische Fragen

1. **Welches Machine** laesst den 24/7-Runner? Mac Mini? Droplet? Docker?
2. **Welches Embedding-Modell** soll der Runner haben?
3. **Soll der CI-Live-Gate als PR-Required Check** sein
   (d.h. ein merge only fuer GO/CONDITIONAL)? Dann muesste im
   .github/settings/rules branch-protection aktiviert sein.
4. **Secret-Handling:** der PAT hat scope `workflow`
   + `repo`. Muss man dafuer ein separates
   PAT fuer CI-only verwenden?
