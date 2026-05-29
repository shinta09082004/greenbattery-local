@echo off
echo =========================================
echo EneMap AI [Ver.AI] 起動スクリプト
echo =========================================

echo 1. PYTHONPATHをセットアップしています...
set PYTHONPATH=.

echo 2. 次世代版APIサーバー(ポート8001)を起動します...
python src\web\main_ai.py

pause
