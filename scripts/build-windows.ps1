param([switch]$SkipDependencyInstall)

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Set-Location -LiteralPath $repoRoot

# A local toolchain can be used without changing the user's persistent PATH.
$localTools = Join-Path $repoRoot '.preview/toolchain'
if (Test-Path -LiteralPath "$localTools/cargo/bin/cargo.exe") {
    $env:CARGO_HOME = "$localTools/cargo"
    $env:RUSTUP_HOME = "$localTools/rustup"
    $env:PATH = "$localTools/cargo/bin;$env:PATH"
}
if (-not (Get-Command cargo -ErrorAction SilentlyContinue)) {
    throw '缺少 Rust MSVC 工具链。请参阅 desktop/README.md。'
}
if (-not $SkipDependencyInstall) {
    uv sync --dev --group desktop
    if ($LASTEXITCODE -ne 0) { throw 'Python 依赖安装失败。' }
}

Push-Location web
try {
    if (-not $SkipDependencyInstall) {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw '前端依赖安装失败。' }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw '前端构建失败。' }
} finally { Pop-Location }

& .venv/Scripts/python.exe desktop/build_sidecar.py
if ($LASTEXITCODE -ne 0) { throw 'Python 服务打包失败。' }

Push-Location desktop
try {
    if (-not $SkipDependencyInstall) {
        npm ci
        if ($LASTEXITCODE -ne 0) { throw '桌面依赖安装失败。' }
    }
    npm run build
    if ($LASTEXITCODE -ne 0) { throw '桌面安装包构建失败。' }
} finally { Pop-Location }

$version = (Get-Content desktop/package.json -Raw | ConvertFrom-Json).version
$installer = Get-ChildItem desktop/src-tauri/target/release/bundle/nsis/*-setup.exe |
    Where-Object { $_.Name -like "*${version}*" } |
    Sort-Object LastWriteTime -Descending | Select-Object -First 1
if (-not $installer) { throw '未找到本次版本的 NSIS 安装包。' }
New-Item -ItemType Directory -Force dist | Out-Null
$releasePath = Join-Path $repoRoot "dist/Xiliu-$version-x64-setup.exe"
Copy-Item -LiteralPath $installer.FullName -Destination $releasePath -Force
$checksum = (Get-FileHash -LiteralPath $releasePath -Algorithm SHA256).Hash.ToLowerInvariant()
"$checksum  $(Split-Path -Leaf $releasePath)" |
    Set-Content -LiteralPath "$releasePath.sha256" -Encoding ascii
Write-Output "安装包：$releasePath"
Write-Output "SHA256：$checksum"
