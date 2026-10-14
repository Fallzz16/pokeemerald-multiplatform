# Emerald Hybrid v0.7.2.2 — remote VPN launcher (Windows PowerShell 5.1+).
# This launches the *existing* 2-player P2P client/host; NOT a dedicated server.
# No firewall or router changes, no administrator rights and no third-party installs.
[CmdletBinding()]
param(
    [ValidateSet('Menu','Offline','Host','Join','Check')]
    [string]$Mode = 'Menu',
    [string]$Address = '',
    [int]$Port = 45680,
    [switch]$DryRun
)
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$game = Join-Path $PSScriptRoot 'pokeemerald.exe'

function Assert-Port([int]$Candidate) {
    if ($Candidate -lt 1 -or $Candidate -gt 65534) {
        throw 'Porta invalida: use 1 a 65534. O jogo tambem usa a porta seguinte para o outro treinador.'
    }
}
function Assert-IPv4([string]$Value) {
    if ($Value -notmatch '^\d{1,3}(\.\d{1,3}){3}$') {
        throw 'Informe apenas um endereco IPv4 numerico: exemplo 100.101.102.103.'
    }
    $parsed = $null
    if (-not [System.Net.IPAddress]::TryParse($Value, [ref]$parsed)) {
        throw 'Endereco IPv4 invalido.'
    }
    if ($parsed.AddressFamily -ne [System.Net.Sockets.AddressFamily]::InterNetwork -or
        $Value -eq '0.0.0.0' -or $Value -eq '255.255.255.255') {
        throw 'Endereco IPv4 indisponivel para conexao.'
    }
}
function Launch-Emerald([string[]]$Arguments) {
    if ($DryRun) {
        Write-Output ("TESTE (sem abrir o jogo): pokeemerald.exe " + ($Arguments -join ' '))
        return
    }
    if (-not (Test-Path -LiteralPath $game -PathType Leaf)) {
        throw "Nao encontrei pokeemerald.exe na pasta do launcher: $PSScriptRoot"
    }
    Write-Host ''
    Write-Host 'Abrindo Emerald Hybrid com seu save original desta pasta...' -ForegroundColor Green
    $start = @{
        FilePath = $game
        WorkingDirectory = $PSScriptRoot
        PassThru = $true
    }
    if ($Arguments.Count -gt 0) {
        $start.ArgumentList = $Arguments
    }
    $process = Start-Process @start
    Write-Host ("Iniciado. PID: " + $process.Id)
}
try {
    if ($Mode -eq 'Menu') {
        Write-Host ''
        Write-Host 'EMERALD HYBRID — CONEXAO LAN / VPN' -ForegroundColor Green
        Write-Host '1) Jogar offline'
        Write-Host '2) Hospedar e jogar (LAN ou VPN)'
        Write-Host '3) Entrar no jogo de um amigo (LAN ou VPN)'
        Write-Host '4) Diagnosticar portas TCP do host'
        Write-Host '0) Sair'
        $choice = Read-Host 'Escolha'
        switch ($choice) {
            '1' { $Mode = 'Offline' }
            '2' { $Mode = 'Host' }
            '3' { $Mode = 'Join' }
            '4' { $Mode = 'Check' }
            '0' { exit 0 }
            default { throw 'Opcao desconhecida. Use 0, 1, 2, 3 ou 4.' }
        }
        if ($Mode -ne 'Offline') {
            $portText = Read-Host 'Porta principal (ENTER para 45680)'
            if ($portText.Trim() -ne '') {
                $enteredPort = 0
                if (-not [int]::TryParse($portText.Trim(), [ref]$enteredPort)) {
                    throw 'Porta deve ser numerica.'
                }
                $Port = $enteredPort
            }
        }
        if ($Mode -eq 'Join' -or $Mode -eq 'Check') {
            $Address = (Read-Host 'IPv4 do host na VPN (ex.: 100.101.102.103)').Trim()
        }
    }
    if ($Mode -ne 'Offline') { Assert-Port $Port }
    switch ($Mode) {
        'Offline' {
            Launch-Emerald -Arguments @()
        }
        'Host' {
            Write-Host ("Portas de jogo: TCP $Port e TCP " + ($Port+1))
            Write-Host 'No Tailscale, procure seu IP de 100.x.y.z com: tailscale ip -4'
            Write-Host 'Nao configure encaminhamento dessas portas para a Internet publica.'
            Launch-Emerald -Arguments @('--lan-log','host-vpn.log',("--lan-host=$Port"))
        }
        'Join' {
            Assert-IPv4 $Address
            Write-Host ("Conectando a $Address na porta $Port (presenca: " + ($Port+1) + ').')
            Launch-Emerald -Arguments @('--lan-log','cliente-vpn.log',("--lan-client=${Address}:$Port"))
        }
        'Check' {
            Assert-IPv4 $Address
            if ($DryRun) {
                Write-Output "TESTE: verificaria TCP $Address : $Port e $($Port+1)"
            } else {
                $okMain = Test-NetConnection -ComputerName $Address -Port $Port -InformationLevel Quiet -WarningAction SilentlyContinue
                $okPresence = Test-NetConnection -ComputerName $Address -Port ($Port+1) -InformationLevel Quiet -WarningAction SilentlyContinue
                Write-Host ("Canal Cable Club TCP $Port : " + $(if ($okMain) {'ABERTO'} else {'SEM RESPOSTA'}))
                Write-Host ("Canal personagem TCP $($Port+1) : " + $(if ($okPresence) {'ABERTO'} else {'SEM RESPOSTA'}))
                if (-not ($okMain -and $okPresence)) {
                    throw 'Verifique se o host abriu o jogo, se a VPN conecta ambos e se o firewall permite as duas portas.'
                }
            }
        }
        default { throw 'Modo desconhecido.' }
    }
} catch {
    [Console]::Error.WriteLine("Erro no launcher: " + $_.Exception.Message)
    exit 1
}
