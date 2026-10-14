# Instruções para qualquer IA que editar este repositório

**Antes de planejar, analisar ou modificar arquivos, leia integralmente:**
1. [AI_README.md](AI_README.md) — histórico, decisões do usuário, estrutura, riscos, ferramentas, QA e instruções de passagem de contexto.
2. [docs/LAN_V080_ARCHITECTURE.md](docs/LAN_V080_ARCHITECTURE.md) — requisitos aprovados 1–50, arquitetura v0.8 planejada, saves, servidor, protocolo e matriz de testes.
3. Documentos de QA relacionados à branch atual: `LAN_V071_QA.md`, `LAN_V0721_CAMERA_CULLING_QA.md`.

**Regras:**
- Confirme a branch/HEAD; não confunda planejamento e implementação, nem testes automáticos com gameplay.
- Preserve rigorosamente os saves, a versão anterior que funciona, batalha/troca Cable Club, sprites GBA, PokéNav, Quest UI, turbo e melhorias Hybrid.
- O usuário exige um resumo explícito do que foi adicionado, modificado, removido, testado e ainda NÃO implementado em cada atualização.
- Cada incremento deve **atualizar o AI_README.md**, com branch+commit, estado, resultados reais de build/QA, decisões, riscos, rollback, caminhos, mudanças e próximos passos. Atualizar a especificação quando mudar o protocolo ou decisões.
- Não criar ou recomendar arquivos `.sav` artificiais obtidos por adulteração de offsets do mapa; versões anteriores causaram problemas gráficos.
- Não dar por implementadas funções do servidor dedicado/até 4 jogadores: no início deste planejamento, o código é P2P para 2 jogadores.
- Para funcionalidades novas, priorizar soluções simples e reutilizar infra que já funciona; antes de mexer em gameplay, construir testes reproduzíveis.
- Em falta de contexto, retomar do último commit verificável, nunca supor recursos não presentes ou sobrescrever código/saves.
- Responder em português brasileiro para este projeto.
