@echo off
echo =========================================
echo ^| Starting Cloud-Native PM Dashboard... ^|
echo =========================================
python -m pip install -r requirements.txt -q
python -m uvicorn main:app --reload --reload-include "*.md" --reload-include "*.html" --port 8000
