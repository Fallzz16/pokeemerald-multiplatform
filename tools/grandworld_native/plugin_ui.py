#!/usr/bin/env python3
"""Grand World Native - graphical resource-pack manager (Python standard library).

This is a separate developer/user tool, not a replacement for the World engine.
Cosmetic choices live outside player saves. Packs are strictly data-only.
"""
import argparse
import os
from pathlib import Path
import subprocess
import sys
try:
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk
except ImportError:  # Backend and CI remain usable without a desktop toolkit.
    tk = None
    filedialog = messagebox = ttk = None

try:
    from .pack_manager import install, toggle, list_packs, safe_index
    from .asset_catalog import generate_catalog
    from .modpacks import PackError
except ImportError:
    from pack_manager import install, toggle, list_packs, safe_index
    from asset_catalog import generate_catalog
    from modpacks import PackError

STYLE_KEYS = {
    "menus": ("menus", "menus/background"),
    "sprites": ("sprites", "sprites/follower")
}
CLASSIC = "classic"


def available_styles(root, kind):
    """Resolve installed AND enabled packs with matching logical assets."""
    if kind not in STYLE_KEYS:
        raise ValueError("unknown style category")
    root = Path(root)
    index = safe_index(root)
    result = [CLASSIC]
    for pack in list_packs(root):
        pack_id = pack["id"]
        if pack_id not in index["enabled"]:
            continue
        try:
            import json
            data = json.loads((root / pack_id / "manifest.json").read_text(encoding="utf-8"))
        except (OSError, ValueError):
            continue
        if not isinstance(data, dict) or not isinstance(data.get("assets"), list):
            continue
        category, logical = STYLE_KEYS[kind]
        if any(isinstance(a, dict) and a.get("id") == logical
               and isinstance(a.get("path"), str)
               and a["path"].startswith("assets/" + category + "/")
               for a in data["assets"]):
            result.append(pack_id)
    return result


def read_selection(root):
    options = {"menus": CLASSIC, "sprites": CLASSIC}
    file = Path(root) / "style-settings.ini"
    if not file.exists():
        return options
    lines = file.read_text(encoding="utf-8").splitlines()
    if not lines or lines[0] != "GW_STYLE_V1":
        raise PackError("Invalid style-settings.ini")
    for line in lines[1:]:
        name, separator, value = line.partition("=")
        if separator and name in options and value:
            if value in available_styles(root, name):
                options[name] = value
    return options


def write_selection(root, menus, sprites):
    root = Path(root)
    root.mkdir(parents=True, exist_ok=True)
    if menus not in available_styles(root, "menus") or sprites not in available_styles(root, "sprites"):
        raise PackError("Style is missing or pack is disabled")
    target = root / "style-settings.ini"
    tmp = root / ".style-settings.tmp"
    try:
        with tmp.open("w", encoding="utf-8", newline="\n") as output:
            output.write(f"GW_STYLE_V1\nmenus={menus}\nsprites={sprites}\n")
        os.replace(tmp, target)
    finally:
        tmp.unlink(missing_ok=True)
    return {"menus": menus, "sprites": sprites}


