-- Hyprland configuration (Lua) — https://wiki.hypr.land/Configuring/Start/
--
-- FercDS: execs, telas de toque e regras. Os atalhos ficam no bindsfercds.lua,
-- menos o SUPER + M, que é daqui. O install.sh põe este arquivo no fim do
-- hyprland.lua.


-- Execs
hl.on("hyprland.start", function()
	hl.exec_cmd("/usr/local/bin/cprofile.sh")

	hl.exec_cmd("/usr/local/bin/toggle_fercds.sh")
end)
hl.workspace_rule({ workspace = "name:secondscreen", monitor = "DP-1", persistent = true})
hl.device({
	name = "ftcs1000:00-2808:1015",
	output = "eDP-1",
	transform = 1
})
hl.device({
	name = "goodix-capacitive-touchscreen-1",
	output = "DP-1",
	transform = 1
})

-- O unbind tira o atalho que a shell (DMS etc.) tenha posto no SUPER + M.
hl.unbind("SUPER + M")
hl.bind("SUPER + M", hl.dsp.exec_cmd("/usr/local/bin/toggle_monitor.sh"), {locked = true})
hl.layer_rule({ match = { namespace = "wvkbd" }, above_lock = 2 })

-- unscale XWayland
hl.config({
  xwayland = {
    force_zero_scaling = true
  }
})

hl.env("XDG_MENU_PREFIX", "plasma-")
hl.env("QT_QPA_PLATFORMTHEME", "kde", true)
