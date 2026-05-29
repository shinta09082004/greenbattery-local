@echo off
echo =========================================
echo EneMap AI 起動スクリプト
echo =========================================

echo 1. PYTHONPATHをセットアップしています...
set PYTHONPATH=.

echo 2. バックエンドAPIサーバー(FastAPI)を起動します...
python src\web\main.py

pause
