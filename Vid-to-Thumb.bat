@echo off
REM UTF-8モードに切り替え
chcp 65001 > nul

REM Pythonスクリプトを実行（引数をそのまま渡す）
C:\Python313\python.exe Vid-to-Thumb.py %*

REM 終了前に一時停止
set /p confirm="処理が完了しました。Enterキーを押して終了します..."