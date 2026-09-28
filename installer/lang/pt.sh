# shellcheck shell=bash
# shellcheck disable=SC2034  # o MSG é lido pela função t, no lib.sh
# Instalador do FercDS - Português. Chave que faltar aqui sai em inglês (en.sh).
# %s é trocado pelos argumentos (printf).
declare -gA MSG

# --- UI ------------------------------------------------------------------------
MSG[ui.tagline]="menu do AYANEO Flip DS para Hyprland"
MSG[ui.yes_letter]="S"
MSG[ui.no_letter]="N"
MSG[ui.press_enter]="Enter para voltar ao menu..."
MSG[ui.interrupted]="interrompido"
MSG[ask.no_tty]="sem terminal para perguntar: respondendo não (use --yes para aceitar os padrões)"
MSG[ask.invalid]="responda s ou n"
MSG[sudo.needed]="algumas etapas mexem no sistema: o sudo vai pedir a sua senha"
MSG[sudo.failed]="sem sudo não dá para continuar"

MSG[file.missing_in_repo]="falta no repo: %s"
MSG[file.unchanged]="sem mudanças  %s"
MSG[file.installed]="instalado     %s"
MSG[file.updated]="atualizado    %s"

# --- MENU ----------------------------------------------------------------------
MSG[title.menu]="instalador"
MSG[title.install]="instalação"
MSG[title.update]="atualização"
MSG[title.setup]="setup do hyprland.lua"
MSG[title.status]="status"

MSG[menu.install]="Instalar"
MSG[menu.install_desc]="instala tudo, etapa por etapa"
MSG[menu.update]="Atualizar"
MSG[menu.update_desc]="troca os arquivos pela versão deste repo"
MSG[menu.setup]="Setup"
MSG[menu.setup_desc]="liga o FercDS no hyprland.lua"
MSG[menu.status]="Status"
MSG[menu.status_desc]="mostra o que está instalado"
MSG[menu.language]="Idioma"
MSG[menu.language_desc]="troca o idioma do instalador"
MSG[menu.quit]="Sair"
MSG[menu.choose]="Escolha uma opção: "

MSG[args.unknown]="opção desconhecida: %s"
MSG[args.bad_lang]="--lang aceita en, pt, es ou it"
MSG[help.text]="FercDS - instalador, updater e setup.

uso: ./install.sh [install|update|setup|status] [--yes] [--no-git] [--lang en|pt|es|it]

  (nada)     abre o menu
  install    instala tudo, etapa por etapa, pedindo confirmação em cada uma
  update     confere os pacotes, troca os arquivos instalados pelos deste repo
             e atualiza/ativa o serviço e o sudoers
  setup      liga o FercDS no hyprland.lua (só completa o que faltar)
  status     mostra o que está instalado e o que está diferente do repo

  --yes      aceita a resposta padrão de todas as perguntas
  --no-git   no update, não procura versão nova no GitHub
  --lang     idioma do instalador, sem perguntar (en, pt, es, it)

Rode como o seu usuário (sem sudo): o instalador pede a senha quando precisa."

# --- ETAPAS --------------------------------------------------------------------
MSG[step.run_q]="Executar esta etapa?"
MSG[step.skipped]="etapa pulada"
MSG[step.cmd_failed]="o último comando falhou (código %s)"
MSG[step.failed]="\"%s\" não terminou"
MSG[step.continue_q]="Continuar mesmo assim?"

