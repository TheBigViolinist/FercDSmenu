#!/usr/bin/env bash
# FercDS - instalador, updater e setup.
#
# uso: ./install.sh [install|update|setup|status] [--yes] [--no-git] [--lang en|pt|es|it]
#
#   (nada)    abre o menu
#   install   instala tudo, etapa por etapa, pedindo confirmação em cada uma
#   update    confere os pacotes, troca os arquivos instalados pelos deste repo
#             e atualiza/ativa o serviço e o sudoers
#   setup     liga o FercDS no hyprland.lua (só completa o que faltar)
#   status    mostra o que está instalado e o que está diferente do repo
#
#   --yes     aceita a resposta padrão de todas as perguntas
#   --no-git  no update, não procura versão nova no GitHub
#   --lang    idioma do instalador, sem perguntar
#
# A primeira coisa que o instalador faz é perguntar o idioma (inglês, português,
# espanhol ou italiano); os textos ficam em installer/lang. Rode como o seu
# usuário (sem sudo): o instalador pede a senha quando precisa.

set -uo pipefail

REPO_DIR=$(cd "$(dirname "$(readlink -f "${BASH_SOURCE[0]}")")" && pwd)

# shellcheck source=installer/lib.sh
source "$REPO_DIR/installer/lib.sh"
# shellcheck source=installer/manifest.sh
source "$REPO_DIR/installer/manifest.sh"
# shellcheck source=installer/steps.sh
source "$REPO_DIR/installer/steps.sh"

TMP_FERCDS=$(mktemp -d "${TMPDIR:-/tmp}/fercds.XXXXXX")
MUDADOS=$TMP_FERCDS/mudados
: >"$MUDADOS"
RESUMO=()
USAR_GIT=1

limpar() {
    [ -n "$SUDO_KEEPALIVE_PID" ] && kill "$SUDO_KEEPALIVE_PID" 2>/dev/null
    rm -rf "$TMP_FERCDS"
}
trap limpar EXIT
trap 'printf "\n"; aviso "$(t ui.interrupted)"; exit 130' INT TERM

uso() { t help.text; printf '\n'; }

# --- IDIOMA --------------------------------------------------------------------
# O último idioma escolhido fica guardado para ser o padrão da próxima vez.
IDIOMA_ARQ=$STATE_DIR/lang

# Idioma do sistema ($LANG), para ser o padrão na primeira vez.
idioma_do_sistema() {
    case ${LC_ALL:-${LC_MESSAGES:-${LANG:-}}} in
        pt*) echo pt ;;
        es*) echo es ;;
        it*) echo it ;;
        *)   echo en ;;
    esac
}

idioma_padrao() {
    local salvo
    salvo=$(cat "$IDIOMA_ARQ" 2>/dev/null)
    if idioma_valido "$salvo"; then echo "$salvo"; else idioma_do_sistema; fi
}

salvar_idioma() {
    mkdir -p "$STATE_DIR" && echo "$1" >"$IDIOMA_ARQ"
}

# Primeiro módulo do instalador: em que idioma ele fala. O Enter fica com o
# último escolhido (ou com o do sistema, na primeira vez); com --yes ou sem
# terminal, fica direto com esse padrão.
escolher_idioma() {
    local padrao escolha i
    padrao=$(idioma_padrao)
    carregar_idioma "$padrao"
    [ "$ASSUME_YES" = 1 ] && return 0

    cabecalho "Language · Idioma · Lingua"
    printf '\n'
    for i in "${!IDIOMAS[@]}"; do
        opcao "$((i + 1))" "$(nome_idioma "${IDIOMAS[$i]}")" ""
    done
    while true; do
        printf '\n  [1-4] (Enter = %s): ' "$(nome_idioma "$padrao")"
        if ! { read -r escolha </dev/tty; } 2>/dev/null; then
            printf '\n'
            break
        fi
        case $escolha in
            '')          break ;;
            [1-4])       padrao=${IDIOMAS[$((escolha - 1))]}; break ;;
            en|pt|es|it) padrao=$escolha; break ;;
        esac
    done
    carregar_idioma "$padrao"
    salvar_idioma "$padrao"
}

# --- ETAPAS DA INSTALAÇÃO ------------------------------------------------------
ETAPAS_INSTALL=(
    etapa_dependencias
    etapa_inputplumber
    etapa_wvkbd
    etapa_ryzenadj
    etapa_scripts
    etapa_menu
    etapa_perfis
    etapa_servico
    etapa_sudoers
    etapa_hypr_configs
    etapa_setup
)

titulo_etapa() { t "step.$1.title"; }

