# Emerald Hybrid LAN v0.7.2.2 — conexão por VPN (candidato)

Este pacote usa o **multiplayer P2P para 2 jogadores da v0.7.2.1**, aprovado pelo usuário na mesma LAN. **Não é um servidor dedicado**, não é modo online público e **a conexão entre duas redes diferentes ainda precisa de teste real**. A VPN é fornecida por aplicativo externo (por exemplo, Tailscale) e não foi integrada ao Emerald.

## Arquivos

- `pokeemerald.exe` e `SDL2.dll`: jogo experimental original da branch funcional v0.7.2.1, **sem recompilar o jogo e sem modificar o formato dos saves**.
- `INICIAR_EMERALD_VPN.bat` / `.ps1`: menu rápido Windows (Offline, Host, Entrar, Diagnosticar) com validação de IP e porta.
- `LAN_V0722_REMOTE_VPN_QA.md`: checklist de testes e resolução de falhas.
- `AI_README_REMOTE_VPN.md`: passagem de contexto técnica obrigatória para próximas IAs.

## Como usar — Windows x Windows, redes diferentes

1. Em cada PC, instale/ative o Tailscale usando uma conta própria. O administrador pode compartilhar apenas a máquina host com a conta do amigo (sem emprestar credenciais). Fonte: https://tailscale.com/kb/1084/sharing
2. Confirme que os dois têm permissão para conversar na rede virtual. O host obtém **seu IPv4 Tailscale**, normalmente `100.x.y.z`, via aplicativo ou `tailscale ip -4`. Fonte: https://tailscale.com/docs/reference/tailscale-cli
3. Copie este pacote para **uma pasta separada em cada PC**, sem substituir saves de uma instalação antiga. Se desejar continuar seu progresso, faça primeiro um backup e copie **seu próprio** `pokeemerald.sav` para a pasta correspondente. Não compartilhe seu save com o outro jogador.
4. No host, execute `INICIAR_EMERALD_VPN.bat`, escolha **2 Hospedar**, aceite a porta padrão `45680` e deixe o Emerald aberto. A rede privada precisa permitir TCP `45680` (Cable Club) e TCP `45681` (personagem remoto).
5. No PC do amigo, abra o mesmo iniciador, escolha **4 Diagnosticar** e informe o IPv4 Tailscale do host. Em seguida escolha **3 Entrar** com o mesmo IP e porta. Se o diagnóstico falhar, confira VPN, IP, acesso à máquina compartilhada e regras restritas de firewall.
6. Coloque os dois treinadores no mesmo mapa acessível a ambos e confirme presença e movimento. Para troca ou batalha, sigam o Cable Club original dentro do Emerald, mas **usem só cópias dos saves até a confiabilidade remota ser medida**.
7. Após terminar, fechem normalmente, façam backup dos arquivos `.sav` e compartilhem *apenas logs sem dados privados* (`host-vpn.log` e `cliente-vpn.log`) se houver erro.

**Não precisa configurar port forwarding/DMZ/UPnP no roteador**, nem abrir as portas para toda a Internet. O protocolo P2P antigo não oferece TLS, PIN, contas ou autenticação adequada para uma porta pública. O acesso deve ficar restrito a dispositivos confiáveis da VPN.

## Modos e portas

`INICIAR_EMERALD_VPN.bat`: apresenta menu de texto para as três formas de iniciar o jogo mais diagnóstico.

Para automação manual, a versão PowerShell aceita:

```powershell
.\INICIAR_EMERALD_VPN.ps1 -Mode Offline
.\INICIAR_EMERALD_VPN.ps1 -Mode Host -Port 45680
.\INICIAR_EMERALD_VPN.ps1 -Mode Join -Address 100.101.102.103 -Port 45680
.\INICIAR_EMERALD_VPN.ps1 -Mode Check -Address 100.101.102.103 -Port 45680
```

Sem PowerShell, comandos originais:

```bat
pokeemerald.exe --lan-log host-vpn.log --lan-host=45680
pokeemerald.exe --lan-log cliente-vpn.log --lan-client=100.101.102.103:45680
```

`100.101.102.103` é **exemplo**, não seu IP real. O launcher só aceita IPv4 literal e portas de 1 a 65534, pois a porta secundária é sempre `base + 1`. IPv6/hostname Tailscale não são compatíveis com o transporte atual.

### Dúvidas frequentes

- **Meu amigo aparece fora da câmera?** Não: v0.7.2.1 usa culling para desenhar o sprite somente no enquadramento; a posição continua sendo enviada mesmo fora de cena.
- **Pode ter quatro jogadores?** Não. Esta etapa é para dois. O servidor dedicado de até quatro participantes é trabalho independente da v0.8.
- **Funciona sem Tailscale?** Sim na mesma LAN. Outras VPNs privadas com IPv4 roteável também podem funcionar; não foi testado automaticamente.
- **Funciona Android?** O binário Windows desta entrega não é APK. O APK Android existente já tem networking LAN, mas sua interface de conexão remota e os parâmetros do launcher ainda precisam de validação específica. Não prometer Android↔Windows sobre VPN nesta entrega.
- **O que não foi testado?** Duas operadoras/ISPs, relés VPN, jitter, Cable Club sob latência, queda de rede e recuperação. Veja o checklist.

## Status honesto

- **Confirmado pelo usuário:** Windows/duas instâncias via LAN e personagem remoto da v0.7.2.1.
- **Confirmado por inspeção de código:** host usa `INADDR_ANY` IPv4, cliente valida IPv4 via `inet_pton`, porta do jogo + porta `+1` para presença.
- **A validar:** VPN real com um jogador em cada rede; batalhas, trocas e saves sem corrupção.
- **Não implementado:** conta, matchmaking, hospedagem pública, NAT traversal embutido, autenticação, servidor dedicado, quatro jogadores, launcher moderno v0.8.
