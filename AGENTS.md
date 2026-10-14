# Instruções para qualquer IA que editar este repositório

**Antes de planejar, analisar ou modificar arquivos, leia integralmente:**
1. [AI_README.md](AI_README.md) — histórico, decisões do usuário, estrutura, riscos, ferramentas, QA e instruções de passagem de contexto.
2. [docs/LAN_V080_ARCHITECTURE.md](docs/LAN_V080_ARCHITECTURE.md) — requisitos aprovados 1–116 (as 16 últimas em docs/LAN_V080_MEGA_DESKTOP_PASS1.md), arquitetura v0.8 planejada, saves, servidor, protocolo e matriz de testes.
3. Documentos de QA relacionados à branch atual: `LAN_V071_QA.md`, `LAN_V0721_CAMERA_CULLING_QA.md`.

**Regras:**
- Confirme a branch/HEAD; não confunda planejamento e implementação, nem testes automáticos com gameplay.
- Preserve rigorosamente os saves, a versão anterior que funciona, batalha/troca Cable Club, sprites GBA, PokéNav, Quest UI, turbo e melhorias Hybrid.
- Respostas recentes vieram numeradas 1–25 em duas rodadas: a primeira corresponde a **51–75**, a mais recente corresponde a **76–100**. O catálogo definitivo de todas as 100 escolhas está na especificação; **não sobrescrever escolhas históricas**.
- O usuário exige um resumo explícito do que foi adicionado, modificado, removido, testado e ainda NÃO implementado em cada atualização.
- Cada incremento deve **atualizar o AI_README.md**, com branch+commit, estado, resultados reais de build/QA, decisões, riscos, rollback, caminhos, mudanças e próximos passos. Atualizar a especificação quando mudar o protocolo ou decisões.
- Não criar ou recomendar arquivos `.sav` artificiais obtidos por adulteração de offsets do mapa; versões anteriores causaram problemas gráficos.
- Não dar por implementadas funções do servidor dedicado/até 4 jogadores: na base funcional aprovada v0.7.2.1, o código é P2P para 2 jogadores. O primeiro marco v0.8 aprovado (#100A) exige servidor dedicado + lobby + perfis com **2 jogadores**; **4** são etapa posterior.
- Para funcionalidades novas, priorizar soluções simples e reutilizar infra que já funciona; antes de mexer em gameplay, construir testes reproduzíveis.
- Em falta de contexto, retomar do último commit verificável, nunca supor recursos não presentes ou sobrescrever código/saves.
- Responder em português brasileiro para este projeto.

- As **100 decisões** foram concluídas: encerrar questionários amplos e avançar com M0/M1 em branch isolada. Ao surgir impedimento real, perguntar apenas o essencial; caso contrário manter as decisões existentes.

- As respostas 101–116 são `101B 102B 103B 104B 105C 106C 107B 108B 109C 110C 111C 112A 113B 114C 115A 116A`. Ver `docs/LAN_V080_MEGA_DESKTOP_PASS1.md` antes de interpretar cada opção. O primeiro incremento 0.8 MEGA só corrige desktop, logs, video e backup manual; não declarar servidor/4 players/instalador pronto.

- **Novo desenvolvimento M2 2026-10-14:** consultar `docs/LAN_V0803_DEDICATED_SESSION_CORE.md`. A ferramenta `tools/emerald_session_server.py` é um serviço EHL8 real para até 2 clientes de protocolo, **NÃO** um servidor de gameplay Emerald já integrado. O botão dedicado do launcher continua desabilitado, raw Cable Club v0.7.2.1 é incompatível sem adaptador EHL8 nativo. Atualizar `AI_README.md` com os CI runs e limitações de cada entrega. Não tocar nos saves originais.
