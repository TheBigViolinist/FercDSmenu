# shellcheck shell=bash
# FercDS - utilitários do instalador: UI de terminal, perguntas, sudo e cópia
# de arquivos. Carregado pelo install.sh; não roda sozinho.

# --- CORES ---------------------------------------------------------------------
# Só em terminal de verdade e respeitando o NO_COLOR (https://no-color.org).
if [ -t 1 ] && [ -z "${NO_COLOR:-}" ]; then
    C_RESET=$'\e[0m' C_BOLD=$'\e[1m' C_DIM=$'\e[2m'
    C_RED=$'\e[31m' C_GREEN=$'\e[32m' C_YELLOW=$'\e[33m'
    C_BLUE=$'\e[34m' C_MAGENTA=$'\e[35m' C_CYAN=$'\e[36m'
else
    C_RESET='' C_BOLD='' C_DIM='' C_RED='' C_GREEN='' C_YELLOW=''
    C_BLUE='' C_MAGENTA='' C_CYAN=''
fi

LINHA='━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━'

# --- IDIOMA --------------------------------------------------------------------
# As mensagens ficam em installer/lang/<idioma>.sh, como MSG[chave]="texto".
# O en.sh carrega sempre primeiro: chave sem tradução sai em inglês.
# shellcheck disable=SC2034  # IDIOMAS e IDIOMA são usados pelo install.sh e steps.sh
IDIOMAS=(en pt es it)
IDIOMA=en
declare -gA MSG=()

carregar_idioma() {
    MSG=()
    # shellcheck source=installer/lang/en.sh
    source "$REPO_DIR/installer/lang/en.sh"
    if [ "$1" != en ]; then
        # shellcheck source=/dev/null
        source "$REPO_DIR/installer/lang/$1.sh"
    fi
    # shellcheck disable=SC2034
    IDIOMA=$1
}

idioma_valido() {
    case $1 in en|pt|es|it) return 0 ;; esac
    return 1
}

nome_idioma() {
    case $1 in
        en) echo "English" ;;
        pt) echo "Português" ;;
        es) echo "Español" ;;
        it) echo "Italiano" ;;
    esac
}

# t CHAVE [ARGS...] -> a mensagem no idioma escolhido, com os %s trocados pelos
# ARGS. Cada tradução tem exatamente os mesmos %s do en.sh.
t() {
    local fmt=${MSG[$1]-$1}
    shift
    # shellcheck disable=SC2059  # o formato vem dos arquivos de idioma
    printf -- "$fmt" "$@"
}

# --- SAÍDA ---------------------------------------------------------------------
cabecalho() {
    printf '%s%s%s\n' "$C_MAGENTA" "$LINHA" "$C_RESET"
    printf '  %sFercDS%s · %s  %s%s%s\n' "$C_BOLD" "$C_RESET" "$1" "$C_DIM" "$(versao_repo)" "$C_RESET"
    printf '  %s%s%s\n' "$C_DIM" "$(t ui.tagline)" "$C_RESET"
    printf '%s%s%s\n' "$C_MAGENTA" "$LINHA" "$C_RESET"
}
secao()   { printf '\n%s%s▌ %s%s\n' "$C_BOLD" "$C_MAGENTA" "$*" "$C_RESET"; }
info()    { printf '  %s•%s %s\n' "$C_BLUE" "$C_RESET" "$*"; }
ok()      { printf '  %s✔%s %s\n' "$C_GREEN" "$C_RESET" "$*"; }
aviso()   { printf '  %s!%s %s\n' "$C_YELLOW" "$C_RESET" "$*"; }
erro()    { printf '  %s✘%s %s\n' "$C_RED" "$C_RESET" "$*" >&2; }
detalhe() { printf '    %s%s%s\n' "$C_DIM" "$*" "$C_RESET"; }

limpar_tela() { [ -t 1 ] && printf '\e[H\e[2J'; return 0; }

# Mostra o comando (com as aspas certas) e roda.
executar() {
    local cmd
    printf -v cmd '%q ' "$@"
    printf '    %s$ %s%s\n' "$C_DIM" "${cmd% }" "$C_RESET"
    "$@"
}

