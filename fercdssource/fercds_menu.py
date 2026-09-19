import sys
import os
import subprocess
import glob
import json
import psutil
import math
import re
from collections import deque
from datetime import datetime

import gi
gi.require_version('Gtk', '3.0')
gi.require_version('GtkLayerShell', '0.1')
gi.require_version('GdkPixbuf', '2.0')
from gi.repository import Gtk, Gdk, GLib, GtkLayerShell, Pango, GdkPixbuf

# Separa o emoji (no inicio ou no fim) do texto de um label das traducoes (ex: seta + "Voltar",
# ou "Avancar" + seta), usado pelos cards quadrados da pagina Sistema para exibir o icone grande
# acima da legenda. Construido via chr()/range() (em vez de colar os simbolos no codigo-fonte)
# para deixar exatos quais blocos Unicode contam como "icone".
def _unicode_range(start_codepoint, end_codepoint_inclusive):
    return "".join(chr(c) for c in range(start_codepoint, end_codepoint_inclusive + 1))

_ICON_CHARS = (
    _unicode_range(0x1F300, 0x1FAFF)  # bloco principal de emojis
    + _unicode_range(0x2600, 0x27BF)  # simbolos diversos + dingbats
    + _unicode_range(0x2B00, 0x2BFF)  # simbolos e setas diversas
    + _unicode_range(0x2190, 0x21FF)  # bloco de setas
    + chr(0xFE0F)                     # variation selector-16 (apresentacao em emoji)
)
_ICON_CLASS = re.escape(_ICON_CHARS)
_ICON_LEAD_RE = re.compile(r"^([" + _ICON_CLASS + r"]+)\s*(.*)$", re.DOTALL)
_ICON_TRAIL_RE = re.compile(r"^(.*?)\s*([" + _ICON_CLASS + r"]+)$", re.DOTALL)

def split_icon_caption(text):
    text = text.strip()
    m = _ICON_LEAD_RE.match(text)
    if m and m.group(1):
        return m.group(1), m.group(2).strip()
    m = _ICON_TRAIL_RE.match(text)
    if m and m.group(2):
        return m.group(2), m.group(1).strip()
    return "", text

# --- CATEGORIAS DA BIBLIOTECA ---
# Ordem fixa da barra de filtros (a primeira e o "mostrar tudo", nao e atribuivel).
CATEGORY_ORDER = ["all", "games", "social", "work", "tools"]
# "Ocultos" nao entra na barra de filtros: app marcado assim some da biblioteca
# inteira (ate de "Todos") e so reaparece na subpagina de configuracoes, que e
# de onde ele pode ser trazido de volta.
HIDDEN_CATEGORY = "hidden"
# Categorias que podem ser marcadas a mao em um app, na subpagina de lancamento.
ASSIGNABLE_CATEGORIES = ["games", "social", "work", "tools", HIDDEN_CATEGORY]
CATEGORY_TEXT_KEYS = {
    "all": "cat_all",
    "games": "cat_games",
    "social": "cat_social",
    "work": "cat_work",
    "tools": "cat_tools",
    HIDDEN_CATEGORY: "cat_hidden",
}

# --- ICONES DOS .DESKTOP ---
# Boa parte dos .desktop instalados (Waydroid, AppImages, jogos exportados pelo
# Ryujinx) poe em Icon= um caminho de arquivo, nao um nome do tema de icones.
# Gtk.Image.new_from_icon_name() so entende nome de tema, entao esses apps
# ficavam sem icone na biblioteca e certinhos no Dolphin, que resolve o caminho
# na mao. As constantes abaixo alimentam resolve_icon_path().
ICON_EXTENSIONS = (".png", ".svg", ".xpm", ".jpg", ".jpeg", ".ico", ".webp")
# Pastas onde um Icon= sem barra ainda pode estar como arquivo solto.
ICON_FALLBACK_DIRS = [
    "/usr/share/pixmaps",
    "/usr/share/icons",
    os.path.expanduser("~/.local/share/pixmaps"),
    os.path.expanduser("~/.local/share/icons"),
    os.path.expanduser("~/.icons"),
]

# Monitor em que o painel deve sempre abrir. A ancoragem e feita pelo proprio
# cliente, via layer shell, entao nao e mais preciso mover o foco do Hyprland
# para esta tela antes de lancar o menu.
TARGET_MONITOR = "DP-1"

def find_gdk_monitor(connector_name):
    """Devolve o GdkMonitor do conector (ex.: "DP-1"), ou None se ele nao existir.

    No Wayland o GDK expoe apenas fabricante/modelo do wl_output, nunca o nome do
    conector, por isso a correspondencia e feita pela posicao logica informada
    pelo Hyprland, tendo o modelo do EDID como ultimo recurso.
    """
    display = Gdk.Display.get_default()
    if display is None:
        return None

    monitors = [display.get_monitor(i) for i in range(display.get_n_monitors())]
    monitors = [m for m in monitors if m is not None]

    # Alguns backends ja devolvem o proprio nome do conector em get_model().
    for m in monitors:
        if m.get_model() == connector_name:
            return m

    try:
        out = subprocess.run(["hyprctl", "monitors", "-j"],
                             capture_output=True, text=True, timeout=2).stdout
        info = next((mon for mon in json.loads(out)
                     if mon.get("name") == connector_name), None)
    except Exception:
        info = None

    if info is not None:
        for m in monitors:
            geo = m.get_geometry()
            if geo.x == info.get("x") and geo.y == info.get("y"):
                return m
        description = info.get("description", "")
        for m in monitors:
            model = m.get_model() or ""
            if model and model in description:
                return m

    return None