MSG[step.etapa_dependencias.title]="Dependências do sistema"
MSG[step.etapa_dependencias.desc]="Pacotes oficiais que o menu e os scripts usam (pacman --needed):
%s"
MSG[step.etapa_inputplumber.title]="InputPlumber"
MSG[step.etapa_inputplumber.desc]="Instala o inputplumber do repositório extra e ativa o serviço dele
(é ele que troca os perfis desktop/gamepad do controle)."
MSG[step.etapa_wvkbd.title]="Teclado virtual (wvkbd-fercds)"
MSG[step.etapa_wvkbd.desc]="Compila e instala o fork wvkbd2fercds (packaging/wvkbd-fercds), o teclado
que abre direto no monitor escolhido (WVKBD_OUTPUT=DP-1)."
MSG[step.etapa_ryzenadj.title]="RyzenAdj"
MSG[step.etapa_ryzenadj.desc]="Compila e instala o RyzenAdj v0.19.0 (packaging/ryzenadj-fercds), que ajusta
o TDP pelo menu. Se já houver um ryzenadj, só pergunta se quer recompilar."
MSG[step.etapa_scripts.title]="Scripts"
MSG[step.etapa_scripts.desc]="toggle_wvkbd.sh, libre_wvkbd.sh, cprofile.sh, toggle_monitor.sh e fercds-gyro
em /usr/local/bin; daemons do backend em %s."
MSG[step.etapa_menu.title]="Menu do FercDS"
MSG[step.etapa_menu.desc]="fercds_menu.py em %s, toggle_fercds.sh em /usr/local/bin e as
traduções em ~/.config/ferc-ds (as suas configurações do menu não mudam)."
MSG[step.etapa_perfis.title]="Perfis do InputPlumber"
MSG[step.etapa_perfis.desc]="fercds_desktop.yaml e fercds_gamepad.yaml em /etc/inputplumber/profiles,
os caminhos que o menu e o cprofile.sh carregam."
MSG[step.etapa_servico.title]="Serviço do backend"
MSG[step.etapa_servico.desc]="Cria e ativa o %s: ventoinha, GPU e EPP da CPU sobem no boot.
O gyro fica de fora (liga pelo menu). Serviços antigos que rodem os mesmos
daemons são desativados, com a sua confirmação."
MSG[step.etapa_sudoers.title]="sudo sem senha (gyro e TDP)"
MSG[step.etapa_sudoers.desc]="Cria %s liberando sem senha só o fercds-gyro e o ryzenadj,
os dois comandos que o menu roda com sudo. Validado com visudo antes de valer."
MSG[step.etapa_hypr_configs.title]="Configs do Hyprland"
MSG[step.etapa_hypr_configs.desc]="bindsfercds.lua, fercds.lua e outputsfercds.lua em %s
(se você tiver mudado algum, a sua versão vai para o backup)."
MSG[step.etapa_setup.title]="Ligar no hyprland.lua (setup)"
MSG[step.etapa_setup.desc]="Põe os require do FercDS no hyprland.lua: outputsfercds antes das outras
configs de monitor (a shell continua mandando) e bindsfercds/fercds nas
últimas linhas. Mostra o diff e pede confirmação antes de gravar."

MSG[summary.title]="Resumo"
MSG[summary.skipped]="%s (pulada)"
MSG[summary.backups]="arquivos substituídos foram guardados em %s"

MSG[env.root]="rode como o seu usuário, sem sudo: o instalador pede a senha quando precisa"
MSG[env.root_detail]="(os arquivos do Hyprland são do seu usuário e o makepkg não roda como root)"
MSG[env.no_src]="não achei a pasta src/ ao lado do install.sh"
MSG[env.no_pacman]="este instalador é para Arch Linux (ou derivados com pacman)"
MSG[env.no_sudo]="sudo não encontrado"

# --- INSTALAÇÃO ----------------------------------------------------------------
MSG[install.plan]="O que vai ser feito"
MSG[install.plan_hint]="cada etapa mostra o que faz e pergunta antes de rodar"
MSG[install.start_q]="Começar a instalação?"
MSG[install.next]="Próximos passos"
MSG[install.next_relogin]="saia e entre de novo na sessão do Hyprland: os execs de início (menu e perfil"
MSG[install.next_relogin2]="do controle) só rodam quando o Hyprland abre"
MSG[install.next_f23]="F23 (botão AYA) abre e fecha o menu"

