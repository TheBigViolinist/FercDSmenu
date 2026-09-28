#!/usr/bin/env python3
"""Liga o FercDS no hyprland.lua (usado pelo "./install.sh setup").

uso:
  hypr_setup.py plan  ARQUIVO   imprime no stdout o hyprland.lua com o FercDS
                                ligado e, no stderr, uma linha por mudança
  hypr_setup.py check ARQUIVO   sai com 0 se já está tudo no lugar e 1 se não
                                (as pendências vão para o stderr)

Onde cada módulo precisa ficar:
  * fercdshypr.outputsfercds antes de qualquer outra configuração de monitor
    (hl.monitor ou require de outro arquivo). O hl.monitor do Hyprland mescla
    chamadas para o mesmo output e a última vence, então o que vier depois
    (DMS ou outra shell) tem prioridade e o FercDS vira só o padrão.
  * fercdshypr.bindsfercds e fercdshypr.fercds nas últimas linhas, depois de
    tudo, para os atalhos do FercDS passarem por cima dos da shell.

O require do Lua só executa um módulo na primeira vez: uma cópia do require
fora do lugar certo impediria a do lugar certo de rodar. Por isso as cópias
fora do lugar são comentadas (nunca apagadas), com o prefixo abaixo.

As mensagens e os comentários que o setup põe no arquivo seguem o idioma do
instalador (variável FERCDS_LANG: en, pt, es ou it).
"""
import os
import re
import sys

HEAD = "fercdshypr.outputsfercds"
TAIL = ("fercdshypr.bindsfercds", "fercdshypr.fercds")

TEXTS = {
    "en": {
        "head_note": "-- FercDS: default monitors; any monitor setting after this line takes priority",
        "tail_note": "-- FercDS: keep these lines at the end of the file (./install.sh setup)",
        "disabled": "line %d: %s commented out (%s)",
        "repeated": "repeated",
        "must_tail": "must be at the end of the file",
        "must_head": "must come before the other monitors",
        "added_tail": 'require("%s") added at the end of the file',
        "added_head": 'require("%s") added before the monitor settings',
    },
    "pt": {
        "head_note": "-- FercDS: monitores padrão; qualquer configuração de monitor depois daqui tem prioridade",
        "tail_note": "-- FercDS: deixe estas linhas no fim do arquivo (./install.sh setup)",
        "disabled": "linha %d: %s comentado (%s)",
        "repeated": "repetido",
        "must_tail": "precisa ficar no fim do arquivo",
        "must_head": "precisa vir antes dos outros monitores",
        "added_tail": 'require("%s") adicionado no fim do arquivo',
        "added_head": 'require("%s") adicionado antes das configurações de monitor',
    },
    "es": {
        "head_note": "-- FercDS: monitores por defecto; cualquier ajuste de monitor después de aquí tiene prioridad",
        "tail_note": "-- FercDS: deja estas líneas al final del archivo (./install.sh setup)",
        "disabled": "línea %d: %s comentado (%s)",
        "repeated": "repetido",
        "must_tail": "tiene que ir al final del archivo",
        "must_head": "tiene que ir antes de los demás monitores",
        "added_tail": 'require("%s") añadido al final del archivo',
        "added_head": 'require("%s") añadido antes de los ajustes de monitor',
    },
    "it": {
        "head_note": "-- FercDS: monitor predefiniti; qualsiasi impostazione dei monitor dopo questa riga ha la precedenza",
        "tail_note": "-- FercDS: lascia queste righe alla fine del file (./install.sh setup)",
        "disabled": "riga %d: %s commentato (%s)",
        "repeated": "ripetuto",
        "must_tail": "deve stare alla fine del file",
        "must_head": "deve venire prima degli altri monitor",
        "added_tail": 'require("%s") aggiunto alla fine del file',
        "added_head": 'require("%s") aggiunto prima delle impostazioni dei monitor',
    },
}
T = TEXTS.get(os.environ.get("FERCDS_LANG", "en"), TEXTS["en"])

HEAD_NOTE = T["head_note"]
TAIL_NOTE = T["tail_note"]
DISABLED = "-- [FercDS setup] "

# Só linhas que são apenas o require (com comentário no fim, no máximo).
REQUIRE_RE = re.compile(r"""^\s*require\s*\(?\s*(["'])([\w.\-/]+)\1\s*\)?\s*;?\s*(--.*)?$""")
MONITOR_RE = re.compile(r"^\s*hl\.monitor\s*\(")


def module_of(line):
    m = REQUIRE_RE.match(line)
    return m.group(2) if m else None


def is_code(line):
    s = line.strip()
    return bool(s) and not s.startswith("--")


def disable(lines, i, changes, why):
    changes.append(T["disabled"] % (i + 1, lines[i].strip(), why))
    lines[i] = DISABLED + lines[i].strip()


def plan(lines):
    out = list(lines)
    changes = []

    # --- fim do arquivo: bindsfercds e fercds depois de todo o resto ---
    tail_start = len(out)
    while tail_start > 0:
        line = out[tail_start - 1]
        if is_code(line) and module_of(line) not in TAIL:
            break
        tail_start -= 1

    in_tail = set()
    for i in range(tail_start, len(out)):
        mod = module_of(out[i])
        if mod in TAIL:
            if mod in in_tail:
                disable(out, i, changes, T["repeated"])
            else:
                in_tail.add(mod)
    for i in range(tail_start):
        if module_of(out[i]) in TAIL:
            disable(out, i, changes, T["must_tail"])

    missing = [m for m in TAIL if m not in in_tail]
    if missing:
        while out and not out[-1].strip():
            out.pop()
        block = [] if in_tail else ["", TAIL_NOTE]
        for mod in missing:
            block.append('require("%s")' % mod)
            changes.append(T["added_tail"] % mod)
        out.extend(block)

    # --- começo: outputsfercds antes de qualquer configuração de monitor ---
    anchor = None
    for i, line in enumerate(out):
        mod = module_of(line)
        if MONITOR_RE.match(line) or (mod and mod != HEAD and mod not in TAIL):
            anchor = i
            break

    head_lines = [i for i, line in enumerate(out) if module_of(line) == HEAD]
    in_place = [i for i in head_lines if anchor is None or i < anchor]
    keep = in_place[0] if in_place else None
    for i in head_lines:
        if i != keep:
            why = T["repeated"] if keep is not None else T["must_head"]
            disable(out, i, changes, why)

    if keep is None:
        first_code = next((i for i, line in enumerate(out) if is_code(line)), len(out))
        out[first_code:first_code] = [HEAD_NOTE, 'require("%s")' % HEAD, ""]
        changes.append(T["added_head"] % HEAD)

    return out, changes


def main():
    if len(sys.argv) != 3 or sys.argv[1] not in ("plan", "check"):
        print(__doc__.strip().split("\n\n")[1], file=sys.stderr)
        return 2
    mode, path = sys.argv[1], sys.argv[2]
    with open(path, encoding="utf-8") as f:
        lines = f.read().splitlines()

    out, changes = plan(lines)
    for c in changes:
        print(c, file=sys.stderr)

    if mode == "check":
        return 1 if changes else 0
    sys.stdout.write("\n".join(out) + "\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
