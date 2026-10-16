"""Emerald Hybrid v1.0 M1: isolated two-instance Windows QA laboratory.

Only starts an existing, unchanged game executable, profilectl and optional EHL8
server. No .sav parsing, save byte editing, network-wide listener or cloud access.
This is a QA tool, not evidence that two in-game avatars render correctly.
"""
from __future__ import annotations

import hashlib
import json
import os
from pathlib import Path
import re
import secrets
import shutil
import socket
import subprocess
import sys
import time
from datetime import datetime

PROFILE_IDS = ("QA_A", "QA_B")
MARKER = "qa-session.json"
GREEN = "#54daa7"
BG = "#091611"
PANEL = "#142c23"
FG = "#e6fff2"
MUTED = "#a5bfb0"


def application_dir():
    return (Path(sys.executable).resolve().parent if getattr(sys, "frozen", False)
            else Path(__file__).resolve().parent.parent)


def lab_root():
    return Path(os.environ.get("LOCALAPPDATA", str(Path.home()))) / "EmeraldHybridV1QALab"


def validate_port(value):
    try:
        number = int(str(value).strip())
    except (TypeError, ValueError):
        raise ValueError("Porta inválida: informe um número de 1 a 65534.") from None
    if not 1 <= number <= 65534:
        raise ValueError("Porta inválida: informe um número de 1 a 65534.")
    return number


def validate_pin(value):
    if not re.fullmatch(r"[0-9]{6}", value or ""):
        raise ValueError("O PIN deve conter exatamente 6 dígitos.")
    return value


def check_files(app, mode):
    required = ["pokeemerald.exe", "emerald_profilectl.exe", "SDL2.dll"]
    if mode == "ehl8":
        required.append("EmeraldSessionServer.exe")
    if mode not in ("ehl8", "offline"):
        raise ValueError("Modo desconhecido.")
    missing = [name for name in required if not (app / name).is_file()]
    if missing:
        raise FileNotFoundError("Arquivos ausentes ao lado do Laboratório: " + ", ".join(missing))


def game_command(app, profiles, profile_id, mode, port):
    if profile_id not in PROFILE_IDS:
        raise ValueError("Perfil de teste não permitido.")
    argv = [str(app / "pokeemerald.exe"), "--profile-root=" + str(profiles),
            "--profile-id=" + profile_id]
    if mode == "ehl8":
        argv += ["--session-client=127.0.0.1:" + str(validate_port(port)),
                 "--session-pin-stdin"]
    elif mode != "offline":
        raise ValueError("Modo de sessão inválido.")
    return argv


def server_command(app, port, admin=False):
    """M2.1 admin server is an optional separate EXE; never replace legacy."""
    app = Path(app)
    advanced = app / "EmeraldSessionServerM21.exe"
    binary = advanced if advanced.is_file() else app / "EmeraldSessionServer.exe"
    command = [str(binary), "--bind", "127.0.0.1",
               "--port", str(validate_port(port)), "--slots", "2",
               "--idle-minutes", "15", "--pin-stdin"]
    if admin and binary == advanced:
        command.append("--admin-stdin")
    return command


def file_digest(path):
    h = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def no_window_flags():
    return getattr(subprocess, "CREATE_NO_WINDOW", 0) if sys.platform == "win32" else 0


