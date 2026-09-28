# shellcheck shell=bash
# shellcheck disable=SC2034  # o MSG é lido pela função t, no lib.sh
# Instalador de FercDS - Español. Si falta una clave aquí, sale en inglés (en.sh).
# %s se reemplaza por los argumentos (printf).
declare -gA MSG

# --- UI ------------------------------------------------------------------------
MSG[ui.tagline]="menú del AYANEO Flip DS para Hyprland"
MSG[ui.yes_letter]="S"
MSG[ui.no_letter]="N"
MSG[ui.press_enter]="Enter para volver al menú..."
MSG[ui.interrupted]="interrumpido"
MSG[ask.no_tty]="no hay terminal para preguntar: se responde que no (usa --yes para aceptar las respuestas por defecto)"
MSG[ask.invalid]="responde s o n"
MSG[sudo.needed]="algunos pasos modifican el sistema: sudo te pedirá la contraseña"
MSG[sudo.failed]="sin sudo no se puede continuar"

MSG[file.missing_in_repo]="falta en el repo: %s"
MSG[file.unchanged]="sin cambios   %s"
MSG[file.installed]="instalado     %s"
MSG[file.updated]="actualizado   %s"

# --- MENÚ ----------------------------------------------------------------------
MSG[title.menu]="instalador"
MSG[title.install]="instalación"
MSG[title.update]="actualización"
MSG[title.setup]="setup del hyprland.lua"
MSG[title.status]="estado"

MSG[menu.install]="Instalar"
MSG[menu.install_desc]="instala todo, paso a paso"
MSG[menu.update]="Actualizar"
MSG[menu.update_desc]="reemplaza los archivos por la versión de este repo"
MSG[menu.setup]="Setup"
MSG[menu.setup_desc]="conecta FercDS al hyprland.lua"
MSG[menu.status]="Estado"
MSG[menu.status_desc]="muestra lo que está instalado"
MSG[menu.language]="Idioma"
MSG[menu.language_desc]="cambia el idioma del instalador"
MSG[menu.quit]="Salir"
MSG[menu.choose]="Elige una opción: "

MSG[args.unknown]="opción desconocida: %s"
MSG[args.bad_lang]="--lang acepta en, pt, es o it"
MSG[help.text]="FercDS - instalador, actualizador y setup.

uso: ./install.sh [install|update|setup|status] [--yes] [--no-git] [--lang en|pt|es|it]

  (nada)     abre el menú
  install    instala todo, paso a paso, pidiendo confirmación en cada uno
  update     comprueba los paquetes, reemplaza los archivos instalados por los de
             este repo y actualiza/activa el servicio y el sudoers
  setup      conecta FercDS al hyprland.lua (solo añade lo que falta)
  status     muestra lo que está instalado y lo que difiere del repo

  --yes      acepta la respuesta por defecto de todas las preguntas
  --no-git   en el update, no busca una versión nueva en GitHub
  --lang     idioma del instalador, sin preguntar (en, pt, es, it)

Ejecútalo con tu usuario (sin sudo): el instalador pide la contraseña cuando la necesita."

# --- PASOS ---------------------------------------------------------------------
MSG[step.run_q]="¿Ejecutar este paso?"
MSG[step.skipped]="paso omitido"
MSG[step.cmd_failed]="el último comando falló (código %s)"
MSG[step.failed]="\"%s\" no terminó"
MSG[step.continue_q]="¿Continuar de todos modos?"

