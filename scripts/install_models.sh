#!/usr/bin/env bash
# ════════════════════════════════════════════════════════════════════════════
#  J.A.Y. Ollama Model Installer  —  Linux / macOS
#  Usage:
#    ./scripts/install_models.sh              # installs recommended set
#    ./scripts/install_models.sh --all        # installs everything (slow)
#    ./scripts/install_models.sh --minimal    # tiny models only (< 3 GB)
#    ./scripts/install_models.sh --custom     # interactive picker
#    ./scripts/install_models.sh --check      # show what's installed
# ════════════════════════════════════════════════════════════════════════════

set -euo pipefail

# ── Colours ──────────────────────────────────────────────────────────────────
RED='\033[0;31m';  GREEN='\033[0;32m';  CYAN='\033[0;36m'
YELLOW='\033[1;33m'; BOLD='\033[1m';    DIM='\033[2m';   NC='\033[0m'

# ── Model catalogue ───────────────────────────────────────────────────────────
# Format: "id|ram_gb|speed|purpose|tier"
# tier: minimal | recommended | optional
declare -a MODELS=(
  "llama3.2:3b|2.0|fast|Quick answers · voice replies · memory|minimal"
  "phi3:3.8b|2.3|fast|Fast reasoning · long context (128K)|minimal"
  "mistral:7b-instruct-q4_K_M|4.1|medium|General workhorse · trading · tools|recommended"
  "llama3.1:8b-instruct-q4_K_M|4.7|medium|Strong general AI · planning · 128K ctx|recommended"
  "deepseek-coder-v2:16b-lite-instruct-q4_K_M|4.9|medium|Best local code model|recommended"
  "codellama:7b-instruct-q4_K_M|3.8|medium|Code fallback (lighter)|recommended"
  "mixtral:8x7b-instruct-v0.1-q2_K|6.5|slow|Powerful MoE · heavy analysis|optional"
)

OLLAMA_URL="${OLLAMA_BASE_URL:-http://localhost:11434}"
RAM_BUDGET="${OLLAMA_RAM_BUDGET_GB:-7.0}"
MODE="${1:---recommended}"

# ── Helpers ───────────────────────────────────────────────────────────────────

print_header() {
  echo ""
  echo -e "${CYAN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${CYAN}${BOLD}║     J.A.Y.  Ollama Model Installer               ║${NC}"
  echo -e "${CYAN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
  echo ""
}

check_ollama() {
  if ! command -v ollama &>/dev/null; then
    echo -e "${RED}✗ Ollama not found.${NC}"
    echo -e "  Install it from: ${CYAN}https://ollama.ai/download${NC}"
    echo -e "  Linux one-liner:  ${DIM}curl -fsSL https://ollama.ai/install.sh | sh${NC}"
    exit 1
  fi

  if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
    echo -e "${YELLOW}⚠  Ollama is installed but not running.${NC}"
    echo -e "   Starting Ollama in the background…"
    ollama serve &>/dev/null &
    sleep 3
    if ! curl -sf "${OLLAMA_URL}/api/tags" >/dev/null 2>&1; then
      echo -e "${RED}✗ Could not start Ollama. Run 'ollama serve' manually.${NC}"
      exit 1
    fi
  fi
  echo -e "${GREEN}✓ Ollama running at ${OLLAMA_URL}${NC}"
}

get_installed() {
  curl -sf "${OLLAMA_URL}/api/tags" 2>/dev/null \
    | python3 -c "import sys,json; d=json.load(sys.stdin); print('\n'.join(m['name'] for m in d.get('models',[])))" \
    2>/dev/null || true
}

is_installed() {
  local model="$1"
  get_installed | grep -qF "$model"
}

ram_fits() {
  local model_ram="$1"
  python3 -c "import sys; sys.exit(0 if float('${model_ram}') <= float('${RAM_BUDGET}') else 1)" 2>/dev/null
}

pull_model() {
  local model="$1"
  local ram="$2"
  local purpose="$3"

  if is_installed "$model"; then
    echo -e "  ${GREEN}✓${NC} ${BOLD}${model}${NC} ${DIM}(already installed)${NC}"
    return 0
  fi

  if ! ram_fits "$ram"; then
    echo -e "  ${YELLOW}⚠${NC}  ${model} needs ${ram} GB but budget is ${RAM_BUDGET} GB — ${YELLOW}skipped${NC}"
    return 0
  fi

  echo -e "\n  ${CYAN}↓${NC}  Pulling ${BOLD}${model}${NC}  (${ram} GB · ${purpose})"
  if ollama pull "$model"; then
    echo -e "  ${GREEN}✓${NC}  ${model} installed successfully"
  else
    echo -e "  ${RED}✗${NC}  Failed to pull ${model}"
  fi
}

