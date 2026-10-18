<#
.SYNOPSIS
  Instala dependencias y arranca el stack completo de DealCompass en local.

.DESCRIPTION
  1. Crea .venv e instala la API en modo editable (pip install -e '.[dev]').
  2. Instala el frontend con bun install (app/).
  3. Crea .env desde .env.example si no existe.
  4. Arranca en background: API (uvicorn), worker de jobs y Vite dev server.
  Los logs quedan en logs/<proceso>.log y logs/<proceso>.err.log.
  Ctrl+C detiene los tres procesos.

.EXAMPLE
  .\scripts\dev.ps1
  .\scripts\dev.ps1 -SkipInstall      # ya instalado
  .\scripts\dev.ps1 -NoWorker         # solo API + frontend
#>
[CmdletBinding()]
param(
    [switch]$SkipInstall,
    [switch]$NoWorker,
    [int]$ApiPort = 8000,
    [int]$WebPort = 5173
)

$ErrorActionPreference = 'Stop'

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

$logDir = Join-Path $root 'logs'
$venvDir = Join-Path $root '.venv'
$venvPython = Join-Path $venvDir 'Scripts\python.exe'
New-Item -ItemType Directory -Force -Path $logDir | Out-Null

function Write-Step([string]$Message) { Write-Host "==> $Message" -ForegroundColor Cyan }
function Write-Ok([string]$Message) { Write-Host "    $Message" -ForegroundColor Green }
function Write-WarnLine([string]$Message) { Write-Host "    $Message" -ForegroundColor Yellow }

# ---------------------------------------------------------------- prerequisitos
# node/npm no hacen falta: el frontend se instala y arranca con bun.
foreach ($tool in 'python', 'bun') {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "No se encontro '$tool' en el PATH. Instalalo antes de volver a ejecutar el script."
    }
}

# ---------------------------------------------------------------- instalacion
if (-not $SkipInstall) {
    if (-not (Test-Path $venvPython)) {
        Write-Step "Creando virtualenv en $venvDir"
        & python -m venv $venvDir
    }

    Write-Step 'Instalando dependencias de la API (pip install -e .[dev])'
    & $venvPython -m pip install --quiet --upgrade pip
    & $venvPython -m pip install --quiet -e '.[dev]'
    if ($LASTEXITCODE -ne 0) { throw 'Fallo la instalacion de dependencias Python.' }

    Write-Step 'Instalando dependencias del frontend (bun install en app/)'
    Push-Location (Join-Path $root 'app')
    bun install
    $bunExit = $LASTEXITCODE
    Pop-Location
    if ($bunExit -ne 0) { throw 'Fallo la instalacion de dependencias del frontend.' }

    Write-Ok 'Dependencias instaladas.'
} else {
    Write-Step 'Instalacion omitida (-SkipInstall)'
}

if (-not (Test-Path $venvPython)) {
    throw "No existe $venvPython. Ejecuta el script sin -SkipInstall."
}

# ---------------------------------------------------------------- entorno
if (-not (Test-Path (Join-Path $root '.env'))) {
    Copy-Item (Join-Path $root '.env.example') (Join-Path $root '.env')
    Write-Ok '.env creado a partir de .env.example (revisalo: claves de OpenRouter, Maps, Apify, Dapta).'
}

$dbUrl = (Get-Content (Join-Path $root '.env') |
    Where-Object { $_ -match '^\s*DATABASE_URL\s*=' } |
    Select-Object -First 1) -replace '^\s*DATABASE_URL\s*=\s*', ''
if (-not $dbUrl) { $dbUrl = 'postgresql+psycopg://postgres:postgres@localhost:5432/dealcompass' }
if ($dbUrl -match '@(?<host>[\w.\-]+):(?<port>\d+)') {
    $dbHost = $Matches['host']; $dbPort = [int]$Matches['port']
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        if (-not $client.ConnectAsync($dbHost, $dbPort).Wait(1500)) { throw 'timeout' }
        Write-Ok "Postgres accesible en ${dbHost}:${dbPort}."
    } catch {
        Write-WarnLine "No hay Postgres en ${dbHost}:${dbPort}. La API arranca igual, pero /api/search fallara hasta que levantes la DB."
    } finally {
        $client.Dispose()
    }
}

