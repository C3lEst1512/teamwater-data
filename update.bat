@echo off
cd /d "%~dp0"

:loop
echo Running Git commands...

git pull
git add .
git commit -m "Add donation collector and GitHub Actions"
git push

echo Waiting 1 hour...
timeout /t 3600 /nobreak
goto loop