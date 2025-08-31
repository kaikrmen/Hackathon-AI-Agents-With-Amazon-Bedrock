python -m venv .venv
.\.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
pip freeze > requirements-lock.txt
Write-Host "Setup completado. Activa con .\.venv\Scripts\activate"
