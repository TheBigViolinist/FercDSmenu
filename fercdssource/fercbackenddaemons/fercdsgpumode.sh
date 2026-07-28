#!/bin/bash

# Verifica se a funcionalidade EPP (amd-pstate-epp) é suportada pelo kernel
if ! ls /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference > /dev/null 2>&1; then
    exit 1
fi

LAST_MODE=""

while true; do
    # Lê a ordem do painel (se não houver, assume 'balance_power' como meio-termo)
    MODE=$(cat /tmp/cpu_epp 2>/dev/null || echo "balance_power")

    if [ "$MODE" != "$LAST_MODE" ]; then
        # Aplica a preferência em todos os núcleos disponíveis
        for EPP_FILE in /sys/devices/system/cpu/cpu*/cpufreq/energy_performance_preference; do
            echo "$MODE" > "$EPP_FILE" 2>/dev/null
        done
        LAST_MODE="$MODE"
    fi
    sleep 2
done
