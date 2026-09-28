#!/bin/bash

# Nome do processo
KB_BIN="wvkbd-mobintl"

# Verifica se já está aberto
if pgrep -x "$KB_BIN" > /dev/null; then
    # Se estiver aberto, fecha
    pkill "$KB_BIN"
else
    # SE NÃO ESTIVER ABERTO: abre o teclado
    #   WVKBD_OUTPUT            : monitor onde o teclado abre (requer o fork com
    #                             seleção de output: wvkbd2fercds)
    #   -l / --landscape-layers : layouts "fullwide" e "special" (retrato e paisagem)
    #   -L 535                  : altura em modo paisagem
    #   --fn                    : fonte um pouco maior que o padrão (Sans 14)
    #   cores                   : mais escuras que o padrão; a cor do texto (branco) é mantida
    WVKBD_OUTPUT="DP-1" $KB_BIN \
        -L 535 \
        -l fullwide,special \
        --landscape-layers fullwide,special \
        --fn "Sans 18" \
        --bg 050505 \
        --fg 1c1c1c \
        --fg-sp 121212 \
        --press 3a3a3a \
        --press-sp 3a3a3a &
fi
