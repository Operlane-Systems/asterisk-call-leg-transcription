[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$EnvFile,

    [ValidateRange(0, 120)]
    [int]$DelaySeconds = 10
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
    $PSNativeCommandUseErrorActionPreference = $false
}

try {
    Clear-Host
}
catch {
    # A recording terminal has a screen buffer; non-interactive validation does not.
}
Write-Host 'Preparing live Asterisk call-leg transcription demo...' -ForegroundColor Cyan
Start-Sleep -Seconds $DelaySeconds

Set-Location (Split-Path -Parent (Split-Path -Parent $PSScriptRoot))
& '.\docker\e2e\demo.ps1' -EnvFile $EnvFile

if ($LASTEXITCODE -ne 0) {
    exit $LASTEXITCODE
}

Write-Host ''
Write-Host 'Demo complete. Recording can stop now.' -ForegroundColor Green
Start-Sleep -Seconds 8