MSG[step.etapa_dependencias.title]="Dependencias del sistema"
MSG[step.etapa_dependencias.desc]="Paquetes oficiales que usan el menú y los scripts (pacman --needed):
%s"
MSG[step.etapa_inputplumber.title]="InputPlumber"
MSG[step.etapa_inputplumber.desc]="Instala inputplumber desde el repositorio extra y activa su servicio
(es el que cambia el mando entre los perfiles desktop y gamepad)."
MSG[step.etapa_wvkbd.title]="Teclado en pantalla (wvkbd-fercds)"
MSG[step.etapa_wvkbd.desc]="Compila e instala el fork wvkbd2fercds (packaging/wvkbd-fercds), el teclado
que se abre directamente en la pantalla elegida (WVKBD_OUTPUT=DP-1)."
MSG[step.etapa_ryzenadj.title]="RyzenAdj"
MSG[step.etapa_ryzenadj.desc]="Compila e instala RyzenAdj v0.19.0 (packaging/ryzenadj-fercds), que el menú usa
para ajustar el TDP. Si ya hay un ryzenadj, solo pregunta si quieres recompilarlo."
MSG[step.etapa_scripts.title]="Scripts"
MSG[step.etapa_scripts.desc]="toggle_wvkbd.sh, libre_wvkbd.sh, cprofile.sh, toggle_monitor.sh y fercds-gyro
en /usr/local/bin; daemons del backend en %s."
MSG[step.etapa_menu.title]="Menú de FercDS"
MSG[step.etapa_menu.desc]="fercds_menu.py en %s, toggle_fercds.sh en /usr/local/bin y las traducciones
en ~/.config/ferc-ds (tus ajustes del menú no se tocan)."
MSG[step.etapa_perfis.title]="Perfiles de InputPlumber"
MSG[step.etapa_perfis.desc]="fercds_desktop.yaml y fercds_gamepad.yaml en /etc/inputplumber/profiles,
las rutas que cargan el menú y cprofile.sh."
MSG[step.etapa_servico.title]="Servicio del backend"
MSG[step.etapa_servico.desc]="Crea y activa %s: ventilador, GPU y EPP de la CPU arrancan con el sistema.
El giroscopio queda fuera (se activa desde el menú). Los servicios antiguos que
ejecuten los mismos daemons se desactivan, si lo confirmas."
MSG[step.etapa_sudoers.title]="sudo sin contraseña (giroscopio y TDP)"
MSG[step.etapa_sudoers.desc]="Crea %s permitiendo sin contraseña solo fercds-gyro y ryzenadj,
los dos comandos que el menú ejecuta con sudo. Se valida con visudo antes de aplicarse."
MSG[step.etapa_hypr_configs.title]="Configuración de Hyprland"
MSG[step.etapa_hypr_configs.desc]="bindsfercds.lua, fercds.lua y outputsfercds.lua en %s
(si modificaste alguno, tu versión va a la copia de seguridad)."
MSG[step.etapa_setup.title]="Conectar al hyprland.lua (setup)"
MSG[step.etapa_setup.desc]="Añade los require de FercDS al hyprland.lua: outputsfercds antes de los demás
ajustes de monitor (tu shell sigue al mando) y bindsfercds/fercds en las últimas
líneas. Muestra el diff y pregunta antes de guardar."

MSG[summary.title]="Resumen"
MSG[summary.skipped]="%s (omitido)"
MSG[summary.backups]="los archivos reemplazados se guardaron en %s"

MSG[env.root]="ejecútalo con tu usuario, sin sudo: el instalador pide la contraseña cuando la necesita"
MSG[env.root_detail]="(los archivos de Hyprland son de tu usuario y makepkg no se ejecuta como root)"
MSG[env.no_src]="no se encontró la carpeta src/ junto a install.sh"
MSG[env.no_pacman]="este instalador es para Arch Linux (o derivadas con pacman)"
MSG[env.no_sudo]="sudo no encontrado"

# --- INSTALACIÓN ---------------------------------------------------------------
MSG[install.plan]="Qué se va a hacer"
MSG[install.plan_hint]="cada paso explica lo que hace y pregunta antes de ejecutarse"
MSG[install.start_q]="¿Empezar la instalación?"
MSG[install.next]="Próximos pasos"
MSG[install.next_relogin]="cierra la sesión de Hyprland y vuelve a entrar: los execs de inicio (menú y"
MSG[install.next_relogin2]="perfil del mando) solo se ejecutan cuando Hyprland arranca"
MSG[install.next_f23]="F23 (botón AYA) abre y cierra el menú"

