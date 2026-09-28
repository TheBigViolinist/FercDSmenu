-- FercDS: monitores padrão do AYANEO Flip DS.
--
-- É uma configuração subsidiária: o install.sh carrega este arquivo antes de
-- qualquer outra configuração de monitor do hyprland.lua. O hl.monitor do
-- Hyprland mescla chamadas para o mesmo output: se a shell (DMS etc.) ou você
-- definir o mesmo monitor depois, cada campo que ela passar vale no lugar do
-- daqui, e os campos que ela não mencionar continuam com o valor daqui.

hl.monitor({ output = "eDP-1", mode = "1080x1920@89.999", position = "0x0", scale = 1.6, transform = 1, vrr = 0, bitdepth = 10 })
hl.monitor({ output = "DP-1", mode = "1080x1620@60.012", position = "207x675", scale = 2, transform = 1, vrr = 0 })
