# shellcheck shell=bash
# shellcheck disable=SC2034  # o MSG é lido pela função t, no lib.sh
# Installer di FercDS - Italiano. Se qui manca una chiave, esce in inglese (en.sh).
# %s viene sostituito dagli argomenti (printf).
declare -gA MSG

# --- UI ------------------------------------------------------------------------
MSG[ui.tagline]="menu dell'AYANEO Flip DS per Hyprland"
MSG[ui.yes_letter]="S"
MSG[ui.no_letter]="N"
MSG[ui.press_enter]="Invio per tornare al menu..."
MSG[ui.interrupted]="interrotto"
MSG[ask.no_tty]="nessun terminale su cui chiedere: rispondo no (usa --yes per accettare le risposte predefinite)"
MSG[ask.invalid]="rispondi s o n"
MSG[sudo.needed]="alcuni passaggi modificano il sistema: sudo chiederà la tua password"
MSG[sudo.failed]="senza sudo non si può continuare"

MSG[file.missing_in_repo]="manca nel repo: %s"
MSG[file.unchanged]="invariato    %s"
MSG[file.installed]="installato   %s"
MSG[file.updated]="aggiornato   %s"

# --- MENU ----------------------------------------------------------------------
MSG[title.menu]="installer"
MSG[title.install]="installazione"
MSG[title.update]="aggiornamento"
MSG[title.setup]="setup di hyprland.lua"
MSG[title.status]="stato"

MSG[menu.install]="Installa"
MSG[menu.install_desc]="installa tutto, un passaggio alla volta"
MSG[menu.update]="Aggiorna"
MSG[menu.update_desc]="sostituisce i file con la versione di questo repo"
MSG[menu.setup]="Setup"
MSG[menu.setup_desc]="collega FercDS a hyprland.lua"
MSG[menu.status]="Stato"
MSG[menu.status_desc]="mostra cosa è installato"
MSG[menu.language]="Lingua"
MSG[menu.language_desc]="cambia la lingua dell'installer"
MSG[menu.quit]="Esci"
MSG[menu.choose]="Scegli un'opzione: "

MSG[args.unknown]="opzione sconosciuta: %s"
MSG[args.bad_lang]="--lang accetta en, pt, es o it"
MSG[help.text]="FercDS - installer, aggiornamento e setup.

uso: ./install.sh [install|update|setup|status] [--yes] [--no-git] [--lang en|pt|es|it]

  (niente)   apre il menu
  install    installa tutto, un passaggio alla volta, chiedendo conferma per ognuno
  update     verifica i pacchetti, sostituisce i file installati con quelli di
             questo repo e aggiorna/attiva il servizio e il sudoers
  setup      collega FercDS a hyprland.lua (aggiunge solo ciò che manca)
  status     mostra cosa è installato e cosa è diverso dal repo

  --yes      accetta la risposta predefinita di tutte le domande
  --no-git   nell'update, non cerca una nuova versione su GitHub
  --lang     lingua dell'installer, senza chiedere (en, pt, es, it)

Eseguilo con il tuo utente (senza sudo): l'installer chiede la password quando serve."

# --- PASSAGGI ------------------------------------------------------------------
MSG[step.run_q]="Eseguire questo passaggio?"
MSG[step.skipped]="passaggio saltato"
MSG[step.cmd_failed]="l'ultimo comando è fallito (codice %s)"
MSG[step.failed]="\"%s\" non è stato completato"
MSG[step.continue_q]="Continuare comunque?"

