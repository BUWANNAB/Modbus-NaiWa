$ErrorActionPreference = 'Stop'

$python = Get-Command py -ErrorAction SilentlyContinue
if (-not $python) {
    throw '找不到 Python Launcher（py）。请先安装 Python 3.11。'
}

Push-Location $PSScriptRoot
try {
    py -3.11 -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw '依赖安装失败。' }

    py -3.11 -m PyInstaller `
        --clean `
        --noconfirm `
        --distpath dist `
        --workpath build\NaiWaModbus `
        NaiWaModbus.spec
    if ($LASTEXITCODE -ne 0) { throw 'PyInstaller 打包失败。' }

    Write-Host "EXE 已生成：$((Resolve-Path 'dist/NaiWaModbus.exe').Path)" -ForegroundColor Green
}
finally {
    Pop-Location
}