MSG[deps.all_installed]="todas as dependências já estão instaladas"
MSG[deps.missing]="faltando: %s"
MSG[ip.installed]="inputplumber já instalado (%s)"
MSG[ip.service_active]="serviço inputplumber já está ativo"
MSG[build.no_makepkg]="makepkg não encontrado: rode antes a etapa de dependências (base-devel)"
MSG[build.compiling]="compilando %s em %s"
MSG[wvkbd.installed]="wvkbd do FercDS já instalado (%s)"
MSG[wvkbd.rebuild_q]="Recompilar mesmo assim (pega o último commit do wvkbd2fercds)?"
MSG[wvkbd.replace]="o wvkbd instalado não tem a seleção de monitor (WVKBD_OUTPUT); o wvkbd-fercds entra no lugar dele"
MSG[ryzenadj.installed]="ryzenadj já instalado (%s)"
MSG[ryzenadj.rebuild_q]="Recompilar pelo PKGBUILD do FercDS (RyzenAdj v0.19.0)?"

MSG[legacy.found]="serviços antigos rodam os mesmos daemons e brigariam com o %s:"
MSG[legacy.disable_q]="Desativar esses serviços e guardar os arquivos deles no backup?"
MSG[legacy.kept]="serviços antigos mantidos: o %s não vai ser ativado para não brigar com eles"
MSG[legacy.done]="serviços antigos desativados (cópias em %s)"
MSG[service.no_daemons]="os daemons ainda não estão instalados: rode antes a etapa de scripts"
MSG[service.up_to_date]="%s já está ativo e em dia"
MSG[service.active]="%s ativo"

MSG[sudoers.unsafe_path]="%s ficou de fora do sudo sem senha: o arquivo (ou uma pasta acima) não é só do root"
MSG[sudoers.visudo_failed]="o visudo recusou a regra; nada foi alterado"
MSG[sudoers.written]="regra gravada em %s"
MSG[sudoers.bad_user]="o nome de usuário \"%s\" não serve numa regra do sudoers"
MSG[sudoers.no_ryzenadj]="ryzenadj não instalado: por enquanto só o fercds-gyro entra na regra"
MSG[sudoers.up_to_date]="%s já está em dia"
MSG[sudoers.new_rule]="regra nova para %s:"
MSG[sudoers.write_q]="Gravar essa regra?"
MSG[sudoers.skipped]="sudoers não alterado: o menu vai continuar pedindo senha para o gyro e o TDP"
MSG[sudoers.legacy_found]="%s (do install-fercds-gyro.sh antigo) ficou redundante"
MSG[sudoers.legacy_remove_q]="Remover %s (fica uma cópia no backup)?"

# --- SETUP ---------------------------------------------------------------------
MSG[setup.sec]="Ligar o FercDS no %s"
MSG[setup.block]="Setup do hyprland.lua"
MSG[setup.no_hyprland_lua]="não achei %s"
MSG[setup.needs_lua]="o FercDS usa a configuração do Hyprland em Lua (hyprland.lua)"
MSG[setup.no_python]="o setup precisa do python3 (etapa de dependências)"
MSG[setup.lua_missing]="os arquivos .lua do FercDS ainda não estão em %s:"
MSG[setup.install_lua_q]="Instalar esses arquivos agora?"
MSG[setup.lua_missing_warn]="sem eles, o Hyprland vai acusar erro nos require até que existam"
MSG[setup.nothing_to_do]="o hyprland.lua já carrega o FercDS: nada a fazer"
MSG[setup.changes]="mudanças no %s:"
MSG[setup.diff_current]="hyprland.lua (atual)"
MSG[setup.diff_new]="hyprland.lua (novo)"
MSG[setup.write_q]="Gravar essas mudanças no hyprland.lua?"
MSG[setup.not_written]="nada foi gravado"
MSG[setup.written]="hyprland.lua atualizado (o original está em %s)"
MSG[setup.reload_hint]="o Hyprland recarrega sozinho quando o arquivo muda; se não recarregar: hyprctl reload"