MSG[step.etapa_dependencias.title]="Dipendenze di sistema"
MSG[step.etapa_dependencias.desc]="Pacchetti ufficiali usati dal menu e dagli script (pacman --needed):
%s"
MSG[step.etapa_inputplumber.title]="InputPlumber"
MSG[step.etapa_inputplumber.desc]="Installa inputplumber dal repository extra e ne attiva il servizio
(è lui che passa il controller dal profilo desktop a quello gamepad)."
MSG[step.etapa_wvkbd.title]="Tastiera a schermo (wvkbd-fercds)"
MSG[step.etapa_wvkbd.desc]="Compila e installa il fork wvkbd2fercds (packaging/wvkbd-fercds), la tastiera
che si apre direttamente sullo schermo scelto (WVKBD_OUTPUT=DP-1)."
MSG[step.etapa_ryzenadj.title]="RyzenAdj"
MSG[step.etapa_ryzenadj.desc]="Compila e installa RyzenAdj v0.19.0 (packaging/ryzenadj-fercds), che il menu usa
per regolare il TDP. Se ryzenadj è già installato, chiede solo se ricompilarlo."
MSG[step.etapa_scripts.title]="Script"
MSG[step.etapa_scripts.desc]="toggle_wvkbd.sh, libre_wvkbd.sh, cprofile.sh, toggle_monitor.sh e fercds-gyro
in /usr/local/bin; demoni del backend in %s."
MSG[step.etapa_menu.title]="Menu di FercDS"
MSG[step.etapa_menu.desc]="fercds_menu.py in %s, toggle_fercds.sh in /usr/local/bin e le traduzioni
in ~/.config/ferc-ds (le tue impostazioni del menu restano come sono)."
MSG[step.etapa_perfis.title]="Profili di InputPlumber"
MSG[step.etapa_perfis.desc]="fercds_desktop.yaml e fercds_gamepad.yaml in /etc/inputplumber/profiles,
i percorsi che il menu e cprofile.sh caricano."
MSG[step.etapa_servico.title]="Servizio del backend"
MSG[step.etapa_servico.desc]="Crea e attiva %s: ventola, GPU ed EPP della CPU partono all'avvio.
Il giroscopio resta fuori (si attiva dal menu). I vecchi servizi che eseguono gli
stessi demoni vengono disattivati, se confermi."
MSG[step.etapa_sudoers.title]="sudo senza password (giroscopio e TDP)"
MSG[step.etapa_sudoers.desc]="Crea %s che consente senza password solo fercds-gyro e ryzenadj,
i due comandi che il menu esegue con sudo. Verificato con visudo prima di entrare in vigore."
MSG[step.etapa_hypr_configs.title]="Configurazioni di Hyprland"
MSG[step.etapa_hypr_configs.desc]="bindsfercds.lua, fercds.lua e outputsfercds.lua in %s
(se ne hai modificato qualcuno, la tua versione va nel backup)."
MSG[step.etapa_setup.title]="Collegare a hyprland.lua (setup)"
MSG[step.etapa_setup.desc]="Aggiunge i require di FercDS a hyprland.lua: outputsfercds prima delle altre
impostazioni dei monitor (comanda sempre la tua shell) e bindsfercds/fercds nelle
ultime righe. Mostra il diff e chiede prima di salvare."

MSG[summary.title]="Riepilogo"
MSG[summary.skipped]="%s (saltato)"
MSG[summary.backups]="i file sostituiti sono stati salvati in %s"

MSG[env.root]="eseguilo con il tuo utente, senza sudo: l'installer chiede la password quando serve"
MSG[env.root_detail]="(i file di Hyprland appartengono al tuo utente e makepkg non gira come root)"
MSG[env.no_src]="cartella src/ non trovata accanto a install.sh"
MSG[env.no_pacman]="questo installer è per Arch Linux (o derivate con pacman)"
MSG[env.no_sudo]="sudo non trovato"

# --- INSTALLAZIONE -------------------------------------------------------------
MSG[install.plan]="Cosa verrà fatto"
MSG[install.plan_hint]="ogni passaggio spiega cosa fa e chiede prima di partire"
MSG[install.start_q]="Iniziare l'installazione?"
MSG[install.next]="Prossimi passi"
MSG[install.next_relogin]="esci e rientra nella sessione di Hyprland: gli exec di avvio (menu e profilo"
MSG[install.next_relogin2]="del controller) partono solo quando si avvia Hyprland"
MSG[install.next_f23]="F23 (tasto AYA) apre e chiude il menu"

