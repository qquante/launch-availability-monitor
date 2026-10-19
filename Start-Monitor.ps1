$ErrorActionPreference = 'Stop'
$monitorRoot = $PSScriptRoot
$runtimeDir = Join-Path $monitorRoot 'runtime'
New-Item -ItemType Directory -Path $runtimeDir -Force | Out-Null
$pythonExe = (Get-Command python -ErrorAction Stop).Source
try {
    $running = Invoke-RestMethod -Uri 'http://127.0.0.1:8888/api/status' -TimeoutSec 2
    if ($running.heartbeat.root -eq $monitorRoot -and $running.heartbeat.running) {
        Write-Output 'Monitor ja ativo: http://127.0.0.1:8888'
        exit 0
    }
} catch {}
$process = Start-Process -FilePath $pythonExe -ArgumentList @('-u', ('"' + (Join-Path $monitorRoot 'monitor.py') + '"'), 'run') -WorkingDirectory $monitorRoot -WindowStyle Hidden -RedirectStandardOutput (Join-Path $runtimeDir 'stdout.log') -RedirectStandardError (Join-Path $runtimeDir 'stderr.log') -PassThru
Write-Output ('Processo iniciado: ' + $process.Id + ' | http://127.0.0.1:8888')
