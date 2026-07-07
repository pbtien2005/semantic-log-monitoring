param(
  [string]$InputPath = "data/realtime_test/anomaly_candidate_logs.jsonl",
  [string]$Endpoint = "http://localhost:8501/api/ingest/logs",
  [int]$DelayMilliseconds = 250
)

$ErrorActionPreference = "Stop"
$resolvedPath = Resolve-Path -LiteralPath $InputPath
$sent = 0

Get-Content -LiteralPath $resolvedPath | ForEach-Object {
  $line = $_.Trim()
  if (-not $line) {
    return
  }

  $payload = $line | ConvertFrom-Json
  $response = Invoke-RestMethod -Uri $Endpoint -Method Post -ContentType "application/json" -Body ($payload | ConvertTo-Json -Depth 8)
  $sent += 1
  Write-Host "[$sent] accepted=$($response.accepted) topic=$($response.topic) key=$($response.key) log_id=$($response.log_id)"
  Start-Sleep -Milliseconds $DelayMilliseconds
}

Write-Host "Sent $sent logs to $Endpoint"