class PluginManagerWindow:
    def __init__(self, root, mods_path, executable=None):
        self.root = root
        self.mods_path = Path(mods_path).resolve()
        self.executable = Path(executable).resolve() if executable else None
        root.title("Grand World Native - Gerenciador de Recursos")
        root.geometry("670x500")
        root.minsize(620, 430)

        main = ttk.Frame(root, padding=16)
        main.pack(fill="both", expand=True)
        ttk.Label(main, text="GRAND WORLD NATIVE", font=("Segoe UI", 16, "bold")).pack(anchor="w")
        ttk.Label(main, text="Gerencie sprites, menus e pacotes de recursos sem editar saves.").pack(anchor="w", pady=(0, 12))

        holder = ttk.LabelFrame(main, text="Pacotes instalados", padding=8)
        holder.pack(fill="both", expand=True)
        self.pack_list = tk.Listbox(holder, height=9, exportselection=False)
        self.pack_list.pack(side="left", fill="both", expand=True)
        scrollbar = ttk.Scrollbar(holder, orient="vertical", command=self.pack_list.yview)
        scrollbar.pack(side="right", fill="y")
        self.pack_list.configure(yscrollcommand=scrollbar.set)
        self.ids = []

        buttons = ttk.Frame(main)
        buttons.pack(fill="x", pady=8)
        ttk.Button(buttons, text="Instalar ZIP", command=self.install_pack).pack(side="left", padx=(0, 5))
        ttk.Button(buttons, text="Ativar", command=lambda: self.set_active(True)).pack(side="left", padx=(0, 5))
        ttk.Button(buttons, text="Desativar", command=lambda: self.set_active(False)).pack(side="left", padx=(0, 5))
        ttk.Button(buttons, text="Atualizar", command=self.refresh).pack(side="left")

        styleframe = ttk.LabelFrame(main, text="Configuracoes visuais", padding=10)
        styleframe.pack(fill="x", pady=(5, 8))
        self.menu_value = tk.StringVar(value=CLASSIC)
        self.sprite_value = tk.StringVar(value=CLASSIC)
        ttk.Label(styleframe, text="Menu:").grid(row=0, column=0, sticky="w", pady=4)
        self.menu_combo = ttk.Combobox(styleframe, textvariable=self.menu_value, state="readonly", width=32)
        self.menu_combo.grid(row=0, column=1, sticky="w", padx=10)
        ttk.Label(styleframe, text="Seguidor:").grid(row=1, column=0, sticky="w", pady=4)
        self.sprite_combo = ttk.Combobox(styleframe, textvariable=self.sprite_value, state="readonly", width=32)
        self.sprite_combo.grid(row=1, column=1, sticky="w", padx=10)
        ttk.Button(styleframe, text="Salvar estilos", command=self.save_styles).grid(row=0, column=2, rowspan=2, padx=12)

        foot = ttk.Frame(main)
        foot.pack(fill="x")
        ttk.Label(foot, text="Após instalar: pressione F5 no Style Lab. F1 abre as opções visuais.").pack(anchor="w")
        if self.executable and self.executable.is_file():
            ttk.Button(foot, text="Abrir Style Lab", command=self.open_lab).pack(anchor="w", pady=(8, 0))
        self.status = tk.StringVar(value="Pronto.")
        ttk.Label(main, textvariable=self.status, foreground="#366975").pack(anchor="w", pady=(8, 0))
        self.refresh()

    def selected_id(self):
        selection = self.pack_list.curselection()
        return self.ids[selection[0]] if selection else None

    def run_action(self, action):
        try:
            action()
        except (OSError, ValueError, PackError, RuntimeError) as exc:
            self.status.set("Erro: " + str(exc))
            messagebox.showerror("Nao foi possivel concluir", str(exc), parent=self.root)

    def refresh(self):
        def action():
            self.ids = []
            self.pack_list.delete(0, tk.END)
            packs = list_packs(self.mods_path)
            for p in packs:
                self.ids.append(p["id"])
                self.pack_list.insert(tk.END, ("[ATIVO] " if p["enabled"] else "[DESLIGADO] ") +
                                      p["id"] + "   v" + str(p["version"]))
            opts = read_selection(self.mods_path)
            self.menu_combo["values"] = available_styles(self.mods_path, "menus")
            self.sprite_combo["values"] = available_styles(self.mods_path, "sprites")
            self.menu_value.set(opts["menus"])
            self.sprite_value.set(opts["sprites"])
            self.status.set(f"{len(packs)} pacotes instalados. Mods em: {self.mods_path}")
        self.run_action(action)

    def install_pack(self):
        chosen = filedialog.askopenfilename(parent=self.root, title="Selecione o pacote ZIP",
                                             filetypes=[("Pacotes ZIP", "*.zip")])
        if not chosen:
            return
        def action():
            info = install(chosen, self.mods_path)
            toggle(self.mods_path, info["id"], True)
            self.refresh()
            self.status.set("Instalado e ativado: " + info["id"])
        self.run_action(action)

    def set_active(self, active):
        pack_id = self.selected_id()
        if not pack_id:
            messagebox.showinfo("Escolha um pacote", "Selecione um pacote na lista.", parent=self.root)
            return
        def action():
            toggle(self.mods_path, pack_id, active)
            self.refresh()
            self.status.set(("Ativado: " if active else "Desativado: ") + pack_id)
        self.run_action(action)

    def save_styles(self):
        def action():
            write_selection(self.mods_path, self.menu_value.get(), self.sprite_value.get())
            self.status.set("Estilos salvos. Pressione F5 no Style Lab para aplicar.")
        self.run_action(action)

    def open_lab(self):
        try:
            subprocess.Popen([str(self.executable), "--mods", str(self.mods_path)],
                             cwd=str(self.executable.parent), shell=False)
        except OSError as exc:
            self.run_action(lambda: (_ for _ in ()).throw(exc))


def main():
    p = argparse.ArgumentParser(description=__doc__)
    installed_exe = Path(sys.executable).parent if getattr(sys, "frozen", False) else Path(".")
    p.add_argument("--mods", default=str(installed_exe / "mods"))
    p.add_argument("--lab", default=str(installed_exe / ("gw_theme_lab.exe" if sys.platform == "win32" else "gw_theme_lab")))
    args = p.parse_args()
    if tk is None:
        p.exit(1, "Tkinter indisponivel; instale o suporte Tk ou use pack_manager.py.\n")
    window = tk.Tk()
    executable = Path(args.lab)
    PluginManagerWindow(window, args.mods, executable if executable.is_file() else None)
    window.mainloop()


if __name__ == "__main__":
    main()
