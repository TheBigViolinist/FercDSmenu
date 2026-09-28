#!/bin/bash

# --- CONFIGURAÇÃO ---
# ATENÇÃO: O nome deve ficar entre aspas duplas por causa dos espaços!
MODO_DESKTOP="busctl call org.shadowblip.InputPlumber   /org/shadowblip/InputPlumber/CompositeDevice0   org.shadowblip.Input.CompositeDevice   LoadProfilePath "s" /etc/inputplumber/profiles/fercds_desktop.yaml"
MODO_JOGO="busctl call org.shadowblip.InputPlumber   /org/shadowblip/InputPlumber/CompositeDevice0   org.shadowblip.Input.CompositeDevice   LoadProfilePath "s" /etc/inputplumber/profiles/fercds_gamepad.yaml"
# Nomes dos Presets (Verifique no app se é "games" ou "Jogos")
# No seu log apareceu "games" minúsculo, então ajustei aqui:
PRESET_JOGO="games"      
PRESET_DESKTOP="desktop" 
# --------------------

# Arquivo de controle (memória)
STATE_FILE="/tmp/modo_jogo_ativo"

# Ignora avisos do Python
export PYTHONWARNINGS="ignore"

if [ -f "$STATE_FILE" ]; then
    # --- MUDAR PARA DESKTOP ---
    echo "Trocando o perfil atual..."
    $MODO_DESKTOP
    
    rm "$STATE_FILE"
    notify-send -t 2000 "🎮 InputPlumber" "Modo $PRESET_DESKTOP Ativado"

else
    # --- MUDAR PARA JOGOS ---
    echo "Trocando perfil atual..."
    $MODO_JOGO
    
    touch "$STATE_FILE"
    notify-send -t 2000 "🎮 InputPlumber" "Modo $PRESET_JOGO Ativado"
fi