class FercDSMenu(Gtk.Window):
    def __init__(self):
        super().__init__(title="Ferc-DS Menu")
        self.set_name("FercDSMenu") 

        # --- CONFIGURAÇÃO NATIVA WAYLAND LAYER SHELL ---
        GtkLayerShell.init_for_window(self)

        # Prende a superfície ao DP-1 antes de mapear a janela; sem isso o
        # compositor entrega o painel ao monitor que estiver em foco na hora.
        target_monitor = find_gdk_monitor(TARGET_MONITOR)
        if target_monitor is not None:
            GtkLayerShell.set_monitor(self, target_monitor)
        else:
            print("[ferc-ds] monitor %s não encontrado; abrindo no monitor em foco"
                  % TARGET_MONITOR, file=sys.stderr)

        # OVERLAY é a camada mais alta do wlr-layer-shell: fica acima de todas as
        # janelas e das camadas background/bottom/top. A posição dentro da própria
        # camada overlay vem da layerrule "order" do Hyprland (customferc/rules.conf).
        GtkLayerShell.set_layer(self, GtkLayerShell.Layer.OVERLAY)
        GtkLayerShell.set_namespace(self, "ferc-ds")
        GtkLayerShell.set_exclusive_zone(self, -1)
        # Sem foco de teclado: o painel é todo por toque/mouse e assim nunca rouba
        # o foco da janela que estiver em uso no outro monitor.
        GtkLayerShell.set_keyboard_mode(self, GtkLayerShell.KeyboardMode.NONE)
        
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
        self.cat_file = os.path.expanduser("~/.config/ferc-ds/categories.json")
        self.pin_file = os.path.expanduser("~/.config/ferc-ds/pinned.json")
        # Pasta onde o usuario larga .desktop proprios; a biblioteca le junto com o sistema.
        self.custom_apps_dir = os.path.expanduser("~/.fercds/customapps")

        # --- CATEGORIAS E FIXADOS (tudo marcado manualmente) ---
        self.app_categories = self.load_app_categories()
        self.pinned_apps = self.load_pinned_apps()
        self.default_category = self.get_default_category()
        self.current_category = self.default_category

        # Icones ja resolvidos: {(valor do Icon=, tamanho em px): cairo surface}.
        # O DP-1 roda em scale=2, entao o arquivo e lido no dobro do tamanho.
        self._icon_cache = {}
        self._icon_scale = self.icon_scale_factor(target_monitor)
        
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

    # --- CATEGORIAS DA BIBLIOTECA ---
    def load_app_categories(self):
        """Mapa {nome do app: categoria}. Nada e adivinhado: so entra aqui o que
        foi marcado a mao na subpagina de lancamento."""
        try:
            if os.path.exists(self.cat_file):
                with open(self.cat_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                return {k: v for k, v in data.items() if v in ASSIGNABLE_CATEGORIES}
        except: pass
        return {}

    def save_app_categories(self):
        try:
            os.makedirs(os.path.dirname(self.cat_file), exist_ok=True)
            with open(self.cat_file, 'w', encoding='utf-8') as f:
                json.dump(self.app_categories, f, ensure_ascii=False, indent=2)
        except: pass

    def cat_label(self, code):
        # code None (app sem categoria) e "none" (opcao de limpar) caem no mesmo texto.
        return self._t(CATEGORY_TEXT_KEYS.get(code, "cat_none"))

    # --- APPS FIXADOS ---
    def load_pinned_apps(self):
        """Nomes dos apps fixados. Fixado sobe pro topo da grade em qualquer
        categoria, mesmo que outro app tenha sido aberto muito mais vezes."""
        try:
            if os.path.exists(self.pin_file):
                with open(self.pin_file, 'r', encoding='utf-8') as f:
                    return set(json.load(f))
        except: pass
        return set()

    def save_pinned_apps(self):
        try:
            os.makedirs(os.path.dirname(self.pin_file), exist_ok=True)
            with open(self.pin_file, 'w', encoding='utf-8') as f:
                json.dump(sorted(self.pinned_apps), f, ensure_ascii=False, indent=2)
        except: pass

    def sort_apps(self):
        """Ordem unica da biblioteca: fixados na frente, depois os mais usados."""
        self.apps_data.sort(key=lambda a: (not a.get("pinned"),
                                           -a.get("count", 0),
                                           a.get("name", "").lower()))

    # --- ICONES DOS APPS ---
    def icon_scale_factor(self, monitor):
        """Escala do monitor do painel. Icone lido de arquivo precisa vir no
        tamanho fisico (logico x escala) para nao sair borrado no HiDPI."""
        try:
            if monitor is not None:
                return max(1, monitor.get_scale_factor())
        except Exception: pass
        return 1

    def resolve_icon_path(self, icon_value):
        """Arquivo apontado por Icon=, ou None quando o tema de icones da conta.

        Trata os tres formatos que aparecem na pratica: caminho absoluto (com ou
        sem extensao), nome de tema puro e nome com extensao colada.
        """
        if not icon_value:
            return None

        value = os.path.expanduser(icon_value)
        if "/" in value:
            base, ext = os.path.splitext(value)
            candidates = [value] + [value + e for e in ICON_EXTENSIONS]
            if ext:
                # Alguns .desktop apontam pra extensao que nao e a do arquivo real.
                candidates += [base + e for e in ICON_EXTENSIONS]
            for candidate in candidates:
                if os.path.isfile(candidate):
                    return candidate
            return None

        name = value
        if name.lower().endswith(ICON_EXTENSIONS):
            name = os.path.splitext(name)[0]
        try:
            if Gtk.IconTheme.get_default().has_icon(name):
                return None
        except Exception:
            return None

        # Ultimo recurso: arquivo solto numa pasta de icones que nao e um tema
        # valido (sem index.theme), que o GTK nao varre sozinho.
        for folder in ICON_FALLBACK_DIRS:
            for ext in ICON_EXTENSIONS:
                candidate = os.path.join(folder, name + ext)
                if os.path.isfile(candidate):
                    return candidate
        for folder in ICON_FALLBACK_DIRS:
            for ext in ICON_EXTENSIONS:
                hits = glob.glob(os.path.join(folder, "*", "*", name + ext))
                if hits:
                    # Entre varios tamanhos (48x48, 512x512...), fica com o maior.
                    return max(hits, key=self._icon_dir_size)
        return None

    @staticmethod
    def _icon_dir_size(path):
        m = re.search(r"(\d+)x\d+", path)
        return int(m.group(1)) if m else 0

    def icon_surface(self, icon_value, size):
        """Surface do icone quando ele vem de arquivo; None manda usar o tema."""
        key = (icon_value, size)
        if key in self._icon_cache:
            return self._icon_cache[key]

        surface = None
        path = self.resolve_icon_path(icon_value)
        if path:
            try:
                scale = self._icon_scale
                pixbuf = GdkPixbuf.Pixbuf.new_from_file_at_scale(
                    path, size * scale, size * scale, True)
                surface = Gdk.cairo_surface_create_from_pixbuf(pixbuf, scale, self.get_window())
            except Exception:
                surface = None

        self._icon_cache[key] = surface
        return surface

    def set_app_icon(self, image, icon_value, size):
        """Preenche um Gtk.Image com o icone do app, venha ele do tema ou de arquivo."""
        surface = self.icon_surface(icon_value, size)
        if surface is not None:
            image.set_from_surface(surface)
            return

        name = icon_value or "application-x-executable"
        if "/" in name:
            # Caminho que nao existe mais: pedir isso ao tema so daria icone quebrado.
            name = "application-x-executable"
        elif name.lower().endswith(ICON_EXTENSIONS):
            name = os.path.splitext(name)[0]
        image.set_from_icon_name(name, Gtk.IconSize.DIALOG)
        image.set_pixel_size(size)

    def new_app_icon(self, icon_value, size):
        image = Gtk.Image()
        self.set_app_icon(image, icon_value, size)
        return image

    def get_default_category(self):
        try:
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    cat = json.load(f).get("default_category", "all")
                if cat in CATEGORY_ORDER:
                    return cat
        except: pass
        return "all"

    def set_default_category(self, cat):
        try:
            data = {}
            if os.path.exists(self.state_file):
                with open(self.state_file, 'r') as f:
                    data = json.load(f)
            data["default_category"] = cat
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
            self.cat_revealer.set_reveal_child(False)
            # A biblioteca sempre reabre na categoria padrao das configuracoes.
            if page_name == "page5" and self.current_category != self.default_category:
                self.current_category = self.default_category
                self.refresh_category_bar()
                self.populate_flowbox()
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
        # A pasta de apps customizados vem primeiro de proposito: um .desktop colocado
        # la substitui o do sistema que tenha o mesmo Name (o seen_names ignora o 2o).
        try:
            os.makedirs(self.custom_apps_dir, exist_ok=True)
        except: pass

        app_paths = [
            self.custom_apps_dir,
            "/usr/share/applications",
            os.path.expanduser("~/.local/share/applications"),
            "/var/lib/flatpak/exports/share/applications/",
            os.path.expanduser("~/.local/share/flatpak/exports/share/applications/")
        ]
        
        seen_names = set()
        for path in app_paths:
            if not os.path.exists(path): continue
            is_custom = path == self.custom_apps_dir
            for file in glob.glob(f"{path}/*.desktop"):
                try:
                    with open(file, 'r', encoding='utf-8') as f:
                        content = f.read()

                    # Na pasta customapps o .desktop foi posto ali de proposito, entao
                    # NoDisplay/Hidden nao escondem o app da biblioteca.
                    if not is_custom and ("NoDisplay=true" in content or "Hidden=true" in content):
                        continue
                        
                    name = ""
                    icon = ""
                    cmd = ""

                    in_entry = False
                    for line in content.splitlines():
                        line = line.strip()
                        if line.startswith("["):
                            # So o grupo [Desktop Entry] vale: os grupos de acao
                            # ("[Desktop Action nova-janela]") trazem Name/Exec/Icon
                            # proprios e sobrescreviam o do app.
                            in_entry = line == "[Desktop Entry]"
                            continue
                        if not in_entry:
                            continue
                        if line.startswith("Name=") and not name:
                            name = line.split("=", 1)[1].strip()
                        elif line.startswith("Icon=") and not icon:
                            icon = line.split("=", 1)[1].strip()
                        elif line.startswith("Exec=") and not cmd:
                            cmd = line.split("=", 1)[1].strip()
                            cmd = cmd.split("%")[0].strip()
                            
                    if name and cmd and name not in seen_names:
                        usage_count = count_db.get(name, 0)
                        self.apps_data.append({
                            "name": name,
                            "icon": icon or "application-x-executable",
                            "command": cmd,
                            "count": usage_count,
                            "category": self.app_categories.get(name),
                            "pinned": name in self.pinned_apps,
                            "custom": is_custom
                        })
                        seen_names.add(name)
                except:
                    continue
                    
        self.sort_apps()

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
        top_bar.set_margin_top(5); top_bar.set_margin_bottom(0)
        top_bar.set_size_request(-1, 56) 
        
        self.lbl_top_battery = Gtk.Label(label="🔋 --% | 🕒 --:--:-- | ⚡ -- | ⏳ --")
        top_bar.pack_start(self.lbl_top_battery, False, False, 0)

        # Container Direita: [Língua] [Processos] [Switch]
        right_box = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=15)
        right_box.set_valign(Gtk.Align.CENTER)

        # 4) Configurações (fica à esquerda do botão de idioma)
        self.btn_settings = Gtk.Button(label="⚙️")
        self.btn_settings.set_can_focus(False)
        self.btn_settings.set_name("btnTopBar")
        self.btn_settings.connect("clicked", self.show_settings_manager)

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
        right_box.pack_start(self.btn_settings, False, False, 0)
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
        self.setup_settings_manager_ui()

        self.master_stack.add_named(main_box, "main_app")
        self.master_stack.add_named(self.proc_manager_box, "proc_manager")
        self.master_stack.add_named(self.lang_manager_box, "lang_manager")
        self.master_stack.add_named(self.settings_manager_box, "settings_manager")

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
        self.lbl_gpu.set_text(f"🎮 GPU\nAuto" if gpu_val == 0 else f"🎮 GPU\n{gpu_val}M")
        self.btn_apply.set_label(self._t("btn_apply"))
        
        self.lbl_vol.set_text(self._t("vol_gen"))
        self.lbl_audio_dev.set_text(self._t("def_audio"))
        
        self.lbl_title_cpu_t.set_text(self._t("t_cpu"))
        self.lbl_title_gpu_t.set_text(self._t("t_gpu"))
        self.lbl_title_watts.set_text(self._t("bat_cons"))
        self.lbl_title_ram.set_text(self._t("ram_mem"))
        self.lbl_title_cpu.set_text(self._t("cpu_usage"))
        self.lbl_title_bat.set_text(self._t("bat_lvl"))
        
        self.set_sys_btn_text(self.btn_prev_ws, self._t("prev_ws"))
        self.set_sys_btn_text(self.btn_next_ws, self._t("next_ws"))
        self.set_sys_btn_text(self.btn_close, self._t("close_app"))
        self.set_sys_btn_text(self.btn_move, self._t("move_mon"))
        self.set_sys_btn_text(self.btn_fs, self._t("fullscreen"))
        self.set_sys_btn_text(self.btn_mic, self._t("mute_mic"))
        self.set_sys_btn_text(self.btn_open_win, self._t("open_wins"))
        self.set_sys_btn_text(self.btn_hide_panel, self._t("hide_panel"))

        self.btn_back_grid.set_label(self._t("back"))
        self.set_sys_btn_text(self.cw_close, self._t("cw_close"))
        self.set_sys_btn_text(self.cw_prev, self._t("cw_prev"))
        self.set_sys_btn_text(self.cw_next, self._t("cw_next"))
        self.set_sys_btn_text(self.cw_move, self._t("cw_move"))
        self.set_sys_btn_text(self.cw_fs, self._t("cw_fs"))
        self.set_sys_btn_text(self.cw_back, self._t("back"))

        self.btn_back_lang.set_label(self._t("back_panel"))
        self.lbl_title_lang.set_text(self._t("lang_title"))
        self.btn_yes_lang.set_label(self._t("btn_start"))
        self.btn_no_lang.set_label(self._t("btn_cancel"))

        # Categorias (barra de filtro, seletor da subpágina de lançamento e configurações)
        self.refresh_category_bar()
        self.refresh_app_cat_button()
        self.refresh_pin_button()
        for code, b in self.cat_choice_buttons.items():
            b.set_label(self.cat_label(code))
        self.lbl_empty_cat.set_text(self._t("no_apps_cat"))

        self.lbl_default_cat.set_text(self._t("default_cat"))
        self.lbl_hidden_hint.set_text(self._t("hidden_hint"))
        self.lbl_no_hidden.set_text(self._t("no_hidden_apps"))
        self.lbl_custom_hint.set_text("%s\n%s/" % (self._t("customapps_hint"), self.custom_apps_dir))
        self.refresh_settings_buttons()
        self.refresh_settings_header()
        self.refresh_hidden_list()

    # Monta o conteúdo dos cards quadrados da página Sistema: ícone grande (emoji extraído
    # da tradução) em cima, legenda pequena embaixo — igual ao padrão da Biblioteca de apps.
    def set_sys_btn_text(self, btn, full_text):
        icon, caption = split_icon_caption(full_text)
        content = btn.get_child()
        if content is None:
            content = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
            content.set_halign(Gtk.Align.CENTER)
            content.set_valign(Gtk.Align.CENTER)

            icon_lbl = Gtk.Label()
            icon_lbl.set_name("sysBtnIcon")

            cap_lbl = Gtk.Label()
            cap_lbl.set_name("sysBtnCaption")
            cap_lbl.set_line_wrap(True)
            cap_lbl.set_justify(Gtk.Justification.CENTER)
            cap_lbl.set_halign(Gtk.Align.CENTER)
            cap_lbl.set_max_width_chars(11)

            content.pack_start(icon_lbl, False, False, 0)
            content.pack_start(cap_lbl, False, False, 0)
            btn.add(content)
            content.show_all()

        icon_lbl, cap_lbl = content.get_children()
        icon_lbl.set_text(icon)
        cap_lbl.set_text(caption)

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

    # --- CONFIGURAÇÕES (SUBPÁGINA DA ENGRENAGEM) ---
    def setup_settings_manager_ui(self):
        self.settings_manager_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        self.settings_manager_box.set_margin_start(20); self.settings_manager_box.set_margin_end(20)
        self.settings_manager_box.set_margin_top(20); self.settings_manager_box.set_margin_bottom(20)

        top_bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL)
        self.btn_back_settings = Gtk.Button()
        self.btn_back_settings.set_name("btnCancel")
        self.btn_back_settings.set_size_request(-1, 55)
        self.btn_back_settings.connect("clicked", self.hide_settings_manager)

        self.lbl_title_settings = Gtk.Label()
        self.lbl_title_settings.set_name("titleLabel")
        self.lbl_title_settings.set_hexpand(True)
        self.lbl_title_settings.set_halign(Gtk.Align.CENTER)

        top_bar.pack_start(self.btn_back_settings, False, False, 0)
        top_bar.pack_start(self.lbl_title_settings, True, True, 0)

        # As configurações são um menu: cada linha abre a sua própria subpágina,
        # para nenhuma lista crescer a ponto de esticar a janela.
        self.settings_stack = Gtk.Stack()
        self.settings_stack.set_transition_type(Gtk.StackTransitionType.CROSSFADE)
        self.settings_stack.set_transition_duration(200)

        self.settings_stack.add_named(self.build_settings_menu(), "menu")
        self.settings_stack.add_named(self.build_default_cat_page(), "default_cat")
        self.settings_stack.add_named(self.build_hidden_apps_page(), "hidden")

        self.settings_manager_box.pack_start(top_bar, False, False, 0)
        self.settings_manager_box.pack_start(self.settings_stack, True, True, 10)

    # Cada página das configurações vive dentro de um scroll, então a altura mínima
    # dela é sempre pequena e a janela nunca passa dos 540px úteis do DP-1.
    def wrap_settings_page(self, body):
        scroll = Gtk.ScrolledWindow()
        scroll.set_policy(Gtk.PolicyType.NEVER, Gtk.PolicyType.AUTOMATIC)
        scroll.set_kinetic_scrolling(True)
        scroll.set_vexpand(True)
        scroll.add(body)
        return scroll

    def build_settings_menu(self):
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=12)
        body.set_valign(Gtk.Align.CENTER); body.set_halign(Gtk.Align.CENTER)

        self.btn_go_default_cat = Gtk.Button()
        self.btn_go_hidden = Gtk.Button()
        for btn, page in ((self.btn_go_default_cat, "default_cat"),
                          (self.btn_go_hidden, "hidden")):
            btn.set_can_focus(False)
            btn.set_name("actionBtn")
            btn.set_size_request(420, 56)
            btn.connect("clicked", self.show_settings_page, page)
            body.pack_start(btn, False, False, 0)

        self.lbl_custom_hint = Gtk.Label()
        self.lbl_custom_hint.set_name("hintLabel")
        self.lbl_custom_hint.set_justify(Gtk.Justification.CENTER)
        self.lbl_custom_hint.set_margin_top(12)
        body.pack_start(self.lbl_custom_hint, False, False, 0)

        return self.wrap_settings_page(body)

    def build_default_cat_page(self):
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_valign(Gtk.Align.CENTER); body.set_halign(Gtk.Align.CENTER)

        self.lbl_default_cat = Gtk.Label()
        self.lbl_default_cat.set_name("sensorText")
        body.pack_start(self.lbl_default_cat, False, False, 0)

        # Uma linha por categoria; a atual fica destacada (mesma cor do botão pressionado).
        # "Ocultos" fica fora: é categoria que some da biblioteca, não filtro de abertura.
        self.default_cat_buttons = {}
        for code in CATEGORY_ORDER:
            btn = Gtk.Button()
            btn.set_can_focus(False)
            btn.set_name("actionBtn")
            btn.set_size_request(380, 48)
            btn.connect("clicked", self.on_default_category_selected, code)
            body.pack_start(btn, False, False, 0)
            self.default_cat_buttons[code] = btn

        return self.wrap_settings_page(body)

    def build_hidden_apps_page(self):
        body = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        body.set_halign(Gtk.Align.CENTER)

        self.lbl_hidden_hint = Gtk.Label()
        self.lbl_hidden_hint.set_name("hintLabel")
        self.lbl_hidden_hint.set_justify(Gtk.Justification.CENTER)
        body.pack_start(self.lbl_hidden_hint, False, False, 0)

        self.lbl_no_hidden = Gtk.Label()
        self.lbl_no_hidden.set_name("emptyCat")
        self.lbl_no_hidden.set_no_show_all(True)   # visibilidade vem do refresh
        self.lbl_no_hidden.set_margin_top(30)
        body.pack_start(self.lbl_no_hidden, False, False, 0)

        self.hidden_list_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        body.pack_start(self.hidden_list_box, False, False, 0)

        return self.wrap_settings_page(body)

    # Lista de ocultos: uma linha por app, e tocar na linha devolve o app à biblioteca.
    def refresh_hidden_list(self):
        if not hasattr(self, "hidden_list_box"):
            return

        for child in self.hidden_list_box.get_children():
            self.hidden_list_box.remove(child)

        apps = self.hidden_apps()
        self.lbl_no_hidden.set_visible(not apps)

        for app in apps:
            row = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=12)
            row.pack_start(self.new_app_icon(app.get("icon"), 32), False, False, 0)

            lbl = Gtk.Label(label=app.get("name", "App"))
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.set_max_width_chars(24)
            lbl.set_xalign(0.0)
            row.pack_start(lbl, True, True, 0)
            row.pack_start(Gtk.Label(label="👁️"), False, False, 0)

            btn = Gtk.Button()
            btn.set_can_focus(False)
            btn.set_name("hiddenRowBtn")
            btn.set_size_request(420, 52)
            btn.add(row)
            btn.connect("clicked", self.on_hidden_app_restored, app)
            self.hidden_list_box.pack_start(btn, False, False, 0)

        self.hidden_list_box.show_all()

    def on_hidden_app_restored(self, btn, app):
        self.play_sound("click")
        self.app_categories.pop(app.get("name"), None)
        app["category"] = None
        self.save_app_categories()
        self.refresh_hidden_list()
        self.populate_flowbox()
        if self.current_selected_app is app:
            self.refresh_app_cat_button()

    def refresh_settings_buttons(self):
        self.btn_go_default_cat.set_label(self._t("settings_default_cat"))
        self.btn_go_hidden.set_label("%s (%d)" % (self._t("settings_hidden"),
                                                  len(self.hidden_apps())))
        for code, btn in self.default_cat_buttons.items():
            btn.set_label(self.cat_label(code))
            ctx = btn.get_style_context()
            if code == self.default_category:
                ctx.add_class("catActive")
            else:
                ctx.remove_class("catActive")

    # Título e botão "voltar" acompanham a subpágina aberta: no menu o voltar sai
    # das configurações, dentro de uma subpágina ele só sobe um nível.
    def refresh_settings_header(self):
        page = self.settings_stack.get_visible_child_name()
        titles = {"default_cat": "settings_default_cat", "hidden": "settings_hidden"}
        self.lbl_title_settings.set_text(self._t(titles.get(page, "settings_title")))
        self.btn_back_settings.set_label(self._t("back_panel" if page == "menu" else "back"))

    def show_settings_page(self, btn, page_name):
        self.play_sound("click")
        if page_name == "hidden":
            self.refresh_hidden_list()
        self.settings_stack.set_visible_child_name(page_name)
        self.refresh_settings_header()

    def show_settings_manager(self, btn):
        self.settings_stack.set_visible_child_name("menu")
        self.refresh_settings_buttons()
        self.refresh_settings_header()
        self.master_stack.set_visible_child_name("settings_manager")

    def hide_settings_manager(self, btn):
        if self.settings_stack.get_visible_child_name() != "menu":
            self.refresh_settings_buttons()
            self.settings_stack.set_visible_child_name("menu")
            self.refresh_settings_header()
            return
        self.master_stack.set_visible_child_name("main_app")

    def on_default_category_selected(self, btn, code):
        self.play_sound("click")
        self.default_category = code
        self.set_default_category(code)
        self.refresh_settings_buttons()
        # Aplica já na biblioteca, sem esperar o próximo arranque do script.
        self.current_category = code
        self.refresh_category_bar()
        self.populate_flowbox()

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
        self.flowbox.set_margin_top(8); self.flowbox.set_margin_bottom(15)

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

        # Grade = barra fina de filtros por categoria + grade de apps.
        grid_box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=0)
        grid_box.pack_start(self.build_category_bar(), False, False, 0)

        self.lbl_empty_cat = Gtk.Label()
        self.lbl_empty_cat.set_name("emptyCat")
        self.lbl_empty_cat.set_no_show_all(True)   # visibilidade controlada no populate
        self.lbl_empty_cat.set_margin_top(60)
        # A grade ja foi populada acima, antes deste label existir: acerta o estado inicial.
        self.lbl_empty_cat.set_visible(not self.apps_in_current_category())
        grid_box.pack_start(self.lbl_empty_cat, False, False, 0)

        grid_box.pack_start(self.scroll_apps, True, True, 0)

        self.page5_stack.add_named(grid_box, "grid")
        self.page5_stack.add_named(self.build_launch_page(), "confirm")

        self.stack.add_named(self.page5_stack, "page5")
        self.refresh_category_bar()

    # Barra de filtros acima da grade: mesmos botões da dock de baixo, porém bem mais finos.
    def build_category_bar(self):
        bar = Gtk.Box(orientation=Gtk.Orientation.HORIZONTAL, spacing=8)
        bar.set_homogeneous(True)
        bar.set_margin_start(20); bar.set_margin_end(20)
        bar.set_margin_top(6)

        self.cat_buttons = {}
        for code in CATEGORY_ORDER:
            btn = Gtk.Button()
            btn.set_can_focus(False)
            btn.set_name("catBtn")
            btn.set_size_request(-1, 34)
            btn.connect("clicked", self.on_category_filter, code)
            bar.pack_start(btn, True, True, 0)
            self.cat_buttons[code] = btn
        return bar

    def refresh_category_bar(self):
        for code, btn in self.cat_buttons.items():
            btn.set_label(self.cat_label(code))
            ctx = btn.get_style_context()
            if code == self.current_category:
                ctx.add_class("catActive")
            else:
                ctx.remove_class("catActive")

    def on_category_filter(self, btn, code):
        if code == self.current_category:
            return
        self.current_category = code
        self.refresh_category_bar()
        self.populate_flowbox()

    # Subpágina de lançamento: o conteúdo continua centralizado, o seletor de categoria
    # flutua no canto superior esquerdo (com a lista descendo logo abaixo dele) e o botão
    # de fixar no canto superior direito.
    def build_launch_page(self):
        self.btn_app_cat = Gtk.Button()
        self.btn_app_cat.set_can_focus(False)
        self.btn_app_cat.set_name("catPickBtn")
        self.btn_app_cat.connect("clicked", self.toggle_cat_dropdown)

        dropdown = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=4)
        dropdown.set_name("catDropdown")

        self.cat_choice_buttons = {}
        for code in ASSIGNABLE_CATEGORIES + ["none"]:
            b = Gtk.Button()
            b.set_can_focus(False)
            b.set_name("catChoiceBtn")
            # 6 opções agora (as 4 categorias + ocultos + limpar): a linha ficou mais
            # baixa para a lista aberta continuar cabendo na altura útil da página.
            b.set_size_request(260, 42)
            b.connect("clicked", self.on_app_category_chosen, code)
            dropdown.pack_start(b, False, False, 0)
            self.cat_choice_buttons[code] = b

        # Revealer em vez de Popover: a janela é layer-shell sem teclado, então um
        # menu flutuante nativo não é confiável aqui.
        self.cat_revealer = Gtk.Revealer()
        self.cat_revealer.set_transition_type(Gtk.RevealerTransitionType.SLIDE_DOWN)
        self.cat_revealer.set_transition_duration(150)
        self.cat_revealer.add(dropdown)

        corner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
        corner.set_halign(Gtk.Align.START); corner.set_valign(Gtk.Align.START)
        corner.set_margin_start(20); corner.set_margin_top(10)
        corner.pack_start(self.btn_app_cat, False, False, 0)
        corner.pack_start(self.cat_revealer, False, False, 0)

        # Fixar: manda o app pro topo da grade em qualquer categoria, à frente até
        # dos mais usados. É um liga/desliga, sem confirmação.
        self.btn_app_pin = Gtk.Button()
        self.btn_app_pin.set_can_focus(False)
        self.btn_app_pin.set_name("catPickBtn")
        self.btn_app_pin.connect("clicked", self.on_pin_toggled)

        pin_corner = Gtk.Box(orientation=Gtk.Orientation.VERTICAL)
        pin_corner.set_halign(Gtk.Align.END); pin_corner.set_valign(Gtk.Align.START)
        pin_corner.set_margin_end(20); pin_corner.set_margin_top(10)
        pin_corner.pack_start(self.btn_app_pin, False, False, 0)

        launch_page = Gtk.Overlay()
        launch_page.add(self.confirm_box)
        launch_page.add_overlay(corner)
        launch_page.add_overlay(pin_corner)
        return launch_page

    def refresh_pin_button(self):
        app = self.current_selected_app or {}
        pinned = bool(app.get("pinned"))
        self.btn_app_pin.set_label(self._t("pin_on") if pinned else self._t("pin_off"))
        ctx = self.btn_app_pin.get_style_context()
        if pinned:
            ctx.add_class("catActive")
        else:
            ctx.remove_class("catActive")

    def on_pin_toggled(self, btn):
        self.play_sound("click")
        app = self.current_selected_app
        if not app:
            return
        name = app.get("name")
        if app.get("pinned"):
            self.pinned_apps.discard(name)
            app["pinned"] = False
        else:
            self.pinned_apps.add(name)
            app["pinned"] = True
        self.save_pinned_apps()
        self.sort_apps()
        self.refresh_pin_button()
        self.populate_flowbox()

    def toggle_cat_dropdown(self, btn):
        self.play_sound("click")
        self.cat_revealer.set_reveal_child(not self.cat_revealer.get_reveal_child())

    def refresh_app_cat_button(self):
        app = self.current_selected_app or {}
        code = app.get("category")
        self.btn_app_cat.set_label("%s: %s" % (self._t("cat_select"), self.cat_label(code)))
        for c, b in self.cat_choice_buttons.items():
            ctx = b.get_style_context()
            if c == code or (c == "none" and not code):
                ctx.add_class("catActive")
            else:
                ctx.remove_class("catActive")

    def on_app_category_chosen(self, btn, code):
        self.play_sound("click")
        app = self.current_selected_app
        if app:
            name = app.get("name")
            if code == "none":
                self.app_categories.pop(name, None)
                app["category"] = None
            else:
                self.app_categories[name] = code
                app["category"] = code
            self.save_app_categories()
            self.refresh_app_cat_button()
            self.populate_flowbox()
            self.refresh_hidden_list()
        self.cat_revealer.set_reveal_child(False)

    def apps_in_current_category(self):
        # Oculto fica de fora de qualquer filtro, "Todos" inclusive.
        visible = [a for a in self.apps_data if a.get("category") != HIDDEN_CATEGORY]
        if self.current_category == "all":
            return visible
        return [a for a in visible if a.get("category") == self.current_category]

    def hidden_apps(self):
        """Apps marcados como ocultos, em ordem alfabetica (lista das configuracoes)."""
        return sorted((a for a in self.apps_data if a.get("category") == HIDDEN_CATEGORY),
                      key=lambda a: a.get("name", "").lower())

    def populate_flowbox(self):
        for child in self.flowbox.get_children():
            self.flowbox.remove(child)

        apps = self.apps_in_current_category()
        if hasattr(self, "lbl_empty_cat"):
            self.lbl_empty_cat.set_visible(not apps)

        for app in apps:
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=8)
            box.set_valign(Gtk.Align.CENTER)
            
            icon = self.new_app_icon(app.get("icon"), 60)

            lbl = Gtk.Label(label=app.get("name", "App"))
            lbl.set_name("appLabel")
            lbl.set_ellipsize(Pango.EllipsizeMode.END)
            lbl.set_max_width_chars(15)
            
            box.pack_start(icon, True, True, 0)
            box.pack_start(lbl, False, False, 0)
            
            child = Gtk.FlowBoxChild()
            child.set_name("appCard")
            if app.get("pinned"):
                child.get_style_context().add_class("pinned")
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
        self.set_app_icon(self.confirm_icon, app.get("icon"), 120)
        self.confirm_label.set_text(app.get("name", "App"))

        self.cat_revealer.set_reveal_child(False)
        self.refresh_app_cat_button()
        self.refresh_pin_button()

        self.page5_stack.set_visible_child_name("confirm")

    def cancel_launch(self, widget):
        self.play_sound("cancel")
        self.cat_revealer.set_reveal_child(False)
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

            self.sort_apps()
            self.cat_revealer.set_reveal_child(False)
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
            box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=20)
            lbl = Gtk.Label()
            lbl.set_justify(Gtk.Justification.CENTER)
            lbl.set_halign(Gtk.Align.CENTER)
            lbl.set_valign(Gtk.Align.CENTER)
            lbl.set_name("sliderText")

            # Tentar limitar a largura via wrap/ellipsize e depois reservar altura pro "pior
            # caso" (3 linhas) se mostrou frágil — o tamanho real de uma linha quebrada varia
            # com a fonte e é difícil de prever com exatidão, então o "pior caso" ainda estourava
            # às vezes (ex: valores de GPU acima de 2000). A solução confiável é garantir, no
            # texto em si (nos métodos onXChange e em update_all_texts), que nenhum valor exiba
            # mais que ~6 caracteres na linha de baixo — assim o label nunca precisa quebrar
            # linha, fica sempre com exatamente 2 linhas e altura constante, e a barra abaixo
            # (que usa o espaço "restante") nunca varia de tamanho.
            lbl.set_size_request(70, 50)

            adj = Gtk.Adjustment(value=curr_val, lower=min_v, upper=max_v, step_increment=step, page_increment=step)
            scale = Gtk.Scale(orientation=Gtk.Orientation.VERTICAL, adjustment=adj)
            scale.set_name("thickSlider") 
            scale.set_inverted(True) 
            scale.set_vexpand(True) 
            scale.set_digits(0)
            scale.set_round_digits(0)
            # O valor numérico nativo do GTK (desenhado sobre a barra) tem largura variável
            # conforme a quantidade de dígitos, o que fazia as 4 barras "dançarem" de tamanho
            # entre si. O label acima (lbl) já mostra o texto e o modo/valor atual, então
            # desligamos o valor nativo por completo.
            scale.set_draw_value(False)

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
        # halign FILL (padrão) faria essa barra esticar para acompanhar a largura da página,
        # que varia conforme o tamanho do título da música em self.lbl_media. CENTER trava
        # a barra no tamanho definido acima, independente do que mais está na tela.
        self.sl_media_pos.set_halign(Gtk.Align.CENTER)

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
        sl_vol.set_size_request(300, -1)  # mesma largura travada da barra de progresso da mídia, para as duas baterem
        sl_vol.set_halign(Gtk.Align.CENTER)  # sem isso, ela esticava até a largura da página (que varia com o título da música)
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

        self.btn_prev_ws = Gtk.Button(); self.btn_prev_ws.set_can_focus(False); self.btn_prev_ws.set_name("sysBtn")
        self.btn_next_ws = Gtk.Button(); self.btn_next_ws.set_can_focus(False); self.btn_next_ws.set_name("sysBtn")
        self.btn_close = Gtk.Button(); self.btn_close.set_can_focus(False); self.btn_close.set_name("sysBtn")
        self.btn_move = Gtk.Button(); self.btn_move.set_can_focus(False); self.btn_move.set_name("sysBtn")
        self.btn_fs = Gtk.Button(); self.btn_fs.set_can_focus(False); self.btn_fs.set_name("sysBtn")
        self.btn_mic = Gtk.Button(); self.btn_mic.set_can_focus(False); self.btn_mic.set_name("sysBtn")
        self.btn_open_win = Gtk.Button(); self.btn_open_win.set_can_focus(False); self.btn_open_win.set_name("sysBtn")
        self.btn_hide_panel = Gtk.Button(); self.btn_hide_panel.set_can_focus(False); self.btn_hide_panel.set_name("sysBtn")

        # Botões quadrados (estilo card de app / sensor): tamanho fixo + centralizado na célula
        btns = [self.btn_prev_ws, self.btn_next_ws, self.btn_close, self.btn_move, self.btn_fs, self.btn_mic, self.btn_open_win, self.btn_hide_panel]
        for b in btns:
            b.set_halign(Gtk.Align.CENTER)
            b.set_valign(Gtk.Align.CENTER)
            b.set_size_request(140, 140)

        # 2 linhas x 4 colunas: cantos superiores = navegação de workspace,
        # meio superior = monitor/fullscreen, linha de baixo = opções restantes
        grid.attach(self.btn_prev_ws, 0, 0, 1, 1)
        grid.attach(self.btn_move, 1, 0, 1, 1)
        grid.attach(self.btn_fs, 2, 0, 1, 1)
        grid.attach(self.btn_next_ws, 3, 0, 1, 1)
        grid.attach(self.btn_close, 0, 1, 1, 1)
        grid.attach(self.btn_mic, 1, 1, 1, 1)
        grid.attach(self.btn_open_win, 2, 1, 1, 1)
        grid.attach(self.btn_hide_panel, 3, 1, 1, 1)
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

        self.cw_close = Gtk.Button(); self.cw_close.set_name("sysBtn")
        self.cw_prev = Gtk.Button(); self.cw_prev.set_name("sysBtn")
        self.cw_next = Gtk.Button(); self.cw_next.set_name("sysBtn")
        self.cw_move = Gtk.Button(); self.cw_move.set_name("sysBtn")
        self.cw_fs = Gtk.Button(); self.cw_fs.set_name("sysBtn")
        self.cw_back = Gtk.Button(); self.cw_back.set_name("sysBtn")

        # Botões quadrados (estilo card de app / sensor): tamanho fixo + centralizado na célula
        for b in [self.cw_close, self.cw_prev, self.cw_next, self.cw_move, self.cw_fs, self.cw_back]:
            b.set_halign(Gtk.Align.CENTER)
            b.set_valign(Gtk.Align.CENTER)
            b.set_size_request(140, 140)

        # 2 linhas x 3 colunas: topo = navegação de janela + monitor,
        # baixo = voltar / fullscreen / fechar
        ctrl_grid.attach(self.cw_prev, 0, 0, 1, 1)
        ctrl_grid.attach(self.cw_move, 1, 0, 1, 1)
        ctrl_grid.attach(self.cw_next, 2, 0, 1, 1)
        ctrl_grid.attach(self.cw_back, 0, 1, 1, 1)
        ctrl_grid.attach(self.cw_fs, 1, 1, 1, 1)
        ctrl_grid.attach(self.cw_close, 2, 1, 1, 1)
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
        lbl.set_text(f"🎮 GPU\nAuto" if val == 0 else f"🎮 GPU\n{val}M")

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

        scale#thickSlider.vertical contents { min-width: 32px; }
        scale#thickSlider.vertical slider { min-height: 34px; min-width: 56px; border-radius: 9px; }

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

        #sysBtn {
            background-color: #1a1a1a;
            border-radius: 16px;
            border: 2px solid #333;
            padding: 8px;
        }
        #sysBtn:hover { background-color: #2a2a2a; border-color: #555; }
        #sysBtn:active { background-color: #444; border-color: #fff; }
        #sysBtnIcon { font-size: 42px; }
        #sysBtnCaption { font-size: 12px; font-weight: bold; }

        #procRow {
            background-color: #1a1a1a;
            border-radius: 10px;
            padding: 10px;
            border: 1px solid #2a2a2a;
        }

        #appLabel { font-size: 14px; font-weight: bold; margin-top: 5px; }

        /* Filtros de categoria: mesma paleta dos cards, só que em botões finos. */
        #catBtn {
            background-color: #1a1a1a;
            border: 1px solid #333333;
            border-radius: 10px;
            padding: 0px 10px;
            min-height: 0px;
            font-size: 13px;
            font-family: 'Public Sans', sans-serif;
        }
        #catBtn:hover { background-color: #2a2a2a; border-color: #555; }
        #catBtn.catActive { background-color: #ffffff; color: #000000; border-color: #ffffff; }

        #catPickBtn {
            background-color: #1a1a1a;
            border: 2px solid #333333;
            border-radius: 14px;
            font-size: 15px;
            padding: 8px 16px;
        }
        #catPickBtn:hover { background-color: #2a2a2a; border-color: #555; }

        #catDropdown {
            background-color: #0a0a0a;
            border: 1px solid #333333;
            border-radius: 14px;
            padding: 8px;
        }
        #catChoiceBtn { background-color: #1a1a1a; border: 1px solid #333333; font-size: 15px; padding: 6px 16px; }
        #catChoiceBtn:hover { background-color: #2a2a2a; border-color: #555; }
        #catChoiceBtn.catActive { background-color: #ffffff; color: #000000; border-color: #ffffff; }

        #actionBtn.catActive { background-color: #ffffff; color: #000000; border-color: #ffffff; }

        /* Fixar (canto superior direito da subpágina de lançamento): usa o mesmo
           corpo do seletor de categoria e acende quando o app está fixado. */
        #catPickBtn.catActive { background-color: #ffffff; color: #000000; border-color: #ffffff; }

        /* Card de app fixado: borda clara para destacar quem furou a fila. */
        flowboxchild#appCard.pinned { border-color: #8a8a8a; }

        /* Linha da lista de apps ocultos. */
        #hiddenRowBtn {
            background-color: #1a1a1a;
            border: 1px solid #333333;
            border-radius: 12px;
            font-size: 15px;
            padding: 4px 14px;
        }
        #hiddenRowBtn:hover { background-color: #2a2a2a; border-color: #555; }

        #emptyCat { font-size: 18px; color: #888888; }
        #hintLabel { font-size: 13px; color: #888888; }

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