def prepare_session(app, root, sources=(None, None), mode="ehl8"):
    """Create brand-new QA profiles through the existing native profile manager.

    The source saves are read-only inputs to `profilectl import`; never imported
    in place, and never copied by this tool to a production profile directory.
    """
    app, root = Path(app).resolve(), Path(root).resolve()
    check_files(app, mode)
    if len(sources) != 2:
        raise ValueError("Informe exatamente duas origens de save (ou deixe vazias).")
    inputs = tuple(Path(s).resolve(strict=True) if s else None for s in sources)
    for src in inputs:
        if src is not None and not src.is_file():
            raise ValueError("O caminho do save deve apontar para um arquivo.")
    (root / "sessions").mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)
    session = root / "sessions" / run_id
    session.mkdir(mode=0o700)  # no exist_ok, avoid reusing a stale directory
    profiles = session / "profiles"
    profiles.mkdir()
    logs = session / "logs"
    logs.mkdir()
    # Put the marker only in a directory this tool just created. Cleanup
    # verifies this marker AND the containment path before deleting anything.
    data = {"schema": 1, "tool": "EmeraldHybridV1QALab", "mode": mode,
            "created": datetime.now().isoformat(timespec="seconds"),
            "profiles": list(PROFILE_IDS), "source_sha256": [None, None]}
    (session / MARKER).write_text(json.dumps(data, indent=2), encoding="utf-8")
    for idx, profile_id in enumerate(PROFILE_IDS):
        src = inputs[idx]
        command = [str(app / "emerald_profilectl.exe"),
                   "import" if src else "new", str(profiles), profile_id]
        if src:
            # A SHA is recorded only to prove the source was not modified.
            before = file_digest(src)
            command.append(str(src))
        result = subprocess.run(command, cwd=str(app), capture_output=True,
                                text=True, timeout=45, creationflags=no_window_flags())
        if result.returncode:
            raise RuntimeError("Não foi possível criar " + profile_id + ": " +
                               (result.stderr or result.stdout or "erro no profilectl")[:350])
        target = profiles / profile_id / "pokeemerald.sav"
        if not target.is_file():
            raise RuntimeError("O gerenciador não criou o save de " + profile_id)
        if src:
            if before != file_digest(src) or before != file_digest(target):
                raise RuntimeError("Cópia de save falhou na verificação de integridade.")
            data["source_sha256"][idx] = before
            (session / MARKER).write_text(json.dumps(data, indent=2), encoding="utf-8")
    return session


def is_redirected(path):
    """Cover symlinks and Windows directory junctions before touching a QA save."""
    return path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction())


def existing_session(root, session, profile_id=None):
    """Validate a previously created lab session, without touching save bytes.

    Never accept a bare arbitrary directory, a bots session, a symbolic link,
    or a redirected profile/save. These checks are also used by the GUI list.
    The native profile lock remains authoritative for simultaneous game launches.
    """
    base = Path(root).resolve() / "sessions"
    candidate = Path(session)
    if is_redirected(base) or not base.is_dir() or is_redirected(candidate):
        raise ValueError("Diretório da sessão de QA inválido ou redirecionado.")
    if not candidate.name.startswith("20") or candidate.parent.resolve() != base.resolve():
        raise ValueError("A sessão precisa estar dentro da pasta de testes do laboratório.")
    if not candidate.is_dir() or candidate.resolve(strict=True) != base.resolve() / candidate.name:
        raise ValueError("Sessão ausente ou redirecionada.")
    marker = candidate / MARKER
    if is_redirected(marker) or not marker.is_file():
        raise ValueError("Marcador da sessão não encontrado ou redirecionado.")
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (ValueError, OSError):
        raise ValueError("Marcador da sessão é inválido.") from None
    if (not isinstance(data, dict) or data.get("schema") != 1 or
            data.get("tool") != "EmeraldHybridV1QALab" or
            data.get("mode") not in ("offline", "ehl8") or
            data.get("profiles") != list(PROFILE_IDS)):
        raise ValueError("Pasta não contém uma sessão de jogos de teste válida.")
    ids = PROFILE_IDS if profile_id is None else (profile_id,)
    if any(pid not in PROFILE_IDS for pid in ids):
        raise ValueError("Conta de QA não permitida.")
    profiles = candidate / "profiles"
    if is_redirected(profiles) or not profiles.is_dir():
        raise ValueError("Diretório de perfis inválido.")
    for pid in ids:
        folder = profiles / pid
        saved = folder / "pokeemerald.sav"
        if (is_redirected(folder) or not folder.is_dir() or is_redirected(saved)
                or not saved.is_file() or saved.stat().st_size not in (131072, 131088)):
            raise ValueError(f"Save de teste {pid} ausente, redirecionado ou com tamanho inválido.")
    return candidate


def saved_game_sessions(root, limit=60):
    """Return newest re-openable sessions; never list protocol-only bots."""
    base = Path(root).resolve() / "sessions"
    if not base.is_dir() or is_redirected(base):
        return []
    result = []
    for session in sorted(base.iterdir(), key=lambda x: x.name, reverse=True):
        # A missing/invalid companion save must not hide a healthy trainer.
        # The selected trainer is revalidated right before launch.
        for pid in PROFILE_IDS:
            try:
                existing_session(root, session, pid)
                result.append(session)
                break
            except (OSError, ValueError):
                continue
        if len(result) >= limit:
            break
    return result