MSG[deps.all_installed]="tutte le dipendenze sono già installate"
MSG[deps.missing]="manca: %s"
MSG[ip.installed]="inputplumber già installato (%s)"
MSG[ip.service_active]="il servizio inputplumber è già attivo"
MSG[build.no_makepkg]="makepkg non trovato: esegui prima il passaggio delle dipendenze (base-devel)"
MSG[build.compiling]="compilazione di %s in %s"
MSG[wvkbd.installed]="wvkbd di FercDS già installato (%s)"
MSG[wvkbd.rebuild_q]="Ricompilare comunque (prende l'ultimo commit di wvkbd2fercds)?"
MSG[wvkbd.replace]="il wvkbd installato non ha la selezione dello schermo (WVKBD_OUTPUT); wvkbd-fercds lo sostituisce"
MSG[ryzenadj.installed]="ryzenadj già installato (%s)"
MSG[ryzenadj.rebuild_q]="Ricompilare con il PKGBUILD di FercDS (RyzenAdj v0.19.0)?"

MSG[legacy.found]="alcuni vecchi servizi eseguono gli stessi demoni e andrebbero in conflitto con %s:"
MSG[legacy.disable_q]="Disattivare questi servizi e conservarne i file nel backup?"
MSG[legacy.kept]="vecchi servizi mantenuti: %s non verrà attivato, per evitare conflitti"
MSG[legacy.done]="vecchi servizi disattivati (copie in %s)"
MSG[service.no_daemons]="i demoni non sono ancora installati: esegui prima il passaggio degli script"
MSG[service.up_to_date]="%s è già attivo e aggiornato"
MSG[service.active]="%s attivo"

MSG[sudoers.unsafe_path]="%s escluso dal sudo senza password: il file (o una cartella superiore) non appartiene solo a root"
MSG[sudoers.visudo_failed]="visudo ha rifiutato la regola; non è stato cambiato nulla"
MSG[sudoers.written]="regola salvata in %s"
MSG[sudoers.bad_user]="il nome utente \"%s\" non è valido in una regola di sudoers"
MSG[sudoers.no_ryzenadj]="ryzenadj non installato: per ora nella regola entra solo fercds-gyro"
MSG[sudoers.up_to_date]="%s è già aggiornato"
MSG[sudoers.new_rule]="nuova regola per %s:"
MSG[sudoers.write_q]="Salvare questa regola?"
MSG[sudoers.skipped]="sudoers invariato: il menu continuerà a chiedere la password per il giroscopio e il TDP"
MSG[sudoers.legacy_found]="%s (del vecchio install-fercds-gyro.sh) ora è superfluo"
MSG[sudoers.legacy_remove_q]="Rimuovere %s (ne resta una copia nel backup)?"

# --- SETUP ---------------------------------------------------------------------
MSG[setup.sec]="Collegare FercDS a %s"
MSG[setup.block]="Setup di hyprland.lua"
MSG[setup.no_hyprland_lua]="%s non trovato"
MSG[setup.needs_lua]="FercDS usa la configurazione di Hyprland in Lua (hyprland.lua)"
MSG[setup.no_python]="il setup richiede python3 (passaggio delle dipendenze)"
MSG[setup.lua_missing]="i file .lua di FercDS non sono ancora in %s:"
MSG[setup.install_lua_q]="Installare questi file adesso?"
MSG[setup.lua_missing_warn]="senza di loro, Hyprland segnalerà errori sui require finché non esistono"
MSG[setup.nothing_to_do]="hyprland.lua carica già FercDS: niente da fare"
MSG[setup.changes]="modifiche a %s:"
MSG[setup.diff_current]="hyprland.lua (attuale)"
MSG[setup.diff_new]="hyprland.lua (nuovo)"
MSG[setup.write_q]="Salvare queste modifiche in hyprland.lua?"
MSG[setup.not_written]="non è stato salvato nulla"
MSG[setup.written]="hyprland.lua aggiornato (l'originale è in %s)"
MSG[setup.reload_hint]="Hyprland si ricarica da solo quando il file cambia; se non lo fa: hyprctl reload"