descricao_etapa() {
    local args=()
    case $1 in
        etapa_dependencias) args=("${DEPS_PACMAN[*]}") ;;
        etapa_scripts)      args=("$BACKEND_DIR") ;;
        etapa_menu)         args=("$LIB_DIR") ;;
        etapa_servico)      args=("$SERVICE_NAME") ;;
        etapa_sudoers)      args=("$SUDOERS_FILE") ;;
        etapa_hypr_configs) args=("$HYPR_DIR/fercdshypr") ;;
    esac
    t "step.$1.desc" "${args[@]}"
    printf '\n'
}

# Roda uma função num subshell com "set -e": se um comando falhar, só ela para.
# Nunca chame dentro de if/while/&&/||: nesses contextos o bash ignora o set -e
# de tudo que roda dentro, mesmo ligado no próprio subshell. O trap só avisa no
# nível da etapa, não nos $(...) e <(...) de verificação que ela abre.
executar_isolado() {
    (
        set -Eeuo pipefail
        NIVEL_ETAPA=$BASH_SUBSHELL
        trap 'CODIGO=$?; [ "$BASH_SUBSHELL" = "$NIVEL_ETAPA" ] && erro "$(t step.cmd_failed "$CODIGO")"' ERR
        "$@"
    )
}

# rodar_etapa FUNCAO N TOTAL: mostra o que a etapa faz, pede confirmação e roda.
rodar_etapa() {
    local fn=$1 n=$2 total=$3 titulo l
    titulo=$(titulo_etapa "$fn")
    secao "[$n/$total] $titulo"
    while IFS= read -r l; do detalhe "$l"; done < <(descricao_etapa "$fn")
    if ! perguntar "$(t step.run_q)" S; then
        info "$(t step.skipped)"
        RESUMO+=("pulada|$titulo")
        return 0
    fi
    rodar_bloco "$titulo" "$fn"
}

# rodar_bloco TITULO FUNCAO: roda isolado e anota o resultado no resumo. Se
# falhar, pergunta se segue; responder não encerra o instalador.
rodar_bloco() {
    local titulo=$1 fn=$2 rc
    executar_isolado "$fn"
    rc=$?
    if [ "$rc" -eq 0 ]; then
        RESUMO+=("ok|$titulo")
        return 0
    fi
    RESUMO+=("falhou|$titulo")
    erro "$(t step.failed "$titulo")"
    if ! perguntar "$(t step.continue_q)" N; then
        mostrar_resumo
        exit 1
    fi
}

mostrar_resumo() {
    [ ${#RESUMO[@]} -eq 0 ] && return 0
    secao "$(t summary.title)"
    local r
    for r in "${RESUMO[@]}"; do
        case ${r%%|*} in
            ok)     ok "${r#*|}" ;;
            pulada) detalhe "–  $(t summary.skipped "${r#*|}")" ;;
            falhou) erro "${r#*|}" ;;
        esac
    done
    [ -d "$BACKUP_DIR" ] && info "$(t summary.backups "$BACKUP_DIR")"
    return 0
}

verificar_ambiente() {
    if [ "$(id -u)" -eq 0 ]; then
        erro "$(t env.root)"
        detalhe "$(t env.root_detail)"
        return 1
    fi
    if [ ! -d "$REPO_DIR/src" ]; then
        erro "$(t env.no_src)"
        return 1
    fi
    [ "$1" = setup ] && return 0
    if ! command -v pacman >/dev/null; then
        erro "$(t env.no_pacman)"
        return 1
    fi
    if [ -n "$SUDO" ] && ! command -v "$SUDO" >/dev/null; then
        erro "$(t env.no_sudo)"
        return 1
    fi
}

