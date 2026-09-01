param(
  [switch]$Reset,
  [string]$EnvFile = '.env.e2e'
)

$ErrorActionPreference = 'Stop'
# Docker Compose reports ordinary progress on stderr.  PowerShell 7 can treat
# that stream as a terminating NativeCommandError when ErrorActionPreference is
# Stop, even when Docker returned success.
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}
if (-not (Test-Path $EnvFile)) { throw "Environment file not found: $EnvFile" }
$compose = @('-f', 'docker-compose.e2e.yml', '--env-file', $EnvFile)

function Invoke-DockerCompose {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ComposeArguments)

  # Docker Compose sends ordinary progress to stderr.  Windows PowerShell 5.1
  # turns that into NativeCommandError before stderr redirection can apply.
  # Silence native output during the call and use Docker's exit code instead.
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'SilentlyContinue'
    $output = @(& docker compose @compose @ComposeArguments)
    $exitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($exitCode -ne 0) {
    throw "docker compose $($ComposeArguments -join ' ') failed (exit code $exitCode)."
  }
  $output
}

if ($Reset) { Invoke-DockerCompose down --volumes --remove-orphans }
Invoke-DockerCompose up --detach --build db pbx
for ($attempt = 0; $attempt -lt 60; $attempt++) {
  $previousErrorActionPreference = $ErrorActionPreference
  try {
    $ErrorActionPreference = 'SilentlyContinue'
    & docker compose @compose exec -T pbx bash -lc "asterisk -rx 'core show uptime'" | Out-Null
    $asteriskExitCode = $LASTEXITCODE
  }
  finally {
    $ErrorActionPreference = $previousErrorActionPreference
  }
  if ($asteriskExitCode -eq 0) { break }
  Start-Sleep -Seconds 2
}
if ($asteriskExitCode -ne 0) { throw 'Asterisk did not become ready.' }
$previousErrorActionPreference = $ErrorActionPreference
try {
  $ErrorActionPreference = 'SilentlyContinue'
  & docker compose @compose exec -T pbx bash -lc "test -f /etc/freepbx.conf" | Out-Null
  $wasInstalled = $LASTEXITCODE -eq 0
}
finally {
  $ErrorActionPreference = $previousErrorActionPreference
}
if (-not $wasInstalled) {
  Invoke-DockerCompose exec -T pbx bash -lc "cd /usr/local/src/freepbx && php install -n --dbuser=freepbxuser --dbpass=freepbx-lab-password --dbhost=db"
}
Invoke-DockerCompose exec -T pbx fwconsole reload
Invoke-DockerCompose up --detach --build transcriber
Invoke-DockerCompose ps
