param(
  [string]$EnvFile = '.env.e2e',
  [string]$ExpectedTranscript
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}

function Write-Banner([string]$Text) {
  Write-Host ''
  Write-Host ('=' * 76) -ForegroundColor DarkCyan
  Write-Host ("  " + $Text) -ForegroundColor Cyan
  Write-Host ('=' * 76) -ForegroundColor DarkCyan
}

function Write-Check([string]$Text) {
  Write-Host ("  [OK] " + $Text) -ForegroundColor Green
}

if (-not (Test-Path $EnvFile)) { throw "Environment file not found: $EnvFile" }
if (-not $ExpectedTranscript) {
  $configuredExpected = Get-Content $EnvFile | Where-Object { $_ -match '^EXPECTED_TRANSCRIPT=' } | Select-Object -First 1
  $ExpectedTranscript = if ($configuredExpected) { ($configuredExpected -split '=', 2)[1] } else { 'one two three four five' }
}

Write-Banner 'ASTERISK CALL-LEG TRANSCRIPTION  |  LIVE PBX DEMO'
Write-Host '  Speaker attribution comes from the PBX media topology -- not diarization.' -ForegroundColor Gray
Write-Host ''
Write-Host '  PJSIP caller channel' -ForegroundColor Yellow
Write-Host '        |  spy=in' -ForegroundColor DarkGray
Write-Host '        v' -ForegroundColor DarkGray
Write-Host '  ARI Snoop  -->  External Media (ulaw RTP)  -->  OpenAI Realtime STT' -ForegroundColor Cyan
Write-Host '        |                                           |' -ForegroundColor DarkGray
Write-Host '        +---------- label: caller ------------------+' -ForegroundColor Magenta

Write-Banner 'RUNNING THE ISOLATED FREEPBX / ASTERISK E2E CALL'
$runOutput = @(& "$PSScriptRoot\run-e2e.ps1" -EnvFile $EnvFile -ExpectedTranscript $ExpectedTranscript 2>&1)
if ($LASTEXITCODE -ne 0) {
  $runOutput | Out-Host
  throw 'The E2E call did not complete successfully.'
}

$compose = @('-f', 'docker-compose.e2e.yml', '--env-file', $EnvFile)
function Invoke-DockerCompose {
  param([Parameter(ValueFromRemainingArguments = $true)][string[]]$ComposeArguments)

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

$artifact = Invoke-DockerCompose exec -T transcriber sh -lc 'cat /artifacts/transcript.jsonl'
$events = @($artifact | ConvertFrom-Json | Where-Object { $_.speaker -eq 'caller' })
$completed = @($events | Where-Object { $_.type -eq 'completed' -and $_.text } | Select-Object -Last 1)
if (-not $completed) { throw 'The E2E call passed but did not leave a caller completion event.' }

Write-Check 'FreePBX and Asterisk accepted the SIP call'
Write-Check 'ARI created an isolated caller-leg Snoop + External Media path'
Write-Check 'OpenAI Realtime received caller RTP and emitted labelled events'

Write-Banner 'CAPTURED LIVE TRANSCRIPT EVENTS'
$deltas = @($events | Where-Object { $_.type -eq 'delta' -and $_.text })
if ($deltas) {
  Write-Host '  caller  > ' -ForegroundColor DarkGray -NoNewline
  foreach ($event in $deltas) {
    Write-Host $event.text -ForegroundColor DarkGray -NoNewline
  }
  Write-Host ''
}
Write-Host ("  caller  > " + $completed[0].text) -ForegroundColor Green

Write-Banner 'RESULT'
Write-Host '  PASS  Caller audio was transcribed through its own PBX-controlled media leg.' -ForegroundColor Green
Write-Host '  PASS  The transcript is labelled caller because the PBX supplied the identity.' -ForegroundColor Green
Write-Host '  Demo complete. No public SIP, RTP, or PBX management ports were exposed.' -ForegroundColor Gray