MSG[deps.all_installed]="todas las dependencias ya están instaladas"
MSG[deps.missing]="falta: %s"
MSG[ip.installed]="inputplumber ya instalado (%s)"
MSG[ip.service_active]="el servicio inputplumber ya está activo"
MSG[build.no_makepkg]="makepkg no encontrado: ejecuta antes el paso de dependencias (base-devel)"
MSG[build.compiling]="compilando %s en %s"
MSG[wvkbd.installed]="wvkbd de FercDS ya instalado (%s)"
MSG[wvkbd.rebuild_q]="¿Recompilar de todos modos (toma el último commit de wvkbd2fercds)?"
MSG[wvkbd.replace]="el wvkbd instalado no tiene selección de pantalla (WVKBD_OUTPUT); wvkbd-fercds lo reemplaza"
MSG[ryzenadj.installed]="ryzenadj ya instalado (%s)"
MSG[ryzenadj.rebuild_q]="¿Recompilar con el PKGBUILD de FercDS (RyzenAdj v0.19.0)?"

MSG[legacy.found]="hay servicios antiguos que ejecutan los mismos daemons y chocarían con %s:"
MSG[legacy.disable_q]="¿Desactivar estos servicios y guardar sus archivos en la copia de seguridad?"
MSG[legacy.kept]="servicios antiguos mantenidos: %s no se activará para no chocar con ellos"
MSG[legacy.done]="servicios antiguos desactivados (copias en %s)"
MSG[service.no_daemons]="los daemons aún no están instalados: ejecuta antes el paso de scripts"
MSG[service.up_to_date]="%s ya está activo y al día"
MSG[service.active]="%s activo"

MSG[sudoers.unsafe_path]="%s quedó fuera del sudo sin contraseña: el archivo (o una carpeta superior) no es solo de root"
MSG[sudoers.visudo_failed]="visudo rechazó la regla; no se cambió nada"
MSG[sudoers.written]="regla guardada en %s"
MSG[sudoers.bad_user]="el nombre de usuario \"%s\" no sirve en una regla de sudoers"
MSG[sudoers.no_ryzenadj]="ryzenadj no instalado: por ahora solo fercds-gyro entra en la regla"
MSG[sudoers.up_to_date]="%s ya está al día"
MSG[sudoers.new_rule]="regla nueva para %s:"
MSG[sudoers.write_q]="¿Guardar esta regla?"
MSG[sudoers.skipped]="sudoers sin cambios: el menú seguirá pidiendo contraseña para el giroscopio y el TDP"
MSG[sudoers.legacy_found]="%s (del antiguo install-fercds-gyro.sh) quedó redundante"
MSG[sudoers.legacy_remove_q]="¿Eliminar %s (queda una copia en la copia de seguridad)?"

# --- SETUP ---------------------------------------------------------------------
MSG[setup.sec]="Conectar FercDS a %s"
MSG[setup.block]="Setup del hyprland.lua"
MSG[setup.no_hyprland_lua]="no se encontró %s"
MSG[setup.needs_lua]="FercDS usa la configuración de Hyprland en Lua (hyprland.lua)"
MSG[setup.no_python]="el setup necesita python3 (paso de dependencias)"
MSG[setup.lua_missing]="los archivos .lua de FercDS aún no están en %s:"
MSG[setup.install_lua_q]="¿Instalar estos archivos ahora?"
MSG[setup.lua_missing_warn]="sin ellos, Hyprland mostrará errores en los require hasta que existan"
MSG[setup.nothing_to_do]="hyprland.lua ya carga FercDS: nada que hacer"
MSG[setup.changes]="cambios en %s:"
MSG[setup.diff_current]="hyprland.lua (actual)"
MSG[setup.diff_new]="hyprland.lua (nuevo)"
MSG[setup.write_q]="¿Guardar estos cambios en hyprland.lua?"
MSG[setup.not_written]="no se guardó nada"
MSG[setup.written]="hyprland.lua actualizado (el original está en %s)"
MSG[setup.reload_hint]="Hyprland se recarga solo cuando el archivo cambia; si no lo hace: hyprctl reload"

