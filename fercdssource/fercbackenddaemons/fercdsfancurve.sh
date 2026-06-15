#!/bin/bash

TEMP_DIR=$(grep -l "k10temp" /sys/class/hwmon/hwmon*/name | xargs dirname | head -n 1)
FAN_DIR=$(grep -l "ayaneo_ec" /sys/class/hwmon/hwmon*/name | xargs dirname | head -n 1)

if [ -z "$TEMP_DIR" ] || [ -z "$FAN_DIR" ]; then exit 1; fi
if [ -f "$FAN_DIR/pwm1_enable" ]; then echo 1 > "$FAN_DIR/pwm1_enable"; fi

while true; do
    # Lê a ordem do painel (se não houver ordem, assume 'auto')
    MODE=$(cat /tmp/fan_mode 2>/dev/null || echo "auto")

    if [ "$MODE" = "auto" ]; then
        # Modo Automático (Curva Térmica)
        TEMP_RAW=$(cat "$TEMP_DIR/temp1_input" 2>/dev/null || echo 0)
        TEMP=$((TEMP_RAW / 1000))
        
        if [ "$TEMP" -ge 80 ]; then PWM=255
        elif [ "$TEMP" -ge 70 ]; then PWM=190
        elif [ "$TEMP" -ge 60 ]; then PWM=140
        elif [ "$TEMP" -ge 50 ]; then PWM=90
        else PWM=0; fi
    else
        # Modo Manual Fixo (Converte a porcentagem 1-100 para PWM 0-255)
        PWM=$((MODE * 255 / 100))
    fi

    echo $PWM > "$FAN_DIR/pwm1" 2>/dev/null
    sleep 3
done
