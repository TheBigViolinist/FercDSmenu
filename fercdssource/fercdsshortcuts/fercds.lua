-- Hyprland configuration (Lua) — https://wiki.hypr.land/Configuring/Start/


-- Execs
hl.on("hyprland.start", function()
	hl.exec_cmd("~/.local/bin/scriptsfercos/cprofile.sh")

	hl.exec_cmd("~/.local/bin/fercds/menu/toggle_fercds.sh")
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

hl.layer_rule({ match = { namespace = "wvkbd" }, above_lock = 2 })

-- unscale XWayland
hl.config({
  xwayland = {
    force_zero_scaling = true
  }
})

hl.env("XDG_MENU_PREFIX", "plasma-")
hl.env("QT_QPA_PLATFORMTHEME", "kde", true)
