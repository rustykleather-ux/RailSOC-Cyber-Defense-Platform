.PHONY: help install install-backend install-frontend seed backend frontend dev clean reset-db

PYTHON := backend/venv/Scripts/python.exe
PIP := backend/venv/Scripts/pip.exe
UVICORN := backend/venv/Scripts/python.exe -m uvicorn

help:
	@echo TrackSentinel Development Commands
	@echo.
	@echo make install          Install backend and frontend dependencies
	@echo make seed             Seed the TrackSentinel database
	@echo make backend          Start the FastAPI backend
	@echo make frontend         Start the React frontend
	@echo make dev              Start backend and frontend
	@echo make reset-db         Delete and reseed the local database
	@echo make clean            Remove caches and generated files

install: install-backend install-frontend

install-backend:
	@if not exist backend\venv (python -m venv backend\venv)
	$(PYTHON) -m pip install --upgrade pip
	$(PIP) install -r backend/requirements.txt

install-frontend:
	cd frontend && npm install

seed:
	cd backend && ..\$(PYTHON) seed.py

backend:
	cd backend && ..\$(UVICORN) main:app --reload

frontend:
	cd frontend && npm run dev

dev:
	@echo Starting TrackSentinel backend and frontend...
	start "TrackSentinel Backend" cmd /k "cd /d %CD%\backend && venv\Scripts\python.exe -m uvicorn main:app --reload"
	start "TrackSentinel Frontend" cmd /k "cd /d %CD%\frontend && npm run dev"

reset-db:
	@if exist backend\tracksentinel.db del backend\tracksentinel.db
	@if exist backend\ot_platform.db del backend\ot_platform.db
	cd backend && venv\Scripts\python.exe seed.py

clean:
	@if exist backend\__pycache__ rmdir /s /q backend\__pycache__
	@if exist backend\.pytest_cache rmdir /s /q backend\.pytest_cache
	@if exist frontend\node_modules\.vite rmdir /s /q frontend\node_modules\.vite
	@if exist frontend\dist rmdir /s /q frontend\dist
	@echo Cleanup complete.