# shellcheck shell=bash
# FercDS - etapas do instalador. Carregado pelo install.sh.
#
# Cada etapa roda num subshell com "set -e" (ver executar_isolado no install.sh):
# um comando que falha encerra só a etapa, e o instalador pergunta se segue.
# Verificações que podem dar "não" ficam sempre dentro de if/||.
# Os textos vêm de installer/lang (função t, no lib.sh).

# shellcheck disable=SC2086  # $SUDO fica sem aspas de propósito (vazio nos testes)

# --- PACOTES -------------------------------------------------------------------
etapa_dependencias() {
    local faltando=() p
    for p in "${DEPS_PACMAN[@]}"; do
        dep_satisfeita "$p" || faltando+=("$p")
    done
    if [ ${#faltando[@]} -eq 0 ]; then
        ok "$(t deps.all_installed)"
        return 0
    fi
    info "$(t deps.missing "${faltando[*]}")"
    executar $SUDO pacman -S --needed "${faltando[@]}"
}

etapa_inputplumber() {
    if dep_satisfeita inputplumber; then
        ok "$(t ip.installed "$(pacman -Q inputplumber 2>/dev/null)")"
    else
        executar $SUDO pacman -S --needed inputplumber
    fi
    if systemctl is-enabled --quiet inputplumber.service 2>/dev/null &&
        systemctl is-active --quiet inputplumber.service 2>/dev/null; then
        ok "$(t ip.service_active)"
    else
        executar $SUDO systemctl enable --now inputplumber.service
    fi
}

# Compila packaging/<nome>/PKGBUILD fora do repo (em ~/.cache/fercds/build) e
# instala com o makepkg, que chama o pacman (e pede confirmação) sozinho.
compilar_pacote() {
    local nome=$1 dir
    dir="$CACHE_DIR/build/$nome"
    if ! command -v makepkg >/dev/null; then
        erro "$(t build.no_makepkg)"
        return 1
    fi
    rm -rf "${dir:?}"
    mkdir -p "$dir"
    cp "$REPO_DIR/packaging/$nome/PKGBUILD" "$dir/"
    info "$(t build.compiling "$nome" "$dir")"
    (cd "$dir" && executar makepkg -si)
}

etapa_wvkbd() {
    if wvkbd_fercds_ok; then
        ok "$(t wvkbd.installed "$(pacman -Q wvkbd-fercds 2>/dev/null || command -v wvkbd-mobintl)")"
        perguntar "$(t wvkbd.rebuild_q)" N || return 0
    elif command -v wvkbd-mobintl >/dev/null; then
        aviso "$(t wvkbd.replace)"
    fi
    compilar_pacote wvkbd-fercds
}

etapa_ryzenadj() {
    if command -v ryzenadj >/dev/null; then
        ok "$(t ryzenadj.installed "$(pacman -Qo "$(command -v ryzenadj)" 2>/dev/null || command -v ryzenadj)")"
        perguntar "$(t ryzenadj.rebuild_q)" N || return 0
    fi
    compilar_pacote ryzenadj-fercds
}

# Só confere (é o que o updater faz): não instala nada.
verificar_pacotes() {
    local p pendente=0
    if ! command -v pacman >/dev/null; then
        aviso "$(t check.no_pacman)"
        return 0
    fi
    for p in "${DEPS_PACMAN[@]}" inputplumber; do
        if ! dep_satisfeita "$p"; then
            aviso "$(t deps.missing "$p")"
            pendente=1
        fi
    done
    [ "$pendente" = 0 ] && ok "$(t check.deps_ok)"

    if wvkbd_fercds_ok; then
        ok "$(t check.wvkbd_ok "$(pacman -Q wvkbd-fercds 2>/dev/null || t check.wvkbd_with_output)")"
    elif command -v wvkbd-mobintl >/dev/null; then
        aviso "$(t check.wvkbd_no_output)"
        pendente=1
    else
        aviso "$(t check.wvkbd_missing)"
        pendente=1
    fi

    if command -v ryzenadj >/dev/null; then
        ok "$(t check.ryzenadj_ok "$(command -v ryzenadj)")"
    else
        aviso "$(t check.ryzenadj_missing)"
        pendente=1
    fi

    if systemctl is-active --quiet inputplumber.service 2>/dev/null; then
        ok "$(t check.ip_active)"
    else
        aviso "$(t check.ip_stopped)"
        pendente=1
    fi

    if [ "$pendente" = 1 ]; then
        info "$(t check.hint_install)"
    fi
    return 0
}

# --- ARQUIVOS ------------------------------------------------------------------
etapa_scripts() {
    instalar_lista sistema "${SCRIPT_FILES[@]}" "${BACKEND_FILES[@]}"
    # O fercds-gyro guarda aqui o driver do sensor enquanto ele está desligado.
    [ -d "$ROOT$GYRO_STATE_DIR" ] || executar $SUDO install -dm755 "$ROOT$GYRO_STATE_DIR"
    gravar_versao
}

etapa_menu() {
    instalar_lista sistema "${MENU_FILES[@]}"
    instalar_lista usuario "${MENU_USER_FILES[@]}"
    # Pasta onde o usuário larga .desktop próprios para a biblioteca do menu.
    mkdir -p "$FERCDS_CONF_DIR" "$FERCDS_CUSTOMAPPS_DIR"
    gravar_versao
}

etapa_perfis() {
    instalar_lista sistema "${PROFILE_FILES[@]}"
}

etapa_hypr_configs() {
    instalar_lista usuario "${HYPR_FILES[@]}"
}

# Versão do repo que está instalada (o "status" compara com a do repo).
gravar_versao() {
    local atual
    atual=$(cat "$ROOT$VERSION_FILE" 2>/dev/null || true)
    [ "$atual" = "$(versao_repo)" ] && return 0
    versao_repo | $SUDO install -Dm644 /dev/stdin "$ROOT$VERSION_FILE"
}

# --- SERVIÇO -------------------------------------------------------------------
# Unidades em /etc/systemd/system (fora o fercds-backend) que rodam algum dos
# daemons: é como as versões antigas do FercDS subiam eles, um serviço cada.
servicos_legados() {
    local f
    for f in "$ROOT"/etc/systemd/system/*.service; do
        [ -f "$f" ] || continue
        [ "$(basename "$f")" = "$SERVICE_NAME" ] && continue
        if grep -qE '^ExecStart=.*/(fercdsfancurve|fercdsgpu|fercdsgpumode)\.sh' "$f"; then
            echo "$f"
        fi
    done
}

# Desativa os serviços antigos e guarda (no backup) as unidades e as cópias
# antigas dos daemons em /usr/local/bin. Sem isso, as duas curvas de
# ventoinha brigariam pelo mesmo PWM.
migrar_servicos_legados() {
    local unidades=() f unidade exe
    mapfile -t unidades < <(servicos_legados)
    [ ${#unidades[@]} -eq 0 ] && return 0

    aviso "$(t legacy.found "$SERVICE_NAME")"
    for f in "${unidades[@]}"; do
        detalhe "$(basename "$f")  →  $(grep -m1 '^ExecStart=' "$f" | cut -d= -f2-)"
    done
    if ! perguntar "$(t legacy.disable_q)" S; then
        aviso "$(t legacy.kept "$SERVICE_NAME")"
        return 1
    fi

    for f in "${unidades[@]}"; do
        unidade=$(basename "$f")
        exe=$(grep -m1 '^ExecStart=' "$f" | cut -d= -f2- | sed 's/^[-@:+!]*//' | awk '{print $1}')
        executar $SUDO systemctl disable --now "$unidade" || true
        fazer_backup "$f"
        executar $SUDO rm -f "$f"
        if [[ $exe == /usr/local/bin/* ]] && [[ " ${DAEMONS_LEGADOS[*]} " == *" $(basename "$exe") "* ]] &&
            [ -f "$ROOT$exe" ]; then
            fazer_backup "$ROOT$exe"
            executar $SUDO rm -f "$ROOT$exe"
        fi
    done
    executar $SUDO systemctl daemon-reload
    ok "$(t legacy.done "$BACKUP_DIR")"
}

# Instala/atualiza a unidade e deixa o serviço ativo: cria e ativa se ainda não
# existir, reinicia se a unidade ou algum daemon mudou.
etapa_servico() {
    if [ ! -x "$ROOT$BACKEND_DIR/fercds-backend" ]; then
        erro "$(t service.no_daemons)"
        return 1
    fi
    local pode_ativar=1
    migrar_servicos_legados || pode_ativar=0

    instalar_lista sistema "${SERVICE_FILES[@]}"
    if mudou_algum "${SERVICE_FILES[@]}"; then
        executar $SUDO systemctl daemon-reload
    fi
    [ "$pode_ativar" = 1 ] || return 0

    if ! systemctl is-enabled --quiet "$SERVICE_NAME" 2>/dev/null; then
        executar $SUDO systemctl enable --now "$SERVICE_NAME"
    elif mudou_algum "${SERVICE_FILES[@]}" "${BACKEND_FILES[@]}"; then
        executar $SUDO systemctl restart "$SERVICE_NAME"
    elif ! systemctl is-active --quiet "$SERVICE_NAME" 2>/dev/null; then
        executar $SUDO systemctl start "$SERVICE_NAME"
    else
        ok "$(t service.up_to_date "$SERVICE_NAME")"
        return 0
    fi
    ok "$(t service.active "$SERVICE_NAME")"
}

# --- SUDO SEM SENHA ------------------------------------------------------------
# Conteúdo do /etc/sudoers.d/fercds: o fercds-gyro (on/off) e o ryzenadj (TDP),
# os dois comandos que o menu roda com sudo. Mantém os outros usuários que já
# estavam no arquivo (cada um que roda o instalador entra na lista). Os
# comentários do arquivo ficam em inglês em qualquer idioma: se mudassem com o
# idioma, o updater acharia diferença e pediria para regravar a regra à toa.
gerar_sudoers() {
    local usuarios=("$USER") u p cmds=("/usr/local/bin/fercds-gyro") lista
    if $SUDO test -f "$ROOT$SUDOERS_FILE"; then
        while read -r u _; do
            [[ " ${usuarios[*]} " == *" $u "* ]] && continue
            id -u "$u" >/dev/null 2>&1 && usuarios+=("$u")
        done < <($SUDO grep -E '^[a-z_][a-z0-9_.-]* ALL=' "$ROOT$SUDOERS_FILE")
    fi

    # O menu chama "sudo ryzenadj" e o sudo acha o binário pelo PATH: entram
    # todos os ryzenadj do PATH, desde que só o root possa mexer neles.
    while read -r p; do
        [ -n "$p" ] || continue
        if seguro_para_sudo "$p"; then
            cmds+=("$p")
        else
            # stderr: o stdout desta função é o próprio arquivo do sudoers.
            aviso "$(t sudoers.unsafe_path "$p")" >&2
        fi
    done < <(type -aP ryzenadj | xargs -r -n1 readlink -f | awk '!visto[$0]++')

    printf -v lista '%s, ' "${cmds[@]}"
    printf '# FercDS: lets the menu run only these commands with sudo, without a password.\n'
    printf '# Generated by the FercDS install.sh, which rewrites this file on every update.\n'
    for u in "${usuarios[@]}"; do
        printf '%s ALL=(root) NOPASSWD: %s\n' "$u" "${lista%, }"
    done
}

# O nome com ponto é ignorado pelo sudo: a regra é validada já no lugar certo,
# com dono e permissão finais, e só então troca o arquivo de verdade.
gravar_sudoers() {
    local novo="$ROOT$SUDOERS_FILE.novo"
    executar $SUDO install -Dm0440 "$1" "$novo"
    if ! executar $SUDO visudo -cf "$novo"; then
        $SUDO rm -f "$novo"
        erro "$(t sudoers.visudo_failed)"
        return 1
    fi
    executar $SUDO mv -f "$novo" "$ROOT$SUDOERS_FILE"
    ok "$(t sudoers.written "$SUDOERS_FILE")"
}

etapa_sudoers() {
    if [[ ! $USER =~ ^[a-z_][a-z0-9_.-]*$ ]]; then
        erro "$(t sudoers.bad_user "$USER")"
        return 1
    fi
    if ! command -v ryzenadj >/dev/null; then
        aviso "$(t sudoers.no_ryzenadj)"
    fi

    local tmp l
    tmp=$(mktemp "$TMP_FERCDS/sudoers.XXXXXX")
    gerar_sudoers >"$tmp"

    if $SUDO cat "$ROOT$SUDOERS_FILE" 2>/dev/null | cmp -s - "$tmp"; then
        ok "$(t sudoers.up_to_date "$SUDOERS_FILE")"
    else
        info "$(t sudoers.new_rule "$SUDOERS_FILE")"
        while IFS= read -r l; do detalhe "$l"; done <"$tmp"
        if perguntar "$(t sudoers.write_q)" S; then
            gravar_sudoers "$tmp"
        else
            info "$(t sudoers.skipped)"
            return 0
        fi
    fi

    # Instalação antiga do gyro (install-fercds-gyro.sh): a regra dela agora
    # está no arquivo acima, então só sai depois que ele estiver no lugar.
    if $SUDO test -f "$ROOT$SUDOERS_LEGADO" && $SUDO test -f "$ROOT$SUDOERS_FILE"; then
        info "$(t sudoers.legacy_found "$SUDOERS_LEGADO")"
        if perguntar "$(t sudoers.legacy_remove_q "$SUDOERS_LEGADO")" S; then
            mkdir -p "$(dirname "$BACKUP_DIR$ROOT$SUDOERS_LEGADO")"
            $SUDO cat "$ROOT$SUDOERS_LEGADO" >"$BACKUP_DIR$ROOT$SUDOERS_LEGADO"
            executar $SUDO rm -f "$ROOT$SUDOERS_LEGADO"
        fi
    fi
}

# --- HYPRLAND.LUA --------------------------------------------------------------
etapa_setup() {
    if [ ! -f "$HYPR_LUA" ]; then
        erro "$(t setup.no_hyprland_lua "$HYPR_LUA")"
        detalhe "$(t setup.needs_lua)"
        return 1
    fi
    if ! command -v python3 >/dev/null; then
        erro "$(t setup.no_python)"
        return 1
    fi
    # Um require apontando para um arquivo que não existe vira erro no Hyprland.
    local faltam=() e l
    mapfile -t faltam < <(pendencias usuario "${HYPR_FILES[@]}" | grep '^ausente|' | cut -d'|' -f2- || true)
    if [ ${#faltam[@]} -gt 0 ]; then
        aviso "$(t setup.lua_missing "$HYPR_DIR/fercdshypr")"
        for e in "${faltam[@]}"; do detalhe "$(cut -d'|' -f2 <<<"$e")"; done
        if perguntar "$(t setup.install_lua_q)" S; then
            instalar_lista usuario "${faltam[@]}"
        else
            aviso "$(t setup.lua_missing_warn)"
        fi
    fi

    local novo="$TMP_FERCDS/hyprland.lua.novo" log="$TMP_FERCDS/hyprland.lua.log"
    FERCDS_LANG=$IDIOMA python3 "$REPO_DIR/installer/hypr_setup.py" plan "$HYPR_LUA" >"$novo" 2>"$log"
    if [ ! -s "$log" ]; then
        ok "$(t setup.nothing_to_do)"
        return 0
    fi

    info "$(t setup.changes "$HYPR_LUA")"
    while IFS= read -r l; do detalhe "$l"; done <"$log"
    printf '\n'
    diff -u --label "$(t setup.diff_current)" --label "$(t setup.diff_new)" "$HYPR_LUA" "$novo" | colorir_diff || true
    printf '\n'
    if ! perguntar "$(t setup.write_q)" S; then
        info "$(t setup.not_written)"
        return 0
    fi
    fazer_backup "$HYPR_LUA"
    # cat > (e não mv) mantém o arquivo no lugar, inclusive se for um link.
    cat "$novo" >"$HYPR_LUA"
    ok "$(t setup.written "$BACKUP_DIR")"
    detalhe "$(t setup.reload_hint)"
}

# Só confere (status e updater).
verificar_setup() {
    [ -f "$HYPR_LUA" ] || { aviso "$(t setup.no_hyprland_lua "$HYPR_LUA")"; return 0; }
    command -v python3 >/dev/null || { aviso "$(t check.no_python)"; return 0; }
    local log="$TMP_FERCDS/check.log" l
    if FERCDS_LANG=$IDIOMA python3 "$REPO_DIR/installer/hypr_setup.py" check "$HYPR_LUA" 2>"$log"; then
        ok "$(t check.setup_ok)"
    else
        aviso "$(t check.setup_needed)"
        while IFS= read -r l; do detalhe "$l"; done <"$log"
    fi
}

# --- MENU EM EXECUÇÃO ----------------------------------------------------------
# Depois de um update, o menu aberto continua com o código antigo na memória.
# O padrão só pega o Python rodando o menu, não um editor com o arquivo aberto.
MENU_PROC='python[0-9.]* .*fercds_menu\.py'

reabrir_menu() {
    pgrep -f "$MENU_PROC" >/dev/null 2>&1 || return 0
    if [ -z "${WAYLAND_DISPLAY:-}" ]; then
        info "$(t menu.reopen_manual)"
        return 0
    fi
    perguntar "$(t menu.reopen_q)" S || return 0
    pkill -f "$MENU_PROC" || true
    local _
    for _ in $(seq 30); do
        pgrep -f "$MENU_PROC" >/dev/null 2>&1 || break
        sleep 0.1
    done
    setsid -f python3 "$LIB_DIR/fercds_menu.py" >/dev/null 2>&1 </dev/null
    ok "$(t menu.reopened)"
}