# --- FLUXOS --------------------------------------------------------------------
fluxo_install() {
    RESUMO=()
    cabecalho "$(t title.install)"
    verificar_ambiente install || return 1

    secao "$(t install.plan)"
    local fn n=0 total=${#ETAPAS_INSTALL[@]}
    for fn in "${ETAPAS_INSTALL[@]}"; do
        n=$((n + 1))
        printf '  %s%2d%s  %s\n' "$C_BOLD" "$n" "$C_RESET" "$(titulo_etapa "$fn")"
    done
    detalhe "$(t install.plan_hint)"
    printf '\n'
    perguntar "$(t install.start_q)" S || return 0
    garantir_sudo || return 1

    n=0
    for fn in "${ETAPAS_INSTALL[@]}"; do
        n=$((n + 1))
        rodar_etapa "$fn" "$n" "$total"
    done

    mostrar_resumo
    secao "$(t install.next)"
    info "$(t install.next_relogin)"
    detalhe "$(t install.next_relogin2)"
    info "$(t install.next_f23)"
}

# Só os arquivos que mudaram: lista, pede confirmação uma vez e troca.
update_arquivos() {
    local pend_sis=() pend_usr=() p
    mapfile -t pend_sis < <(pendencias sistema "${SYSTEM_FILES[@]}")
    mapfile -t pend_usr < <(pendencias usuario "${USER_FILES[@]}")

    if [ $(( ${#pend_sis[@]} + ${#pend_usr[@]} )) -eq 0 ]; then
        ok "$(t update.all_same)"
    else
        for p in "${pend_sis[@]}" "${pend_usr[@]}"; do
            if [ "${p%%|*}" = ausente ]; then
                info "$(t update.new "$(cut -d'|' -f3 <<<"$p")")"
            else
                info "$(t update.changed "$(cut -d'|' -f3 <<<"$p")")"
            fi
        done
        if ! perguntar "$(t update.replace_q)" S; then
            info "$(t update.nothing_changed)"
            return 0
        fi
        for p in "${pend_sis[@]}"; do instalar_arquivo sistema "${p#*|}"; done
        for p in "${pend_usr[@]}"; do instalar_arquivo usuario "${p#*|}"; done
    fi
    # shellcheck disable=SC2086  # $SUDO vazio nos testes
    [ -d "$ROOT$GYRO_STATE_DIR" ] || executar $SUDO install -dm755 "$ROOT$GYRO_STATE_DIR"
    mkdir -p "$FERCDS_CONF_DIR" "$FERCDS_CUSTOMAPPS_DIR"
    gravar_versao
}

# Quem clonou o repo pode puxar a versão nova antes de atualizar. Se vier
# código novo, o instalador reinicia já com ele (e no mesmo idioma).
buscar_atualizacao_git() {
    git -C "$REPO_DIR" rev-parse --is-inside-work-tree >/dev/null 2>&1 || return 0
    local upstream antes
    upstream=$(git -C "$REPO_DIR" rev-parse --abbrev-ref --symbolic-full-name '@{u}' 2>/dev/null) || return 0
    perguntar "$(t git.pull_q "$upstream")" S || return 0
    antes=$(git -C "$REPO_DIR" rev-parse HEAD)
    if ! executar git -C "$REPO_DIR" pull --ff-only; then
        aviso "$(t git.pull_failed)"
        return 0
    fi
    if [ "$(git -C "$REPO_DIR" rev-parse HEAD)" != "$antes" ]; then
        info "$(t git.restarting)"
        local args=(update --no-git --lang "$IDIOMA")
        [ "$ASSUME_YES" = 1 ] && args+=(--yes)
        exec "$REPO_DIR/install.sh" "${args[@]}"
    fi
    ok "$(t git.up_to_date)"
}

fluxo_update() {
    RESUMO=()
    cabecalho "$(t title.update)"
    verificar_ambiente update || return 1

    if [ "$USAR_GIT" = 1 ]; then
        secao "$(t update.sec_version)"
        buscar_atualizacao_git
    fi

    secao "$(t update.sec_packages)"
    verificar_pacotes

    garantir_sudo || return 1
    secao "$(t update.sec_files)"
    rodar_bloco "$(t update.block_files)" update_arquivos
    secao "$(t update.sec_service)"
    rodar_bloco "$(t update.block_service)" etapa_servico
    secao "$(t update.sec_sudo)"
    rodar_bloco "$(t update.block_sudoers)" etapa_sudoers
    secao "hyprland.lua"
    verificar_setup
    if mudou_algum "${MENU_FILES[@]}" "${MENU_USER_FILES[@]}"; then
        reabrir_menu
    fi
    mostrar_resumo
}

fluxo_setup() {
    RESUMO=()
    cabecalho "$(t title.setup)"
    verificar_ambiente setup || return 1
    secao "$(t setup.sec "$HYPR_LUA")"
    rodar_bloco "$(t setup.block)" etapa_setup
    mostrar_resumo
}

fluxo_status() {
    cabecalho "$(t title.status)"
    verificar_ambiente setup || return 1

    secao "$(t status.sec_version)"
    info "$(t status.repo_version "$(versao_repo)")"
    info "$(t status.installed_version "$(cat "$ROOT$VERSION_FILE" 2>/dev/null || t status.none)")"

    secao "$(t status.sec_packages)"
    verificar_pacotes

    secao "$(t status.sec_files)"
    local entrada origem destino dst estado desatualizados=0
    for entrada in "${SYSTEM_FILES[@]}" "${SERVICE_FILES[@]}" "${USER_FILES[@]}"; do
        IFS='|' read -r origem destino _ <<<"$entrada"
        dst=$destino
        [[ $destino == "$HOME"/* ]] || dst="$ROOT$destino"
        estado=$(estado_arquivo "$REPO_DIR/$origem" "$dst")
        case $estado in
            igual)     ok "$destino" ;;
            diferente) aviso "$(t status.file_differs "$destino")"; desatualizados=1 ;;
            ausente)   erro "$(t status.file_missing "$destino")"; desatualizados=1 ;;
        esac
    done
    [ "$desatualizados" = 1 ] && info "$(t status.hint_update)"

    secao "$(t status.sec_services)"
    if systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        ok "$(t service.active "$SERVICE_NAME")"
    elif systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        aviso "$(t status.service_stopped "$SERVICE_NAME" "$SERVICE_NAME")"
    else
        aviso "$(t status.service_inactive "$SERVICE_NAME")"
    fi
    local f
    while read -r f; do
        [ -n "$f" ] && aviso "$(t status.legacy_service "$(basename "$f")")"
    done < <(servicos_legados)

    secao "$(t status.sec_sudo)"
    if [ -z "$SUDO" ]; then
        detalhe "$(t status.test_mode)"
    else
        if sudo -n -l /usr/local/bin/fercds-gyro on >/dev/null 2>&1; then
            ok "$(t status.gyro_ok)"
        else
            aviso "$(t status.gyro_pw)"
        fi
        if ! command -v ryzenadj >/dev/null; then
            aviso "$(t status.ryzenadj_missing)"
        elif sudo -n -l ryzenadj --info >/dev/null 2>&1; then
            ok "$(t status.ryzenadj_ok)"
        else
            aviso "$(t status.ryzenadj_pw)"
        fi
    fi

    secao "hyprland.lua"
    verificar_setup
}

# --- MENU ----------------------------------------------------------------------
opcao() { printf '  %s%s%s  %-10s %s%s%s\n' "$C_BOLD$C_CYAN" "$1" "$C_RESET" "$2" "$C_DIM" "$3" "$C_RESET"; }

menu_principal() {
    local escolha
    while true; do
        limpar_tela
        cabecalho "$(t title.menu)"
        printf '\n'
        opcao 1 "$(t menu.install)"  "$(t menu.install_desc)"
        opcao 2 "$(t menu.update)"   "$(t menu.update_desc)"
        opcao 3 "$(t menu.setup)"    "$(t menu.setup_desc)"
        opcao 4 "$(t menu.status)"   "$(t menu.status_desc)"
        opcao 5 "$(t menu.language)" "$(t menu.language_desc)"
        opcao 0 "$(t menu.quit)"     ""
        printf '\n  %s' "$(t menu.choose)"
        { read -r escolha </dev/tty; } 2>/dev/null || { printf '\n'; exit 0; }
        printf '\n'
        case $escolha in
            1) fluxo_install; pausar ;;
            2) fluxo_update; pausar ;;
            3) fluxo_setup; pausar ;;
            4) fluxo_status; pausar ;;
            5) limpar_tela; escolher_idioma ;;
            0|q) exit 0 ;;
        esac
    done
}

# --- ARGUMENTOS ----------------------------------------------------------------
# Até a pergunta do idioma, vale o padrão (último escolhido ou o do sistema):
# é nele que saem a ajuda e os erros de argumento.
carregar_idioma "$(idioma_padrao)"

ACAO=menu
IDIOMA_ARG=
while [ $# -gt 0 ]; do
    case $1 in
        install|instalar)           ACAO=install ;;
        update|updater|atualizar)   ACAO=update ;;
        setup)                      ACAO=setup ;;
        status)                     ACAO=status ;;
        -y|--yes)                   ASSUME_YES=1 ;;
        --no-git)                   USAR_GIT=0 ;;
        --lang|--lang=*)
            if [ "$1" = --lang ]; then
                IDIOMA_ARG=${2:-}
                shift
            else
                IDIOMA_ARG=${1#--lang=}
            fi
            idioma_valido "$IDIOMA_ARG" || { erro "$(t args.bad_lang)"; exit 2; }
            carregar_idioma "$IDIOMA_ARG"
            ;;
        -h|--help|help)             uso; exit 0 ;;
        *) erro "$(t args.unknown "$1")"; uso; exit 2 ;;
    esac
    shift
done

# Primeiro módulo: o idioma (a não ser que tenha vindo no --lang).
if [ -n "$IDIOMA_ARG" ]; then
    salvar_idioma "$IDIOMA_ARG"
else
    escolher_idioma
fi

case $ACAO in
    menu)    menu_principal ;;
    install) fluxo_install ;;
    update)  fluxo_update ;;
    setup)   fluxo_setup ;;
    status)  fluxo_status ;;
esac
