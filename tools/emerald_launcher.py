"""Emerald Hybrid experimental graphical launcher for Windows.
Local accounts are save PROFILES, not Internet authentication.
EHL8 presence mode is distinct from the legacy P2P Cable Club link.
"""
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
from datetime import datetime
import subprocess
import sys
import tkinter as tk
from tkinter import filedialog, messagebox, simpledialog

INK="#091510"; LEFT="#10231c"; PANEL="#18352a"; GREEN="#49d5a0"; WHITE="#e9fff5"; MUTED="#9dbbaa"
PATTERN=re.compile(r"^[A-Za-z0-9_-]{1,48}$")

def application_dir():
    return Path(sys.executable).resolve().parent if getattr(sys,"frozen",False) else Path(__file__).resolve().parent.parent

def profile_root():
    here=application_dir()
    if (here/"PORTABLE_MODE.txt").exists():
        return here/"profiles"
    if (here/"EHL8_PREVIEW_MODE.txt").exists():
        # The beta installer must not open the user's already-proven v0.8.2
        # save profiles without an explicit import/backup step.
        return Path(os.environ.get("LOCALAPPDATA",str(Path.home()))) / "EmeraldHybridEHL8Preview" / "profiles"
    return Path(os.environ.get("LOCALAPPDATA",str(Path.home()))) / "EmeraldHybrid" / "profiles"

def settings_path(root):
    # Local profiles live under %LOCALAPPDATA%/EmeraldHybrid or portable ./profiles.
    return root.parent / "launcher-settings.json"

def read_settings(root):
    path = settings_path(root)
    try:
        if path.stat().st_size > 32768:
            return {}
        data = json.loads(path.read_text(encoding="utf-8"))
        return data if isinstance(data, dict) and data.get("schema") == 1 else {}
    except (OSError, UnicodeError, ValueError, TypeError):
        return {}

def write_settings(root, selected, diagnostics, ip, port):
    data = {"schema": 1, "selected_profile": selected, "diagnostics": bool(diagnostics),
            "last_host": ip, "last_port": port}
    target = settings_path(root)
    target.parent.mkdir(parents=True, exist_ok=True)
    temporary = target.with_name(target.name + "." + secrets.token_hex(5) + ".tmp")
    try:
        with temporary.open("x", encoding="utf-8") as stream:
            json.dump(data, stream, indent=2, ensure_ascii=False)
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, target)
    finally:
        try: temporary.unlink(missing_ok=True)
        except OSError: pass

def read_room_occupancy(log_path):
    """Read only the tail of this launcher's server log; never parse secrets."""
    if not log_path:
        return None
    try:
        with open(log_path, "rb") as stream:
            stream.seek(0, os.SEEK_END)
            end = stream.tell()
            stream.seek(max(0, end - 8192))
            tail = stream.read(8192).decode("utf-8", "replace")
    except OSError:
        return None
    matches = re.findall(r"EHL8_ROOM_COUNT=([0-2])/([12])(?:\s|$)", tail)
    if not matches:
        return None
    current, capacity = map(int, matches[-1])
    return (current, capacity) if current <= capacity else None


