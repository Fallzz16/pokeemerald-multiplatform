# Emerald Hybrid v0.8.2 — instalação Windows (distribuição corrigida)

> **Status experimental; não incluir saves de usuário no instalador.** Esta entrega existe porque os links de sandbox do ChatGPT não baixaram corretamente para o usuário e porque ele queria INSTALAR, mas as versões anteriores eram arquivos ZIP portáteis.

## Duas opções claras na MESMA entrega do GitHub

O workflow `.github/workflows/package-v0802-complete.yml` baixa **binários já compilados e testados** nos runs GitHub Actions e **confere os hashes SHA256** antes de publicar um único artifact denominado `BAIXAR_AQUI_Emerald_v0802_INSTALADOR_e_PORTATIL_COMPLETOS`. Depois de clicar para baixar esse artifact, o usuário deve **extrair uma vez o ZIP externo do GitHub**, para encontrar:

- `Emerald_Hybrid_v0802_INSTALADOR_Windows.exe` — instalador NSIS verdadeiro, independente de Python, instalação por usuário em `%LOCALAPPDATA%\Programs\EmeraldHybrid`, atalho no menu Iniciar, desinstalador. **NÃO** inclui marcador PORTABLE_MODE, portanto o save/perfis ficam em `%LOCALAPPDATA%\EmeraldHybrid\profiles` fora da pasta instalada.
- `Emerald_Hybrid_v0802_PORTATIL_Windows.zip` — versão sem instalação: extrair o ZIP interno numa pasta nova e executar `ABRIR_LAUNCHER.bat`, que checa os quatro executáveis/dll antes de abrir a GUI. Usa `PORTABLE_MODE.txt` e `profiles/` na própria pasta extraída. Não executar arquivos diretamente do ZIP sem extrair.

**Nunca só `EmeraldLauncher.exe` avulso:** isso causou erro real de `emerald_profilectl.exe precisa estar ao lado do launcher`.

### Origem de cada executável (todos conferidos por hash)

- Windows GUI `EmeraldLauncher.exe`: run `38522309384`, artifact `11874218835`. SHA256 `3e2b7a885a22c075d04b87d97b4dab05cee68098375e692e30f47f7c2bdcc239`.
- Jogo `pokeemerald.exe` + SDL2.dll: run `38522309182`, artifact `11874860082`. SHA256 jogo `2e00b3099a47f7fe5e49a886885a7847b781159e0a00159cdfbe111b2229b2d7`; SDL2 `eb323e920739ff48f72b28cd20f0cf6a58507bff852cbf1bacb4fb6fa07d1a3d`.
- `emerald_profilectl.exe` perfis: run `38522309249`, artifact `11873839627`. SHA256 `09a865bc08bed2d5d7673114db1f381a5a12ce2df260c89ae7e9bc0fe6d52679`.

O workflow falha se qualquer executável faltar, tiver hash diferente ou se encontrar `.sav` nos arquivos baixados.

## Instruções ao usuário

1. Entre no **GitHub → Pull Request #9 → Checks** e abra a execução `Emerald Hybrid v0.8.2 COMPLETO - Instalador e Portatil` concluída com sucesso. Alternativamente abra a página Actions do workflow na branch `feature/lan-v080-mega-desktop-polish`. Não inventar link para run antes de conferir o run real.
2. Na seção **Artifacts**, baixe `BAIXAR_AQUI_Emerald_v0802_INSTALADOR_e_PORTATIL_COMPLETOS`. Alguns artefatos exigem login no GitHub do dono do repositório.
3. Extraia esse primeiro download. Escolha **Instalador.exe** (duplo clique) OU o ZIP portátil (extrair tudo e abrir `ABRIR_LAUNCHER.bat`).
4. Faça backup do save anterior antes de importar ou testar; a v0.7.2.1 aprovada permanece em sua pasta antiga.

## Segurança e limites

- O instalador é **não assinado**, e o Windows SmartScreen/antivírus pode avisar. Não recomendar desabilitar proteções. Confirmar origem e hash em `AI_README.md` e revisar o arquivo, se houver bloqueio.
- O instalador NSIS é por usuário (`RequestExecutionLevel user`) e registra desinstalação apenas em HKCU. Não solicita privilégios de administrador.
- A desinstalação apaga apenas executáveis/arquivos conhecidos sob a pasta instalada; **preserva** perfis e logs em `%LOCALAPPDATA%\EmeraldHybrid\`. O instalador não migra automaticamente os perfis portáteis existentes; importar cópias via launcher.
- O servidor dedicado, lobby até 4 jogadores e login online permanecem **não implementados**. Build/teste automatizado não garante funcionamento com saves reais de usuário.
- Publicar para o usuário só depois da conclusão com sucesso do workflow de distribuição; se falhar, registrar e corrigir primeiro.

## Continuidade técnica para outras IAs

- Branch `feature/lan-v080-mega-desktop-polish`, PR #9.
- **Adicionado:** `packaging/emerald_hybrid_setup.nsi`, `.github/workflows/package-v0802-complete.yml`, este guia.
- **Modificado gameplay:** nada por esta etapa de empacotamento; cores, áudio, link LAN, save e SDL são exatamente os binários já aprovados em compilação.
- **Removido:** nada.
- **QA:** conferir hash e CRC, compilação NSIS, ZIP portátil, artefato duplo, uninstall preservando arquivos de perfil; validação de instalação em Windows real ainda depende de usuário.
- **Rollback:** voltar à pasta da v0.7.2.1 já aprovada. Nunca apagar `profiles`/saves sem cópia.
