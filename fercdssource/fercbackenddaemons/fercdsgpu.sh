#!/bin/bash

# Aguarda o sistema carregar o módulo de vídeo no boot
sleep 5

# Localiza dinamicamente o diretório da GPU que tem suporte a OverDrive
GPU_DIR=$(dirname $(ls /sys/class/drm/card*/device/pp_od_clk_voltage 2>/dev/null | head -n 1))

# Se não encontrar, encerra o serviço silenciosamente
if [ -z "$GPU_DIR" ]; then exit 1; fi

LAST_MODE=""

while true; do
    # Lê a ordem do painel (se não houver, assume 'auto')
    MODE=$(cat /tmp/gpu_clock 2>/dev/null || echo "auto")

    if [ "$MODE" != "$LAST_MODE" ]; then
        if [ "$MODE" = "auto" ] || [ "$MODE" -eq 0 ]; then
            echo "auto" > "$GPU_DIR/power_dpm_force_performance_level"
        else
            echo "manual" > "$GPU_DIR/power_dpm_force_performance_level"
            
            # --- CORREÇÃO DO BUG (A Lógica dos 100MHz) ---
            # Define o mínimo como 100MHz abaixo do valor escolhido
            MIN_CLOCK=$((MODE - 100))
            
            # Garante que o mínimo absoluto nunca seja menor que 400MHz (Evita Hard Freeze)
            if [ "$MIN_CLOCK" -lt 600 ]; then
                MIN_CLOCK=600
            fi
            
            # 1. Ajusta o Estado 0 (Mínimo) PRIMEIRO
            echo "s 0 $MIN_CLOCK" > "$GPU_DIR/pp_od_clk_voltage"
            
            # 2. Ajusta o Estado 1 (Máximo) DEPOIS
            echo "s 1 $MODE" > "$GPU_DIR/pp_od_clk_voltage"
            
            # 3. Confirma e aplica tudo simultaneamente
            echo "c" > "$GPU_DIR/pp_od_clk_voltage"
        fi
        LAST_MODE="$MODE"
    fi
    sleep 2
done
