# Tests never start the executable, access the network, edit the firewall or write saves.
Set-StrictMode -Version Latest
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$launcher = Join-Path $repo 'INICIAR_EMERALD_VPN.ps1'
$tokens = $null
$errors = $null
[void][System.Management.Automation.Language.Parser]::ParseFile($launcher,[ref]$tokens,[ref]$errors)
if ($errors.Count -ne 0) {
    $errors | ForEach-Object { Write-Host $_.Message }
    throw 'PowerShell launcher has parser errors.'
}
function Assert-Run([string[]]$Arguments, [bool]$ShouldSucceed, [string]$Expected) {
    $output = & powershell.exe -NoLogo -NoProfile -ExecutionPolicy Bypass -File $launcher @Arguments 2>&1
    $status = $LASTEXITCODE
    $result = ($output | Out-String)
    if ((($status -eq 0) -ne $ShouldSucceed)) {
        throw "Unexpected exit code $status for $($Arguments -join ' '): $result"
    }
    if ($Expected -and -not $result.Contains($Expected)) {
        throw "Missing expected text '$Expected' for $($Arguments -join ' '): $result"
    }
}
Assert-Run @('-Mode','Offline','-DryRun') $true 'pokeemerald.exe'
Assert-Run @('-Mode','Host','-Port','45680','-DryRun') $true '--lan-host=45680'
Assert-Run @('-Mode','Join','-Address','100.101.102.103','-Port','45680','-DryRun') $true '--lan-client=100.101.102.103:45680'
Assert-Run @('-Mode','Join','-Address','127.0.0.1','-Port','65534','-DryRun') $true '--lan-client=127.0.0.1:65534'
Assert-Run @('-Mode','Check','-Address','100.101.102.103','-Port','45680','-DryRun') $true '45681'
Assert-Run @('-Mode','Host','-Port','65535','-DryRun') $false 'Porta invalida'
Assert-Run @('-Mode','Host','-Port','0','-DryRun') $false 'Porta invalida'
Assert-Run @('-Mode','Join','-Address','example.com','-Port','45680','-DryRun') $false 'IPv4'
Assert-Run @('-Mode','Join','-Address','100.999.2.3','-Port','45680','-DryRun') $false 'IPv4'
Assert-Run @('-Mode','Join','-Address','0.0.0.0','-Port','45680','-DryRun') $false 'IPv4'
Assert-Run @('-Mode','Join','-Address','255.255.255.255','-Port','45680','-DryRun') $false 'IPv4'
Write-Host 'Passed: PowerShell parser + 11 standalone launch checks; no game, network or saves touched.'
