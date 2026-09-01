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
if ($Reset) { & docker compose @compose down --volumes --remove-orphans }
& docker compose @compose up --detach --build db pbx
for ($attempt = 0; $attempt -lt 60; $attempt++) {
  & docker compose @compose exec -T pbx bash -lc "asterisk -rx 'core show uptime'" 2>$null
  if ($LASTEXITCODE -eq 0) { break }
  Start-Sleep -Seconds 2
}
if ($LASTEXITCODE -ne 0) { throw 'Asterisk did not become ready.' }
& docker compose @compose exec -T pbx bash -lc "test -f /etc/freepbx.conf"
$wasInstalled = $LASTEXITCODE -eq 0
if (-not $wasInstalled) {
  & docker compose @compose exec -T pbx bash -lc "cd /usr/local/src/freepbx && php install -n --dbuser=freepbxuser --dbpass=freepbx-lab-password --dbhost=db"
}
& docker compose @compose exec -T pbx fwconsole reload
& docker compose @compose up --detach --build transcriber
& docker compose @compose ps
