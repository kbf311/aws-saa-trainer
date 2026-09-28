@echo off
cd /d %~dp0

:: 仮想環境の有効化
call venv\Scripts\activate

:: ダミーデータ生成スクリプトの実行（100日前からのダミー回答を作成）
:: 既存ログを初期化して作り直したい場合は引数に --clear を追加してください
python scripts/generate_dummy_answers.py %*

pause
