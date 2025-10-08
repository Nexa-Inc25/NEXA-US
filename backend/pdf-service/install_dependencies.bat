@echo off
echo Installing NEXA Document Intelligence Dependencies...
echo.

echo [1/6] Installing core dependencies...
pip install streamlit PyPDF2 requests python-dotenv

echo [2/6] Installing spaCy and language model...
pip install spacy
python -m spacy download en_core_web_sm

echo [3/6] Installing LangChain ecosystem...
pip install langchain langchain-community openai

echo [4/6] Installing embeddings and vector search...
pip install sentence-transformers faiss-cpu numpy huggingface-hub

echo [5/6] Installing ML dependencies...
pip install torch transformers

echo [6/6] Installation complete!
echo.
echo You can now run: python -m streamlit run app_langchain_xai.py
pause