def remove_session(session, root):
    """Only explicitly remove a known lab session, never a user profile root."""
    base = (Path(root).resolve() / "sessions").resolve()
    target = Path(session).resolve(strict=True)
    if target.parent != base or not target.name.startswith("20"):
        raise ValueError("Diretório não é uma sessão de testes criada pelo laboratório.")
    marker = target / MARKER
    try:
        data = json.loads(marker.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise ValueError("Marcador da sessão não encontrado ou inválido.") from None
    if data.get("schema") != 1 or data.get("tool") != "EmeraldHybridV1QALab":
        raise ValueError("Diretório não pertence ao laboratório.")
    # Avoid traversing linked dirs within a session during removal. Deny any
    # symlink to keep deletions constrained to files owned by this test run.
    for path in target.rglob("*"):
        if path.is_symlink() or (hasattr(path, "is_junction") and path.is_junction()):
            raise ValueError("Sessão contém links/junções; remoção recusada.")
    shutil.rmtree(target)


class QASession:
    """Owns at most two Emerald processes and one loopback server."""
    def __init__(self, app, root):
        self.app, self.root = Path(app).resolve(), Path(root).resolve()
        self.session = None
        self.games = []
        self.server = None
        self.mode = "offline"
        self.backups_done = False
        self.backup_status = []
        self.active_profiles = PROFILE_IDS
        self.report_name = "report.json"
        self.admin_enabled = False

    def running(self):
        return any(p.poll() is None for p in self.games) or (
            self.server is not None and self.server.poll() is None)

    def launch(self, mode, sources=(None, None), port=45680, pin=""):
        if self.running():
            raise RuntimeError("Uma sessão de testes ainda está executando.")
        if mode == "ehl8":
            validate_port(port)
            validate_pin(pin)
        if mode == "ehl8":
            # Fail visibly if another EHL8/P2P process already owns the port.
            # This cannot fully prevent a race, but avoids joining the wrong
            # local service accidentally in the common case.
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
                try:
                    probe.bind(("127.0.0.1", validate_port(port)))
                except OSError as exc:
                    raise RuntimeError("Porta local ocupada. Encerre o outro servidor ou escolha outra porta.") from exc
        self.mode = mode
        self.session = prepare_session(self.app, self.root, sources, mode)
        self.games = []
        self.server = None
        self.backups_done = False
        self.backup_status = []
        self.active_profiles = PROFILE_IDS
        self.report_name = "report.json"
        self.admin_enabled = False
        profiles = self.session / "profiles"
        logs = self.session / "logs"
        try:
            if mode == "ehl8":
                with (logs / "servidor.log").open("wb") as out:
                    server_args = server_command(self.app, port, admin=True)
                    self.server = subprocess.Popen(server_args,
                        cwd=str(self.app), stdin=subprocess.PIPE, stdout=out,
                        stderr=subprocess.STDOUT, creationflags=no_window_flags())
                self.admin_enabled = "--admin-stdin" in server_args
                self._send_pin(self.server, pin, keep_open=self.admin_enabled)
                if self.server.poll() is not None:
                    raise RuntimeError("Servidor EHL8 encerrou ao iniciar. Verifique servidor.log.")
            for profile_id in PROFILE_IDS:
                argv = game_command(self.app, profiles, profile_id, mode, port)
                argv += ["--lan-log", str(logs / (profile_id + "-rede.log"))]
                with (logs / (profile_id + "-jogo.log")).open("wb") as err:
                    process = subprocess.Popen(argv, cwd=str(self.app),
                        stdin=subprocess.PIPE if mode == "ehl8" else subprocess.DEVNULL,
                        stdout=subprocess.DEVNULL, stderr=err,
                        creationflags=no_window_flags())
                self.games.append(process)
                if mode == "ehl8":
                    self._send_pin(process, pin)
        except Exception:
            self.stop()
            raise
        return self.session

    def reopen_single(self, session, profile_id):
        """Continue one trainer OFFLINE in its original QA session and save.

        The EHL8 server intentionally needs two players to start. Reopening a
        single account is offline: do not create a server, companion trainer,
        new flash/save or temporary copy. Old reports are never overwritten.
        """
        if self.games and all(p.poll() is not None for p in self.games) and not self.backups_done:
            self.complete()
        if self.running():
            raise RuntimeError("Feche a sessão anterior antes de reabrir um treinador.")
        check_files(self.app, "offline")
        selected = existing_session(self.root, session, profile_id)
        logs = selected / "logs"
        if is_redirected(logs) or not logs.is_dir():
            raise ValueError("Diretório de logs da sessão inválido.")
        self.session = selected
        self.mode = "offline"
        self.games = []
        self.server = None
        self.backups_done = False
        self.backup_status = []
        self.active_profiles = (profile_id,)
        run_id = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)
        self.admin_enabled = False
        self.report_name = "reopen-" + profile_id + "-" + run_id + ".json"
        argv = game_command(self.app, selected / "profiles", profile_id, "offline", 45680)
        argv += ["--lan-log", str(logs / (profile_id + "-" + run_id + "-rede.log"))]
        with (logs / (profile_id + "-" + run_id + "-jogo.log")).open("xb") as err:
            proc = subprocess.Popen(argv, cwd=str(self.app), stdin=subprocess.DEVNULL,
                                    stdout=subprocess.DEVNULL, stderr=err,
                                    creationflags=no_window_flags())
        self.games.append(proc)
        return selected

    @staticmethod
    def _send_pin(process, pin, keep_open=False):
        try:
            process.stdin.write((pin + "\n").encode("ascii"))
            process.stdin.flush()
        finally:
            if not keep_open:
                process.stdin.close()

    def admin_command(self, action, profile=None):
        """Allowlisted commands to our own child server's private stdin pipe."""
        actions = {"lock": "LOCK ON", "unlock": "LOCK OFF"}
        if action == "kick" and profile in PROFILE_IDS:
            command = "KICK " + profile
        elif action in actions and profile is None:
            command = actions[action]
        else:
            raise ValueError("Comando administrativo desconhecido.")
        if (self.mode != "ehl8" or not self.admin_enabled or self.server is None
                or self.server.poll() is not None or self.server.stdin is None
                or self.server.stdin.closed):
            raise RuntimeError("Servidor M2.1 com administração não está ativo.")
        try:
            self.server.stdin.write((command + "\n").encode("ascii"))
            self.server.stdin.flush()
        except (OSError, ValueError) as exc:
            raise RuntimeError("Não foi possível enviar o comando à sala.") from exc
        return command

    def stop(self):
        for process in self.games + ([self.server] if self.server else []):
            if process is not None and process.poll() is None:
                process.terminate()

    def complete(self):
        """Back up only launched profiles, after every game process exits."""
        if self.backups_done or not self.session or any(p.poll() is None for p in self.games):
            return
        self.backups_done = True
        if self.server is not None and self.server.poll() is None:
            self.server.terminate()
        profiles = self.session / "profiles"
        for profile_id in self.active_profiles:
            command = [str(self.app / "emerald_profilectl.exe"),
                       "backup", str(profiles), profile_id]
            try:
                result = subprocess.run(command, cwd=str(self.app),
                    capture_output=True, text=True, timeout=45,
                    creationflags=no_window_flags())
                if result.returncode == 0:
                    message = profile_id + ": backup criado"
                else:
                    # Fresh, never-saved blank flash is invalid for backup,
                    # as designed in SaveProfileManager. Never overwrite it.
                    message = profile_id + ": backup não disponível (save novo ou inválido)"
            except (OSError, subprocess.TimeoutExpired):
                message = profile_id + ": falha ao executar backup; save mantido"
            self.backup_status.append(message)
        report = {"schema": 1, "mode": self.mode,
                  "profiles": list(self.active_profiles),
                  "exit_codes": [p.poll() for p in self.games],
                  "backups": self.backup_status,
                  "finished": datetime.now().isoformat(timespec="seconds")}
        (self.session / self.report_name).write_text(
            json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")


def create_bot_session(root):
    """Create a QA-only metadata folder; bot clients never create game saves."""
    base = Path(root).resolve() / 'sessions'
    base.mkdir(parents=True, exist_ok=True)
    run_id = datetime.now().strftime('%Y%m%d-%H%M%S') + '-' + secrets.token_hex(4)
    session = base / run_id
    session.mkdir(mode=0o700)
    (session / 'logs').mkdir()
    marker = {'schema': 1, 'tool': 'EmeraldHybridV1QALab', 'mode': 'bots',
              'profiles': [], 'created': datetime.now().isoformat(timespec='seconds')}
    (session / MARKER).write_text(json.dumps(marker, indent=2), encoding='utf-8')
    return session


def bot_command(app, port, report):
    """Prefer a companion packaged EXE; allow Python source for development."""
    app = Path(app)
    binary = app / 'EmeraldQABots.exe'
    source = app / 'tools' / 'emerald_qa_bots.py'
    if binary.is_file():
        prefix = [str(binary)]
    elif source.is_file() and not getattr(sys, 'frozen', False):
        prefix = [sys.executable, str(source)]
    else:
        raise FileNotFoundError('EmeraldQABots.exe não encontrado ao lado do Laboratório.')
    return prefix + ['--host', '127.0.0.1', '--port', str(validate_port(port)),
                     '--rounds', '25', '--pin-stdin', '--report', str(report)]


class QABotSession:
    """Orchestrates only localhost server + a protocol-only test executable."""
    def __init__(self, app, root):
        self.app, self.root = Path(app).resolve(), Path(root).resolve()
        self.session = None
        self.server = None
        self.bot = None
        self.done = False

    def running(self):
        return any(p is not None and p.poll() is None for p in (self.server, self.bot))

    def launch(self, port, pin):
        validate_port(port)
        validate_pin(pin)
        if self.running():
            raise RuntimeError('Teste de bots ainda ativo.')
        if not (self.app / 'EmeraldSessionServer.exe').is_file():
            raise FileNotFoundError('EmeraldSessionServer.exe ausente no pacote.')
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
            try:
                probe.bind(('127.0.0.1', validate_port(port)))
            except OSError as exc:
                raise RuntimeError('Porta local ocupada, escolha outra porta.') from exc
        # Fail before allocating the session if the companion EXE is missing.
        bot_command(self.app, port, self.root / 'placeholder.json')
        self.session = create_bot_session(self.root)
        self.done = False
        logs = self.session / 'logs'
        try:
            with (logs / 'servidor-bots.log').open('wb') as stdout:
                self.server = subprocess.Popen(server_command(self.app, port),
                    cwd=str(self.app), stdout=stdout, stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE, creationflags=no_window_flags())
            QASession._send_pin(self.server, pin)
            with (logs / 'clientes-simulados.log').open('wb') as stdout:
                self.bot = subprocess.Popen(bot_command(self.app, port, self.session / 'bots-report.json'),
                    cwd=str(self.app), stdout=stdout, stderr=subprocess.STDOUT,
                    stdin=subprocess.PIPE, creationflags=no_window_flags())
            QASession._send_pin(self.bot, pin)
        except Exception:
            self.stop()
            raise
        return self.session

    def stop(self):
        for process in (self.bot, self.server):
            if process is not None and process.poll() is None:
                process.terminate()

    def complete(self):
        if self.done or self.bot is None or self.bot.poll() is None:
            return None
        self.done = True
        if self.server is not None and self.server.poll() is None:
            self.server.terminate()
        report = self.session / 'bots-report.json'
        try:
            data = json.loads(report.read_text(encoding='utf-8'))
            return (f"{data['rounds_passed']}/{data['rounds_requested']} rodadas aprovadas; "
                    f"{data['identities_attempted']} identidades, máximo de 2 simultâneas. "
                    'Confira bots-report.json.')
        except (OSError, ValueError, KeyError, TypeError):
            return 'Teste encerrado sem relatório válido. Consulte clientes-simulados.log.'


def main():
    import tkinter as tk
    from tkinter import filedialog, messagebox, ttk

    app, root = application_dir(), lab_root()
    gui = tk.Tk()
    gui.title("Emerald Hybrid v1.0 - Laboratório de Contas")
    gui.geometry("830x845")
    gui.minsize(770, 780)
    gui.configure(bg=BG)
    manager = QASession(app, root)
    bot_manager = QABotSession(app, root)
    sources = [tk.StringVar(), tk.StringVar()]
    mode = tk.StringVar(value="ehl8")
    pin = tk.StringVar(value=f"{secrets.randbelow(1000000):06d}")
    port = tk.StringVar(value="45680")
    status = tk.StringVar(value="Crie duas contas novas ou reabra um save de teste anterior sozinho.")
    bot_status = tk.StringVar(value="Bots EHL8: aguardando. Nunca usam saves.")

    def label(text, size=11, color=FG):
        return tk.Label(gui, text=text, font=("Segoe UI", size), bg=BG,
                        fg=color, justify="left", anchor="w")

    label("EMERALD HYBRID  /  LABORATÓRIO V1.0", 20, GREEN).pack(
        fill="x", padx=27, pady=(23, 5))
    label("Dois jogos reais, saves isolados e servidor local de teste.", 11, MUTED).pack(
        fill="x", padx=27, pady=(0, 18))
    for idx in range(2):
        area = tk.Frame(gui, bg=PANEL, padx=13, pady=10)
        area.pack(fill="x", padx=27, pady=5)
        tk.Label(area, text=f"CONTA DE TESTE {'A' if idx == 0 else 'B'}",
                 font=("Segoe UI", 10, "bold"), fg=GREEN, bg=PANEL).pack(anchor="w")
        line = tk.Frame(area, bg=PANEL)
        line.pack(fill="x", pady=(7, 0))
        tk.Entry(line, textvariable=sources[idx], bg="#234439", fg=FG,
                 insertbackground=FG, relief="flat", font=("Segoe UI", 10)).pack(
                    side="left", fill="x", expand=True, ipady=6)
        tk.Button(line, text="Importar cópia .sav", command=lambda i=idx:
                  sources[i].set(filedialog.askopenfilename(
                      filetypes=[("Emerald save", "*.sav"), ("Todos os arquivos", "*.*")])
                     or sources[i].get()), bg="#236448", fg=FG, relief="flat").pack(
                         side="left", padx=(8, 0))
        tk.Label(area, text="Deixe vazio para iniciar uma aventura nova (flash vazio).",
                 bg=PANEL, fg=MUTED, font=("Segoe UI", 9)).pack(anchor="w", pady=(5, 0))
    config = tk.Frame(gui, bg=BG)
    config.pack(fill="x", padx=27, pady=(18, 6))
    for caption, value in (("EHL8 local (2 jogadores)", "ehl8"),
                           ("Offline (2 janelas)", "offline")):
        tk.Radiobutton(config, text=caption, variable=mode, value=value,
                       bg=BG, fg=FG, activebackground=BG, activeforeground=GREEN,
                       selectcolor=PANEL).pack(side="left", padx=(0, 20))
    options = tk.Frame(gui, bg=BG)
    options.pack(fill="x", padx=27, pady=(2, 12))
    tk.Label(options, text="Porta local:", bg=BG, fg=MUTED).pack(side="left")
    tk.Entry(options, width=7, textvariable=port, bg=PANEL, fg=FG,
             insertbackground=FG).pack(side="left", padx=(6, 19))
    tk.Label(options, text="PIN:", bg=BG, fg=MUTED).pack(side="left")
    tk.Entry(options, width=8, textvariable=pin, show="*", bg=PANEL,
             fg=FG, insertbackground=FG).pack(side="left", padx=6)

    def start():
        if manager.running() or bot_manager.running():
            messagebox.showwarning("Sessão ativa", "Encerre a sessão atual antes de começar outra.")
            return
        try:
            folder = manager.launch(mode.get(), tuple(s.get().strip() or None for s in sources),
                                    port.get(), pin.get())
            status.set("Sessão NOVA iniciada: " + str(folder) + ". Para continuar depois, use REABRIR 1 CONTA.")
            refresh_saved()
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            messagebox.showerror("Não foi possível iniciar", str(exc))
            status.set("Falha no início; consulte os logs da pasta de testes.")

    def stop():
        if manager.running() and messagebox.askyesno(
                "Encerrar testes", "Encerrar somente os processos iniciados pelo Laboratório?"):
            manager.stop()
            status.set("Encerrando jogos de teste; perfis e saves serão preservados.")

    def open_dir():
        path = manager.session or root
        path.mkdir(parents=True, exist_ok=True)
        if sys.platform == "win32":
            os.startfile(path)
        else:
            messagebox.showinfo("Diretório de testes", str(path))

    def delete():
        if manager.running() or not manager.session:
            messagebox.showwarning("Sessão indisponível", "Feche os jogos e selecione uma sessão concluída.")
            return
        manager.complete()  # Finish eligible backups before destructive cleanup.
        if messagebox.askyesno("Excluir sessão de QA",
                "Excluir permanentemente os dois SAVES DE TESTE, logs e relatórios desta sessão?\n"
                "Os saves originais importados nunca serão apagados."):
            try:
                remove_session(manager.session, root)
                manager.session = None
                refresh_saved()
                status.set("Sessão de QA apagada. Perfis reais preservados.")
            except (OSError, ValueError) as exc:
                messagebox.showerror("Remoção recusada", str(exc))

    buttons = tk.Frame(gui, bg=BG)
    buttons.pack(fill="x", padx=27, pady=(6, 12))
    for text, callback in (("ABRIR 2 JOGOS (NOVO)", start), ("Parar testes", stop),
                           ("Abrir pasta", open_dir), ("Limpar sessão", delete)):
        tk.Button(buttons, text=text, command=callback, bg="#176449" if text.startswith("ABRIR")
                  else PANEL, fg=FG, activebackground="#277d5e", relief="flat",
                  font=("Segoe UI", 10, "bold"), padx=11, pady=9).pack(side="left", padx=(0, 7))
    # M2.1-A monitor reads real localhost session logs; READY stays automatic.
    def show_lobby_monitor():
        from emerald_qa_lobby import show_lobby
        show_lobby(gui, manager, bg=BG, panel=PANEL, green=GREEN,
                   fg=FG, muted=MUTED)

    tk.Button(buttons, text="LOBBY AO VIVO", command=show_lobby_monitor,
              bg=PANEL, fg=FG, activebackground="#277d5e", relief="flat",
              font=("Segoe UI", 10, "bold"), padx=11, pady=9).pack(
                  side="left", padx=(0, 7))
    # Solo continuation uses a previously created, isolated QA session.
    # It never starts a new game/save and never joins EHL8 (requires 2 ready).
    solo_area = tk.Frame(gui, bg=PANEL, padx=11, pady=9)
    solo_area.pack(fill="x", padx=27, pady=(0, 10))
    tk.Label(solo_area, text="CONTINUAR SOZINHO — mesmo save de teste, modo offline",
             fg=GREEN, bg=PANEL, font=("Segoe UI", 10, "bold")).pack(anchor="w")
    solo_line = tk.Frame(solo_area, bg=PANEL)
    solo_line.pack(fill="x", pady=(6, 0))
    saved_choice = tk.StringVar()
    saved_map = {}
    saved_combo = ttk.Combobox(solo_line, textvariable=saved_choice, state="readonly", width=29)
    saved_combo.pack(side="left", fill="x", expand=True, padx=(0, 9))
    selected_solo = tk.StringVar(value="QA_A")
    for profile_id in PROFILE_IDS:
        tk.Radiobutton(solo_line, text=profile_id, value=profile_id,
                       variable=selected_solo, bg=PANEL, fg=FG,
                       selectcolor=BG, activebackground=PANEL,
                       activeforeground=GREEN).pack(side="left")

    def refresh_saved():
        nonlocal saved_map
        previous = saved_choice.get()
        sessions = saved_game_sessions(root)
        saved_map = {f"{p.name} (QA_A e QA_B)": p for p in sessions}
        saved_combo.configure(values=tuple(saved_map))
        if previous in saved_map:
            saved_choice.set(previous)
        else:
            saved_choice.set(next(iter(saved_map), ""))

    def reopen_solo():
        if manager.running() or bot_manager.running():
            messagebox.showwarning("Sessão ativa", "Feche os jogos e bots antes de continuar.")
            return
        folder = saved_map.get(saved_choice.get())
        if folder is None:
            messagebox.showinfo("Sem sessão", "Primeiro abra 2 jogos e salve; depois reabra uma conta aqui.")
            return
        try:
            manager.reopen_single(folder, selected_solo.get())
            status.set("Reaberto " + selected_solo.get() + " OFFLINE, com o MESMO save. "
                       "Feche normalmente para criar backup somente desta conta.")
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            messagebox.showerror("Não foi possível reabrir", str(exc))

    tk.Button(solo_area, text="Atualizar sessões", command=refresh_saved,
              bg=PANEL, fg=FG, relief="flat").pack(side="left", pady=(8, 0))
    tk.Button(solo_area, text="REABRIR 1 CONTA", command=reopen_solo,
              bg="#176449", fg=FG, font=("Segoe UI", 10, "bold"),
              relief="flat", padx=11, pady=5).pack(side="right", pady=(8, 0))
    refresh_saved()

    def start_bots():
        if manager.running() or bot_manager.running():
            messagebox.showwarning('Sessão ativa', 'Feche os jogos ou bots antes de iniciar outro teste.')
            return
        try:
            folder = bot_manager.launch(port.get(), pin.get())
            bot_status.set('Bots iniciados: 50 identidades em 25 rodadas de 2. Pasta: ' + str(folder))
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as exc:
            messagebox.showerror('Não foi possível iniciar bots', str(exc))

    bot_buttons = tk.Frame(gui, bg=BG)
    bot_buttons.pack(fill='x', padx=27, pady=(0, 10))
    tk.Button(bot_buttons, text='SIMULAR 50 CONTAS', command=start_bots,
              bg='#1b695b', fg=FG, relief='flat', font=('Segoe UI', 10, 'bold'),
              padx=11, pady=9).pack(side='left', padx=(0, 8))
    tk.Button(bot_buttons, text='Parar bots', command=bot_manager.stop,
              bg=PANEL, fg=FG, relief='flat', font=('Segoe UI', 10, 'bold'),
              padx=11, pady=9).pack(side='left', padx=(0, 8))
    def clear_bots():
        if bot_manager.running():
            messagebox.showwarning('Bots ativos', 'Pare os bots antes de limpar o teste.')
            return
        if bot_manager.session and messagebox.askyesno('Limpar dados simulados',
                'Excluir somente os relatórios/logs temporários deste teste de bots?'):
            try:
                remove_session(bot_manager.session, root)
                bot_manager.session = None
                bot_status.set('Dados temporários dos bots removidos. Saves não afetados.')
            except (OSError, ValueError) as exc:
                messagebox.showerror('Remoção recusada', str(exc))
    tk.Button(bot_buttons, text='Limpar teste bots', command=clear_bots,
              bg=PANEL, fg=FG, relief='flat', font=('Segoe UI', 10, 'bold'),
              padx=11, pady=9).pack(side='left')
    tk.Label(gui, textvariable=bot_status, bg=BG, fg=GREEN, wraplength=735,
             font=('Segoe UI', 9), justify='left', anchor='w').pack(
                 fill='x', padx=27, pady=(0, 9))

    label("O laboratório não altera perfis do launcher nem envia saves ao servidor.",
          9, MUTED).pack(fill="x", padx=27)
    tk.Label(gui, textvariable=status, bg=BG, fg=GREEN, wraplength=690,
             font=("Segoe UI", 10), justify="left", anchor="w").pack(
                 fill="x", padx=27, pady=(13, 0))

    def monitor():
        if manager.session and not manager.backups_done and manager.games:
            if all(p.poll() is not None for p in manager.games):
                manager.complete()
                status.set("Jogos encerrados. " + "; ".join(manager.backup_status) +
                           ". Logs e relatório preservados.")
        if bot_manager.bot is not None and not bot_manager.done and bot_manager.bot.poll() is not None:
            result = bot_manager.complete()
            bot_status.set('Bots: ' + result)
        gui.after(1000, monitor)

    def close():
        if (manager.running() or bot_manager.running()) and not messagebox.askyesno("Fechar laboratório",
                "Os jogos de teste ainda estão rodando. Encerrá-los e fechar o laboratório?"):
            return
        manager.stop()
        bot_manager.stop()
        gui.destroy()

    gui.protocol("WM_DELETE_WINDOW", close)
    gui.after(1000, monitor)
    gui.mainloop()


if __name__ == "__main__":
    main()