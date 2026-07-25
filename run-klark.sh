#!/usr/bin/env bash
set -uo pipefail

# ========= À CONFIGURER (2 valeurs) =========
JIRA_PROJECT_KEY="SCRUM"            # le préfixe de tes tickets (regarde un ticket: KLARK-1 -> "KLARK")
REPO_DIR="$HOME/projects/perso/lelouch/Klark"         # chemin ABSOLU vers ton dépôt Git klark
# ============================================

MAX_TICKETS=20                     # sécurité: nb max de tickets traités sur un run
PER_TICKET_TIMEOUT="30m"           # sécurité: temps max par ticket (protège ton quota, pas ton argent)
MAX_TURNS=60                       # sécurité: nb max d'étapes par ticket avant abandon
LOG_DIR="$REPO_DIR/.klark-agent/logs"
WT_DIR="$REPO_DIR/.klark-agent/worktrees"

command -v claude >/dev/null || { echo "❌ Claude Code introuvable (npm i -g @anthropic-ai/claude-code)"; exit 1; }
command -v git    >/dev/null || { echo "❌ git introuvable"; exit 1; }
[ -d "$REPO_DIR/.git" ]      || { echo "❌ '$REPO_DIR' n'est pas un dépôt Git. Corrige REPO_DIR."; exit 1; }

mkdir -p "$LOG_DIR" "$WT_DIR"
cd "$REPO_DIR"

git fetch origin --quiet
git remote set-head origin -a >/dev/null 2>&1 || true
BASE_BRANCH="$(git symbolic-ref --quiet --short refs/remotes/origin/HEAD 2>/dev/null | sed 's@^origin/@@')"
BASE_BRANCH="${BASE_BRANCH:-main}"
echo "▶ Dépôt : $REPO_DIR"
echo "▶ Branche de base : $BASE_BRANCH"
echo "▶ Projet Jira : $JIRA_PROJECT_KEY"

CLAUDE_FLAGS=(--dangerously-skip-permissions --max-turns "$MAX_TURNS" --output-format stream-json --verbose)

count=0
while [ "$count" -lt "$MAX_TICKETS" ]; do
  echo "──────────────────────────────────────────────"
  echo "🔎 Recherche du prochain ticket 'To Do' dans $JIRA_PROJECT_KEY ..."

  KEY="$(claude -p "Via l'outil Jira (MCP atlassian), trouve le prochain ticket du projet $JIRA_PROJECT_KEY au statut 'To Do', trié par priorité puis par ancienneté. Réponds UNIQUEMENT avec sa clé (ex: $JIRA_PROJECT_KEY-12) et rien d'autre. S'il n'y en a aucun, réponds exactement: NO_MORE_TICKETS" \
        --dangerously-skip-permissions --max-turns 15 --output-format text 2>/dev/null \
        | grep -oE "($JIRA_PROJECT_KEY-[0-9]+|NO_MORE_TICKETS)" | head -n1)"

  if [ -z "$KEY" ] || [ "$KEY" = "NO_MORE_TICKETS" ]; then
    echo "✅ Plus aucun ticket 'To Do'. Fin du run."
    break
  fi

  count=$((count+1))
  TS="$(date +%Y%m%d-%H%M%S)"
  LOG="$LOG_DIR/${KEY}-${TS}.log"
  BRANCH="agent/${KEY}"
  WT="$WT_DIR/$KEY"

  echo "🎫 Ticket #$count : $KEY  →  branche $BRANCH"
  echo "📄 Log en direct : $LOG"

  git worktree remove --force "$WT" 2>/dev/null || true
  git branch -D "$BRANCH" 2>/dev/null || true
  git worktree add -b "$BRANCH" "$WT" "origin/$BASE_BRANCH" >/dev/null

  (
    cd "$WT"
    timeout "$PER_TICKET_TIMEOUT" claude -p \
"Tu travailles sur le ticket Jira $KEY (projet $JIRA_PROJECT_KEY), sur la branche $BRANCH.
1. Passe le ticket $KEY au statut 'In Progress' via l'outil Jira.
2. Lis sa description et ses critères d'acceptation.
3. Implémente les changements dans CE dépôt (répertoire courant).
4. Lance les tests du projet et corrige jusqu'à ce qu'ils passent.
5. Fais un commit clair référençant $KEY, puis: git push -u origin $BRANCH
6. Ouvre une pull request EN BROUILLON: gh pr create --draft --fill --base $BASE_BRANCH (si 'gh' n'est pas installé, contente-toi de pousser la branche).
7. Commente le ticket $KEY avec le lien de la PR, puis passe-le au statut 'In Review' (ou 'Done' si aucun statut de revue n'existe).
Ne merge JAMAIS la PR toi-même." \
      "${CLAUDE_FLAGS[@]}" 2>&1 | tee "$LOG"
  )
  status=$?

  if [ "$status" -eq 124 ]; then echo "⏱️  $KEY : timeout ($PER_TICKET_TIMEOUT) atteint."
  elif [ "$status" -ne 0 ]; then echo "⚠️  $KEY : terminé avec le code $status (voir le log)."
  else echo "✔️  $KEY : terminé."; fi

  cd "$REPO_DIR"
  git worktree remove --force "$WT" 2>/dev/null || true
  sleep 3
done

echo "🏁 Run terminé : $count ticket(s) traité(s). Logs : $LOG_DIR"
