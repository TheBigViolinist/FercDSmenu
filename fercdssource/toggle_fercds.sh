#!/bin/bash

# Liga/desliga o ferc-DS.
#
# O menu se ancora sozinho no monitor DP-1 (gtk-layer-shell, ver TARGET_MONITOR
# em fercds_menu.py), por isso aqui nao ha mais troca de foco, dispatcher do
# Hyprland nem sleep: e so abrir ou fechar.

if pkill -f "fercds_menu.py"; then
    exit 0
fi

exec python ~/.local/bin/fercds/menu/fercds_menu.py