# --- AGGIORNAMENTO -------------------------------------------------------------
MSG[update.sec_version]="Versione del repo"
MSG[update.sec_packages]="Pacchetti (solo verifica)"
MSG[update.sec_files]="File di FercDS"
MSG[update.sec_service]="Servizio del backend"
MSG[update.sec_sudo]="sudo senza password"
MSG[update.block_files]="File"
MSG[update.block_service]="Servizio"
MSG[update.block_sudoers]="sudoers"
MSG[update.all_same]="tutti i file sono già uguali a quelli del repo"
MSG[update.new]="nuovo       %s"
MSG[update.changed]="cambiato    %s"
MSG[update.replace_q]="Sostituirli con i file del repo? (quelli vecchi vanno nel backup)"
MSG[update.nothing_changed]="non è stato cambiato nulla"

MSG[git.pull_q]="Cercare prima una nuova versione su GitHub (%s)?"
MSG[git.pull_failed]="impossibile aggiornare con git; si prosegue con i file presenti qui"
MSG[git.restarting]="nuova versione scaricata: riavvio l'aggiornamento con quella"
MSG[git.up_to_date]="il repo era già all'ultima versione"

MSG[menu.reopen_manual]="il menu è aperto: chiudilo e riaprilo (F23) per usare la nuova versione"
MSG[menu.reopen_q]="Il menu è aperto con la vecchia versione. Riaprirlo adesso?"
MSG[menu.reopened]="menu riaperto"

# --- VERIFICHE E STATO ---------------------------------------------------------
MSG[check.no_pacman]="pacman non trovato: impossibile verificare i pacchetti"
MSG[check.deps_ok]="dipendenze e inputplumber installati"
MSG[check.wvkbd_ok]="wvkbd di FercDS (%s)"
MSG[check.wvkbd_with_output]="con WVKBD_OUTPUT"
MSG[check.wvkbd_no_output]="wvkbd senza selezione dello schermo: la tastiera si aprirà sullo schermo attivo"
MSG[check.wvkbd_missing]="wvkbd-fercds non installato"
MSG[check.ryzenadj_ok]="ryzenadj (%s)"
MSG[check.ryzenadj_missing]="ryzenadj non installato: il controllo del TDP nel menu non funzionerà"
MSG[check.ip_active]="servizio inputplumber attivo"
MSG[check.ip_stopped]="servizio inputplumber fermo"
MSG[check.hint_install]="per installare ciò che manca: ./install.sh install (i passaggi dei pacchetti)"
MSG[check.no_python]="manca python3 per verificare hyprland.lua"
MSG[check.setup_ok]="hyprland.lua carica FercDS (outputs all'inizio, binds e fercds alla fine)"
MSG[check.setup_needed]="hyprland.lua va sistemato: esegui ./install.sh setup"

MSG[status.sec_version]="Versione"
MSG[status.repo_version]="in questo repo:  %s"
MSG[status.installed_version]="installata:      %s"
MSG[status.none]="nessuna"
MSG[status.sec_packages]="Pacchetti"
MSG[status.sec_files]="File"
MSG[status.file_differs]="%s  (diverso dal repo)"
MSG[status.file_missing]="%s  (non installato)"
MSG[status.hint_update]="per allinearlo al repo: ./install.sh update"
MSG[status.sec_services]="Servizi"
MSG[status.service_stopped]="%s abilitato, ma fermo (journalctl -u %s)"
MSG[status.service_inactive]="%s non è attivo"
MSG[status.legacy_service]="vecchio servizio: %s (install/update propongono di disattivarlo)"
MSG[status.sec_sudo]="sudo senza password"
MSG[status.test_mode]="(modalità di test: niente sudo per verificare)"
MSG[status.gyro_ok]="fercds-gyro consentito"
MSG[status.gyro_pw]="fercds-gyro chiede ancora la password"
MSG[status.ryzenadj_missing]="ryzenadj non installato"
MSG[status.ryzenadj_ok]="ryzenadj consentito"
MSG[status.ryzenadj_pw]="ryzenadj chiede ancora la password"
