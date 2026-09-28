# shellcheck shell=bash
# shellcheck disable=SC2034  # o MSG é lido pela função t, no lib.sh
# FercDS installer - English. It is also the fallback for any key missing from
# the other languages. %s is replaced by the arguments (printf).
declare -gA MSG

# --- UI ------------------------------------------------------------------------
MSG[ui.tagline]="AYANEO Flip DS menu for Hyprland"
MSG[ui.yes_letter]="Y"
MSG[ui.no_letter]="N"
MSG[ui.press_enter]="Press Enter to go back to the menu..."
MSG[ui.interrupted]="interrupted"
MSG[ask.no_tty]="no terminal to ask on: answering no (use --yes to accept the defaults)"
MSG[ask.invalid]="answer y or n"
MSG[sudo.needed]="some steps change the system: sudo will ask for your password"
MSG[sudo.failed]="can't continue without sudo"

MSG[file.missing_in_repo]="missing from the repo: %s"
MSG[file.unchanged]="unchanged   %s"
MSG[file.installed]="installed   %s"
MSG[file.updated]="updated     %s"

# --- MENU ----------------------------------------------------------------------
MSG[title.menu]="installer"
MSG[title.install]="install"
MSG[title.update]="update"
MSG[title.setup]="hyprland.lua setup"
MSG[title.status]="status"

MSG[menu.install]="Install"
MSG[menu.install_desc]="installs everything, step by step"
MSG[menu.update]="Update"
MSG[menu.update_desc]="replaces the files with this repo's version"
MSG[menu.setup]="Setup"
MSG[menu.setup_desc]="hooks FercDS into hyprland.lua"
MSG[menu.status]="Status"
MSG[menu.status_desc]="shows what is installed"
MSG[menu.language]="Language"
MSG[menu.language_desc]="changes the installer language"
MSG[menu.quit]="Quit"
MSG[menu.choose]="Choose an option: "

MSG[args.unknown]="unknown option: %s"
MSG[args.bad_lang]="--lang takes en, pt, es or it"
MSG[help.text]="FercDS - installer, updater and setup.

usage: ./install.sh [install|update|setup|status] [--yes] [--no-git] [--lang en|pt|es|it]

  (nothing)  opens the menu
  install    installs everything, step by step, asking before each step
  update     checks the packages, replaces the installed files with this repo's
             and updates/enables the service and sudoers
  setup      hooks FercDS into hyprland.lua (only adds what is missing)
  status     shows what is installed and what differs from the repo

  --yes      accepts the default answer to every question
  --no-git   on update, doesn't look for a new version on GitHub
  --lang     installer language, without asking (en, pt, es, it)

Run it as your own user (no sudo): the installer asks for the password when needed."

# --- STEPS ---------------------------------------------------------------------
MSG[step.run_q]="Run this step?"
MSG[step.skipped]="step skipped"
MSG[step.cmd_failed]="the last command failed (exit code %s)"
MSG[step.failed]="\"%s\" did not finish"
MSG[step.continue_q]="Continue anyway?"

MSG[step.etapa_dependencias.title]="System dependencies"
MSG[step.etapa_dependencias.desc]="Official packages used by the menu and the scripts (pacman --needed):
%s"
MSG[step.etapa_inputplumber.title]="InputPlumber"
MSG[step.etapa_inputplumber.desc]="Installs inputplumber from the extra repository and enables its service
(it is what switches the controller between the desktop and gamepad profiles)."
MSG[step.etapa_wvkbd.title]="On-screen keyboard (wvkbd-fercds)"
MSG[step.etapa_wvkbd.desc]="Builds and installs the wvkbd2fercds fork (packaging/wvkbd-fercds), the keyboard
that opens straight on the chosen screen (WVKBD_OUTPUT=DP-1)."
MSG[step.etapa_ryzenadj.title]="RyzenAdj"
MSG[step.etapa_ryzenadj.desc]="Builds and installs RyzenAdj v0.19.0 (packaging/ryzenadj-fercds), which the menu
uses to set the TDP. If ryzenadj is already installed, it only asks whether to rebuild it."
MSG[step.etapa_scripts.title]="Scripts"
MSG[step.etapa_scripts.desc]="toggle_wvkbd.sh, libre_wvkbd.sh, cprofile.sh, toggle_monitor.sh and fercds-gyro
in /usr/local/bin; backend daemons in %s."
MSG[step.etapa_menu.title]="FercDS menu"
MSG[step.etapa_menu.desc]="fercds_menu.py in %s, toggle_fercds.sh in /usr/local/bin and the translations
in ~/.config/ferc-ds (your menu settings are left as they are)."
MSG[step.etapa_perfis.title]="InputPlumber profiles"
MSG[step.etapa_perfis.desc]="fercds_desktop.yaml and fercds_gamepad.yaml in /etc/inputplumber/profiles,
the paths the menu and cprofile.sh load."
MSG[step.etapa_servico.title]="Backend service"
MSG[step.etapa_servico.desc]="Creates and enables %s: fan, GPU and CPU EPP start at boot.
The gyro is left out (it is switched from the menu). Old services that run the same
daemons are disabled, after you confirm."
MSG[step.etapa_sudoers.title]="Passwordless sudo (gyro and TDP)"
MSG[step.etapa_sudoers.desc]="Creates %s allowing only fercds-gyro and ryzenadj without a password,
the two commands the menu runs with sudo. Checked with visudo before it takes effect."
MSG[step.etapa_hypr_configs.title]="Hyprland configs"
MSG[step.etapa_hypr_configs.desc]="bindsfercds.lua, fercds.lua and outputsfercds.lua in %s
(if you changed any of them, your version goes to the backup)."
MSG[step.etapa_setup.title]="Hook into hyprland.lua (setup)"
MSG[step.etapa_setup.desc]="Adds the FercDS require lines to hyprland.lua: outputsfercds before the other
monitor settings (your shell stays in charge) and bindsfercds/fercds on the last
lines. Shows the diff and asks before writing."

