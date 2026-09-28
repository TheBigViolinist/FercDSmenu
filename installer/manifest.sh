# shellcheck shell=bash
# FercDS - o que o instalador põe em cada lugar. Carregado pelo install.sh.
#
# Cada entrada é "origem no repo|destino|modo". Os destinos de sistema são os
# caminhos reais (é o que os scripts e o menu esperam); o instalador só põe
# $ROOT na frente na hora de copiar. FERCDS_DESTDIR existe para testar o
# instalador numa pasta de mentira e fica vazio no uso normal.

# shellcheck disable=SC2034  # as variáveis são usadas pelo steps.sh e install.sh

ROOT=${FERCDS_DESTDIR:-}

HYPR_DIR=${XDG_CONFIG_HOME:-$HOME/.config}/hypr
HYPR_LUA=$HYPR_DIR/hyprland.lua
# O menu lê ~/.config/ferc-ds fixo (sem XDG_CONFIG_HOME), então aqui também.
FERCDS_CONF_DIR=$HOME/.config/ferc-ds
FERCDS_CUSTOMAPPS_DIR=$HOME/.fercds/customapps

CACHE_DIR=${XDG_CACHE_HOME:-$HOME/.cache}/fercds
STATE_DIR=${XDG_STATE_HOME:-$HOME/.local/state}/fercds
BACKUP_DIR=$STATE_DIR/backups/$(date +%Y-%m-%d_%H%M%S)

LIB_DIR=/usr/local/lib/fercds
BACKEND_DIR=$LIB_DIR/backend
VERSION_FILE=$LIB_DIR/VERSION
GYRO_STATE_DIR=/var/lib/fercds
SERVICE_NAME=fercds-backend.service
SUDOERS_FILE=/etc/sudoers.d/fercds
SUDOERS_LEGADO=/etc/sudoers.d/fercds-gyro

# Etapa "scripts": atalhos do usuário e o gyro em /usr/local/bin, daemons do
# serviço em /usr/local/lib/fercds/backend.
SCRIPT_FILES=(
    "src/scripts/toggle_wvkbd.sh|/usr/local/bin/toggle_wvkbd.sh|755"
    "src/scripts/libre_wvkbd.sh|/usr/local/bin/libre_wvkbd.sh|755"
    "src/scripts/cprofile.sh|/usr/local/bin/cprofile.sh|755"
    "src/scripts/toggle_monitor.sh|/usr/local/bin/toggle_monitor.sh|755"
    "src/backend/fercds-gyro|/usr/local/bin/fercds-gyro|755"
)
BACKEND_FILES=(
    "src/backend/fercds-backend|$BACKEND_DIR/fercds-backend|755"
    "src/backend/fercdsfancurve.sh|$BACKEND_DIR/fercdsfancurve.sh|755"
    "src/backend/fercdsgpu.sh|$BACKEND_DIR/fercdsgpu.sh|755"
    "src/backend/fercdsgpumode.sh|$BACKEND_DIR/fercdsgpumode.sh|755"
)

# Etapa "menu": o menu e o toggle dele (sistema) + traduções (usuário).
MENU_FILES=(
    "src/menu/fercds_menu.py|$LIB_DIR/fercds_menu.py|644"
    "src/menu/toggle_fercds.sh|/usr/local/bin/toggle_fercds.sh|755"
)
MENU_USER_FILES=(
    "src/config/fercds_lang.json|$FERCDS_CONF_DIR/fercds_lang.json|644"
)

# Etapa "perfis": o menu e o cprofile.sh carregam estes caminhos pelo busctl.
PROFILE_FILES=(
    "src/inputplumber/fercds_desktop.yaml|/etc/inputplumber/profiles/fercds_desktop.yaml|644"
    "src/inputplumber/fercds_gamepad.yaml|/etc/inputplumber/profiles/fercds_gamepad.yaml|644"
)

SERVICE_FILES=(
    "src/systemd/fercds-backend.service|/etc/systemd/system/$SERVICE_NAME|644"
)

# Etapa "configs do Hyprland": o setup liga estes módulos no hyprland.lua
# (require("fercdshypr.<nome>")).
HYPR_FILES=(
    "src/hypr/bindsfercds.lua|$HYPR_DIR/fercdshypr/bindsfercds.lua|644"
    "src/hypr/fercds.lua|$HYPR_DIR/fercdshypr/fercds.lua|644"
    "src/hypr/outputsfercds.lua|$HYPR_DIR/fercdshypr/outputsfercds.lua|644"
)

SYSTEM_FILES=("${SCRIPT_FILES[@]}" "${BACKEND_FILES[@]}" "${MENU_FILES[@]}" "${PROFILE_FILES[@]}")
USER_FILES=("${MENU_USER_FILES[@]}" "${HYPR_FILES[@]}")

# Pacotes dos repositórios oficiais que o menu e os scripts usam.
#   base-devel, git            compilar wvkbd-fercds e ryzenadj-fercds (makepkg)
#   python, python-gobject,
#   python-cairo, gtk3,
#   gtk-layer-shell            o menu (GTK3 + layer shell, ícones em cairo)
#   python-psutil              telemetria e gerenciador de processos do menu
#   jq                         toggle_monitor.sh
#   libnotify                  notify-send
#   playerctl                  controles de mídia do menu
#   wireplumber                wpctl (volume e microfone)
#   libpulse                   paplay (sons)
DEPS_PACMAN=(
    base-devel git
    python python-gobject python-cairo python-psutil gtk3 gtk-layer-shell
    jq libnotify playerctl wireplumber libpulse
)

# Daemons que versões antigas rodavam em serviços separados (ayaneo-fan etc.).
DAEMONS_LEGADOS=(fercdsfancurve.sh fercdsgpu.sh fercdsgpumode.sh)
