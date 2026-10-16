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
ROOM_LOCKED = re.compile(r"EHL8_ROOM_LOCKED=([01])")
ROOM_RESERVED = re.compile(r"EHL8_ROOM_RESERVED=(\d+)/(\d+)")
ROOM_READY = re.compile(r"EHL8_READY_COUNT=(\d+)/(\d+)")
ROOM_STARTED = re.compile(r"EHL8_ROOM_STARTED=([01])")
LABELS = {0: "CONECTANDO", 1: "NEGOCIANDO", 2: "AUTENTICANDO",
          3: "ENTRANDO NA SALA", 4: "AGUARDANDO SEGUNDO JOGADOR",
          5: "EM JOGO", 6: "ERRO DE CONEXÃO",
          7: "RECONECTANDO (ATÉ 60s)"}


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


def latest_room_lock(log_text):
    found = ROOM_LOCKED.findall(log_text)
    return bool(int(found[-1])) if found else None


def latest_reservations(log_text):
    values = ROOM_RESERVED.findall(log_text)
    if not values:
        return None
    used, capacity = (int(n) for n in values[-1])
    return used if capacity == 2 and 0 <= used <= 2 else None


def latest_ready_count(log_text):
    matches = ROOM_READY.findall(log_text)
    if not matches:
        return None
    ready, slots = (int(v) for v in matches[-1])
    return ready if slots == 2 and 0 <= ready <= slots else None


def latest_room_started(log_text):
    matches = ROOM_STARTED.findall(log_text)
    return bool(int(matches[-1])) if matches else None


def latest_client_state(log_text):
    found = STATE.findall(log_text)
    return LABELS.get(int(found[-1]), "ESTADO DESCONHECIDO") if found else None


def lobby_snapshot(manager):
    players = {"QA_A": "NÃO INICIADO", "QA_B": "NÃO INICIADO"}
    if manager.session is None or manager.mode != "ehl8":
        return {"room": "SEM SESSÃO EHL8", "server": "DESLIGADO",
                "players": players, "live": False, "locked": None, "admin": False,
                "ready": None, "started": None, "host_start": False,
                "reserved": None}
    live = manager.server is not None and manager.server.poll() is None
    logdir = Path(manager.session) / "logs"
    server_log = tail_text(logdir / "servidor.log")
    reported = latest_room(server_log)
    locked = latest_room_lock(server_log) if live else None
    reserved = latest_reservations(server_log) if live else None
    ready = latest_ready_count(server_log) if live else None
    started = latest_room_started(server_log) if live else None
    host_start = bool(live and getattr(manager, "admin_enabled", False)
                      and getattr(manager, "app", None)
                      and (Path(manager.app) / "EHL8_M23_GAME_MATCHED.txt").is_file())
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
            if host_start and ready == 2 and not started and players[profile] == "AGUARDANDO SEGUNDO JOGADOR":
                players[profile] = "PRONTO — AGUARDANDO ANFITRIÃO"
    return {"room": room, "server": "ATIVO (localhost)" if live else "DESLIGADO",
            "players": players, "live": live, "locked": locked,
            "reserved": reserved, "ready": ready, "started": started,
            "host_start": host_start,
            "admin": bool(live and getattr(manager, "admin_enabled", False))}