# --- ATUALIZAÇÃO ---------------------------------------------------------------
MSG[update.sec_version]="Versão do repo"
MSG[update.sec_packages]="Pacotes (só conferência)"
MSG[update.sec_files]="Arquivos do FercDS"
MSG[update.sec_service]="Serviço do backend"
MSG[update.sec_sudo]="sudo sem senha"
MSG[update.block_files]="Arquivos"
MSG[update.block_service]="Serviço"
MSG[update.block_sudoers]="sudoers"
MSG[update.all_same]="todos os arquivos já estão iguais aos do repo"
MSG[update.new]="novo    %s"
MSG[update.changed]="mudou   %s"
MSG[update.replace_q]="Substituir pelos arquivos do repo? (os antigos vão para o backup)"
MSG[update.nothing_changed]="nada foi alterado"

MSG[git.pull_q]="Procurar versão nova no GitHub antes (%s)?"
MSG[git.pull_failed]="não deu para atualizar pelo git; seguindo com os arquivos que estão aqui"
MSG[git.restarting]="versão nova baixada: reiniciando o updater com ela"
MSG[git.up_to_date]="o repo já estava na versão mais nova"

MSG[menu.reopen_manual]="o menu está aberto: feche e abra de novo (F23) para usar a versão nova"
MSG[menu.reopen_q]="O menu está aberto com a versão antiga. Reabrir agora?"
MSG[menu.reopened]="menu reaberto"

# --- CONFERÊNCIAS E STATUS -----------------------------------------------------
MSG[check.no_pacman]="pacman não encontrado: não dá para conferir os pacotes"
MSG[check.deps_ok]="dependências e inputplumber instalados"
MSG[check.wvkbd_ok]="wvkbd do FercDS (%s)"
MSG[check.wvkbd_with_output]="com WVKBD_OUTPUT"
MSG[check.wvkbd_no_output]="wvkbd sem seleção de monitor: o teclado vai abrir no monitor em foco"
MSG[check.wvkbd_missing]="wvkbd-fercds não instalado"
MSG[check.ryzenadj_ok]="ryzenadj (%s)"
MSG[check.ryzenadj_missing]="ryzenadj não instalado: o TDP do menu não vai funcionar"
MSG[check.ip_active]="serviço inputplumber ativo"
MSG[check.ip_stopped]="serviço inputplumber parado"
MSG[check.hint_install]="para instalar o que falta: ./install.sh install (as etapas de pacotes)"
MSG[check.no_python]="sem python3 para conferir o hyprland.lua"
MSG[check.setup_ok]="hyprland.lua carrega o FercDS (outputs no começo, binds e fercds no fim)"
MSG[check.setup_needed]="o hyprland.lua precisa de ajuste: rode ./install.sh setup"

MSG[status.sec_version]="Versão"
MSG[status.repo_version]="neste repo:  %s"
MSG[status.installed_version]="instalada:   %s"
MSG[status.none]="nenhuma"
MSG[status.sec_packages]="Pacotes"
MSG[status.sec_files]="Arquivos"
MSG[status.file_differs]="%s  (diferente do repo)"
MSG[status.file_missing]="%s  (não instalado)"
MSG[status.hint_update]="para igualar ao repo: ./install.sh update"
MSG[status.sec_services]="Serviços"
MSG[status.service_stopped]="%s habilitado, mas parado (journalctl -u %s)"
MSG[status.service_inactive]="%s não está ativo"
MSG[status.legacy_service]="serviço antigo: %s (o update/install oferece desativar)"
MSG[status.sec_sudo]="sudo sem senha"
MSG[status.test_mode]="(modo de teste: sem sudo para conferir)"
MSG[status.gyro_ok]="fercds-gyro liberado"
MSG[status.gyro_pw]="fercds-gyro ainda pede senha"
MSG[status.ryzenadj_missing]="ryzenadj não instalado"
MSG[status.ryzenadj_ok]="ryzenadj liberado"
MSG[status.ryzenadj_pw]="ryzenadj ainda pede senha"
