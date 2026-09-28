# FercDS

A menu and a set of tools for using the **AYANEO Flip DS / Flip 1S DS** with **Hyprland**: a panel that stays on the bottom screen, TDP, fan and GPU control, controller profile switching, gyro, an on-screen keyboard and shortcuts built around the device's buttons.

> Work in progress.

## What's included

| Part | What it does |
|---|---|
| **Menu** (`fercds_menu.py`) | A GTK panel that opens on its own on the bottom screen (DP-1): app library, hardware (TDP, CPU, GPU, fan), media, open windows, gyro and language. |
| **Backend** (`fercds-backend.service`) | Applies to the hardware what the menu asks for: fan curve, GPU clock and CPU EPP. Starts at boot. |
| **Gyro** (`fercds-gyro`) | Turns the gyroscope on and off from the menu. Turning it off saves battery. |
| **InputPlumber profiles** | *Desktop* (the controller becomes a mouse and keyboard) and *gamepad*, switched from the menu or with SUPER + G. |
| **On-screen keyboard** (`wvkbd-fercds`) | A fork of [wvkbd](https://github.com/jjsullivan5196/wvkbd) that opens straight on the bottom screen. |
| **RyzenAdj** | TDP control (the menu calls `ryzenadj`). |
| **Hyprland configs** | Shortcuts, touchscreens and default monitor settings. |

## Requirements

- Arch Linux, or a derivative with `pacman`
- Hyprland with a **Lua** config (`~/.config/hypr/hyprland.lua`)
- AYANEO Flip DS or Flip 1S DS (screens `eDP-1` and `DP-1`)

## Installation

```bash
git clone https://github.com/TheBigViolinist/FercDSmenu.git
cd FercDSmenu
./install.sh
```

1. The installer first asks for its language: **English, Português, Español or Italiano**. Enter keeps the last one you picked (or your system language, the first time).
2. In the menu, choose **1 · Install**. Before starting, it lists every step; then, for each one, it explains what it will do and asks before running it (you can skip any step).

- Run it as **your own user**, without `sudo`. The installer asks for your password when it needs it.
- When it's done, **log out and back into** your Hyprland session: the menu and the controller profile start together with Hyprland.
- The **AYA** button (F23) opens and closes the menu.

### The steps

| # | Step | What it does |
|---|---|---|
| 1 | Dependencies | Installs with `pacman` what the menu and the scripts use (GTK, gtk-layer-shell, python-psutil, jq, playerctl…). |
| 2 | InputPlumber | Installs `inputplumber` (from the `extra` repository) and enables its service. |
| 3 | On-screen keyboard | Builds and installs `wvkbd-fercds` ([wvkbd2fercds](https://github.com/TheBigViolinist/wvkbd2fercds)). |
| 4 | RyzenAdj | Builds and installs RyzenAdj v0.19.0. If you already have `ryzenadj`, it only asks whether to rebuild it. |
| 5 | Scripts | Scripts in `/usr/local/bin` and the backend daemons in `/usr/local/lib/fercds/backend`. |
| 6 | Menu | The menu in `/usr/local/lib/fercds`, `toggle_fercds.sh` in `/usr/local/bin` and the translations in `~/.config/ferc-ds`. |
| 7 | Profiles | `fercds_desktop.yaml` and `fercds_gamepad.yaml` in `/etc/inputplumber/profiles`. |
| 8 | Service | Creates and enables `fercds-backend.service`. Old services that run the same daemons are disabled, if you confirm. |
| 9 | Passwordless sudo | Allows `fercds-gyro` and `ryzenadj` without a password (the only two commands the menu runs with `sudo`). |
| 10 | Hyprland configs | `bindsfercds.lua`, `fercds.lua` and `outputsfercds.lua` in `~/.config/hypr/fercdshypr`. |
| 11 | Setup | Hooks FercDS into `hyprland.lua` (see below). Shows the diff before writing. |

## Updating

```bash
cd FercDSmenu
./install.sh update
```

The updater:

1. offers to download the newest version from GitHub (`git pull`);
2. checks the packages (only checks; to install what's missing, use `install`);
3. shows which FercDS files changed and, if you confirm, replaces only those (the old ones go to the backup);
4. creates and enables the service if it doesn't exist yet, or restarts it if a daemon changed;
5. updates the sudo rule;
6. checks `hyprland.lua`;
7. reopens the menu if it was open with the old version.

Changed a file in `src/`? Run `./install.sh update` to put it on your machine.

## hyprland.lua setup

`./install.sh setup` adds the FercDS `require` lines to `hyprland.lua`. If some of them are already there, it only adds the missing ones.

```lua
-- at the top, before any other monitor setting
require("fercdshypr.outputsfercds")

-- ... the rest of your config (DMS etc.) ...

-- on the last lines
require("fercdshypr.bindsfercds")
require("fercdshypr.fercds")
```

- **`outputsfercds` comes first, as a default.** Hyprland's `hl.monitor` merges settings for the same monitor and the last one wins. So if your shell (DMS, for example) changes the monitors, whatever it sets takes priority, and FercDS only fills in what it doesn't set.
- **`bindsfercds` and `fercds` go last**, so the FercDS shortcuts override the shell's.
- A `require` in the wrong place is commented out, never deleted. The original `hyprland.lua` goes to the backup.

## Commands

```
./install.sh [install|update|setup|status] [--yes] [--no-git] [--lang en|pt|es|it]
```

| Command | |
|---|---|
| *(none)* | Opens the installer menu. |
| `install` | Full installation, step by step. |
| `update` | Updates the files, the service and the sudo rule. |
| `setup` | Hooks FercDS into `hyprland.lua`. |
| `status` | Shows what is installed and what differs from the repo. |
| `--yes` | Accepts the default answer to every question. |
| `--no-git` | On `update`, doesn't look for a new version on GitHub. |
| `--lang` | Installer language (`en`, `pt`, `es`, `it`), without asking. |

## Shortcuts

| Key | Action |
|---|---|
| **F23** (AYA button) | Opens and closes the menu |
| **SUPER + D** | On-screen keyboard on the bottom screen |
| **SUPER + CTRL + D** | On-screen keyboard on the focused screen |
| **SUPER + G** | Switches the controller profile (desktop ↔ gamepad) |
| **SUPER + M** | Turns the bottom screen on and off |
| **F19 / F24** (bumpers in desktop mode) | Next / previous workspace |
| **SUPER + Q** | Closes the window |
| **SUPER + CTRL + Q** | Force-closes the window |
| **SUPER + Return** | Terminal (kitty) |

## Where everything goes

| Path | Contents |
|---|---|
| `/usr/local/bin/` | `toggle_fercds.sh`, `toggle_wvkbd.sh`, `libre_wvkbd.sh`, `cprofile.sh`, `toggle_monitor.sh`, `fercds-gyro` |
| `/usr/local/lib/fercds/` | `fercds_menu.py` and `backend/` (the service's daemons) |
| `/etc/systemd/system/fercds-backend.service` | Backend service |
| `/etc/inputplumber/profiles/` | `fercds_desktop.yaml` and `fercds_gamepad.yaml` profiles |
| `/etc/sudoers.d/fercds` | Passwordless sudo rule |
| `~/.config/hypr/fercdshypr/` | `bindsfercds.lua`, `fercds.lua`, `outputsfercds.lua` |
| `~/.config/ferc-ds/` | Translations and your menu settings (language, categories, pinned apps) |
| `~/.fercds/customapps/` | Your extra `.desktop` files for the menu's library |
| `~/.local/state/fercds/backups/` | Copies of everything the installer replaced, one folder per run |
| `~/.local/state/fercds/lang` | The installer language you picked last |

## Troubleshooting

- **The TDP doesn't change.** `ryzenadj` needs access to the processor's SMU: it tries the `ryzen_smu` module first and then `/dev/mem`, which some kernels block. Install `ryzen_smu-dkms-git` (AUR) or add `iomem=relaxed` to your kernel parameters.
- **The keyboard opens on the wrong screen.** Run `./install.sh status`: the keyboard has to be `wvkbd-fercds`, the only one that knows the `WVKBD_OUTPUT` variable.
- **The fan, GPU or EPP don't respond.** Check the service log: `journalctl -u fercds-backend`. If the device lacks a feature, the matching daemon keeps retrying every 5 minutes without affecting the others.
- **The gyro is greyed out in the menu.** `fercds-gyro status` couldn't find the sensor (`i2c-BOSC0200:00`).

## Repository layout

```
FercDSmenu/
├── install.sh              installer, updater and setup
├── installer/              installer parts
│   ├── lib.sh              terminal UI and utilities
│   ├── manifest.sh         what goes where
│   ├── steps.sh            the steps
│   ├── hypr_setup.py       edits hyprland.lua
│   └── lang/               installer texts (en, pt, es, it)
├── packaging/              PKGBUILDs built by the installer
│   ├── wvkbd-fercds/
│   └── ryzenadj-fercds/
└── src/                    everything that gets installed
    ├── menu/               fercds_menu.py and toggle_fercds.sh
    ├── scripts/            shortcuts (keyboard, profile, screen)
    ├── backend/            the service's daemons and fercds-gyro
    ├── systemd/            fercds-backend.service
    ├── inputplumber/       desktop and gamepad profiles
    ├── hypr/               Hyprland configs in Lua
    └── config/             menu translations
```

- New file in `src/`? Add a line to `installer/manifest.sh` (source, destination and permissions) so the installer starts copying it.
- New installer message? Add the key to every file in `installer/lang/` (`en.sh` is the fallback for any key missing from the others).

## Credits

- [wvkbd](https://github.com/jjsullivan5196/wvkbd) (jjsullivan5196), with the screen selection from the [niteria/wvkbd](https://github.com/niteria/wvkbd) fork, in [wvkbd2fercds](https://github.com/TheBigViolinist/wvkbd2fercds): GPL-3.0-or-later
- [RyzenAdj](https://github.com/FlyGoat/RyzenAdj) (FlyGoat): LGPL-3.0
- [InputPlumber](https://github.com/ShadowBlip/InputPlumber) (ShadowBlip)