MSG[summary.title]="Summary"
MSG[summary.skipped]="%s (skipped)"
MSG[summary.backups]="replaced files were saved in %s"

MSG[env.root]="run it as your own user, without sudo: the installer asks for the password when needed"
MSG[env.root_detail]="(the Hyprland files belong to your user and makepkg doesn't run as root)"
MSG[env.no_src]="the src/ folder was not found next to install.sh"
MSG[env.no_pacman]="this installer is for Arch Linux (or derivatives with pacman)"
MSG[env.no_sudo]="sudo not found"

# --- INSTALL -------------------------------------------------------------------
MSG[install.plan]="What will be done"
MSG[install.plan_hint]="each step explains what it does and asks before running"
MSG[install.start_q]="Start the installation?"
MSG[install.next]="Next steps"
MSG[install.next_relogin]="log out and back into the Hyprland session: the startup execs (menu and"
MSG[install.next_relogin2]="controller profile) only run when Hyprland starts"
MSG[install.next_f23]="F23 (AYA button) opens and closes the menu"

MSG[deps.all_installed]="all dependencies are already installed"
MSG[deps.missing]="missing: %s"
MSG[ip.installed]="inputplumber already installed (%s)"
MSG[ip.service_active]="inputplumber service already running"
MSG[build.no_makepkg]="makepkg not found: run the dependencies step first (base-devel)"
MSG[build.compiling]="building %s in %s"
MSG[wvkbd.installed]="FercDS wvkbd already installed (%s)"
MSG[wvkbd.rebuild_q]="Rebuild anyway (gets the latest wvkbd2fercds commit)?"
MSG[wvkbd.replace]="the installed wvkbd has no screen selection (WVKBD_OUTPUT); wvkbd-fercds replaces it"
MSG[ryzenadj.installed]="ryzenadj already installed (%s)"
MSG[ryzenadj.rebuild_q]="Rebuild with the FercDS PKGBUILD (RyzenAdj v0.19.0)?"

MSG[legacy.found]="old services run the same daemons and would fight with %s:"
MSG[legacy.disable_q]="Disable these services and keep their files in the backup?"
MSG[legacy.kept]="old services kept: %s won't be enabled, so they don't fight"
MSG[legacy.done]="old services disabled (copies in %s)"
MSG[service.no_daemons]="the daemons are not installed yet: run the scripts step first"
MSG[service.up_to_date]="%s is already running and up to date"
MSG[service.active]="%s running"

MSG[sudoers.unsafe_path]="%s was left out of passwordless sudo: the file (or a folder above it) is not owned by root alone"
MSG[sudoers.visudo_failed]="visudo rejected the rule; nothing was changed"
MSG[sudoers.written]="rule written to %s"
MSG[sudoers.bad_user]="the user name \"%s\" can't be used in a sudoers rule"
MSG[sudoers.no_ryzenadj]="ryzenadj not installed: for now only fercds-gyro goes into the rule"
MSG[sudoers.up_to_date]="%s is already up to date"
MSG[sudoers.new_rule]="new rule for %s:"
MSG[sudoers.write_q]="Write this rule?"
MSG[sudoers.skipped]="sudoers unchanged: the menu will keep asking for a password for the gyro and the TDP"
MSG[sudoers.legacy_found]="%s (from the old install-fercds-gyro.sh) is now redundant"
MSG[sudoers.legacy_remove_q]="Remove %s (a copy stays in the backup)?"

