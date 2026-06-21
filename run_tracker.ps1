param(
    [switch]$NoReport
)

$env:PYTHONIOENCODING = "utf-8"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $ScriptDir

$LogDir = "$ScriptDir\logs"
if (-not (Test-Path $LogDir)) { New-Item -ItemType Directory -Path $LogDir -Force | Out-Null }

$Timestamp = Get-Date -Format "yyyyMMdd_HHmmss"
$LogFile = "$LogDir\tracker_$Timestamp.log"

$Args = @("main.py", "track", "-i", "0")
if ($NoReport) { $Args += "--no-report" }

Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Starting Instagram tracker..." -ForegroundColor Cyan
& python $Args *>&1 | Tee-Object -FilePath $LogFile
Write-Host "[$(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')] Finished." -ForegroundColor Cyan