def show_lobby(parent, manager, bg="#091611", panel="#142c23",
               green="#54daa7", fg="#e6fff2", muted="#a5bfb0"):
    import tkinter as tk
    from tkinter import messagebox

    win = tk.Toplevel(parent)
    win.title("Emerald Hybrid — Lobby EHL8 ao vivo")
    win.geometry("680x690")
    win.minsize(600, 530)
    win.configure(bg=bg)
    win.transient(parent)
    tk.Label(win, text="LOBBY EHL8 — MONITOR AO VIVO", bg=bg, fg=green,
             font=("Segoe UI", 17, "bold")).pack(anchor="w", padx=24, pady=(20, 4))
    tk.Label(win, text="Status dos logs reais da sessão local.",
             bg=bg, fg=muted, font=("Segoe UI", 10)).pack(anchor="w", padx=24)
    variables = [(name, tk.StringVar(value="AGUARDANDO")) for name in
                 ("SALA (2 slots)", "SERVIDOR", "PRONTOS", "PARTIDA INICIADA", "VAGAS RESERVADAS", "JOGADOR QA_A", "JOGADOR QA_B", "ENTRADAS NOVAS")]
    for name, var in variables:
        area = tk.Frame(win, bg=panel, padx=12, pady=8)
        area.pack(fill="x", padx=24, pady=(9, 0))
        tk.Label(area, text=name, bg=panel, fg=muted).pack(side="left")
        tk.Label(area, textvariable=var, bg=panel, fg=green,
                 font=("Segoe UI", 11, "bold")).pack(side="right")

    buttons_admin = []
    buttons_drop = []
    lock_button = [None]
    start_button = [None]

    def refresh():
        state = lobby_snapshot(manager)
        lock_label = ("BLOQUEADAS" if state["locked"] else "PERMITIDAS"
                      if state["locked"] is not None else "NÃO DISPONÍVEL")
        reservation_label = (str(state["reserved"]) + "/2" if state["reserved"] is not None
                             else "NÃO DISPONÍVEL")
        ready_label = (str(state["ready"]) + "/2" if state["ready"] is not None
                       else "NÃO DISPONÍVEL")
        started_label = ("SIM" if state["started"] else "NÃO"
                         if state["started"] is not None else "NÃO DISPONÍVEL")
        values = (state["room"], state["server"], ready_label, started_label,
                  reservation_label, state["players"]["QA_A"],
                  state["players"]["QA_B"], lock_label)
        for (_, var), value in zip(variables, values):
            var.set(value)
        for btn in buttons_admin:
            btn.configure(state="normal" if state["admin"] else "disabled")
        resume_qa = bool(state["admin"] and getattr(manager, "app", None) and
                         (Path(manager.app) / "EHL8_M22B_GAME_MATCHED.txt").is_file())
        for btn in buttons_drop:
            btn.configure(state="normal" if resume_qa else "disabled")
        if lock_button[0] is not None:
            lock_button[0].configure(text="PERMITIR ENTRADAS" if state["locked"]
                                     else "BLOQUEAR ENTRADAS")
        if start_button[0] is not None:
            can_start = bool(state["host_start"] and state["ready"] == 2
                             and state["room"] == "2/2" and not state["started"])
            start_button[0].configure(
                state="normal" if can_start else "disabled")

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
    def admin(action, profile=None):
        target = "a conta " + profile if profile else "as entradas na sala"
        if not messagebox.askyesno("Confirmar administração",
                "Alterar " + target + "?", parent=win):
            return
        try:
            manager.admin_command(action, profile)
        except (OSError, ValueError, RuntimeError) as exc:
            messagebox.showerror("Falha ao administrar", str(exc), parent=win)

    extra = tk.Frame(win, bg=bg)
    extra.pack(anchor="w", padx=24, pady=(12, 0))
    for profile in ("QA_A", "QA_B"):
        button = tk.Button(extra, text="REMOVER " + profile,
                           command=lambda profile=profile: admin("kick", profile),
                           bg=panel, fg=fg, relief="flat", padx=10, pady=8)
        button.pack(side="left", padx=(0, 9))
        buttons_admin.append(button)
    lock_button[0] = tk.Button(extra, text="BLOQUEAR ENTRADAS",
        command=lambda: admin("unlock" if lobby_snapshot(manager)["locked"] else "lock"),
        bg=panel, fg=fg, relief="flat", padx=10, pady=8)
    lock_button[0].pack(side="left")
    buttons_admin.append(lock_button[0])
    start_area = tk.Frame(win, bg=bg)
    start_area.pack(anchor="w", padx=24, pady=(10, 0))
    start_button[0] = tk.Button(
        start_area, text="INICIAR SALA (2/2 PRONTOS)",
        command=lambda: admin("start"), bg="#236448", fg=fg,
        relief="flat", padx=14, pady=10)
    start_button[0].pack(side="left")
    reconnection = tk.Frame(win, bg=bg)
    reconnection.pack(anchor="w", padx=24, pady=(10, 0))
    for profile in ("QA_A", "QA_B"):
        button = tk.Button(reconnection, text="SIMULAR QUEDA " + profile,
                           command=lambda profile=profile: admin("drop", profile),
                           bg=panel, fg=fg, relief="flat", padx=10, pady=8)
        button.pack(side="left", padx=(0, 9))
        buttons_drop.append(button)
    tk.Label(win, text="Comandos do lobby usam apenas o stdin privado do servidor.\n"
             "SIMULAR QUEDA afeta só a rede. READY é automático; no M2.3, START é manual.",
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