# --- SETUP ---------------------------------------------------------------------
MSG[setup.sec]="Hook FercDS into %s"
MSG[setup.block]="hyprland.lua setup"
MSG[setup.no_hyprland_lua]="%s not found"
MSG[setup.needs_lua]="FercDS uses the Lua Hyprland config (hyprland.lua)"
MSG[setup.no_python]="setup needs python3 (dependencies step)"
MSG[setup.lua_missing]="the FercDS .lua files are not in %s yet:"
MSG[setup.install_lua_q]="Install these files now?"
MSG[setup.lua_missing_warn]="without them, Hyprland will report errors on the require lines until they exist"
MSG[setup.nothing_to_do]="hyprland.lua already loads FercDS: nothing to do"
MSG[setup.changes]="changes to %s:"
MSG[setup.diff_current]="hyprland.lua (current)"
MSG[setup.diff_new]="hyprland.lua (new)"
MSG[setup.write_q]="Write these changes to hyprland.lua?"
MSG[setup.not_written]="nothing was written"
MSG[setup.written]="hyprland.lua updated (the original is in %s)"
MSG[setup.reload_hint]="Hyprland reloads by itself when the file changes; if it doesn't: hyprctl reload"

# --- UPDATE --------------------------------------------------------------------
MSG[update.sec_version]="Repo version"
MSG[update.sec_packages]="Packages (check only)"
MSG[update.sec_files]="FercDS files"
MSG[update.sec_service]="Backend service"
MSG[update.sec_sudo]="Passwordless sudo"
MSG[update.block_files]="Files"
MSG[update.block_service]="Service"
MSG[update.block_sudoers]="sudoers"
MSG[update.all_same]="all files already match the repo"
MSG[update.new]="new       %s"
MSG[update.changed]="changed   %s"
MSG[update.replace_q]="Replace them with the repo files? (the old ones go to the backup)"
MSG[update.nothing_changed]="nothing was changed"

MSG[git.pull_q]="Look for a newer version on GitHub first (%s)?"
MSG[git.pull_failed]="couldn't update through git; going on with the files that are here"
MSG[git.restarting]="new version downloaded: restarting the updater with it"
MSG[git.up_to_date]="the repo was already up to date"

MSG[menu.reopen_manual]="the menu is open: close it and open it again (F23) to use the new version"
MSG[menu.reopen_q]="The menu is open with the old version. Reopen it now?"
MSG[menu.reopened]="menu reopened"

# --- CHECKS AND STATUS ---------------------------------------------------------
MSG[check.no_pacman]="pacman not found: can't check the packages"
MSG[check.deps_ok]="dependencies and inputplumber installed"
MSG[check.wvkbd_ok]="FercDS wvkbd (%s)"
MSG[check.wvkbd_with_output]="with WVKBD_OUTPUT"
MSG[check.wvkbd_no_output]="wvkbd without screen selection: the keyboard will open on the focused screen"
MSG[check.wvkbd_missing]="wvkbd-fercds not installed"
MSG[check.ryzenadj_ok]="ryzenadj (%s)"
MSG[check.ryzenadj_missing]="ryzenadj not installed: the menu's TDP control won't work"
MSG[check.ip_active]="inputplumber service running"
MSG[check.ip_stopped]="inputplumber service stopped"
MSG[check.hint_install]="to install what is missing: ./install.sh install (the package steps)"
MSG[check.no_python]="no python3 to check hyprland.lua"
MSG[check.setup_ok]="hyprland.lua loads FercDS (outputs at the top, binds and fercds at the end)"
MSG[check.setup_needed]="hyprland.lua needs adjusting: run ./install.sh setup"

MSG[status.sec_version]="Version"
MSG[status.repo_version]="in this repo:  %s"
MSG[status.installed_version]="installed:     %s"
MSG[status.none]="none"
MSG[status.sec_packages]="Packages"
MSG[status.sec_files]="Files"
MSG[status.file_differs]="%s  (differs from the repo)"
MSG[status.file_missing]="%s  (not installed)"
MSG[status.hint_update]="to match the repo: ./install.sh update"
MSG[status.sec_services]="Services"
MSG[status.service_stopped]="%s enabled, but stopped (journalctl -u %s)"
MSG[status.service_inactive]="%s is not running"
MSG[status.legacy_service]="old service: %s (install/update offer to disable it)"
MSG[status.sec_sudo]="Passwordless sudo"
MSG[status.test_mode]="(test mode: no sudo to check with)"
MSG[status.gyro_ok]="fercds-gyro allowed"
MSG[status.gyro_pw]="fercds-gyro still asks for a password"
MSG[status.ryzenadj_missing]="ryzenadj not installed"
MSG[status.ryzenadj_ok]="ryzenadj allowed"
MSG[status.ryzenadj_pw]="ryzenadj still asks for a password"
