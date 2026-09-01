param(
  [string]$EnvFile = '.env.e2e',
  [string]$ExpectedTranscript
)

$ErrorActionPreference = 'Stop'
if (Get-Variable -Name PSNativeCommandUseErrorActionPreference -ErrorAction SilentlyContinue) {
  $PSNativeCommandUseErrorActionPreference = $false
}
if (-not (Test-Path $EnvFile)) { throw "Environment file not found: $EnvFile" }
if (-not $ExpectedTranscript) {
  $configuredExpected = (Get-Content $EnvFile | Where-Object { $_ -match '^EXPECTED_TRANSCRIPT=' } | Select-Object -First 1)
  $ExpectedTranscript = if ($configuredExpected) { ($configuredExpected -split '=', 2)[1] } else { 'one two three four five' }
}
$compose = @('-f', 'docker-compose.e2e.yml', '--env-file', $EnvFile)
& "$PSScriptRoot\bootstrap.ps1" -EnvFile $EnvFile
& docker compose @compose exec -T transcriber sh -lc 'rm -f /artifacts/transcript.jsonl'
& docker compose @compose --profile test run --build --rm caller
if ($LASTEXITCODE -ne 0) { throw 'SIP caller failed.' }
$actual = ''
for ($attempt = 0; $attempt -lt 12; $attempt++) {
  $artifact = & docker compose @compose exec -T transcriber sh -lc 'cat /artifacts/transcript.jsonl 2>/dev/null || true'
  $completed = if ($artifact) { $artifact | ConvertFrom-Json | Where-Object { $_.speaker -eq 'caller' -and $_.type -eq 'completed' -and $_.text } }
  $actual = ($completed | ForEach-Object { $_.text }) -join ' '
  if ($actual) { break }
  Start-Sleep -Seconds 2
}
$normal = { param($text) (($text.ToLower() -replace '[^a-z0-9]+', ' ').Trim() -replace '\s+', ' ') }
$expectedTokens = (& $normal $ExpectedTranscript).Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries) | Select-Object -Unique
$actualTokens = (& $normal $actual).Split(' ', [System.StringSplitOptions]::RemoveEmptyEntries)
$matchedTokens = @($expectedTokens | Where-Object { $actualTokens -contains $_ }).Count
$minimumMatches = [Math]::Min(3, $expectedTokens.Count)
if (-not $actual -or $matchedTokens -lt $minimumMatches) {
  throw "Expected transcript was not sufficiently observed ($matchedTokens/$($expectedTokens.Count) tokens). Completed transcript: $actual"
}
Write-Host 'E2E PASS: OpenAI STT received and labelled the SIP caller audio.'
