param(
  [string]$InputPath = "data/realtime_test/anomaly_candidate_logs.jsonl",
  [string]$Endpoint = "http://localhost:8501/api/ingest/logs",
  [string]$AppContainer = "semantic-log-monitoring-app-1",
  [int]$DelaySeconds = 2,
  [switch]$MockAnomalyForErrors
)

$ErrorActionPreference = "Stop"

function Get-TextValue($Object, $Name, $Fallback = $null) {
  if ($null -eq $Object) {
    return $Fallback
  }
  $property = $Object.PSObject.Properties[$Name]
  if ($null -eq $property -or $null -eq $property.Value -or [string]::IsNullOrWhiteSpace([string]$property.Value)) {
    return $Fallback
  }
  return [string]$property.Value
}

function Set-TextValue($Object, $Name, $Value) {
  $property = $Object.PSObject.Properties[$Name]
  if ($null -eq $property) {
    $Object | Add-Member -NotePropertyName $Name -NotePropertyValue $Value
  } else {
    $property.Value = $Value
  }
}

function New-AnomalyFields($Level, [bool]$Mock) {
  $upperLevel = ([string]$Level).ToUpperInvariant()
  if (-not $Mock) {
    return @{
      score = $null
      level = "unknown"
      decision = "not_scored"
      baseline = "disabled"
      reasons = @()
    }
  }

  if ($upperLevel -eq "ERROR") {
    return @{
      score = 0.94
      level = "high"
      decision = "anomalous"
      baseline = "ready"
      reasons = @("mock anomaly for UI test", "level=ERROR")
    }
  }

  if ($upperLevel -eq "WARN") {
    return @{
      score = 0.68
      level = "medium"
      decision = "watch"
      baseline = "ready"
      reasons = @("mock anomaly for UI test", "level=WARN")
    }
  }

  return @{
    score = 0.08
    level = "normal"
    decision = "normal"
    baseline = "ready"
    reasons = @("mock normal")
  }
}

function Convert-ToDashboardLog($Payload, $Response, [bool]$MockAnomaly) {
  $level = (Get-TextValue $Payload "level" "UNKNOWN").ToUpperInvariant()
  $service = Get-TextValue $Payload "component" (Get-TextValue $Payload "service" "unknown-service")
  $rawLog = Get-TextValue $Payload "raw_log" (Get-TextValue $Payload "message" "")
  $message = Get-TextValue $Payload "message" $rawLog
  $timestamp = Get-TextValue $Payload "timestamp" ""
  $timestampMs = $null
  if (-not [string]::IsNullOrWhiteSpace($timestamp)) {
    $timestampMs = [DateTimeOffset]::Parse($timestamp).ToUnixTimeMilliseconds()
  }

  $anomaly = New-AnomalyFields $level $MockAnomaly
  $logId = Get-TextValue $Response "log_id" (Get-TextValue $Payload "source_id" "")

  return [ordered]@{
    dataset = Get-TextValue $Payload "dataset" "unknown"
    timestamp = $timestamp
    timestamp_ms = $timestampMs
    level = $level
    service = $service
    message = $message
    rawLog = $rawLog
    log_id = $logId
    line_number = [int](Get-TextValue $Payload "line_number" 1)
    template_id = $null
    anomaly_score = $anomaly.score
    anomaly_level = $anomaly.level
    anomaly_decision = $anomaly.decision
    anomaly_baseline_status = $anomaly.baseline
    anomaly_reasons = $anomaly.reasons
    anomaly_components = @{}
  }
}

function Publish-DashboardData($Logs, $SourcePath, $ContainerName) {
  $today = Get-Date -Format "yyyy-MM-dd"
  $document = [ordered]@{
    generatedAt = (Get-Date).ToUniversalTime().ToString("o")
    source = @($SourcePath)
    filter = [ordered]@{
      mode = "current-day"
      date = $today
      timeZone = "Asia/Ho_Chi_Minh"
      inputLogCount = $Logs.Count
    }
    logs = $Logs
  }

  $tempFile = Join-Path $env:TEMP "semantic-dashboard-data.json"
  $document | ConvertTo-Json -Depth 20 | Set-Content -LiteralPath $tempFile -Encoding UTF8
  Copy-Item -LiteralPath $tempFile -Destination "frontend/public/dashboard-data.json" -Force
  docker cp $tempFile "${ContainerName}:/usr/share/nginx/html/dashboard-data.json" | Out-Null
}

$resolvedPath = Resolve-Path -LiteralPath $InputPath
$records = @(Get-Content -LiteralPath $resolvedPath | Where-Object { -not [string]::IsNullOrWhiteSpace($_) } | ForEach-Object { $_ | ConvertFrom-Json })
$visibleLogs = @()
$startedAt = Get-Date

Write-Host "Playing $($records.Count) logs to $Endpoint"
  Write-Host "UI data target: ${AppContainer}:/usr/share/nginx/html/dashboard-data.json"
if ($MockAnomalyForErrors) {
  Write-Host "Mock anomaly highlight is ON for ERROR/WARN rows"
}

for ($index = 0; $index -lt $records.Count; $index += 1) {
  $payload = $records[$index]
  $currentTime = $startedAt.AddSeconds($index * [Math]::Max(1, $DelaySeconds))
  Set-TextValue $payload "timestamp" $currentTime.ToString("yyyy-MM-ddTHH:mm:sszzz")

  $jsonBody = $payload | ConvertTo-Json -Depth 20
  $response = Invoke-RestMethod -Uri $Endpoint -Method Post -ContentType "application/json" -Body $jsonBody
  $dashboardLog = Convert-ToDashboardLog $payload $response ([bool]$MockAnomalyForErrors)
  $visibleLogs = @($dashboardLog) + $visibleLogs

  Publish-DashboardData $visibleLogs $InputPath $AppContainer

  Write-Host ("[{0}/{1}] {2} {3} {4} -> {5}" -f ($index + 1), $records.Count, $dashboardLog.timestamp, $dashboardLog.level, $dashboardLog.service, $response.log_id)
  Start-Sleep -Seconds $DelaySeconds
}

Write-Host "Done. The UI should have $($visibleLogs.Count) visible logs."