# El codigo vive en src/; uvicorn y el worker necesitan PYTHONPATH.
$env:PYTHONPATH = Join-Path $root 'src'
$env:APP_ENV = 'local'

# ---------------------------------------------------------------- procesos
$started = @()

function Start-DevProcess([string]$Name, [string]$FilePath, [string[]]$ArgumentList, [string]$WorkingDir) {
    $outLog = Join-Path $script:logDir "$Name.log"
    $errLog = Join-Path $script:logDir "$Name.err.log"
    $process = Start-Process -FilePath $FilePath `
        -ArgumentList $ArgumentList `
        -WorkingDirectory $WorkingDir `
        -RedirectStandardOutput $outLog `
        -RedirectStandardError $errLog `
        -NoNewWindow -PassThru
    $script:started += [pscustomobject]@{ Name = $Name; Process = $process }
    Write-Ok ("{0,-6} pid {1,-8} -> {2}" -f $Name, $process.Id, $outLog)
    return $process
}

Write-Step 'Arrancando servicios de desarrollo'
# bun es un ejecutable nativo, asi que Start-Process lo lanza directo (a
# diferencia de npm, que en Windows resuelve a un npm.ps1 no lanzable).
$bunCmd = (Get-Command bun -ErrorAction SilentlyContinue).Source

Start-DevProcess -Name 'api' -FilePath $venvPython `
    -ArgumentList @('-m', 'uvicorn', 'dealcompass_api.main:app', '--reload', '--port', $ApiPort) `
    -WorkingDir $root | Out-Null

if (-not $NoWorker) {
    Start-DevProcess -Name 'worker' -FilePath $venvPython `
        -ArgumentList @('-m', 'dealcompass_api.workers.runner') `
        -WorkingDir $root | Out-Null
}

Start-DevProcess -Name 'web' -FilePath $bunCmd `
    -ArgumentList @('run', 'dev', '--port', $WebPort, '--strictPort') `
    -WorkingDir (Join-Path $root 'app') | Out-Null

Write-Host ''
Write-Host '  Frontend  ' -NoNewline -ForegroundColor Green
Write-Host "http://localhost:$WebPort/app/"
Write-Host '  API       ' -NoNewline -ForegroundColor Green
Write-Host "http://localhost:$ApiPort/api/docs"
Write-Host '  Logs      ' -NoNewline -ForegroundColor Green
Write-Host "$logDir\*.log"
Write-Host ''
Write-Host '  Ctrl+C para detener todo.' -ForegroundColor DarkGray
Write-Host ''

# ---------------------------------------------------------------- supervision
# Un proceso caido no tumba el resto: se avisa una vez y se sigue esperando.
# El script solo termina cuando Ctrl+C o cuando mueren todos.
try {
    $reported = @{}
    while ($true) {
        Start-Sleep -Seconds 2
        $alive = 0
        foreach ($entry in $started) {
            if ($entry.Process.HasExited) {
                if (-not $reported.ContainsKey($entry.Name)) {
                    $reported[$entry.Name] = $true
                    Write-Host ''
                    Write-WarnLine ("'{0}' se detuvo (exit code {1}). Revisa logs\{0}.err.log" -f `
                        $entry.Name, $entry.Process.ExitCode)
                }
            } else {
                $alive++
            }
        }
        if ($alive -eq 0) {
            throw 'Todos los servicios se detuvieron.'
        }
    }
} catch {
    Write-Host ''
    Write-WarnLine $_.Exception.Message
} finally {
    Write-Step 'Deteniendo servicios'
    $taskkill = Get-Command 'taskkill.exe' -ErrorAction SilentlyContinue
    foreach ($entry in $started) {
        if (-not $entry.Process.HasExited) {
            # /T mata el arbol de procesos: uvicorn --reload y bun run dev
            # spawning el proceso hijo deben morir con su padre.
            try {
                if ($taskkill) {
                    & $taskkill.Source /PID $entry.Process.Id /T /F *> $null
                } else {
                    Stop-Process -Id $entry.Process.Id -Force -ErrorAction Stop
                }
            } catch { }
            Write-Ok "$($entry.Name) detenido."
        }
    }
}