def file_sha256(path):
    digest = hashlib.sha256()
    with open(path, "rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def server_launch_plan(app_dir, game_path, port):
    """Prefer matched M2.3 host-controlled server; never mix mismatched EXEs.

    Returns (argv, is_manual_start). An older ZIP without a marker retains
    its previous automatic READY/START behavior.
    """
    app_dir = Path(app_dir)
    marker = app_dir / "EHL8_M23_GAME_MATCHED.txt"
    server = app_dir / "EmeraldSessionServer.exe"
    manual = marker.is_file()
    if manual:
        server = app_dir / "EmeraldSessionServerM23.exe"
        if not server.is_file() or not Path(game_path).is_file():
            raise ValueError("Pacote M2.3 incompleto. Extraia o ZIP inteiro em pasta nova.")
        try:
            if marker.stat().st_size > 4096:
                raise ValueError("Manifesto EHL8 grande demais.")
            data = json.loads(marker.read_text(encoding="utf-8-sig"))
            if not isinstance(data, dict) or (
                data.get("game_sha256") != file_sha256(game_path) or
                data.get("server_sha256") != file_sha256(server)
            ):
                raise ValueError("Hashes de jogo/servidor incompatíveis.")
        except (OSError, ValueError, UnicodeError) as error:
            raise ValueError("Par jogo/servidor M2.3 não verificado; use o ZIP completo.") from error
    elif not server.is_file():
        raise ValueError("EmeraldSessionServer.exe ausente; use o pacote completo.")
    command = [str(server), "--bind", "0.0.0.0", "--port", str(validate_port(port)),
               "--slots", "2", "--idle-minutes", "15", "--pin-stdin"]
    if manual:
        command.extend(["--admin-stdin", "--resume-v1", "--host-start"])
    return command, manual


def read_lobby_gate(log_path):
    """Read bounded server log tail; never infer readiness from occupancy."""
    if not log_path:
        return None
    try:
        with open(log_path, "rb") as stream:
            stream.seek(0, os.SEEK_END)
            end = stream.tell()
            stream.seek(max(0, end - 16384))
            tail = stream.read(16384).decode("utf-8", "replace")
    except OSError:
        return None
    def most_recent(pattern):
        items = re.findall(pattern, tail)
        return items[-1] if items else None
    occupancy = most_recent(r"EHL8_ROOM_COUNT=([0-2])/2(?:\s|$)")
    ready = most_recent(r"EHL8_READY_COUNT=([0-2])/2(?:\s|$)")
    started = most_recent(r"EHL8_ROOM_STARTED=([01])(?:\s|$)")
    if occupancy is None or ready is None or started is None:
        return None
    return {"players": int(occupancy), "ready": int(ready),
            "started": started == "1"}


def send_lobby_admin(process, command):
    """Only recognized local host commands are sent via an open private pipe."""
    if command != "START":
        raise ValueError("Comando administrativo inválido.")
    if process is None or process.poll() is not None or process.stdin is None or process.stdin.closed:
        raise OSError("Servidor não está ativo ou canal administrativo indisponível.")
    process.stdin.write(b"START\n")
    process.stdin.flush()


def deliver_pin_or_terminate(process, pin, keep_open=False):
    """Deliver the private EHL8 PIN or stop a child that was not adopted.

    The launcher must only track the new process after PIN delivery succeeds.
    """
    try:
        if process.stdin is None:
            raise OSError("Canal privado do PIN indisponível.")
        process.stdin.write((pin + "\n").encode("ascii"))
        process.stdin.flush()
    except (OSError, ValueError, UnicodeError) as cause:
        try:
            if process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait(timeout=3)
        except (OSError, subprocess.TimeoutExpired):
            pass
        raise OSError(
            "O jogo/servidor não recebeu o PIN; o processo foi encerrado ou já havia terminado."
        ) from cause
    finally:
        if process.stdin is not None and (not keep_open or process.poll() is not None):
            try:
                process.stdin.close()
            except OSError:
                pass


def validate_port(value):
    try: p=int(str(value).strip())
    except ValueError: raise ValueError("A porta precisa ser um número.")
    if p < 1 or p > 65534:
        raise ValueError("Porta inválida: use 1 a 65534 (a segunda conexão usa porta + 1).")
    return p

def validate_ipv4(value):
    try: addr=ipaddress.IPv4Address(value.strip())
    except ipaddress.AddressValueError: raise ValueError("Use o IPv4 numérico do host (ex.: 100.101.102.103).")
    if addr.is_unspecified or addr.is_multicast or str(addr)=="255.255.255.255":
        raise ValueError("Esse endereço IP não pode ser utilizado.")
    return str(addr)

def validate_nickname(value):
    value=value.strip()
    if not 1 <= len(value) <= 18 or any(ord(c)<32 for c in value):
        raise ValueError("O apelido deve ter de 1 a 18 caracteres.")
    return value

def make_command(game,root,pid,mode,ip="",port="45680",pin=""):
    if not PATTERN.fullmatch(pid):
        raise ValueError("Identificador de perfil inválido.")
    args=[str(game),"--profile-root="+str(root),"--profile-id="+pid]
    if mode=="offline": return args
    p=validate_port(port)
    if mode=="host":return args+["--lan-log","host-launcher.log","--lan-host="+str(p)]
    if mode=="join":return args+["--lan-log","cliente-launcher.log","--lan-client="+validate_ipv4(ip)+":"+str(p)]
    if mode=="dedicated":
        if not re.fullmatch(r"[0-9]{6}",pin):
            raise ValueError("Informe o PIN de seis dígitos do servidor dedicado.")
        return args+["--lan-log","cliente-ehl8.log",
                     "--session-client="+validate_ipv4(ip)+":"+str(p),"--session-pin-stdin"]
    raise ValueError("Modo de jogo desconhecido.")

def find_profiles(root):
    if not root.is_dir():return []
    out=[]
    for folder in root.iterdir():
        if not folder.is_dir() or not PATTERN.fullmatch(folder.name) or not (folder/"pokeemerald.sav").is_file():continue
        nick=folder.name
        try:
            meta=json.loads((folder/"profile.json").read_text(encoding="utf-8"))
            nick=validate_nickname(meta.get("nickname",nick))
        except (OSError,ValueError,TypeError):
            pass
        out.append((folder.name,nick))
    return sorted(out,key=lambda x:x[1].casefold())

def write_nickname(folder,nick):
    meta=folder/"profile.json";tmp=folder/"profile.json.tmp"
    with tmp.open("x",encoding="utf-8") as fp:
        json.dump({"schema":1,"nickname":nick,"profile_id":folder.name},fp,ensure_ascii=False,indent=2)
        fp.flush();os.fsync(fp.fileno())
    os.replace(tmp,meta)

class EmeraldLauncher(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Emerald Hybrid — Multiplayer Launcher")
        self.geometry("1040x715"); self.minsize(880,640)
        self.configure(bg=INK)
        self.root_dir=profile_root()
        self.game=application_dir()/"pokeemerald.exe"
        self.cli=application_dir()/"emerald_profilectl.exe"
        self.server_exe=application_dir()/"EmeraldSessionServer.exe"
        self.server_process=None
        self.server_log_path=None
        self.manual_start_available=False
        settings=read_settings(self.root_dir)
        selected=settings.get("selected_profile")
        self.selected=selected if isinstance(selected,str) and PATTERN.fullmatch(selected) else None
        self.ip=tk.StringVar(value=str(settings.get("last_host",""))[:48])
        self.port=tk.StringVar(value=str(settings.get("last_port","45680"))[:6])
        self.diagnostics=tk.BooleanVar(value=settings.get("diagnostics",False) is True)
        self.pin=tk.StringVar()
        self.dedicated_mode=tk.BooleanVar(value=False)
        self.server_status=tk.StringVar(value="Servidor dedicado: desligado")
        self.active_process=None
        self.active_log=None
        self.active_mode=None
        self.status=tk.StringVar(value="Selecione ou crie um perfil para começar.")
        self.sidebar=tk.Frame(self,bg=LEFT,width=275)
        self.sidebar.pack(side="left",fill="y");self.sidebar.pack_propagate(False)
        self.main=tk.Frame(self,bg=INK);self.main.pack(side="left",fill="both",expand=True)
        self.sidebar_ui();self.main_ui();self.refresh()
        self.protocol("WM_DELETE_WINDOW",self.shutdown)

    def text(self,parent,value,sz=11,color=WHITE,bold=False):
        return tk.Label(parent,text=value,fg=color,bg=parent["bg"],
                        font=("Segoe UI",sz,"bold" if bold else "normal"),justify="left",anchor="w")

    def btn(self,parent,name,callback,accent=False,disabled=False):
        button=tk.Button(parent,text=name,command=callback,relief="flat",bd=0,
                         bg="#1b654d" if accent else "#264739",fg=WHITE,
                         activebackground="#338e69",activeforeground=WHITE,
                         disabledforeground="#789188",font=("Segoe UI",10,"bold"),padx=15,pady=10,
                         cursor="arrow" if disabled else "hand2")
        if disabled:button.configure(state="disabled")
        return button

    def sidebar_ui(self):
        f=self.sidebar
        tk.Frame(f,bg=GREEN,height=5).pack(fill="x")
        self.text(f,"EMERALD",22,GREEN,True).pack(anchor="w",padx=22,pady=(33,0))
        self.text(f,"HYBRID MULTIPLAYER",11,WHITE,True).pack(anchor="w",padx=22)
        self.text(f,"VERSÃO EXPERIMENTAL v0.8",9,MUTED).pack(anchor="w",padx=22,pady=(4,36))
        self.text(f,"CONTA / PERFIL LOCAL",10,MUTED,True).pack(anchor="w",padx=22)
        self.choices=tk.Frame(f,bg=LEFT);self.choices.pack(fill="x",padx=16,pady=(10,6))
        self.btn(f,"+ Criar ou importar conta",self.new_profile,accent=True).pack(fill="x",padx=16,pady=6)
        self.btn(f,"Atualizar lista",self.refresh).pack(fill="x",padx=16,pady=6)
        self.btn(f,"Abrir pasta de logs",self.open_logs).pack(fill="x",padx=16,pady=6)
        self.btn(f,"Criar backup do perfil",self.backup_selected).pack(fill="x",padx=16,pady=6)
        self.btn(f,"Recuperar backup",self.restore_selected).pack(fill="x",padx=16,pady=6)
        tk.Frame(f,bg=LEFT).pack(expand=True)
        self.text(f,"Progresso individual",10,MUTED,True).pack(anchor="w",padx=20)
        self.text(f,"Nenhuma conta online é exigida.\nSeus saves permanecem locais.",9,MUTED).pack(anchor="w",padx=20,pady=(6,25))

    def card(self,parent,title,subtitle,action,label,available=True,accent=False):
        card=tk.Frame(parent,bg=PANEL,highlightbackground="#325344",highlightthickness=1)
        card.pack(fill="x",pady=5,ipady=8)
        box=tk.Frame(card,bg=PANEL);box.pack(side="left",fill="x",expand=True,padx=20,pady=5)
        self.text(box,title,13,WHITE,True).pack(anchor="w")
        self.text(box,subtitle,9,MUTED).pack(anchor="w",pady=(5,0))
        self.btn(card,label,action,accent,not available).pack(side="right",padx=17)

    def main_ui(self):
        f=self.main
        heading=tk.Frame(f,bg=INK);heading.pack(fill="x",padx=32,pady=(31,14))
        self.text(heading,"SUA AVENTURA EM HOENN",20,WHITE,True).pack(anchor="w")
        self.text(heading,"Escolha um perfil e como deseja jogar.",10,MUTED).pack(anchor="w",pady=(6,0))
        info=tk.Frame(f,bg="#194131",padx=17,pady=12);info.pack(fill="x",padx=32,pady=(0,12))
        tk.Label(info,textvariable=self.status,fg=GREEN,bg=info["bg"],font=("Segoe UI",11,"bold"),anchor="w").pack(fill="x")
        self.text(info,"Conta = perfil local. EHL8 dedicado: beta para 2, presença apenas; batalhas/trocas usam P2P.",9,MUTED).pack(anchor="w",pady=(3,0))
        cards=tk.Frame(f,bg=INK);cards.pack(fill="x",padx=32)
        self.card(cards,"Jogar offline","Seu save, sem precisar de Internet.",lambda:self.play("offline"),"JOGAR",accent=True)
        self.card(cards,"Cable Club legado (P2P)","Hospedar link antigo; NÃO cria sala de presença EHL8.",lambda:self.play("host"),"HOST P2P")
        self.card(cards,"Entrar com amigo","Para aparecer no mapa: marque EHL8 e informe IP, porta e PIN.",self.play_with_friends,"ENTRAR")
        self.card(cards,"Hospedar EHL8 (2 jogadores)","1. Inicie servidor. 2. Marque EHL8 e entre no próprio IP.",self.start_server,"CRIAR SALA")
        rowserver=tk.Frame(f,bg=INK);rowserver.pack(fill="x",padx=32,pady=(1,0))
        tk.Label(rowserver,textvariable=self.server_status,fg=GREEN,bg=INK,
                 font=("Segoe UI",9),anchor="w").pack(side="left",fill="x",expand=True)
        self.btn(rowserver,"Parar servidor",self.stop_server).pack(side="right")
        self.start_room_button = self.btn(rowserver, "INICIAR SALA (2/2)", self.start_room,
                                          accent=True, disabled=True)
        self.start_room_button.pack(side="right", padx=(0, 9))
        section=tk.Frame(f,bg=INK);section.pack(fill="x",padx=32,pady=(19,6))
        self.text(section,"CONFIGURAÇÕES DA CONEXÃO",10,MUTED,True).pack(anchor="w")
        row=tk.Frame(f,bg=INK);row.pack(fill="x",padx=32)
        self.text(row,"IP do host:",10,MUTED).pack(side="left")
        tk.Entry(row,textvariable=self.ip,width=20,bg=PANEL,fg=WHITE,insertbackground=WHITE,relief="flat",font=("Consolas",11)).pack(side="left",padx=(10,22),ipady=7)
        self.text(row,"Porta:",10,MUTED).pack(side="left")
        tk.Entry(row,textvariable=self.port,width=7,bg=PANEL,fg=WHITE,insertbackground=WHITE,relief="flat",font=("Consolas",11)).pack(side="left",padx=9,ipady=7)
        secretrow=tk.Frame(f,bg=INK);secretrow.pack(fill="x",padx=32,pady=(6,0))
        tk.Checkbutton(secretrow,text="Entrar via servidor dedicado EHL8",variable=self.dedicated_mode,
                       selectcolor=PANEL,activebackground=INK,activeforeground=WHITE,
                       bg=INK,fg=MUTED,font=("Segoe UI",9)).pack(side="left")
        self.text(secretrow,"PIN:",9,MUTED).pack(side="left",padx=(8,2))
        tk.Entry(secretrow,textvariable=self.pin,show="*",width=8,bg=PANEL,fg=WHITE,
                 insertbackground=WHITE,relief="flat",font=("Consolas",10)).pack(side="left",ipady=5)
        tk.Checkbutton(f,text="Diagnóstico opcional: mostrar console CMD",variable=self.diagnostics,
                       command=self.persist,selectcolor=PANEL,activebackground=INK,activeforeground=WHITE,
                       bg=INK,fg=MUTED,font=("Segoe UI",10),anchor="w").pack(anchor="w",padx=32,pady=(13,0))
        self.text(f,"Conexão remota: use VPN privada; não exponha as portas no roteador.",9,"#ffc783").pack(anchor="w",padx=32,pady=(8,0))

    def refresh(self):
        for child in self.choices.winfo_children():child.destroy()
        profiles=find_profiles(self.root_dir)
        if self.selected not in [id for id,_ in profiles]:
            self.selected=None
            self.status.set("Selecione ou crie um perfil para começar.")
        for pid,nick in profiles:
            chosen=pid==self.selected
            self.btn(self.choices,("● " if chosen else "○ ")+nick,
                     lambda pid=pid:self.select(pid),accent=chosen).pack(fill="x",pady=3)

    def persist(self):
        try:
            write_settings(self.root_dir,self.selected,self.diagnostics.get(),self.ip.get(),self.port.get())
        except OSError:
            self.status.set("Não foi possível salvar as preferências do launcher.")

    def select(self,pid):
        self.selected=pid
        name=next((nick for id,nick in find_profiles(self.root_dir) if id==pid),pid)
        self.status.set("Perfil ativo: "+name)
        self.refresh()
        self.persist()

    def open_logs(self):
        directory=self.root_dir.parent/"logs"
        try:
            directory.mkdir(parents=True,exist_ok=True)
            if sys.platform=="win32": os.startfile(directory)
            else: messagebox.showinfo("Logs",str(directory))
        except OSError as exc:
            messagebox.showerror("Logs indisponíveis",str(exc))

    def profile_can_be_edited(self):
        if self.active_process is not None and self.active_process.poll() is None:
            messagebox.showwarning("Feche o jogo","O Emerald precisa estar fechado antes de acessar backups.")
            return False
        if self.selected is None:
            messagebox.showwarning("Selecione um perfil","Escolha um perfil antes de criar ou recuperar backups.")
            return False
        if not self.cli.is_file():
            messagebox.showerror("Dependência ausente","emerald_profilectl.exe não foi encontrado.")
            return False
        return True

    def run_profile_tool(self, *options):
        result=subprocess.run([str(self.cli),*map(str,options)],
                              cwd=str(application_dir()), capture_output=True,text=True,
                              timeout=45,creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
        if result.returncode != 0:
            raise RuntimeError((result.stderr or result.stdout).strip()[:450] or
                               "O gerenciador recusou a operação. Seu save não foi alterado.")
        return result.stdout.strip()

    def backup_selected(self):
        if not self.profile_can_be_edited(): return
        try:
            result=self.run_profile_tool("backup",self.root_dir,self.selected)
            messagebox.showinfo("Backup criado",result+"\nO .sav original continua intacto.")
        except (OSError,RuntimeError,subprocess.TimeoutExpired) as err:
            messagebox.showerror("Backup não criado",str(err)+
                                 "\nUm perfil novo sem save completo ainda pode ser recusado.")

    def restore_selected(self):
        if not self.profile_can_be_edited(): return
        folder=self.root_dir/self.selected/"backups"
        items=sorted((p for p in folder.glob("[0-9][0-9][0-9][0-9][0-9][0-9].sav") if p.is_file()),
                     key=lambda p:p.name) if folder.is_dir() else []
        if not items:
            messagebox.showinfo("Nenhum backup","Este perfil ainda não possui backups disponíveis.")
            return
        latest=items[-1]
        ask=simpledialog.askinteger("Recuperar backup",
                f"Backup mais recente: {latest.name}\n"
                f"Criado/modificado: {datetime.fromtimestamp(latest.stat().st_mtime):%d/%m/%Y %H:%M}\n"
                "Informe o número do backup que deseja restaurar:",parent=self,
                initialvalue=int(latest.stem),minvalue=1,maxvalue=999999)
        if ask is None:return
        if not any(int(p.stem)==ask for p in items):
            messagebox.showerror("Backup ausente","Não existe backup com esse número.")
            return
        if not messagebox.askyesno("Confirmar recuperação",
              f"Substituir o save atual pelo backup {ask:06d}.sav?\n"
              "O gerenciador tentará preservar uma cópia de segurança do save atual.\n"
              "Confirme somente após fechar o Emerald."):
            return
        try:
            result=self.run_profile_tool("restore",self.root_dir,self.selected,ask)
            messagebox.showinfo("Recuperação concluída",result or "Backup restaurado. Abra o Emerald para conferir o progresso.")
        except (OSError,RuntimeError,subprocess.TimeoutExpired) as err:
            messagebox.showerror("Não foi possível recuperar",str(err))

    def play_with_friends(self):
        self.play("dedicated" if self.dedicated_mode.get() else "join")

    def start_server(self):
        if self.server_process is not None and self.server_process.poll() is None:
            messagebox.showinfo("Servidor ativo","Já existe um servidor em execução neste launcher.")
            return
        if not self.server_exe.is_file():
            messagebox.showerror("Servidor ausente","EmeraldSessionServer.exe não foi encontrado. Use o pacote completo EHL8.")
            return
        try:
            port=validate_port(self.port.get())
            pin=self.pin.get()
            if not re.fullmatch(r"[0-9]{6}",pin):
                raise ValueError("Informe um PIN de seis dígitos antes de hospedar.")
            if not messagebox.askyesno("Servidor experimental LAN",
                  "Iniciar servidor EHL8 na rede local privada?\n"
                  "Somente personagens no mapa; batalhas e trocas ainda usam P2P.\n"
                  "Não abra portas públicas no roteador."):
                return
            logs=self.root_dir.parent/"logs"
            logs.mkdir(parents=True,exist_ok=True)
            path=logs/("servidor-"+datetime.now().strftime("%Y%m%d-%H%M%S")+".log")
            flags=(getattr(subprocess,"CREATE_NO_WINDOW",0) if sys.platform=="win32" else 0)
            command, manual = server_launch_plan(application_dir(), self.game, port)
            with path.open("ab") as log:
                proc=subprocess.Popen(command,cwd=str(application_dir()),creationflags=flags,
                     stdin=subprocess.PIPE,stdout=log,stderr=subprocess.STDOUT)
                deliver_pin_or_terminate(proc, pin, keep_open=manual)
            self.manual_start_available=manual
            self.server_process=proc
            self.server_log_path=path
            self.server_status.set("Servidor EHL8 iniciando · porta "+str(port)+" · até 2 jogadores")
            self.after(1500,self.watch_server)
        except (OSError,ValueError) as exc:
            messagebox.showerror("Não foi possível hospedar",str(exc))

    def watch_server(self):
        if self.server_process is None:return
        rc=self.server_process.poll()
        if rc is not None:
            self.server_process=None
            self.manual_start_available=False
            self.start_room_button.configure(state="disabled")
            self.server_status.set("Servidor desligado (código "+str(rc)+"). Veja os logs.")
        else:
            occupancy=read_room_occupancy(self.server_log_path)
            state=read_lobby_gate(self.server_log_path) if self.manual_start_available else None
            can_start=bool(state and state["players"]==2 and state["ready"]==2
                           and not state["started"])
            self.start_room_button.configure(state="normal" if can_start else "disabled")
            if state:
                self.server_status.set(
                    f"Sala EHL8 {state['players']}/2 · prontos {state['ready']}/2 · "
                    + ("EM JOGO" if state["started"] else "aguardando START do anfitrião"))
            elif occupancy is None:
                self.server_status.set("Servidor EHL8 ativo (beta) · aguardando participantes")
            else:
                connected, limit=occupancy
                self.server_status.set(
                    f"Servidor EHL8 ativo (beta) · jogadores conectados: {connected}/{limit}")
            self.after(1300,self.watch_server)

    def start_room(self):
        state = read_lobby_gate(self.server_log_path) if self.manual_start_available else None
        if not state or state["players"] != 2 or state["ready"] != 2 or state["started"]:
            messagebox.showwarning("Sala indisponível",
                                   "São necessários 2/2 jogadores prontos; aguarde o lobby.")
            return
        try:
            send_lobby_admin(self.server_process, "START")
            self.start_room_button.configure(state="disabled")
            self.server_status.set("Solicitação START enviada; aguardando confirmação do servidor.")
        except (OSError, ValueError) as exc:
            messagebox.showerror("Não foi possível iniciar a sala", str(exc))

    def stop_server(self):
        if self.server_process is not None and self.server_process.poll() is None:
            if not messagebox.askyesno("Parar servidor","Desconectar os jogadores e encerrar o servidor EHL8?"):
                return
            self.server_process.terminate()
            self.start_room_button.configure(state="disabled")
            self.server_status.set("Servidor encerrando...")
        else:
            self.server_status.set("Servidor dedicado: desligado")

    def shutdown(self):
        if self.server_process is not None and self.server_process.poll() is None:
            if not messagebox.askyesno("Encerrar servidor","Fechar o launcher também encerrará a sala dedicada. Continuar?"):
                return
            self.server_process.terminate()
        self.persist()
        self.destroy()

    def watch_game(self):
        if self.active_process is None:
            return
        rc=self.active_process.poll()
        if rc is None:
            self.after(900,self.watch_game)
            return
        self.active_process=None
        mode=self.active_mode
        logfile=self.active_log
        self.active_mode=None
        self.active_log=None
        self.deiconify()
        self.lift()
        if rc==0:
            self.status.set("Jogo encerrado normalmente. Seu perfil continua selecionado.")
        else:
            self.status.set(f"O jogo terminou com erro ({rc}). Consulte os logs.")
            messagebox.showwarning("Diagnóstico da execução",
               f"O Emerald terminou com código {rc}.\n"
               f"Confira o perfil e os logs em:\n{self.root_dir.parent / 'logs'}\n"
               "Ative 'Diagnóstico opcional' para ver mensagens de console.")
        self.persist()

    def new_profile(self):
        if not self.cli.is_file():
            messagebox.showerror("Arquivo necessário","emerald_profilectl.exe precisa estar ao lado do launcher.")
            return
        modal=tk.Toplevel(self);modal.title("Criar conta local");modal.geometry("470x300")
        modal.transient(self);modal.grab_set();modal.configure(bg=PANEL)
        self.text(modal,"CRIAR PERFIL LOCAL",17,GREEN,True).pack(anchor="w",padx=24,pady=(24,13))
        self.text(modal,"Seu apelido (o Trainer ID original não muda):",10).pack(anchor="w",padx=24)
        name=tk.StringVar()
        entry=tk.Entry(modal,textvariable=name,bg="#264739",fg=WHITE,insertbackground=WHITE,font=("Segoe UI",12),relief="flat")
        entry.pack(fill="x",padx=24,pady=(7,13),ipady=6);entry.focus_set()
        def create(import_save):
            try:
                nickname=validate_nickname(name.get())
                save=None
                if import_save:
                    save=filedialog.askopenfilename(parent=modal,filetypes=[("Emerald Save","*.sav"),("Todos","*.*")])
                    if not save:return
                self.root_dir.mkdir(parents=True,exist_ok=True)
                pid="profile_"+secrets.token_hex(6)
                argv=[str(self.cli),"import" if import_save else "new",str(self.root_dir),pid]
                if save:argv.append(save)
                proc=subprocess.run(argv,cwd=str(application_dir()),capture_output=True,text=True,timeout=45,
                                    creationflags=getattr(subprocess,"CREATE_NO_WINDOW",0))
                if proc.returncode:raise RuntimeError("O save não foi importado.\n"+(proc.stderr or proc.stdout)[:350])
                write_nickname(self.root_dir/pid,nickname)
                modal.destroy();self.selected=pid
                self.status.set("Perfil ativo: "+nickname);self.refresh();self.persist()
            except (OSError,ValueError,RuntimeError,subprocess.TimeoutExpired) as err:
                messagebox.showerror("Não foi possível criar",str(err),parent=modal)
        self.btn(modal,"Começar do zero",lambda:create(False),accent=True).pack(fill="x",padx=24,pady=5)
        self.btn(modal,"Importar meu save .sav",lambda:create(True)).pack(fill="x",padx=24,pady=5)

    def play(self,mode):
        if self.active_process is not None and self.active_process.poll() is None:
            messagebox.showinfo("Jogo em execução","O Emerald já está aberto. Feche-o antes de iniciar outra partida.")
            return
        if self.selected is None:
            messagebox.showwarning("Falta um perfil","Crie ou selecione uma conta local primeiro.");return
        if not self.game.is_file():
            messagebox.showerror("Jogo não encontrado","Coloque pokeemerald.exe ao lado do launcher.");return
        if not (self.root_dir/self.selected/"pokeemerald.sav").is_file():
            messagebox.showerror("Save não encontrado","O arquivo de save deste perfil não existe.");return
        try:
            host=self.ip.get().strip()
            if mode=="dedicated" and not host and self.server_process is not None and self.server_process.poll() is None:
                host="127.0.0.1"
            args=make_command(self.game,self.root_dir,self.selected,mode,host,self.port.get(),self.pin.get())
            self.persist()
            logs=self.root_dir.parent/"logs"
            logs.mkdir(parents=True,exist_ok=True)
            if mode!="offline":
                # The older P2P link uses an independent --lan-log file.
                pos=args.index("--lan-log")
                args[pos+1]=str(logs/("host-lan.log" if mode=="host" else
                                     "cliente-ehl8.log" if mode=="dedicated" else "cliente-lan.log"))
            flags=0
            if sys.platform=="win32":
                flags=(getattr(subprocess,"CREATE_NEW_CONSOLE",0) if self.diagnostics.get()
                       else getattr(subprocess,"CREATE_NO_WINDOW",0))
            if self.diagnostics.get():
                p=subprocess.Popen(args,cwd=str(application_dir()),creationflags=flags,
                                   stdin=subprocess.PIPE if mode=="dedicated" else subprocess.DEVNULL)
            else:
                # ReadFlash normally prints huge amounts of debug lines. Avoid
                # spawning a console or growing a multi-gigabyte stdout log.
                # Keep stderr (startup and crash diagnostics) in a dated file.
                diag=logs/("jogo-"+datetime.now().strftime("%Y%m%d-%H%M%S")
                           +"-"+secrets.token_hex(3)+".log")
                with diag.open("wb") as errfile:
                    p=subprocess.Popen(args,cwd=str(application_dir()),creationflags=flags,
                                       stdin=subprocess.PIPE if mode=="dedicated" else subprocess.DEVNULL,
                                       stdout=subprocess.DEVNULL,stderr=errfile)
            if mode=="dedicated":
                # Never place a LAN room PIN in argv, persisted settings or logs.
                deliver_pin_or_terminate(p, self.pin.get())
            self.active_process=p
            self.active_mode=mode
            self.active_log=logs
            self.status.set("Emerald em execução. O launcher acompanha o processo em segundo plano.")
            self.iconify()
            self.after(900,self.watch_game)
        except (OSError,ValueError) as err:messagebox.showerror("Falha ao iniciar",str(err))

def main():
    if "--self-test" in sys.argv:
        assert validate_port("45680")==45680
        assert make_command("pokeemerald.exe","profiles","trainer","host")[-1]=="--lan-host=45680"
        print("PASS: launcher offline/host/join command tests");return
    EmeraldLauncher().mainloop()

if __name__=="__main__":main()
