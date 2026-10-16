"""Windowed M2.2-A local-only EHL8 resume QA. No personal saves or public network."""
from __future__ import annotations
import io
import json
import os
from pathlib import Path
import queue
import secrets
import threading
from datetime import datetime
import tkinter as tk
from tkinter import messagebox
import unittest

import test_ehl8_resume_v1 as tests

BG, FG, PANEL, GREEN = "#091611", "#e6fff2", "#142c23", "#54daa7"


def report_root():
    home = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(home) / "EmeraldHybridV1QALab" / "reconnect"


def run_suite():
    output = io.StringIO()
    suite = unittest.defaultTestLoader.loadTestsFromModule(tests)
    result = unittest.TextTestRunner(stream=output, verbosity=2).run(suite)
    report = {
        "name": "EHL8 Resume M2.2-A",
        "scope": "Real TCP loopback against production Python server module",
        "real_windows_game_tested": False,
        "game_saves_read_or_modified": False,
        "server_listens_publicly": False,
        "tests_run": result.testsRun,
        "errors": len(result.errors),
        "failures": len(result.failures),
        "skipped": len(result.skipped),
        "passed": result.wasSuccessful(),
        "finished": datetime.now().isoformat(timespec="seconds"),
        "details": output.getvalue()[:20000],
    }
    target = report_root()
    target.mkdir(parents=True, exist_ok=True)
    filename = datetime.now().strftime("%Y%m%d-%H%M%S") + "-" + secrets.token_hex(4)
    path = target / ("resume-qa-" + filename + ".json")
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return report, path


def main():
    root = tk.Tk()
    root.title("Emerald Hybrid — Reconexão EHL8 M2.2-A")
    root.geometry("690x450")
    root.minsize(590, 390)
    root.configure(bg=BG)
    tk.Label(root, text="EMERALD HYBRID  /  RECONEXÃO M2.2-A", bg=BG, fg=GREEN,
             font=("Segoe UI", 18, "bold")).pack(anchor="w", padx=24, pady=(24, 8))
    description = (
        "Testa o servidor EHL8 REAL em localhost com dois clientes simulados.\n"
        "Valida token de 32 bytes, retomada de vaga, bloqueio, revogação e expiração.\n\n"
        "Não abre o jogo, não usa seus saves e não testa FPS ou reconexão\n"
        "automática dentro do Emerald. O recurso do jogo vem no M2.2-B.")
    tk.Label(root, text=description, bg=BG, fg=FG, justify="left",
             font=("Segoe UI", 10)).pack(anchor="w", padx=24, pady=(4, 14))
    state = tk.StringVar(value="Pronto. Nenhum teste executado.")
    status = tk.Label(root, textvariable=state, bg=PANEL, fg=GREEN, justify="left",
                      anchor="w", font=("Segoe UI", 11, "bold"), wraplength=600,
                      padx=15, pady=14)
    status.pack(fill="x", padx=24, pady=(8, 14))
    messages = queue.Queue()

    def worker():
        try:
            messages.put(("result", *run_suite()))
        except Exception as exc:
            messages.put(("error", str(exc)[:300]))

    def start():
        button.configure(state="disabled")
        state.set("Executando testes reais TCP em 127.0.0.1, aguarde...")
        threading.Thread(target=worker, daemon=True).start()

    def tick():
        try:
            item = messages.get_nowait()
        except queue.Empty:
            root.after(150, tick)
            return
        button.configure(state="normal")
        if item[0] == "error":
            state.set("ERRO: " + item[1])
            messagebox.showerror("Falha de execução", item[1], parent=root)
        else:
            report, path = item[1:]
            state.set(
                f"Testes: {report['tests_run']} | falhas: {report['failures']} | "
                f"erros: {report['errors']} | status: " +
                ("APROVADO" if report["passed"] else "NÃO APROVADO"))
            messagebox.showinfo("Resultado do M2.2-A",
                                f"Relatório salvo em:\n{path}\n\n"
                                "Envie esse JSON se houver problemas.", parent=root)
        root.after(150, tick)

    button = tk.Button(root, text="EXECUTAR TESTES DE RECONEXÃO", command=start,
                       font=("Segoe UI", 11, "bold"), bg="#236448", fg=FG,
                       activebackground=GREEN, padx=18, pady=13, relief="flat")
    button.pack(anchor="w", padx=24)
    tk.Label(root, text="Protegido: nenhuma porta pública, nenhum save e nenhum PIN em relatórios.",
             bg=BG, fg="#a5bfb0", font=("Segoe UI", 9)).pack(anchor="w", padx=24, pady=(16, 0))
    root.after(150, tick)
    root.mainloop()


if __name__ == "__main__":
    main()
