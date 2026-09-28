#!/bin/bash

# ================= CONFIGURAÇÕES =================
MONITOR="DP-1"
# =================================================

# No novo Hyprland com Lua, o comando 'keyword monitor disable' apresenta bugs de reativação.
# A solução oficial da Wiki para "desligar a tela" (screensaver style) é usar o dispatcher DPMS.
# Usamos 'jq' para verificar o status real de energia (dpmsStatus) da API do Hyprland.

STATUS=$(hyprctl monitors -j | jq -r ".[] | select(.name == \"$MONITOR\") | .dpmsStatus")

if [ "$STATUS" = "true" ]; then
    # === SE ENTROU AQUI, ELA ESTÁ LIGADA ===
    notify-send -u low -t 1000 "Ayaneo Flip" "Desligando Tela 🌑"
    
    # 1. Mata os widgets da tela inferi
    pkill -f "nwg-dock-hyprland"
    
    # 2. Desliga a tela usando o dispatcher Lua (DPMS)
    hyprctl dispatch "hl.dispatch(hl.dsp.dpms({ action = \"disable\", monitor = \"$MONITOR\" }))"
else
    # === SE ENTROU AQUI, ELA ESTÁ DESLIGADA ===
    notify-send -u low -t 1000 "Ayaneo Flip" "Ligando Tela ☀️"
    
    # 1. Liga a tela usando o dispatcher Lua (DPMS)
    hyprctl dispatch "hl.dispatch(hl.dsp.dpms({ action = \"enable\", monitor = \"$MONITOR\" }))"
    
    # Espera a tela acordar fisicamente
    sleep 0.5
    
    # 2. Força o foco para a tela inferior
    hyprctl dispatch "hl.dispatch(hl.dsp.focus({ monitor = \"$MONITOR\" }))"
    
    sleep 0.8
    
    # 3. Limpa mensagens de erro e inicia widget
    hyprctl seterror disable
    # Adicione aqui o seu comando de iniciar o widget, se necessário.
fi

# Nos dois casos, limpa a barra de erro do Hyprland.
hyprctl seterror disable
