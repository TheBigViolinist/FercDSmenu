#!/bin/bash

# Nome do processo
KB_BIN="wvkbd-mobintl"

# Verifica se já está aberto
if pgrep -x "$KB_BIN" > /dev/null; then
    # Se estiver aberto, fecha
    pkill "$KB_BIN"
else

    # 3. Abre o teclado
    $KB_BIN -L 400 &

    # 4. (Opcional) Pequena pausa para garantir que o wvkbd pegue a tela certa
    # Se o teclado aparecer na tela errada, descomente a linha abaix
fi