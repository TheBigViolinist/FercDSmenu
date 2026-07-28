import sys
import os
import subprocess
import glob
import json
import psutil
import math
from collections import deque
from datetime import datetime

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango

class FercDSMenu(Gtk.Window):
    def __init__(self):
        super().__init__(title="Ferc-DS Menu")
        self.set_name("FercDSMenu") 

        # --- CONFIGURAÇÃO NATIVA WAYLAND LAYER SHELL ---
        GtkLayerShell.init_for_window(self)
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "ferc-ds")
        GtkLayerShell.set_exclusive_zone(self, -1)
        
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.TOP, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.BOTTOM, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.LEFT, True)
        GtkLayerShell.set_anchor(self, GtkLayerShell.Edge.RIGHT, True)

        # --- VARIÁVEIS DE ESTADO ---
        self.initial_tdp = self.get_current_tdp()
        self.initial_fan = self.get_current_fan()
        self.initial_gpu = self.get_current_gpu()
        self.initial_cpu_epp = self.get_current_cpu_epp() 
        self.initial_volume = self.get_current_volume() 
        
        self.history_len = 50
        self.bat_w_history = deque([0.0]*self.history_len, maxlen=self.history_len)
        
        self.ram_percent = 0.0
        self.cpu_percent = 0.0
        self.bat_percent = 0.0

        self.apps_data = []
        self.usage_file = os.path.expanduser("~/.config/ferc-ds/usage.json")
        self.state_file = os.path.expanduser("~/.config/ferc-ds/state.json")
        self.lang_file = os.path.expanduser("~/.config/ferc-ds/fercds_lang.json")
        
        # --- SISTEMA DE IDIOMAS E EASTER EGG ---
        self.translations = self.load_translations()
        self.current_lang = self.get_saved_lang()
        self.pt_confirm_count = 0
        self.pending_lang = None
        
        self.active_control_window_address = None
        self.proc_timer_id = None

        self.apply_css()
        self.setup_ui()
        self.update_all_texts()
        
        GLib.timeout_add(1000, self.update_telemetry)
        self.update_telemetry() 

    # --- SISTEMA DE TRADUÇÃO ---
    def load_translations(self):
        try:
            if os.path.exists(self.lang_file):
                with open(self.lang_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except: pass
        return {"pt": {}}

    def _t(self, key):
        return self.translations.get(self.current_lang, {}).get(key, self.translations.get("pt", {}).get(key, key))

    def get_saved_lang(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f).get("lang", "pt")
        except: pass
        return "pt"

    def set_saved_lang(self, lang):
        try:
            data = {}
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
            data["lang"] = lang
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(data, f)
        except: pass

    # --- GERENCIAMENTO DE ESTADO DA PÁGINA ---
    def get_last_page(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    return json.load(f).get("last_page", "page1")
        except: pass
        return "page1"

    def set_last_page(self, page_name):
        try:
            data = {}
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
            data["last_page"] = page_name
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
            with open(self.state_file, 'w') as f:
                json.dump(data, f)
        except: pass

    def change_main_page(self, widget, page_name):
        self.stack.set_visible_child_name(page_name)
        self.set_last_page(page_name)
        
        if hasattr(self, 'page5_stack'):
            self.page5_stack.set_visible_child_name("grid")
        if hasattr(self, 'page4_stack'):
            self.page4_stack.set_visible_child_name("main")
            self.active_control_window_address = None

    # --- LEITURA DE HARDWARE ---
    def get_current_tdp(self):
        if os.path.exists("/tmp/current_tdp"):
            try:
                with open("/tmp/current_tdp", "r") as f: return int(f.read().strip())
            except: pass
        return 15

    def get_current_cpu_epp(self):
        if os.path.exists("/tmp/cpu_epp"):
            try:
                with open("/tmp/cpu_epp", "r") as f:
                    c = f.read().strip()
                    if c == "power": return 0
                    elif c == "balance_power": return 1
                    elif c == "balance_performance": return 2
                    elif c == "performance": return 3
            except: pass
        return 1 

    def get_current_fan(self):
        if os.path.exists("/tmp/fan_mode"):
            try:
                with open("/tmp/fan_mode", "r") as f:
                    c = f.read().strip()
                    return 0 if c == "auto" else int(c)
            except: pass
        return 0

    def get_current_gpu(self):
        if os.path.exists("/tmp/gpu_clock"):
            try:
                with open("/tmp/gpu_clock", "r") as f:
                    c = f.read().strip()
                    return 0 if c == "auto" else int(c)
            except: pass
        return 0

    def get_current_volume(self):
        try:
            out = subprocess.getoutput("wpctl get-volume @DEFAULT_AUDIO_SINK@")
            if "Volume:" in out:
                vol_str = out.split()[1]
                return int(float(vol_str) * 100)
        except: pass
        return 50 

    def load_apps_database(self):
        count_db = {}
        try:
            if os.path.exists(self.usage_file):
                with open(self.usage_file, 'r') as f:
                    count_db = json.load(f)
        except: pass

        self.apps_data = []
        app_paths = [
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/flatpak/exports/share/applications/",
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications/")
        ]
        
        seen_names = set()
        for path in app_paths:
            if not os.path.exists(path): continue
            for file in glob.glob(f"{path}/*.desktop"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()
                        
                    if "NoDisplay=true" in content or "Hidden=true" in content:
                        continue
                        
                    name = ""
                    icon = "application-x-executable"
                    cmd = ""
                    
                    for line in content.splitlines():
                        if line.startswith("Name=") and not name:
                            name = line.split("=", 1)[1].strip()
                        elif line.startswith("Icon=") and icon == "application-x-executable":
                            icon = line.split("=", 1)[1].strip()
                        elif line.startswith("Exec=") and not cmd:
                            cmd = line.split("=", 1)[1].strip()
                            cmd = cmd.split("%")[0].strip()
                            
                    if name and cmd and name not in seen_names:
                        usage_count = count_db.get(name, 0)
                        self.apps_data.append({
                            "name": name,
                            "icon": icon,
                            "command": cmd,
                            "count": usage_count
                        })
                        seen_names.add(name)
                except:
                    continue
                    
        self.apps_data.sort(key=lambda x: (-x["count"], x["name"].lower()))

    # --- UI PRINCIPAL & MASTER STACK ---
    def setup_ui(self):
        self.master_stack = Gtk.Stack()
        self.master_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.master_stack.set_transition_duration(250)
        self.add(self.master_stack)

        main_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)

        # 1. STATUS BAR SUPERIOR (Reduzida em 25%)
        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=10)
        top_bar.set_name("statusBar")
        top_bar.set_margin_start(15); top_bar.set_margin_end(15)
        top_bar.set_margin_top(5); top_bar.set_margin_bottom(5)
        top_bar.set_size_request(-1, 56) 
        
        self.lbl_top_battery = Gtk.Label(label="🔋 --% | 🕒 --:--:-- | ⚡ -- | ⏳ --")
        top_bar.pack_start(self.lbl_top_battery, False, False, 0)

        # Container Direita: [Língua] [Processos] [Switch]
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        right_box.set_valign(Gtk.Align.CENTER)

        # 3) Tradução
        self.btn_lang = Gtk.Button(label="🌐")
        self.btn_lang.set_can_focus(False)
        self.btn_lang.set_name("btnTopBar")
        self.btn_lang.connect("clicked", self.show_lang_manager)

        # 2) Processos
        self.btn_sys_mon = Gtk.Button(label="📊")
        self.btn_sys_mon.set_can_focus(False)
        self.btn_sys_mon.set_name("btnTopBar")
        self.btn_sys_mon.connect("clicked", self.show_process_manager)
        
        # 1) Switch InputPlumber
        self.switch_frame = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        self.switch_frame.set_name("btnTopBar")
        self.switch_frame.set_margin_top(5); self.switch_frame.set_margin_bottom(5)
        self.lbl_profile_icon = Gtk.Label(label="🖱️")
        self.profile_switch = Gtk.Switch()
        self.profile_switch.set_valign(Gtk.Align.CENTER)
        
        # Leitura inicial da RAM (/tmp)
        is_game = os.path.exists("/tmp/modo_jogo_ativo")
        self.lbl_profile_icon.set_text("🎮" if is_game else "🖱️")
        self.profile_switch.set_active(is_game)
        self.profile_switch.connect("notify::active", self.on_profile_switch_toggled)
        
        self.switch_frame.pack_start(self.lbl_profile_icon, False, False, 0)
        self.switch_frame.pack_start(self.profile_switch, False, False, 0)

        # Empacotamento na ordem solicitada (Direita para esquerda: Switch, Proc, Lang)
        right_box.pack_start(self.btn_lang, False, False, 0)
        right_box.pack_start(self.btn_sys_mon, False, False, 0)
        right_box.pack_start(self.switch_frame, False, False, 0)

        top_bar.pack_end(right_box, False, False, 0)
        main_box.pack_start(top_bar, False, False, 0)

        # 2. SELETOR DE PÁGINAS PRINCIPAL
        self.stack = Gtk.Stack()
        self.stack.set_transition_type(Gtk.StackTransitionType.SLIDE_LEFT_RIGHT)
        self.stack.set_transition_duration(300)
        
        self.setup_page_5() 
        self.setup_page_1()
        self.setup_page_2()
        self.setup_page_3()
        self.setup_page_4()
        
        self.stack.set_visible_child_name(self.get_last_page())
        main_box.pack_start(self.stack, True, True, 0)

        # 3. STATUS BAR INFERIOR
        bottom_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        bottom_bar.set_name("statusBar")
        bottom_bar.set_margin_start(15); bottom_bar.set_margin_end(15)
        bottom_bar.set_margin_top(10); bottom_bar.set_margin_bottom(10)

        nav_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        nav_box.set_hexpand(True); nav_box.set_halign(Gtk.Align.FILL) 
        nav_box.set_homogeneous(True) 

        self.btn_p5 = Gtk.Button(label="🎮 Biblioteca"); self.btn_p5.set_can_focus(False); self.btn_p5.set_name("navBtn")
        self.btn_p1 = Gtk.Button(label="⚡ Energia"); self.btn_p1.set_can_focus(False); self.btn_p1.set_name("navBtn")
        self.btn_p2 = Gtk.Button(label="🎵 Mídia"); self.btn_p2.set_can_focus(False); self.btn_p2.set_name("navBtn")
        self.btn_p3 = Gtk.Button(label="📊 Sensores"); self.btn_p3.set_can_focus(False); self.btn_p3.set_name("navBtn")
        self.btn_p4 = Gtk.Button(label="🖥️ Sistema"); self.btn_p4.set_can_focus(False); self.btn_p4.set_name("navBtn")
        
        for b in [self.btn_p5, self.btn_p1, self.btn_p2, self.btn_p3, self.btn_p4]:
            b.set_size_request(-1, 65) 

        self.btn_p5.connect("clicked", self.change_main_page, "page5")
        self.btn_p1.connect("clicked", self.change_main_page, "page1")
        self.btn_p2.connect("clicked", self.change_main_page, "page2")
        self.btn_p3.connect("clicked", self.change_main_page, "page3")
        self.btn_p4.connect("clicked", self.change_main_page, "page4")

        nav_box.pack_start(self.btn_p5, True, True, 0)
        nav_box.pack_start(self.btn_p1, True, True, 0)
        nav_box.pack_start(self.btn_p2, True, True, 0)
        nav_box.pack_start(self.btn_p3, True, True, 0)
        nav_box.pack_start(self.btn_p4, True, True, 0)

        bottom_bar.pack_start(nav_box, True, True, 0)
        main_box.pack_end(bottom_bar, False, False, 0)

        self.setup_process_manager_ui()
        self.setup_lang_manager_ui()

        self.master_stack.add_named(main_box, "main_app")
        self.master_stack.add_named(self.proc_manager_box, "proc_manager")
        self.master_stack.add_named(self.lang_manager_box, "lang_manager")

    # --- FUNÇÃO DE ATUALIZAÇÃO TEXTUAL ---
    def update_all_texts(self):
        self.btn_p5.set_label(self._t("nav_lib"))
        self.btn_p1.set_label(self._t("nav_pwr"))
        self.btn_p2.set_label(self._t("nav_med"))
        self.btn_p3.set_label(self._t("nav_sen"))
        self.btn_p4.set_label(self._t("nav_sys"))
        
        self.btn_back_proc.set_label(self._t("back_panel"))
        self.lbl_title_proc.set_text(self._t("sys_procs"))
        
        self.lbl_ask_p5.set_text(self._t("ask_launch"))
        self.btn_yes_p5.set_label(self._t("btn_start"))
        self.btn_no_p5.set_label(self._t("btn_cancel"))
        
        self.lbl_tdp.set_text(f"🔥 TDP\n{int(self.sl_tdp.get_value())}W")
        
        cpu_val = int(self.sl_cpu_epp.get_value())
        epp_labels = {0: "Power", 1: "Bal-Pw", 2: "Bal-Pf", 3: "Perf"}
        self.lbl_cpu_epp.set_text(f"⚙️ CPU\n{epp_labels.get(cpu_val, 'Bal-Pw')}")
        
        fan_val = int(self.sl_fan.get_value())
        self.lbl_fan.set_text(f"🌀 FAN\nAuto" if fan_val == 0 else f"🌀 FAN\n{fan_val}%")
        gpu_val = int(self.sl_gpu.get_value())
        self.lbl_gpu.set_text(f"🎮 GPU\nAuto" if gpu_val == 0 else f"🎮 GPU\n{gpu_val}MHz")
        self.btn_apply.set_label(self._t("btn_apply"))
        
        self.lbl_vol.set_text(self._t("vol_gen"))
        self.lbl_audio_dev.set_text(self._t("def_audio"))
        
        self.lbl_title_cpu_t.set_text(self._t("t_cpu"))
        self.lbl_title_gpu_t.set_text(self._t("t_gpu"))
        self.lbl_title_watts.set_text(self._t("bat_cons"))
        self.lbl_title_ram.set_text(self._t("ram_mem"))
        self.lbl_title_cpu.set_text(self._t("cpu_usage"))
        self.lbl_title_bat.set_text(self._t("bat_lvl"))
        
        self.btn_prev_ws.set_label(self._t("prev_ws"))
        self.btn_next_ws.set_label(self._t("next_ws"))
        self.btn_close.set_label(self._t("close_app"))
        self.btn_move.set_label(self._t("move_mon"))
        self.btn_fs.set_label(self._t("fullscreen"))
        self.btn_mic.set_label(self._t("mute_mic"))
        self.btn_open_win.set_label(self._t("open_wins"))
        self.btn_hide_panel.set_label(self._t("hide_panel"))
        
        self.btn_back_grid.set_label(self._t("back"))
        self.cw_close.set_label(self._t("cw_close"))
        self.cw_prev.set_label(self._t("cw_prev"))
        self.cw_next.set_label(self._t("cw_next"))
        self.cw_move.set_label(self._t("cw_move"))
        self.cw_fs.set_label(self._t("cw_fs"))
        self.cw_back.set_label(self._t("back"))
        
        self.btn_back_lang.set_label(self._t("back_panel"))
        self.lbl_title_lang.set_text(self._t("lang_title"))
        self.btn_yes_lang.set_label(self._t("btn_start"))
        self.btn_no_lang.set_label(self._t("btn_cancel"))

    # --- GERENCIADOR DE IDIOMAS E EASTER EGG ---
    def setup_lang_manager_ui(self):
        self.lang_manager_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.lang_manager_box.set_margin_start(20); self.lang_manager_box.set_margin_end(20)
        self.lang_manager_box.set_margin_top(20); self.lang_manager_box.set_margin_bottom(20)

        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.btn_back_lang = Gtk.Button()
        self.btn_back_lang.set_name("btnCancel")
        self.btn_back_lang.set_size_request(-1, 55)
        self.btn_back_lang.connect("clicked", self.hide_lang_manager)
        
        self.lbl_title_lang = Gtk.Label()
        self.lbl_title_lang.set_name("titleLabel")
        self.lbl_title_lang.set_hexpand(True)
        self.lbl_title_lang.set_halign(Gtk.Align.CENTER)

        top_bar.pack_start(self.btn_back_lang, False, False, 0)
        top_bar.pack_start(self.lbl_title_lang, True, True, 0)
        
        self.lang_stack = Gtk.Stack()
        self.lang_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.lang_stack.set_transition_duration(200)
        
        list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        list_box.set_valign(Gtk.Align.CENTER); list_box.set_halign(Gtk.Align.CENTER)
        
        langs = [("pt", "Português"), ("en", "English"), ("es", "Español"), ("it", "Italiano")]
        for code, name in langs:
            btn = Gtk.Button(label=name)
            btn.set_size_request(300, 60)
            btn.set_name("actionBtn")
            btn.connect("clicked", self.on_lang_selected, code, name)
            list_box.pack_start(btn, False, False, 0)
            
        confirm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        confirm_box.set_valign(Gtk.Align.CENTER); confirm_box.set_halign(Gtk.Align.CENTER)
        
        self.lbl_lang_confirm_ask = Gtk.Label()
        self.lbl_lang_confirm_ask.set_name("sensorText")
        
        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        btn_box.set_halign(Gtk.Align.CENTER)
        
        self.btn_yes_lang = Gtk.Button(); self.btn_yes_lang.set_size_request(200, 70); self.btn_yes_lang.set_name("btnLaunch")
        self.btn_no_lang = Gtk.Button(); self.btn_no_lang.set_size_request(200, 70); self.btn_no_lang.set_name("btnCancel")
        
        self.btn_no_lang.connect("clicked", lambda x: self.lang_stack.set_visible_child_name("list"))
        self.btn_yes_lang.connect("clicked", self.confirm_lang)

        btn_box.pack_start(self.btn_no_lang, False, False, 0)
        btn_box.pack_start(self.btn_yes_lang, False, False, 0)

        confirm_box.pack_start(self.lbl_lang_confirm_ask, False, False, 0)
        confirm_box.pack_start(btn_box, False, False, 10)
        
        self.lang_stack.add_named(list_box, "list")
        self.lang_stack.add_named(confirm_box, "confirm")
        
        self.lang_manager_box.pack_start(top_bar, False, False, 0)
        self.lang_manager_box.pack_start(self.lang_stack, True, True, 10)

    def show_lang_manager(self, btn):
        self.lang_stack.set_visible_child_name("list")
        self.master_stack.set_visible_child_name("lang_manager")

    def hide_lang_manager(self, btn):
        self.master_stack.set_visible_child_name("main_app")

    def on_lang_selected(self, btn, lang_code, lang_name):
        self.play_sound("click")
        if self.current_lang == 'pt' and lang_code == 'pt':
            self.pt_confirm_count += 1
        else:
            self.pt_confirm_count = 0

        if self.pt_confirm_count == 5:
            self.lbl_lang_confirm_ask.set_text("Mudar a lingua pra 'Mineirês?' uai?")
            self.play_sound("complete") 
            self.pending_lang = 'mineires'
            self.pt_confirm_count = 0 
        else:
            self.lbl_lang_confirm_ask.set_text(f"{self._t('change_lang_to')} {lang_name}?")
            self.pending_lang = lang_code
            
        self.lang_stack.set_visible_child_name("confirm")

    def confirm_lang(self, btn):
        self.current_lang = self.pending_lang
        self.set_saved_lang(self.current_lang)
        self.update_all_texts()
        self.update_telemetry()
        self.hide_lang_manager(None)

    # --- GERENCIADOR DE SWITCH (INPUTPLUMBER) ---
    def on_profile_switch_toggled(self, switch, gparam):
        is_game = switch.get_active()
        state_file = "/tmp/modo_jogo_ativo"
        cmd_desk = "busctl call org.shadowblip.InputPlumber /org/shadowblip/InputPlumber/CompositeDevice0 org.shadowblip.Input.CompositeDevice LoadProfilePath s \"/etc/inputplumber/profiles/fercds_desktop.yaml\""
        cmd_game = "busctl call org.shadowblip.InputPlumber /org/shadowblip/InputPlumber/CompositeDevice0 org.shadowblip.Input.CompositeDevice LoadProfilePath s \"/etc/inputplumber/profiles/fercds_gamepad.yaml\""

        if is_game:
            self.lbl_profile_icon.set_text("🎮")
            subprocess.Popen(['bash', '-c', f"touch {state_file} && {cmd_game} && notify-send -t 2000 '🎮 InputPlumber' 'Modo games Ativado'"])
        else:
            self.lbl_profile_icon.set_text("🖱️")
            subprocess.Popen(['bash', '-c', f"rm -f {state_file} && {cmd_desk} && notify-send -t 2000 '🎮 InputPlumber' 'Modo desktop Ativado'"])

    # --- GERENCIADOR DE TAREFAS (SUBPÁGINA) ---
    def setup_process_manager_ui(self):
        self.proc_manager_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.proc_manager_box.set_margin_start(20); self.proc_manager_box.set_margin_end(20)
        self.proc_manager_box.set_margin_top(20); self.proc_manager_box.set_margin_bottom(20)

        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.btn_back_proc = Gtk.Button()
        self.btn_back_proc.set_name("btnCancel")
        self.btn_back_proc.set_size_request(-1, 55)
        self.btn_back_proc.connect("clicked", self.hide_process_manager)
        
        self.lbl_title_proc = Gtk.Label()
        self.lbl_title_proc.set_name("titleLabel")
        self.lbl_title_proc.set_hexpand(True)
        self.lbl_title_proc.set_halign(Gtk.Align.CENTER)

        top_bar.pack_start(self.btn_back_proc, False, False, 0)
        top_bar.pack_start(self.lbl_title_proc, True, True, 0)
        
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_kinetic_scrolling(True)
        scroll.set_vexpand(True)

        self.proc_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        scroll.add(self.proc_list_box)

        self.proc_manager_box.pack_start(top_bar, False, False, 0)
        self.proc_manager_box.pack_start(scroll, True, True, 10)

    def show_process_manager(self, btn):
        self.master_stack.set_visible_child_name("proc_manager")
        self.update_process_list()
        if not self.proc_timer_id:
            self.proc_timer_id = GLib.timeout_add(2000, self.update_process_list)

    def hide_process_manager(self, btn):
        self.master_stack.set_visible_child_name("main_app")
        if self.proc_timer_id:
            GLib.source_remove(self.proc_timer_id)
            self.proc_timer_id = None

    def update_process_list(self):
        if self.master_stack.get_visible_child_name() != "proc_manager":
            return False
        
        for child in self.proc_list_box.get_children():
            self.proc_list_box.remove(child)
            
        procs = []
        for p in psutil.process_iter(['name', 'memory_percent', 'cpu_percent']):
            try:
                if p.info['memory_percent'] is not None:
                    procs.append(p.info)
            except: pass
            
        procs.sort(key=lambda x: x.get('memory_percent', 0) or 0, reverse=True)
        
        for p in procs[:40]: 
            name = p.get('name', self._t('unknown_proc'))
            mem = p.get('memory_percent', 0) or 0
            cpu = p.get('cpu_percent', 0) or 0
            
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
            row.set_name("procRow")
            
            lbl_name = Gtk.Label(label=name)
            lbl_name.set_halign(Gtk.Align.START)
            lbl_name.set_hexpand(True)
            lbl_name.set_ellipsize(Pango.EllipsizeMode.END)
            
            lbl_mem = Gtk.Label(label=f"{self._t('ram_mem')}: {mem:.1f}%")
            lbl_mem.set_size_request(120, -1)
            lbl_mem.set_name("sensorText")
            
            lbl_cpu = Gtk.Label(label=f"{self._t('cpu_usage')}: {cpu:.1f}%")
            lbl_cpu.set_size_request(120, -1)
            lbl_cpu.set_name("sensorText")
            
            row.pack_start(lbl_name, True, True, 0)
            row.pack_start(lbl_cpu, False, False, 0)
            row.pack_start(lbl_mem, False, False, 0)
            
            self.proc_list_box.add(row)
            
        self.proc_list_box.show_all()
        return True

    # --- PAGE 5: BIBLIOTECA (meu Deus quando isso acaba?) ---
    def setup_page_5(self):
        self.load_apps_database()
        
        self.page5_stack = Gtk.Stack()
        self.page5_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.page5_stack.set_transition_duration(200)

        self.scroll_apps = Gtk.ScrolledWindow()
        self.scroll_apps.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.scroll_apps.set_kinetic_scrolling(True) 
        
        self.flowbox = Gtk.FlowBox()
        self.flowbox.set_valign(Gtk.Align.START)
        self.flowbox.set_max_children_per_line(5)
        self.flowbox.set_min_children_per_line(5)
        self.flowbox.set_selection_mode(Gtk.SelectionMode.NONE) 
        self.flowbox.set_homogeneous(True) 
        self.flowbox.set_row_spacing(15); self.flowbox.set_column_spacing(15)
        self.flowbox.set_margin_start(20); self.flowbox.set_margin_end(20)
        self.flowbox.set_margin_top(15); self.flowbox.set_margin_bottom(15)

        self.flowbox.connect("child-activated", self.on_app_activated)

        self.populate_flowbox()
        self.scroll_apps.add(self.flowbox)

        self.confirm_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=25)
        self.confirm_box.set_valign(Gtk.Align.CENTER)
        self.confirm_box.set_halign(Gtk.Align.CENTER)
        
        self.confirm_icon = Gtk.Image()
        self.confirm_icon.set_pixel_size(120) 
        self.confirm_label = Gtk.Label()
        self.confirm_label.set_name("titleLabel")
        
        self.lbl_ask_p5 = Gtk.Label()
        self.lbl_ask_p5.set_name("sensorText")

        btn_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=30)
        btn_box.set_halign(Gtk.Align.CENTER)
        
        self.btn_yes_p5 = Gtk.Button(); self.btn_yes_p5.set_size_request(200, 70); self.btn_yes_p5.set_name("btnLaunch")
        self.btn_no_p5 = Gtk.Button(); self.btn_no_p5.set_size_request(200, 70); self.btn_no_p5.set_name("btnCancel")
        
        self.current_selected_app = None
        self.btn_no_p5.connect("clicked", self.cancel_launch)
        self.btn_yes_p5.connect("clicked", self.confirm_launch)

        btn_box.pack_start(self.btn_no_p5, False, False, 0)
        btn_box.pack_start(self.btn_yes_p5, False, False, 0)

        self.confirm_box.pack_start(self.confirm_icon, False, False, 0)
        self.confirm_box.pack_start(self.confirm_label, False, False, 0)
        self.confirm_box.pack_start(self.lbl_ask_p5, False, False, 0)
        self.confirm_box.pack_start(btn_box, False, False, 10)

        self.page5_stack.add_named(self.scroll_apps, "grid")
        self.page5_stack.add_named(self.confirm_box, "confirm")

        self.stack.add_named(self.page5_stack, "page5")

    def populate_flowbox(self):
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)

        for app in self.apps_data:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.set_valign(Gtk.Align.CENTER)
            
            icon = Gtk.Image.new_from_icon_name(app.get("icon", "application-x-executable"), Gtk.IconSize.DIALOG)
            icon.set_pixel_size(60) 
            
            lbl = Gtk.Label(label=app.get("name", "App"))
            lbl.set_name("appLabel")
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.set_max_width_chars(15)
            
            box.pack_start(icon, True, True, 0)
            box.pack_start(lbl, False, False, 0)
            
            child = Gtk.FlowBoxChild()
            child.set_name("appCard")
            child.add(box)
            child.app_data = app 
            self.flowbox.add(child)
            
        self.flowbox.show_all()

    def play_sound(self, sound_type="click"):
        path = "/usr/share/sounds/freedesktop/stereo/dialog-information.oga"
        if sound_type == "cancel":
            path = "/usr/share/sounds/freedesktop/stereo/dialog-warning.oga"
        elif sound_type == "complete":
            path = "/usr/share/sounds/freedesktop/stereo/complete.oga"
        subprocess.Popen(["paplay", path], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def on_app_activated(self, flowbox, child):
        self.play_sound("click")
        app = child.app_data
        self.current_selected_app = app
        self.confirm_icon.set_from_icon_name(app.get("icon", "application-x-executable"), Gtk.IconSize.DIALOG)
        self.confirm_icon.set_pixel_size(120)
        self.confirm_label.set_text(app.get("name", "App"))
        
        self.page5_stack.set_visible_child_name("confirm")

    def cancel_launch(self, widget):
        self.play_sound("cancel")
        self.page5_stack.set_visible_child_name("grid")

    def confirm_launch(self, widget):
        app = self.current_selected_app
        if app:
            app["count"] = app.get("count", 0) + 1
            
            count_db = {}
            if os.path.exists(self.usage_file):
                try:
                    with open(self.usage_file, 'r') as f:
                        count_db = json.load(f)
                except: pass
            
            count_db[app["name"]] = app["count"]
            os.makedirs(os.path.dirname(self.usage_file), exist_ok=True)
            with open(self.usage_file, 'w') as f:
                json.dump(count_db, f)

            self.apps_data.sort(key=lambda x: (-x["count"], x["name"].lower()))
            self.populate_flowbox()
            
            # ATUALIZADO: Usando ';' para encadear a ação no Hyprland 0.56.0
            cmd = f"hyprctl dispatch 'hl.dispatch(hl.dsp.focus({{ monitor = \"eDP-1\" }}))' ; {app['command']} &"
            subprocess.Popen(cmd, shell=True)
            
        self.page5_stack.set_visible_child_name("grid")
        
    # --- PÁGINA 1: ENERGIA TDP E OS TREM BAO DEMAIS DA CONTA ---
    def setup_page_1(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_margin_start(20); page.set_margin_end(20)
        page.set_margin_top(20); page.set_margin_bottom(20)

        grid = Gtk.Grid(column_spacing=30)
        grid.set_column_homogeneous(True) 
        grid.set_vexpand(True)

        bat_frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        bat_frame.set_name("cardFrame")
        
        self.lbl_p1_bat_w = Gtk.Label(label="⚡ 0.0 W")
        self.lbl_p1_bat_w.set_name("bigValue")
        self.lbl_p1_bat_time = Gtk.Label(label="⏳ --")
        self.graph_bat_p1 = Gtk.DrawingArea()
        self.graph_bat_p1.set_size_request(50, 100) 
        self.graph_bat_p1.set_vexpand(True) 
        self.graph_bat_p1.connect("draw", self.draw_line_graph)
        
        bat_frame.pack_start(self.lbl_p1_bat_w, False, False, 10)
        bat_frame.pack_start(self.lbl_p1_bat_time, False, False, 5)
        bat_frame.pack_start(self.graph_bat_p1, True, True, 10)
        
        grid.attach(bat_frame, 0, 0, 1, 1)

        right_panel = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        
        # ATUALIZADO: Espaçamento reduzido de 30 para 5 para acomodar a nova barra
        sliders_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=5)
        sliders_box.set_halign(Gtk.Align.CENTER)
        sliders_box.set_vexpand(True)
        sliders_box.set_homogeneous(True) 

        def create_slider(title_key, min_v, max_v, step, curr_val, cb, marks=None):
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
            lbl = Gtk.Label()
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.set_name("sliderText")
            
            # ATUALIZADO: Tamanho de etiqueta travado em 65 pixels para evitar "dança"
            lbl.set_size_request(65, -1)
            
            adj = Gtk.Adjustment(value=curr_val, lower=min_v, upper=max_v, step_increment=step, page_increment=step)
            scale = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=adj)
            scale.set_name("thickSlider") 
            scale.set_inverted(True) 
            scale.set_vexpand(True) 
            scale.set_digits(0)
            scale.set_round_digits(0)
            
            if marks:
                for m in marks:
                    scale.add_mark(m, Gtk.PositionType.RIGHT, str(m))
            
            scale.connect("value-changed", cb, lbl, title_key)
            cb(scale, lbl, title_key) 
            
            box.pack_start(lbl, False, False, 0)
            box.pack_start(scale, True, True, 0)
            return box, scale, lbl

        self.box_tdp, self.sl_tdp, self.lbl_tdp = create_slider("🔥 TDP", 5, 30, 1, self.initial_tdp, self.on_tdp_change)
        self.box_cpu, self.sl_cpu_epp, self.lbl_cpu_epp = create_slider("⚙️ CPU", 0, 3, 1, self.initial_cpu_epp, self.on_cpu_epp_change)
        self.box_fan, self.sl_fan, self.lbl_fan = create_slider("🌀 FAN", 0, 100, 1, self.initial_fan, self.on_fan_change)
        self.box_gpu, self.sl_gpu, self.lbl_gpu = create_slider("🎮 GPU", 0, 2900, 100, self.initial_gpu, self.on_gpu_change)

        sliders_box.pack_start(self.box_tdp, True, True, 0)
        sliders_box.pack_start(self.box_cpu, True, True, 0)
        sliders_box.pack_start(self.box_fan, True, True, 0)
        sliders_box.pack_start(self.box_gpu, True, True, 0)
        right_panel.pack_start(sliders_box, True, True, 0)

        btns_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        btns_box.set_halign(Gtk.Align.CENTER)
        
        self.btn_apply = Gtk.Button(); self.btn_apply.set_can_focus(False); self.btn_apply.set_name("actionBtn")
        self.btn_apply.set_size_request(200, -1)
        self.btn_apply.connect("clicked", lambda x: self.apply_hardware())
        
        btns_box.pack_start(self.btn_apply, True, False, 0)
        right_panel.pack_start(btns_box, False, False, 0)

        grid.attach(right_panel, 1, 0, 1, 1)
        page.pack_start(grid, True, True, 0)
        self.stack.add_named(page, "page1")

    # --- PÁGINA 2: MÍDIA ---
    def setup_page_2(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page.set_valign(Gtk.Align.CENTER); page.set_halign(Gtk.Align.CENTER)

        self.lbl_media = Gtk.Label()
        self.lbl_media.set_name("titleLabel")
        self.lbl_media.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_media.set_max_width_chars(45) 
        
        media_prog_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
        self.lbl_media_time = Gtk.Label(label="0:00 / 0:00")
        
        self.media_adj = Gtk.Adjustment(value=0, lower=0, upper=100, step_increment=1)
        self.sl_media_pos = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=self.media_adj)
        self.sl_media_pos.set_draw_value(False)
        self.sl_media_pos.set_size_request(300, -1)
        
        self.sl_media_pos.connect("change-value", self.on_media_seek)
        
        media_prog_box.pack_start(self.sl_media_pos, False, False, 0)
        media_prog_box.pack_start(self.lbl_media_time, False, False, 0)
        
        ctrl_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=20)
        ctrl_box.set_halign(Gtk.Align.CENTER)
        
        btn_prev = Gtk.Button(label="⏪"); btn_prev.set_size_request(100, 80); btn_prev.set_can_focus(False); btn_prev.set_name("mediaBtn")
        btn_play = Gtk.Button(label="⏯️"); btn_play.set_size_request(100, 80); btn_play.set_can_focus(False); btn_play.set_name("mediaBtn")
        btn_next = Gtk.Button(label="⏩"); btn_next.set_size_request(100, 80); btn_next.set_can_focus(False); btn_next.set_name("mediaBtn")
        
        btn_prev.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', 'playerctl previous']))
        btn_play.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', 'playerctl play-pause']))
        btn_next.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', 'playerctl next']))
        
        ctrl_box.pack_start(btn_prev, False, False, 0)
        ctrl_box.pack_start(btn_play, False, False, 0)
        ctrl_box.pack_start(btn_next, False, False, 0)

        vol_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        self.lbl_vol = Gtk.Label()
        
        adj_vol = Gtk.Adjustment(value=self.initial_volume, lower=0, upper=200, step_increment=5)
        sl_vol = Gtk.Scale(orientation=Gtk.Orientation.HORIZONTAL, adjustment=adj_vol)
        sl_vol.set_digits(0); sl_vol.set_round_digits(0)
        sl_vol.connect("value-changed", self.on_volume_change)
        
        self.lbl_audio_dev = Gtk.Label()
        
        vol_box.pack_start(self.lbl_vol, False, False, 0)
        vol_box.pack_start(sl_vol, False, False, 0)
        vol_box.pack_start(self.lbl_audio_dev, False, False, 0)

        page.pack_start(self.lbl_media, False, False, 0)
        page.pack_start(media_prog_box, False, False, 0)
        page.pack_start(ctrl_box, False, False, 0)
        page.pack_start(vol_box, False, False, 0)
        self.stack.add_named(page, "page2")

    # --- PÁGINA 3: SENSORES ---
    def setup_page_3(self):
        page = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        page.set_valign(Gtk.Align.CENTER); page.set_halign(Gtk.Align.CENTER)
        
        grid = Gtk.Grid(row_spacing=15, column_spacing=15)
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)

        def create_card(is_pie=False, pie_type="ram"):
            frame = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=5)
            frame.set_name("cardFrame")
            frame.set_halign(Gtk.Align.FILL); frame.set_valign(Gtk.Align.FILL)
            
            lbl_title = Gtk.Label()
            frame.pack_start(lbl_title, False, False, 5)
            
            if is_pie:
                da = Gtk.DrawingArea()
                da.set_size_request(50, 50) 
                da.set_vexpand(True); da.set_hexpand(True)
                da.connect("draw", self.draw_pie, pie_type)
                lbl_val = Gtk.Label(label="--%")
                lbl_val.set_name("sensorText")
                frame.pack_start(da, True, True, 0)
                frame.pack_start(lbl_val, False, False, 5)
                return frame, lbl_title, da, lbl_val
            else:
                lbl_val = Gtk.Label(label="--")
                lbl_val.set_name("bigValue")
                frame.pack_start(lbl_val, True, True, 0)
                return frame, lbl_title, lbl_val, None

        card_cpu_t, self.lbl_title_cpu_t, self.lbl_cpu_t, _ = create_card(False)
        card_gpu_t, self.lbl_title_gpu_t, self.lbl_gpu_t, _ = create_card(False)
        card_watts, self.lbl_title_watts, self.lbl_watts, _ = create_card(False)
        
        card_ram, self.lbl_title_ram, self.da_ram, self.lbl_ram = create_card(True, "ram")
        card_cpu, self.lbl_title_cpu, self.da_cpu, self.lbl_cpu = create_card(True, "cpu")
        card_bat_pct, self.lbl_title_bat, self.da_bat, self.lbl_bat_pct = create_card(True, "bat")

        grid.attach(card_cpu_t, 0, 0, 1, 1)
        grid.attach(card_gpu_t, 1, 0, 1, 1)
        grid.attach(card_watts, 2, 0, 1, 1)
        
        grid.attach(card_ram, 0, 1, 1, 1)
        grid.attach(card_cpu, 1, 1, 1, 1)
        grid.attach(card_bat_pct, 2, 1, 1, 1)

        page.pack_start(grid, True, True, 0) 
        self.stack.add_named(page, "page3")

    # --- PÁGINA 4: SISTEMA E JANELAS ---
    def setup_page_4(self):
        self.page4_stack = Gtk.Stack()
        self.page4_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.page4_stack.set_transition_duration(200)

        # 4.1 SUBPÁGINA PRINCIPAL
        page_main = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
        page_main.set_valign(Gtk.Align.CENTER); page_main.set_halign(Gtk.Align.CENTER)
        page_main.set_margin_start(10); page_main.set_margin_end(10) 

        self.lbl_app = Gtk.Label()
        self.lbl_app.set_name("titleLabel")
        self.lbl_app.set_ellipsize(Pango.EllipsizeMode.END)
        self.lbl_app.set_max_width_chars(30)
        page_main.pack_start(self.lbl_app, False, False, 0)

        grid = Gtk.Grid(row_spacing=10, column_spacing=15)
        grid.set_halign(Gtk.Align.FILL)
        grid.set_row_homogeneous(True)
        grid.set_column_homogeneous(True)

        self.btn_prev_ws = Gtk.Button(); self.btn_prev_ws.set_can_focus(False); self.btn_prev_ws.set_name("actionBtn")
        self.btn_next_ws = Gtk.Button(); self.btn_next_ws.set_can_focus(False); self.btn_next_ws.set_name("actionBtn")
        self.btn_close = Gtk.Button(); self.btn_close.set_can_focus(False); self.btn_close.set_name("actionBtn")
        self.btn_move = Gtk.Button(); self.btn_move.set_can_focus(False); self.btn_move.set_name("actionBtn")
        self.btn_fs = Gtk.Button(); self.btn_fs.set_can_focus(False); self.btn_fs.set_name("actionBtn")
        self.btn_mic = Gtk.Button(); self.btn_mic.set_can_focus(False); self.btn_mic.set_name("actionBtn")
        self.btn_open_win = Gtk.Button(); self.btn_open_win.set_can_focus(False); self.btn_open_win.set_name("actionBtn")
        self.btn_hide_panel = Gtk.Button(); self.btn_hide_panel.set_can_focus(False); self.btn_hide_panel.set_name("actionBtn")
        
        btns = [self.btn_prev_ws, self.btn_next_ws, self.btn_close, self.btn_move, self.btn_fs, self.btn_mic, self.btn_open_win, self.btn_hide_panel]
        for b in btns: 
            b.set_vexpand(True) 
            b.set_hexpand(True) 
            b.set_size_request(-1, 55) 
            
        grid.attach(self.btn_prev_ws, 0, 0, 1, 1)
        grid.attach(self.btn_next_ws, 1, 0, 1, 1)
        grid.attach(self.btn_close, 0, 1, 1, 1)
        grid.attach(self.btn_move, 1, 1, 1, 1)
        grid.attach(self.btn_fs, 0, 2, 1, 1)
        grid.attach(self.btn_mic, 1, 2, 1, 1)
        grid.attach(self.btn_open_win, 0, 3, 1, 1)
        grid.attach(self.btn_hide_panel, 1, 3, 1, 1)
        page_main.pack_start(grid, True, True, 0)
        
        # ATUALIZADO: Usando ';' para encadear a ação no Hyprland 0.56.0
        self.btn_prev_ws.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', "sleep 0.1 ; hyprctl dispatch 'hl.dispatch(hl.dsp.focus({ monitor = \"eDP-1\" }))' ; hyprctl dispatch 'hl.dispatch(hl.dsp.focus({ workspace = \"m-1\" }))'"]))
        self.btn_next_ws.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', "sleep 0.1 ; hyprctl dispatch 'hl.dispatch(hl.dsp.focus({ monitor = \"eDP-1\" }))' ; hyprctl dispatch 'hl.dispatch(hl.dsp.focus({ workspace = \"m+1\" }))'"]))
        self.btn_close.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', "hyprctl dispatch 'hl.dispatch(hl.dsp.window.close())'"]))
        self.btn_move.connect("clicked", self.toggle_window_monitor_exact)
        self.btn_fs.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', "hyprctl dispatch 'hl.dispatch(hl.dsp.window.fullscreen())'"]))
        self.btn_mic.connect("clicked", lambda x: subprocess.Popen(['bash', '-c', 'wpctl set-mute @DEFAULT_AUDIO_SOURCE@ toggle']))
        self.btn_open_win.connect("clicked", self.show_open_windows)
        self.btn_hide_panel.connect("clicked", lambda x: Gtk.main_quit())

        # 4.2 SUBPÁGINA: GRADE DE JANELAS ABERTAS
        page_windows = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        
        self.btn_back_grid = Gtk.Button(); self.btn_back_grid.set_name("btnCancel")
        self.btn_back_grid.set_size_request(-1, 50)
        self.btn_back_grid.connect("clicked", lambda x: self.page4_stack.set_visible_child_name("main"))
        
        self.win_scroll = Gtk.ScrolledWindow()
        self.win_scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        self.win_scroll.set_kinetic_scrolling(True)
        self.win_scroll.set_vexpand(True)
        
        self.win_flowbox = Gtk.FlowBox()
        self.win_flowbox.set_valign(Gtk.Align.START)
        self.win_flowbox.set_max_children_per_line(4)
        self.win_flowbox.set_min_children_per_line(4)
        self.win_flowbox.set_selection_mode(Gtk.SelectionMode.NONE)
        self.win_flowbox.set_homogeneous(True)
        self.win_flowbox.set_row_spacing(15)
        self.win_flowbox.set_column_spacing(15)
        self.win_flowbox.set_margin_start(20); self.win_flowbox.set_margin_end(20)
        self.win_flowbox.set_margin_top(15); self.win_flowbox.set_margin_bottom(15)
        
        self.win_flowbox.connect("child-activated", self.on_window_selected)
        self.win_scroll.add(self.win_flowbox)
        
        top_box = Gtk.Box()
        top_box.set_margin_start(20); top_box.set_margin_top(20); top_box.set_margin_bottom(10)
        top_box.pack_start(self.btn_back_grid, False, False, 0)
        page_windows.pack_start(top_box, False, False, 0)
        page_windows.pack_start(self.win_scroll, True, True, 0)

        # 4.3 SUBPÁGINA: COMANDOS ESPECÍFICOS DA JANELA
        page_controls = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=15)
        page_controls.set_valign(Gtk.Align.CENTER); page_controls.set_halign(Gtk.Align.CENTER)
        
        self.lbl_ctrl_win = Gtk.Label()
        self.lbl_ctrl_win.set_name("titleLabel")
        page_controls.pack_start(self.lbl_ctrl_win, False, False, 0)
        
        ctrl_grid = Gtk.Grid(row_spacing=10, column_spacing=15)
        ctrl_grid.set_halign(Gtk.Align.CENTER)
        ctrl_grid.set_row_homogeneous(True)
        ctrl_grid.set_column_homogeneous(True)

        self.cw_close = Gtk.Button(); self.cw_close.set_name("actionBtn")
        self.cw_prev = Gtk.Button(); self.cw_prev.set_name("actionBtn")
        self.cw_next = Gtk.Button(); self.cw_next.set_name("actionBtn")
        self.cw_move = Gtk.Button(); self.cw_move.set_name("actionBtn")
        self.cw_fs = Gtk.Button(); self.cw_fs.set_name("actionBtn")
        self.cw_back = Gtk.Button(); self.cw_back.set_name("btnCancel")
        
        for b in [self.cw_close, self.cw_prev, self.cw_next, self.cw_move, self.cw_fs, self.cw_back]:
            b.set_size_request(180, 45)
            b.set_hexpand(True)

        ctrl_grid.attach(self.cw_prev, 0, 0, 1, 1)
        ctrl_grid.attach(self.cw_next, 1, 0, 1, 1)
        ctrl_grid.attach(self.cw_close, 0, 1, 1, 1)
        ctrl_grid.attach(self.cw_move, 1, 1, 1, 1)
        ctrl_grid.attach(self.cw_fs, 0, 2, 2, 1)
        ctrl_grid.attach(self.cw_back, 0, 3, 2, 1)
        page_controls.pack_start(ctrl_grid, True, True, 0)

        self.cw_close.connect("clicked", self.on_cw_close)
        self.cw_prev.connect("clicked", self.on_cw_prev)
        self.cw_next.connect("clicked", self.on_cw_next)
        self.cw_move.connect("clicked", self.on_cw_move)
        self.cw_fs.connect("clicked", self.on_cw_fs)
        self.cw_back.connect("clicked", lambda x: self.close_window_controls())

        self.page4_stack.add_named(page_main, "main")
        self.page4_stack.add_named(page_windows, "windows_grid")
        self.page4_stack.add_named(page_controls, "window_controls")

        self.stack.add_named(self.page4_stack, "page4")

    # --- LÓGICA DOS SLIDERS (GPU/TDP/FAN/CPU) ---
    def on_tdp_change(self, scale, lbl, title_key):
        val = int(scale.get_value())
        lbl.set_text(f"🔥 TDP\n{val}W")
        
    def on_cpu_epp_change(self, scale, lbl, title_key):
        val = int(scale.get_value())
        epp_labels = {0: "Power", 1: "Bal-Pw", 2: "Bal-Pf", 3: "Perf"}
        lbl.set_text(f"⚙️ CPU\n{epp_labels.get(val, 'Bal-Pw')}")

    def on_fan_change(self, scale, lbl, title_key):
        val = int(scale.get_value())
        lbl.set_text(f"🌀 FAN\nAuto" if val == 0 else f"🌀 FAN\n{val}%")

    def on_gpu_change(self, scale, lbl, title_key):
        val = int(scale.get_value())
        if 0 < val < 700:
            GLib.idle_add(scale.set_value, 700)
            val = 700
        lbl.set_text(f"🎮 GPU\nAuto" if val == 0 else f"🎮 GPU\n{val}MHz")

    def apply_hardware(self):
        tdp = int(self.sl_tdp.get_value())
        fan = int(self.sl_fan.get_value())
        gpu = int(self.sl_gpu.get_value())
        cpu_val = int(self.sl_cpu_epp.get_value())
        mw = tdp * 1000
        
        gpu_cmd = f"echo {'auto' if gpu == 0 else gpu} > /tmp/gpu_clock; "
        
        epp_modes = {0: "power", 1: "balance_power", 2: "balance_performance", 3: "performance"}
        cpu_cmd = f"echo {epp_modes.get(cpu_val, 'balance_power')} > /tmp/cpu_epp; "
        
        bash_cmd = f"sudo ryzenadj --stapm-limit={mw} --fast-limit={mw} --slow-limit={mw}; echo {tdp} > /tmp/current_tdp; " + gpu_cmd + cpu_cmd
        
        if fan == 0:
            bash_cmd += "echo 'auto' > /tmp/fan_mode; "
            for p_en in glob.glob("/sys/class/hwmon/hwmon*/pwm1_enable"): bash_cmd += f"echo 0 | sudo tee {p_en} > /dev/null; "
        else:
            bash_cmd += f"echo {fan} > /tmp/fan_mode; "
            pwm = int((fan / 100) * 255)
            for p_en in glob.glob("/sys/class/hwmon/hwmon*/pwm1_enable"): bash_cmd += f"echo 1 | sudo tee {p_en} > /dev/null; "
            for p_pwm in glob.glob("/sys/class/hwmon/hwmon*/pwm1"): bash_cmd += f"echo {pwm} | sudo tee {p_pwm} > /dev/null; "
        
        subprocess.Popen(['bash', '-c', bash_cmd])
        os.system(f"notify-send 'Ayaneo Control' 'Configurações de Hardware Aplicadas'")

    # --- LÓGICA DE JANELAS ESPECÍFICAS ---
    def show_open_windows(self, btn=None):
        for child in self.win_flowbox.get_children():
            self.win_flowbox.remove(child)
            
        try:
            out = subprocess.getoutput("hyprctl clients -j")
            clients = json.loads(out)
            for c in clients:
                if c.get("mapped") and c.get("class"): 
                    box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
                    box.set_valign(Gtk.Align.CENTER)
                    
                    icon_name = c.get("initialClass", "application-x-executable").lower()
                    icon = Gtk.Image.new_from_icon_name(icon_name, Gtk.IconSize.DIALOG)
                    icon.set_pixel_size(60)
                    
                    title = c.get("title", c.get("class"))
                    lbl = Gtk.Label(label=title)
                    lbl.set_name("appLabel")
                    lbl.set_ellipsize(Pango.EllipsizeMode.END)
                    lbl.set_max_width_chars(15)
                    
                    box.pack_start(icon, True, True, 0)
                    box.pack_start(lbl, False, False, 0)
                    
                    child = Gtk.FlowBoxChild()
                    child.set_name("appCard")
                    child.add(box)
                    child.window_data = c
                    self.win_flowbox.add(child)
            self.win_flowbox.show_all()
        except: pass
        self.page4_stack.set_visible_child_name("windows_grid")
        return False

    def on_window_selected(self, flowbox, child):
        c = child.window_data
        self.active_control_window_address = c.get("address")
        title = c.get("title", c.get("class"))
        
        if title and len(title) > 35:
            title = title[:33] + "..."
            
        self.lbl_ctrl_win.set_text(f"{self._t('manage')}: {title}")
        
        subprocess.Popen(f"hyprctl dispatch 'hl.dispatch(hl.dsp.focus({{ window = \"address:{self.active_control_window_address}\" }}))'", shell=True)
        self.page4_stack.set_visible_child_name("window_controls")

    def close_window_controls(self):
        self.active_control_window_address = None
        self.page4_stack.set_visible_child_name("windows_grid")

    def on_cw_close(self, btn):
        if self.active_control_window_address:
            subprocess.Popen(f"hyprctl dispatch 'hl.dispatch(hl.dsp.window.close({{ window = \"address:{self.active_control_window_address}\" }}))'", shell=True)
            GLib.timeout_add(400, self.show_open_windows) 

    def on_cw_prev(self, btn):
        if self.active_control_window_address:
            # ATUALIZADO: Usando ';' para encadear a ação no Hyprland 0.56.0
            subprocess.Popen(f"hyprctl dispatch 'hl.dispatch(hl.dsp.focus({{ window = \"address:{self.active_control_window_address}\" }}))' ; hyprctl dispatch 'hl.dispatch(hl.dsp.window.move({{ workspace = \"m-1\" }}))'", shell=True)

    def on_cw_next(self, btn):
        if self.active_control_window_address:
            # ATUALIZADO: Usando ';' para encadear a ação no Hyprland 0.56.0
            subprocess.Popen(f"hyprctl dispatch 'hl.dispatch(hl.dsp.focus({{ window = \"address:{self.active_control_window_address}\" }}))' ; hyprctl dispatch 'hl.dispatch(hl.dsp.window.move({{ workspace = \"m+1\" }}))'", shell=True)
            
    def on_cw_fs(self, btn):
        if self.active_control_window_address:
            # ATUALIZADO: Usando ';' para encadear a ação no Hyprland 0.56.0
            subprocess.Popen(f"hyprctl dispatch 'hl.dispatch(hl.dsp.focus({{ window = \"address:{self.active_control_window_address}\" }}))' ; hyprctl dispatch 'hl.dispatch(hl.dsp.window.fullscreen())'", shell=True)

    def on_cw_move(self, btn):
        if not self.active_control_window_address: return
        try:
            out = subprocess.getoutput("hyprctl clients -j")
            clients = json.loads(out)
            client = next((c for c in clients if c["address"] == self.active_control_window_address), None)
            if not client: return
            
            monitors_out = subprocess.getoutput("hyprctl monitors -j")
            monitors = json.loads(monitors_out)
            current_name = next((m["name"] for m in monitors if m["id"] == client["monitor"]), "")
            
            target_mon = "eDP-1" if current_name == "DP-1" else "DP-1"
            # ATUALIZADO: Usando ';' para encadear a ação no Hyprland 0.56.0
            cmd = f"hyprctl dispatch 'hl.dispatch(hl.dsp.focus({{ window = \"address:{self.active_control_window_address}\" }}))' ; hyprctl dispatch 'hl.dispatch(hl.dsp.window.move({{ monitor = \"{target_mon}\" }}))'"
            subprocess.Popen(cmd, shell=True)
        except Exception as e: pass

    # --- LÓGICA DE EVENTOS (HARDWARE/MÍDIA) ---
    def on_volume_change(self, scale):
        val = int(scale.get_value())
        subprocess.Popen(['bash', '-c', f'wpctl set-volume -l 2 @DEFAULT_AUDIO_SINK@ {val}%'])

    def on_media_seek(self, scale, scroll_type, value):
        subprocess.Popen(['bash', '-c', f'playerctl position {value}'])
        return False

    def toggle_window_monitor_exact(self, btn):
        try:
            out = subprocess.getoutput("hyprctl activewindow -j")
            if not out.strip(): return
            data = json.loads(out)
            current_mon_id = data.get("monitor", -1)
            
            monitors_out = subprocess.getoutput("hyprctl monitors -j")
            monitors = json.loads(monitors_out)
            current_name = ""
            for m in monitors:
                if m["id"] == current_mon_id:
                    current_name = m["name"]
            
            target_mon = "eDP-1" if current_name == "DP-1" else "DP-1"
            subprocess.Popen(['bash', '-c', f"hyprctl dispatch 'hl.dispatch(hl.dsp.window.move({{ monitor = \"{target_mon}\" }}))'"])
        except Exception as e:
            pass

    # --- DESENHO COM CAIRO ---
    def draw_pie(self, widget, cr, pie_type):
        if pie_type == "ram": val = self.ram_percent
        elif pie_type == "cpu": val = self.cpu_percent
        else: val = self.bat_percent

        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        r = min(w, h) / 2.0 - 5

        cr.set_source_rgb(0.16, 0.16, 0.16) 
        cr.arc(w/2, h/2, r, 0, 2*math.pi)
        cr.fill()
        
        if pie_type == "bat":
            if val > 50: cr.set_source_rgb(0.2, 0.8, 0.2)
            elif val > 20: cr.set_source_rgb(0.8, 0.8, 0.2)
            else: cr.set_source_rgb(0.8, 0.2, 0.2)
        else:
            cr.set_source_rgb(1.0, 1.0, 1.0)
            
        start_angle = -math.pi / 2
        end_angle = start_angle + (val / 100.0) * 2 * math.pi
        cr.move_to(w/2, h/2)
        cr.arc(w/2, h/2, r, start_angle, end_angle)
        cr.close_path()
        cr.fill()

    def draw_line_graph(self, widget, cr):
        w = widget.get_allocated_width()
        h = widget.get_allocated_height()
        
        cr.set_source_rgb(0.2, 0.2, 0.2)
        cr.move_to(0, h/2)
        cr.line_to(w, h/2)
        cr.stroke()
        
        if not self.bat_w_history: return
        max_v = max(abs(max(self.bat_w_history)), abs(min(self.bat_w_history)))
        max_v = max_v if max_v > 1 else 1
        
        cr.set_source_rgb(1.0, 1.0, 1.0)
        cr.set_line_width(2)
        
        for i, val in enumerate(self.bat_w_history):
            norm = val / max_v
            x = (i / self.history_len) * w
            y = (h / 2) - (norm * (h / 2) * 0.8)
            if i == 0: cr.move_to(x, y)
            else: cr.line_to(x, y)
        cr.stroke()

    # --- TELEMETRIA PRINCIPAL ---
    def update_telemetry(self):
        current_time = datetime.now().strftime("%H:%M:%S")

        if hasattr(self, 'page4_stack') and self.page4_stack.get_visible_child_name() == "window_controls":
            if self.active_control_window_address:
                try:
                    active_out = subprocess.getoutput("hyprctl activewindow -j")
                    active_data = json.loads(active_out)
                    if active_data.get("address") != self.active_control_window_address:
                        subprocess.Popen(f"hyprctl dispatch 'hl.dispatch(hl.dsp.focus({{ window = \"address:{self.active_control_window_address}\" }}))'", shell=True)
                except: pass

        try:
            bat_path = glob.glob("/sys/class/power_supply/BAT*")[0]
            with open(f"{bat_path}/status", "r") as f: status = f.read().strip()
            with open(f"{bat_path}/power_now", "r") as f: p_now = int(f.read())
            with open(f"{bat_path}/capacity", "r") as f: cap = int(f.read())
            
            self.bat_percent = cap
            w = p_now / 1000000
            sign = "+" if status == "Charging" else "-" if status == "Discharging" else ""
            w_str = f"{sign}{w:.1f}W"
            
            self.lbl_p1_bat_w.set_text(f"⚡ {w_str}")
            self.lbl_watts.set_text(f"⚡ {w_str}")
            self.bat_w_history.append(w if status == "Charging" else -w)

            time_str = ""
            if status == "Discharging" and p_now > 0:
                with open(f"{bat_path}/energy_now", "r") as f: energy = int(f.read())
                h_float = energy / p_now
                time_str = f"{int(h_float)}h {int((h_float - int(h_float)) * 60):02d}m {self._t('remaining')}"
            elif status == "Charging" and p_now > 0:
                with open(f"{bat_path}/energy_now", "r") as f: e_now = int(f.read())
                with open(f"{bat_path}/energy_full", "r") as f: e_full = int(f.read())
                h_float = (e_full - e_now) / p_now
                time_str = f"{int(h_float)}h {int((h_float - int(h_float)) * 60):02d}m {self._t('to_full')}"
            else:
                time_str = self._t('charged')

            self.lbl_p1_bat_time.set_text(f"⏳ {time_str}")
            self.lbl_top_battery.set_text(f"🔋 {cap}% | 🕒 {current_time} | ⚡ {w_str} | ⏳ {time_str}")
            self.lbl_bat_pct.set_text(f"🔋 {cap}%")
            
            self.graph_bat_p1.queue_draw()
            self.da_bat.queue_draw()
        except: pass

        cpu_t = 0
        gpu_t = 0
        for p in glob.glob("/sys/class/hwmon/hwmon*"):
            try:
                with open(f"{p}/name", "r") as f:
                    name = f.read().strip()
                if name == "k10temp":
                    with open(f"{p}/temp1_input", "r") as f:
                        cpu_t = float(f.read()) / 1000
                elif name == "amdgpu":
                    with open(f"{p}/temp1_input", "r") as f:
                        gpu_t = float(f.read()) / 1000
            except: pass

        self.lbl_cpu_t.set_text(f"🌡️ {cpu_t:.0f}°C")
        self.lbl_gpu_t.set_text(f"🌡️ {gpu_t:.0f}°C")

        ram = psutil.virtual_memory()
        self.cpu_percent = psutil.cpu_percent()
        self.ram_percent = ram.percent
        
        # NOVO: RAM em GB no lugar de %
        ram_used_gb = ram.used / (1024**3)
        
        self.lbl_ram.set_text(f"🧠 {ram_used_gb:.1f} GB")
        self.lbl_cpu.set_text(f"⚙️ {self.cpu_percent}%")
        self.da_ram.queue_draw()
        self.da_cpu.queue_draw()

        curr_page = self.stack.get_visible_child_name()
        if curr_page == "page2":
            media = subprocess.getoutput("playerctl metadata --format '{{ artist }} - {{ title }}' 2>/dev/null")
            if media and media.strip(): 
                self.lbl_media.set_text(f"🎵 {media.strip()}")
                try:
                    pos = float(subprocess.getoutput("playerctl position 2>/dev/null"))
                    length = float(subprocess.getoutput("playerctl metadata mpris:length 2>/dev/null")) / 1000000.0
                    
                    self.media_adj.set_upper(length)
                    self.sl_media_pos.set_value(pos)
                    
                    def fmt(s): return f"{int(s)//60}:{int(s)%60:02d}"
                    self.lbl_media_time.set_text(f"{fmt(pos)} / {fmt(length)}")
                    
                    self.sl_media_pos.show()
                    self.lbl_media_time.show()
                except:
                    self.sl_media_pos.hide()
                    self.lbl_media_time.hide()
            else:
                self.lbl_media.set_text(self._t("no_media"))
                self.sl_media_pos.hide()
                self.lbl_media_time.hide()
                
        elif curr_page == "page4":
            try:
                out = subprocess.getoutput("hyprctl activewindow -j")
                data = json.loads(out)
                app_name = data.get('class', self._t('none'))
                self.lbl_app.set_text(f"{self._t('app_foc')}: {app_name}")
            except: pass

        return True 

    # --- ESTILIZAÇÃO CSS GLOBAL ---
    def apply_css(self):
        css_str = """
        window { 
            background-color: #121212; 
            color: #ffffff; 
            font-family: 'Inter', sans-serif; 
            font-size: 18px; 
        }
        #statusBar { background-color: #0a0a0a; border-top: 1px solid #2a2a2a; border-bottom: 1px solid #2a2a2a; }
        #cardFrame { background-color: #1a1a1a; border-radius: 14px; border: 1px solid #333333; padding: 15px; }
        #titleLabel { font-size: 24px; font-weight: bold; }
        #bigValue { font-size: 32px; font-weight: bold; }
        #sensorText { font-size: 18px; font-weight: bold; }
        #sliderText { font-size: 18px; font-weight: bold; }
        
        scale contents { background-color: #2a2a2a; border-radius: 8px; }
        scale highlight { background-color: #ffffff; border-radius: 8px; }
        scale slider { background-color: #ffffff; border-radius: 12px; min-width: 25px; min-height: 25px; }
        
        scale#thickSlider.vertical contents { min-width: 25px; }
        scale#thickSlider.vertical slider { min-height: 35px; min-width: 45px; border-radius: 8px; }
        
        button { 
            background-color: #2a2a2a; border-radius: 14px; border: 1px solid #444; 
            font-weight: bold; padding: 12px 18px; color: #ffffff; font-size: 14px;
        }
        
        button:hover { background-color: #333333; } 
        button:active { background-color: #ffffff; color: #000000; }
        button:focus { outline: none; } 
        
        #btnTopBar {
            background-color: transparent;
            border: none;
            color: #ffffff;
            font-size: 20px;
            padding: 2px 10px;
        }
        #btnTopBar:hover { background-color: #333; border-radius: 8px; }
        
        flowboxchild#appCard {
            background-color: #1a1a1a;
            border-radius: 16px;
            border: 2px solid #333;
            padding: 10px;
            outline: none; 
        }
        flowboxchild#appCard:hover { background-color: #2a2a2a; border-color: #555; }
        flowboxchild#appCard:active { background-color: #444; border-color: #fff; }
        
        #procRow {
            background-color: #1a1a1a;
            border-radius: 10px;
            padding: 10px;
            border: 1px solid #2a2a2a;
        }
        
        #appLabel { font-size: 14px; font-weight: bold; margin-top: 5px; }
        
        #btnLaunch { background-color: #1a4a22; font-size: 22px;}
        #btnCancel { background-color: #4a1a1a; font-size: 22px;}
        #btnLaunch:hover { background-color: #256b31; }
        #btnCancel:hover { background-color: #6b2525; }
        
        scrollbar { opacity: 0.1; }
        #navBtn { font-family: 'Public Sans', sans-serif; }
        #mediaBtn { font-size: 36px; }
        """
        provider = Gtk.CssProvider()
        provider.load_from_data(css_str.encode('utf-8'))
        Gtk.StyleContext.add_provider_for_screen(Gdk.Screen.get_default(), provider, Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION)

if __name__ == "__main__":
    win = FercDSMenu()
    win.connect("destroy", Gtk.main_quit)
    win.show_all()
    Gtk.main()
