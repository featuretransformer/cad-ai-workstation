<#
.SYNOPSIS
    Runs the entire AI-Native CAD-CAM Workstation stack.
.DESCRIPTION
    Launches FastAPI Backend, Celery Worker, and Next.js Frontend with unified monitoring.
.EXAMPLE
    .\run.ps1
    .\run.ps1 -NoCelery -NoBrowser
#>
param(
    [switch]$NoCelery,
    [switch]$NoBrowser,
    [int]$BackendPort = 8000,
    [int]$FrontendPort = 3000
)

$scriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $scriptDir

$python = "python"
if (Test-Path "backend\.venv\Scripts\python.exe") {
    $python = "backend\.venv\Scripts\python.exe"
} elseif (Test-Path ".venv\Scripts\python.exe") {
    $python = ".venv\Scripts\python.exe"
}

$argsList = @("run.py", "--backend-port", "$BackendPort", "--frontend-port", "$FrontendPort")
if ($NoCelery) { $argsList += "--no-celery" }
if ($NoBrowser) { $argsList += "--no-browser" }

& $python $argsList
