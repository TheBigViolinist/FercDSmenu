#!/bin/bash

# Nome do processo

# Verifica se já está aberto
if  pgrep -f "fercds_menu.py" > /dev/null; then
    pkill -f "fercds_menu.py"
else
    # SE NÃO ESTIVER ABERTO:

    # 1. Descobre qual monitor está em foco AGORA (requer 'jq' instalado)
    current_monitor=$(hyprctl monitors -j | jq -r '.[] | select(.focused) | .name')

    # 2. Move o foco para a tela de baixo (DP-1) apenas para lançar o app
    hyprctl dispatch "hl.dispatch(hl.dsp.focus({ monitor = \"DP-1\" }))"

    # 3. Abre o ferc-DS
    python ~/.local/bin/fercds/menu/fercds_menu.py &

    # 4. (Opcional) Pequena pausa para garantir que o wvkbd pegue a tela certa
    # Se o teclado aparecer na tela errada, descomente a linha abaixo:
    sleep 1

    # 5. Devolve o foco imediatamente para o monitor onde você estava
    hyprctl dispatch "hl.dispatch(hl.dsp.focus({ monitor = \"$current_monitor\" }))"
fi