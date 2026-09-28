-- FercDS: atalhos. Cada tecla daqui primeiro se desliga (hl.unbind), para
-- passar por cima do atalho que a shell (DMS etc.) tenha posto nela, e só
-- depois recebe o do FercDS. O install.sh põe este arquivo no fim do
-- hyprland.lua; a ordem em relação ao fercds.lua não importa, porque nenhuma
-- tecla é configurada nos dois.

hl.unbind("F23")
hl.bind("F23", hl.dsp.exec_cmd("/usr/local/bin/toggle_fercds.sh"))
hl.unbind("SUPER + D")
hl.bind("SUPER + D", hl.dsp.exec_cmd("/usr/local/bin/toggle_wvkbd.sh"), { locked = true, description = "Keyboard" })
hl.unbind("SUPER + G")
hl.bind("SUPER + G", hl.dsp.exec_cmd("/usr/local/bin/cprofile.sh"), { locked = true })
hl.unbind("SUPER + Return")
hl.bind("SUPER + Return", hl.dsp.exec_cmd("kitty"))
hl.unbind("F19")
hl.bind("F19", hl.dsp.focus({ workspace = "m+1" }))
hl.bind("F19", hl.dsp.exec_cmd("paplay ~/.local/share/sounds/nintendold/stereo/desktop-switch-right.wav"))
hl.unbind("F24")
hl.bind("F24", hl.dsp.focus({ workspace = "m-1" }))
hl.bind("F24", hl.dsp.exec_cmd("paplay ~/.local/share/sounds/nintendold/stereo/desktop-switch-right.wav"))
hl.unbind("SUPER + CTRL + Q")
hl.bind("SUPER + CTRL + Q", hl.dsp.window.kill(), { description = "Force Kill Window" })
hl.unbind("SUPER + Q")
hl.bind("SUPER + Q", hl.dsp.window.close(), { description = "Close Window (by selector)" })
hl.unbind("SUPER + T")
hl.unbind("SUPER + mouse:273")
hl.unbind("SUPER + CTRL + D")
hl.bind("SUPER + CTRL + D", hl.dsp.exec_cmd("/usr/local/bin/libre_wvkbd.sh"))