# diff -u com cor, para o setup mostrar o que muda no hyprland.lua.
colorir_diff() {
    local l
    while IFS= read -r l; do
        case $l in
            '+++'*|'---'*) printf '    %s%s%s\n' "$C_BOLD" "$l" "$C_RESET" ;;
            '+'*)          printf '    %s%s%s\n' "$C_GREEN" "$l" "$C_RESET" ;;
            '-'*)          printf '    %s%s%s\n' "$C_RED" "$l" "$C_RESET" ;;
            '@@'*)         printf '    %s%s%s\n' "$C_CYAN" "$l" "$C_RESET" ;;
            *)             printf '    %s\n' "$l" ;;
        esac
    done
}

# --- PERGUNTAS -----------------------------------------------------------------
# ASSUME_YES=1 (--yes) aceita a resposta padrão de cada pergunta: as de [S/n]
# viram sim e as de [s/N] continuam não.
ASSUME_YES=${ASSUME_YES:-0}

# perguntar "texto" [S|N] -> 0 se a resposta for sim (S = o padrão é sim, N =
# o padrão é não). Lê do terminal mesmo com o stdin redirecionado; sem terminal
# (e sem --yes) a resposta é sempre não. Aceita sim em qualquer um dos idiomas.
perguntar() {
    local texto=$1 padrao=${2:-S} sim nao opcoes escolhido resp
    sim=$(t ui.yes_letter)
    nao=$(t ui.no_letter)
    if [ "$padrao" = S ]; then
        opcoes="${sim^^}/${nao,,}" escolhido=${sim^^}
    else
        opcoes="${sim,,}/${nao^^}" escolhido=${nao^^}
    fi
    if [ "$ASSUME_YES" = 1 ]; then
        printf '  %s?%s %s [%s] %s(--yes: %s)%s\n' "$C_CYAN" "$C_RESET" "$texto" "$opcoes" "$C_DIM" "$escolhido" "$C_RESET"
        [ "$padrao" = S ]
        return
    fi
    while true; do
        printf '  %s?%s %s [%s] ' "$C_CYAN" "$C_RESET" "$texto" "$opcoes"
        if ! { read -r resp </dev/tty; } 2>/dev/null; then
            printf '\n'
            aviso "$(t ask.no_tty)"
            return 1
        fi
        [ -z "$resp" ] && [ "$padrao" = S ] && return 0
        [ -z "$resp" ] && return 1
        case ${resp,,} in
            y|yes|s|sim|si|sí|sì) return 0 ;;
            n|no|nao|não) return 1 ;;
        esac
        aviso "$(t ask.invalid)"
    done
}

# Espera um Enter (só no modo menu).
pausar() {
    [ "$ASSUME_YES" = 1 ] && return 0
    printf '\n  %s%s%s' "$C_DIM" "$(t ui.press_enter)" "$C_RESET"
    { read -r _ </dev/tty; } 2>/dev/null || true
}

# --- VERSÃO --------------------------------------------------------------------
# Sem texto traduzido aqui: a versão também é gravada no sistema (VERSION).
versao_repo() {
    local v hash
    v=$(tr -d '[:space:]' 2>/dev/null <"$REPO_DIR/VERSION" || true)
    hash=$(git -C "$REPO_DIR" rev-parse --short HEAD 2>/dev/null) && v="$v+$hash"
    if git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 &&
        [ -n "$(git -C "$REPO_DIR" status --porcelain 2>/dev/null)" ]; then
        v="$v-dirty"
    fi
    printf 'v%s' "${v:-?}"
}

# --- SUDO ----------------------------------------------------------------------
# FERCDS_SUDO existe para os testes do instalador (vazio = roda direto).
SUDO=${FERCDS_SUDO-sudo}
SUDO_KEEPALIVE_PID=

# Pede a senha uma vez e mantém o sudo vivo até o instalador terminar
# (o makepkg sozinho pode passar dos 5 min do timeout padrão do sudo).
garantir_sudo() {
    [ -z "$SUDO" ] && return 0
    if ! $SUDO -n true 2>/dev/null; then
        info "$(t sudo.needed)"
        $SUDO -v || { erro "$(t sudo.failed)"; return 1; }
    fi
    if [ -z "$SUDO_KEEPALIVE_PID" ]; then
        ( while kill -0 "$$" 2>/dev/null; do $SUDO -n -v 2>/dev/null; sleep 50; done ) &
        SUDO_KEEPALIVE_PID=$!
    fi
}

