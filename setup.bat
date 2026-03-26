@echo off
echo 🚀 Setting up DeepSeek SQL Analyzer
echo ===================================

:: Check if Ollama is installed
where ollama >nul 2>nul
if %errorlevel% neq 0 (
    echo 📦 Please install Ollama from https://ollama.ai/download/windows
    pause
    exit /b
) else (
    echo ✓ Ollama already installed
)

:: Pull DeepSeek model
echo 📥 Pulling DeepSeek-R1:1.5B model...
ollama pull deepseek-r1:1.5b

:: Create virtual environment
echo 🐍 Setting up Python environment...
python -m venv venv
call venv\Scripts\activate

:: Install packages
echo 📦 Installing Python packages...
pip install --upgrade pip
pip install ollama sqlalchemy pandas tabulate click streamlit plotly

:: Create database
echo 🗄️ Creating sample database...
python setup_database.py

:: Quick test
echo 🧪 Running quick test...
python quick_test.py

echo.
echo ✅ Setup complete!
echo.
echo To start the CLI version:
echo   venv\Scripts\activate
echo   python deepseek_analyzer.py
echo.
echo To start the web interface:
echo   venv\Scripts\activate
echo   streamlit run web_app.py

pause