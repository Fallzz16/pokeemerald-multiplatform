# Emerald Hybrid — Lobby dedicado v0.8.4 (prévia Windows)

**Esta versão ainda é experimental.** Sua versão v0.8.2, que já funcionou, deve continuar instalada e guardada. **Não sobrescreva os saves originais.**

## O que mudou

O launcher agora pode mostrar os participantes **de verdade** da sala hospedada, em vez de chamar um servidor de "ativo" só porque o programa abriu. No painel aparecem `Lobby aguardando · 1/2 conectados`, os IDs dos perfis e o estado Pronto. Quando dois participantes estão prontos, muda para `Em jogo · 2/2 conectados`.

O indicador funciona apenas para o **servidor iniciado neste mesmo launcher/PC**, por meio de um arquivo de status **local**, sem PIN, IP ou conteúdo dos saves. Não é ainda um lobby gráfico com todas as funções administrativas e convites.

## Como testar sem prejudicar sua instalação

1. Instale **esta prévia** ou extraia o ZIP completo em uma **pasta nova**. Não use apenas o EXE do launcher.
2. Abra o launcher e confira que o perfil experimental está separado do jogo anterior. Crie perfis novos ou **importe cópias** dos seus saves. O servidor não recebe nem armazena .sav.
3. No PC que hospedará a sala, informe uma porta (padrão **45680**) e um PIN de **seis números**. Clique em **Iniciar servidor dedicado**. Confirme que aparece `Lobby aguardando · 0/2 conectados` e não só “processo ativo”.
4. Em cada um dos dois clientes, escolha seu **próprio** perfil; marque **Entrar via servidor dedicado EHL8**, informe IPv4 **privado** do servidor, mesma porta e PIN, depois **Jogar com amigos**.
5. Verifique se o host exibe `1/2` e depois `2/2`, e se a sala muda para `Em jogo`. Dentro do Emerald, tentem ficar no mesmo mapa, andar, sair/reentrar no enquadramento e trocar de rota.
6. Cada jogador salva **localmente**. Fechem, reabram, confirmem que o progresso de cada perfil não se misturou. Façam o teste inicial com cópias, não com únicos saves pessoais.
7. Se houver erro, abra a pasta de logs pelo launcher, preserve os registros, remova PINs/IPs privados antes de compartilhá-los.

## Limitações IMPORTANTES

- **Duas pessoas apenas** nesta etapa; três/quatro ainda precisam de integração e testes.
- O EHL8 hoje sincroniza **presença no mundo**, não batalhas/trocas. Para Cable Club use modo P2P antigo, separado do servidor dedicado.
- Reconexão automática com reserva de vaga por 60 segundos, chat, convites, controle de expulsão e administração completa do lobby **ainda não foram implementados**.
- Acesso ao servidor exige **LAN privada** ou VPN confiável (ex.: Tailscale). **Não encaminhe portas públicas do roteador.** PIN LAN não é criptografia.
- Os resultados de build/CI não comprovam qualidade visual em dois Emeralds rodando no seu computador; precisamos da sua confirmação.

## Quando pedir ajuda

Diga qual modalidade usou (instalador ou ZIP), se o host mostrou `0/2 → 1/2 → 2/2`, se a troca de mapa funcionou, se houve desconexões e se ambos os saves continuaram intactos. Se possível, uma captura com o lobby e os dois personagens facilita o QA.

**Rollback:** manter a v0.8.2 funcional em sua pasta/instalação própria; nunca excluir as pastas `profiles` sem backup. O instalador experimental é separado e desinstalá-lo deve preservar saves experimentais.
