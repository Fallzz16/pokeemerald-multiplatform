"""M2.1-A: read-only EHL8 live lobby monitor for the isolated QA laboratory.

EHL8 READY/START are currently automatic; this panel never invents manual
controls. Only local bounded log tails are inspected. No saves are accessed.
"""
from pathlib import Path
import os
import re
import sys

ROOM = re.compile(r"EHL8_ROOM_COUNT=(\d+)/(\d+)")
STATE = re.compile(r"\[EHL8\] session state=(\d+)")
LABELS = {0: "CONECTANDO", 1: "NEGOCIANDO", 2: "AUTENTICANDO",
          3: "ENTRANDO NA SALA", 4: "AGUARDANDO SEGUNDO JOGADOR",
          5: "EM JOGO", 6: "ERRO DE CONEXÃO"}


def tail_text(path, limit=8192):
    path = Path(path)
    try:
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            return ""
        with path.open("rb") as stream:
            stream.seek(0, 2)
            stream.seek(max(0, stream.tell() - limit))
            return stream.read(limit).decode("utf-8", errors="replace")
    except (OSError, ValueError):
        return ""


def latest_room(log_text):
    found = ROOM.findall(log_text)
    if not found:
        return None
    used, slots = (int(x) for x in found[-1])
    return (used, slots) if slots == 2 and 0 <= used <= slots else None


def latest_client_state(log_text):
    found = STATE.findall(log_text)
    return LABELS.get(int(found[-1]), "ESTADO DESCONHECIDO") if found else None


def lobby_snapshot(manager):
    players = {"QA_A": "NÃO INICIADO", "QA_B": "NÃO INICIADO"}
    if manager.session is None or manager.mode != "ehl8":
        return {"room": "SEM SESSÃO EHL8", "server": "DESLIGADO",
                "players": players, "live": False}
    live = manager.server is not None and manager.server.poll() is None
    logdir = Path(manager.session) / "logs"
    reported = latest_room(tail_text(logdir / "servidor.log"))
    room = (f"{reported[0]}/{reported[1]}" if live and reported else
            "AGUARDANDO DADOS" if live else "ENCERRADA")
    for i, profile in enumerate(("QA_A", "QA_B")):
        if i >= len(manager.games):
            continue
        if manager.games[i].poll() is not None:
            players[profile] = "FECHADO"
        elif not live:
            players[profile] = "SEM SERVIDOR"
        else:
            players[profile] = latest_client_state(
                tail_text(logdir / (profile + "-rede.log"))) or "INICIANDO"
    return {"room": room, "server": "ATIVO (localhost)" if live else "DESLIGADO",
            "players": players, "live": live}


def show_lobby(parent, manager, bg="#091611", panel="#142c23",
               green="#54daa7", fg="#e6fff2", muted="#a5bfb0"):
    import tkinter as tk
    from tkinter import messagebox

    win = tk.Toplevel(parent)
    win.title("Emerald Hybrid — Lobby EHL8 ao vivo")
    win.geometry("570x440")
    win.minsize(510, 390)
    win.configure(bg=bg)
    win.transient(parent)
    tk.Label(win, text="LOBBY EHL8 — MONITOR AO VIVO", bg=bg, fg=green,
             font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=24, pady=(20, 4))
    tk.Label(win, text="Status dos logs reais da sessão local.",
             bg=bg, fg=muted, font=("Segoe UI", 10)).pack(anchor="w", padx=24)
    variables = [(name, tk.StringVar(value="AGUARDANDO")) for name in
                 ("SALA (2 slots)", "SERVIDOR", "JOGADOR QA_A", "JOGADOR QA_B")]
    for name, var in variables:
        area = tk.Frame(win, bg=panel, padx=12, pady=8)
        area.pack(fill="x", padx=24, pady=(9, 0))
        tk.Label(area, text=name, bg=panel, fg=muted).pack(side="left")
        tk.Label(area, textvariable=var, bg=panel, fg=green,
                 font=("Segoe UI", 11, "bold")).pack(side="right")

    def refresh():
        state = lobby_snapshot(manager)
        values = (state["room"], state["server"],
                  state["players"]["QA_A"], state["players"]["QA_B"])
        for (_, var), value in zip(variables, values):
            var.set(value)

    def open_logs():
        folder = Path(manager.session) / "logs" if manager.session else None
        if not folder or not folder.is_dir():
            messagebox.showinfo("Sem logs", "Abra uma sessão EHL8 primeiro.", parent=win)
        elif sys.platform == "win32":
            os.startfile(folder)
        else:
            messagebox.showinfo("Pasta de logs", str(folder), parent=win)

    def stop_server():
        server = manager.server
        if manager.mode != "ehl8" or server is None or server.poll() is not None:
            messagebox.showinfo("Sala encerrada", "Nenhum servidor local ativo.", parent=win)
        elif messagebox.askyesno("Encerrar sala", "Desligar SOMENTE o servidor local?\n"
                                 "Os jogos permanecem abertos, mas perdem a rede.",
                                 parent=win):
            server.terminate()
            refresh()

    controls = tk.Frame(win, bg=bg)
    controls.pack(anchor="w", padx=24, pady=(14, 0))
    for title, func in (("Atualizar", refresh), ("Abrir logs", open_logs),
                        ("ENCERRAR SALA", stop_server)):
        tk.Button(controls, text=title, command=func, bg=panel, fg=fg,
                  relief="flat", padx=10, pady=8).pack(side="left", padx=(0, 9))
    tk.Label(win, text="READY/START são automáticos nesta versão.\n"
             "Controles manuais e reconexão segura serão desenvolvidos depois.",
             bg=bg, fg=muted, justify="left").pack(anchor="w", padx=24, pady=(15, 0))

    scheduled = [None]
    def tick():
        try:
            if win.winfo_exists():
                refresh()
                scheduled[0] = win.after(800, tick)
        except tk.TclError:
            pass
    def close():
        if scheduled[0] is not None:
            win.after_cancel(scheduled[0])
        win.destroy()
    win.protocol("WM_DELETE_WINDOW", close)
    tick()
    return win
