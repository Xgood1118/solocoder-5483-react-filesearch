@echo off
chcp 65001 >nul
setlocal

echo.
echo =============================================
echo   NAS 全文检索 - 一键启动 (Windows)
echo =============================================
echo.

cd /d "%~dp0"

:: 1. 后端依赖
echo [1/4] 检查后端依赖...
cd backend
if not exist venv (
  echo     创建 Python 虚拟环境...
  python -m venv venv || goto :err
)
call venv\Scripts\activate.bat
pip install -r requirements.txt -q || goto :err
cd ..

:: 2. 前端依赖
echo.
echo [2/4] 检查前端依赖...
cd frontend
if not exist node_modules (
  echo     安装 npm 依赖，需要一点时间...
  call npm install || goto :err
)
cd ..

:: 3. 启动后端（后台）
echo.
echo [3/4] 启动后端服务 (端口 %FLASK_PORT:-5000%) ...
start "Filesearch Backend" cmd /c "cd /d %~dp0backend && call venv\Scripts\activate.bat && python run.py"

:: 4. 启动前端
timeout /t 3 /nobreak >nul
echo.
echo [4/4] 启动前端服务 (端口 5173) ...
echo.
cd frontend
call npm run dev

goto :eof

:err
echo.
echo [91m启动失败，请检查错误信息。[0m
pause
exit /b 1
