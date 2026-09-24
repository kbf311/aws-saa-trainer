@echo off
cd /d %~dp0

:: 0. .env が存在しない場合は .env.sample をコピー
if not exist .env (
    if exist .env.sample (
        echo [INFO] .env が見つからないため、.env.sample から .env を作成します...
        copy .env.sample .env >nul
    )
)

:: 1. 仮想環境を有効化
call venv\Scripts\activate

:: 2. ブラウザでURLを開く
start http://localhost:8000

:: 3. Python スクリプトを実行
python -m app.main

pause