# --- ACTUALIZACIÓN -------------------------------------------------------------
MSG[update.sec_version]="Versión del repo"
MSG[update.sec_packages]="Paquetes (solo comprobación)"
MSG[update.sec_files]="Archivos de FercDS"
MSG[update.sec_service]="Servicio del backend"
MSG[update.sec_sudo]="sudo sin contraseña"
MSG[update.block_files]="Archivos"
MSG[update.block_service]="Servicio"
MSG[update.block_sudoers]="sudoers"
MSG[update.all_same]="todos los archivos ya son iguales a los del repo"
MSG[update.new]="nuevo      %s"
MSG[update.changed]="cambió     %s"
MSG[update.replace_q]="¿Reemplazarlos por los archivos del repo? (los antiguos van a la copia de seguridad)"
MSG[update.nothing_changed]="no se cambió nada"

MSG[git.pull_q]="¿Buscar antes una versión nueva en GitHub (%s)?"
MSG[git.pull_failed]="no se pudo actualizar con git; se sigue con los archivos que hay aquí"
MSG[git.restarting]="versión nueva descargada: reiniciando el actualizador con ella"
MSG[git.up_to_date]="el repo ya estaba en la versión más reciente"

MSG[menu.reopen_manual]="el menú está abierto: ciérralo y vuelve a abrirlo (F23) para usar la versión nueva"
MSG[menu.reopen_q]="El menú está abierto con la versión antigua. ¿Reabrirlo ahora?"
MSG[menu.reopened]="menú reabierto"

# --- COMPROBACIONES Y ESTADO ---------------------------------------------------
MSG[check.no_pacman]="pacman no encontrado: no se pueden comprobar los paquetes"
MSG[check.deps_ok]="dependencias e inputplumber instalados"
MSG[check.wvkbd_ok]="wvkbd de FercDS (%s)"
MSG[check.wvkbd_with_output]="con WVKBD_OUTPUT"
MSG[check.wvkbd_no_output]="wvkbd sin selección de pantalla: el teclado se abrirá en la pantalla con el foco"
MSG[check.wvkbd_missing]="wvkbd-fercds no instalado"
MSG[check.ryzenadj_ok]="ryzenadj (%s)"
MSG[check.ryzenadj_missing]="ryzenadj no instalado: el control de TDP del menú no funcionará"
MSG[check.ip_active]="servicio inputplumber activo"
MSG[check.ip_stopped]="servicio inputplumber detenido"
MSG[check.hint_install]="para instalar lo que falta: ./install.sh install (los pasos de paquetes)"
MSG[check.no_python]="no hay python3 para comprobar hyprland.lua"
MSG[check.setup_ok]="hyprland.lua carga FercDS (outputs al principio, binds y fercds al final)"
MSG[check.setup_needed]="hyprland.lua necesita un ajuste: ejecuta ./install.sh setup"

MSG[status.sec_version]="Versión"
MSG[status.repo_version]="en este repo:  %s"
MSG[status.installed_version]="instalada:     %s"
MSG[status.none]="ninguna"
MSG[status.sec_packages]="Paquetes"
MSG[status.sec_files]="Archivos"
MSG[status.file_differs]="%s  (distinto del repo)"
MSG[status.file_missing]="%s  (no instalado)"
MSG[status.hint_update]="para igualarlo al repo: ./install.sh update"
MSG[status.sec_services]="Servicios"
MSG[status.service_stopped]="%s habilitado, pero detenido (journalctl -u %s)"
MSG[status.service_inactive]="%s no está activo"
MSG[status.legacy_service]="servicio antiguo: %s (install/update ofrecen desactivarlo)"
MSG[status.sec_sudo]="sudo sin contraseña"
MSG[status.test_mode]="(modo de prueba: sin sudo para comprobar)"
MSG[status.gyro_ok]="fercds-gyro permitido"
MSG[status.gyro_pw]="fercds-gyro todavía pide contraseña"
MSG[status.ryzenadj_missing]="ryzenadj no instalado"
MSG[status.ryzenadj_ok]="ryzenadj permitido"
MSG[status.ryzenadj_pw]="ryzenadj todavía pide contraseña"