# --- ARQUIVOS ------------------------------------------------------------------
# Cópia do arquivo antes de ser substituído, com o caminho original dentro do
# BACKUP_DIR (uma pasta por execução do instalador).
fazer_backup() {
    local f=$1 alvo="$BACKUP_DIR$1"
    mkdir -p "$(dirname "$alvo")"
    cp -p "$f" "$alvo" 2>/dev/null || $SUDO cat "$f" >"$alvo"
}

# estado_arquivo ORIGEM DESTINO -> "igual", "diferente" ou "ausente"
estado_arquivo() {
    if [ ! -e "$2" ]; then echo ausente
    elif cmp -s "$1" "$2"; then echo igual
    else echo diferente
    fi
}

# instalar_arquivo sistema|usuario "origem|destino|modo"
# Copia só o que mudou, guarda backup do que for substituído e anota o destino
# em $MUDADOS (o serviço usa isso para saber se precisa reiniciar).
instalar_arquivo() {
    local escopo=$1 origem destino modo src dst estado run=()
    IFS='|' read -r origem destino modo <<<"$2"
    src="$REPO_DIR/$origem"
    dst=$destino
    if [ "$escopo" = sistema ]; then
        dst="$ROOT$destino"
        [ -n "$SUDO" ] && run=("$SUDO")
    fi
    if [ ! -f "$src" ]; then
        erro "$(t file.missing_in_repo "$origem")"
        return 1
    fi

    estado=$(estado_arquivo "$src" "$dst")
    if [ "$estado" = igual ]; then
        if [ "$(stat -c %a "$dst")" != "$modo" ]; then
            "${run[@]}" chmod "$modo" "$dst"
        fi
        detalhe "$(t file.unchanged "$destino")"
        return 0
    fi
    if [ "$estado" = diferente ]; then
        fazer_backup "$dst"
    fi
    "${run[@]}" install -Dm"$modo" "$src" "$dst"
    echo "$destino" >>"$MUDADOS"
    if [ "$estado" = ausente ]; then ok "$(t file.installed "$destino")"; else ok "$(t file.updated "$destino")"; fi
}

# instalar_lista sistema|usuario ENTRADA... (para em qualquer erro)
instalar_lista() {
    local escopo=$1 entrada
    shift
    for entrada in "$@"; do
        instalar_arquivo "$escopo" "$entrada" || return 1
    done
}

# pendencias sistema|usuario ENTRADA... -> imprime "estado|ENTRADA" de cada
# arquivo que não está igual ao repo (estado: ausente ou diferente).
pendencias() {
    local escopo=$1 entrada origem destino modo dst estado
    shift
    for entrada in "$@"; do
        IFS='|' read -r origem destino modo <<<"$entrada"
        dst=$destino
        [ "$escopo" = sistema ] && dst="$ROOT$destino"
        estado=$(estado_arquivo "$REPO_DIR/$origem" "$dst")
        [ "$estado" != igual ] && echo "$estado|$entrada"
    done
    return 0
}

# Algum destino da lista mudou nesta execução?
mudou_algum() {
    local entrada origem destino modo
    [ -s "$MUDADOS" ] || return 1
    for entrada in "$@"; do
        IFS='|' read -r origem destino modo <<<"$entrada"
        grep -qxF "$destino" "$MUDADOS" && return 0
    done
    return 1
}

# --- PACOTES -------------------------------------------------------------------
# pacman -T também entende "provides" (ex.: ryzenadj-fercds fornece ryzenadj).
dep_satisfeita() { pacman -T "$1" >/dev/null 2>&1; }

# O wvkbd do FercDS é o que conhece a variável WVKBD_OUTPUT.
wvkbd_fercds_ok() {
    local bin
    bin=$(command -v wvkbd-mobintl) && grep -qa WVKBD_OUTPUT "$bin"
}

# Arquivo (e todas as pastas acima dele) do root e sem escrita para grupo ou
# outros: só um binário assim pode entrar numa regra de sudo sem senha.
seguro_para_sudo() {
    local p=$1
    while [ "$p" != / ]; do
        [ "$(stat -c %u "$p" 2>/dev/null)" = 0 ] || return 1
        (( (8#$(stat -c %a "$p") & 8#022) == 0 )) || return 1
        p=$(dirname "$p")
    done
}