show_catalogue() {
  echo -e "\n${BOLD}Available models for 12 GB RAM:${NC}\n"
  printf "  %-52s %-6s %-8s %s\n" "Model ID" "RAM" "Speed" "Purpose"
  printf "  %-52s %-6s %-8s %s\n" "────────────────────────────────────────────────────" "────" "────────" "───────"
  for entry in "${MODELS[@]}"; do
    IFS='|' read -r id ram speed purpose tier <<< "$entry"
    local mark=" "
    is_installed "$id" && mark="${GREEN}✓${NC}"
    ! ram_fits "$ram" && mark="${YELLOW}!${NC}"
    local tier_color="${NC}"
    [[ "$tier" == "minimal"     ]] && tier_color="${GREEN}"
    [[ "$tier" == "recommended" ]] && tier_color="${CYAN}"
    [[ "$tier" == "optional"    ]] && tier_color="${DIM}"
    printf "  ${mark} %-50s %-6s %-8s " "$id" "${ram}GB" "$speed"
    echo -e "${tier_color}${purpose}${NC}"
  done
  echo ""
}

# ── Modes ─────────────────────────────────────────────────────────────────────

do_check() {
  echo -e "\n${BOLD}Installed models:${NC}"
  local installed
  installed=$(get_installed)
  if [[ -z "$installed" ]]; then
    echo -e "  ${YELLOW}None installed yet.${NC}"
  else
    while IFS= read -r m; do
      echo -e "  ${GREEN}✓${NC}  $m"
    done <<< "$installed"
  fi
  show_catalogue
}

do_minimal() {
  echo -e "\n${CYAN}Installing minimal set (< 3 GB each):${NC}"
  for entry in "${MODELS[@]}"; do
    IFS='|' read -r id ram speed purpose tier <<< "$entry"
    [[ "$tier" == "minimal" ]] && pull_model "$id" "$ram" "$purpose"
  done
}

do_recommended() {
  echo -e "\n${CYAN}Installing recommended set:${NC}"
  echo -e "${DIM}  (models that don't fit your ${RAM_BUDGET} GB budget will be skipped)${NC}\n"
  for entry in "${MODELS[@]}"; do
    IFS='|' read -r id ram speed purpose tier <<< "$entry"
    [[ "$tier" == "minimal" || "$tier" == "recommended" ]] && pull_model "$id" "$ram" "$purpose"
  done
}

do_all() {
  echo -e "\n${YELLOW}Installing ALL models (this will take a while):${NC}"
  for entry in "${MODELS[@]}"; do
    IFS='|' read -r id ram speed purpose tier <<< "$entry"
    pull_model "$id" "$ram" "$purpose"
  done
}

do_custom() {
  show_catalogue
  echo -e "${BOLD}Enter model IDs to install (space-separated), or press Enter to cancel:${NC}"
  read -r -p "> " choices
  if [[ -z "$choices" ]]; then
    echo "Cancelled."
    return
  fi
  for model in $choices; do
    # Find in catalogue
    local found=false
    for entry in "${MODELS[@]}"; do
      IFS='|' read -r id ram speed purpose tier <<< "$entry"
      if [[ "$id" == "$model" ]]; then
        pull_model "$id" "$ram" "$purpose"
        found=true
        break
      fi
    done
    if ! $found; then
      echo -e "  ${YELLOW}⚠${NC}  '$model' not in catalogue — pulling anyway"
      ollama pull "$model" && echo -e "  ${GREEN}✓${NC}  $model installed" || echo -e "  ${RED}✗${NC}  Failed"
    fi
  done
}

# ── Summary ───────────────────────────────────────────────────────────────────

print_summary() {
  echo ""
  echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════╗${NC}"
  echo -e "${GREEN}${BOLD}║          Model installation complete             ║${NC}"
  echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════╝${NC}"
  echo ""
  echo -e "${BOLD}Installed models:${NC}"
  local installed
  installed=$(get_installed)
  if [[ -z "$installed" ]]; then
    echo -e "  ${YELLOW}None${NC}"
  else
    while IFS= read -r m; do
      echo -e "  ${GREEN}✓${NC}  $m"
    done <<< "$installed"
  fi
  echo ""
  echo -e "${DIM}J.A.Y. will automatically choose the right model per task.${NC}"
  echo -e "${DIM}Start the backend: cd backend && uvicorn app.main:app --reload${NC}"
  echo ""
}

# ── Entry point ───────────────────────────────────────────────────────────────

print_header
check_ollama

case "$MODE" in
  --check)       do_check ;;
  --minimal)     do_minimal;    print_summary ;;
  --recommended) do_recommended; print_summary ;;
  --all)         do_all;        print_summary ;;
  --custom)      do_custom;     print_summary ;;
  *)
    echo -e "${YELLOW}Unknown option '$MODE'. Running recommended install.${NC}"
    do_recommended
    print_summary
    ;;
esac
