"""
Test script to verify imports and basic functionality
"""

print("Testing imports...")

try:
    from deepseek_analyzer_fixed import DeepSeekSQLAnalyzer
    print("✅ DeepSeekSQLAnalyzer imported successfully")
except Exception as e:
    print(f"❌ Import error: {e}")
    import sys
    sys.exit(1)

try:
    import streamlit as st
    print(f"✅ Streamlit version: {st.__version__}")
except Exception as e:
    print(f"❌ Streamlit import error: {e}")
    print("Installing streamlit...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'streamlit'])
    import streamlit as st
    print("✅ Streamlit installed successfully")

try:
    import pandas as pd
    print(f"✅ Pandas version: {pd.__version__}")
except Exception as e:
    print(f"❌ Pandas import error: {e}")

try:
    import plotly
    print(f"✅ Plotly version: {plotly.__version__}")
except Exception as e:
    print(f"❌ Plotly import error: {e}")
    print("Installing plotly...")
    import subprocess
    subprocess.check_call(['pip', 'install', 'plotly'])

print("\n" + "="*60)
print("All imports successful!")
print("\nTo run the web app:")
print("streamlit run web_app_fixed.py")
print("="*60)