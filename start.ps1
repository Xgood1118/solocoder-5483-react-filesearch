# 启动脚本 - NAS 全文检索
# 使用方法: 右键 -> 使用 PowerShell 运行, 或在终端执行: .\start.ps1

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $Root

Write-Host ""
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host "  NAS 全文检索 - 一键启动 (PowerShell)" -ForegroundColor Cyan
Write-Host "=============================================" -ForegroundColor Cyan
Write-Host ""

# 1. 后端
Write-Host "[1/4] 检查后端依赖..." -ForegroundColor Yellow
Set-Location "$Root\backend"
if (-not (Test-Path "venv")) {
  Write-Host "     创建 Python 虚拟环境..."
  python -m venv venv
  if ($LASTEXITCODE -ne 0) { throw "创建 venv 失败，请确认已安装 Python 3.10+" }
}
$VenvPy = Join-Path (Resolve-Path "venv\Scripts").Path "python.exe"
& $VenvPy -m pip install -r requirements.txt -q
if ($LASTEXITCODE -ne 0) { throw "pip 安装依赖失败" }
Set-Location $Root

# 2. 前端
Write-Host ""
Write-Host "[2/4] 检查前端依赖..." -ForegroundColor Yellow
Set-Location "$Root\frontend"
if (-not (Test-Path "node_modules")) {
  Write-Host "     安装 npm 依赖，请稍候..."
  npm install
  if ($LASTEXITCODE -ne 0) { throw "npm install 失败" }
}
Set-Location $Root

# 3. 后端进程
$FlaskPort = if ($env:FLASK_PORT) { [int]$env:FLASK_PORT } else { 5000 }
Write-Host ""
Write-Host "[3/4] 启动后端服务 (端口 $FlaskPort)..." -ForegroundColor Yellow
$BackendJob = Start-Process -FilePath "cmd" -ArgumentList "/c cd /d `"$Root\backend`" && call venv\Scripts\activate.bat && python run.py" -PassThru -WindowStyle Normal
Start-Sleep -Seconds 3

# 4. 前端进程
Write-Host ""
Write-Host "[4/4] 启动前端服务..." -ForegroundColor Yellow
Write-Host ""
Write-Host "服务启动中，浏览器访问：" -ForegroundColor Green
Write-Host "   前端: http://localhost:5173" -ForegroundColor Green
Write-Host "   后端健康检查: http://localhost:$FlaskPort/api/health" -ForegroundColor Green
Write-Host ""
Write-Host "提示：关闭此窗口即可停止所有服务。" -ForegroundColor Gray
Write-Host ""

Set-Location "$Root\frontend"
npm run dev

# 清理
try { Stop-Process -Id $BackendJob.Id -Force -ErrorAction SilentlyContinue } catch {}
