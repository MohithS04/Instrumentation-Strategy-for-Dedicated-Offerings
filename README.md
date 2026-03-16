# Instrumentation-Strategy-for-Dedicated-Offerings
# FinSight Copilot

A minimal but realistic LLM-powered RAG (Retrieval-Augmented Generation) application for asset management. This system ingests financial documents and portfolio data, builds a vector store, and provides a question-answering interface for querying portfolios and funds.

## Features

- 📄 **Document Ingestion**: Loads PDF, markdown, and HTML financial documents
- 📊 **Portfolio Management**: Processes CSV files with portfolio holdings and prices
- 🔍 **Vector Search**: Uses ChromaDB for semantic search over documents
- 💬 **Question Answering**: LangChain-powered RAG for answering questions about funds and portfolios
- 🧪 **Evaluation**: Built-in evaluation script with retrieval metrics and LLM-judge scoring
- 🖥️ **Streamlit UI**: Simple web interface for interacting with the system

## Architecture

- **Document Ingestion**: PDF/markdown/HTML → text extraction → chunking
- **Portfolio Ingestion**: CSV → pandas → structured storage
- **Vector Store**: ChromaDB with embeddings (OpenAI or sentence-transformers)
- **QA Chain**: LangChain RAG (retrieval + LLM generation)
- **UI**: Streamlit for Q&A interface
- **Evaluation**: Test cases with retrieval metrics (recall@k) and LLM-judge scoring

## Project Structure

```
.
├── app/
│   ├── ingestion/
│   │   ├── load_documents.py      # Document loading and chunking
│   │   └── load_portfolios.py     # Portfolio CSV loading
│   ├── retrieval/
│   │   └── vector_store.py        # ChromaDB vector store
│   ├── llm/
│   │   └── qa_chain.py            # LangChain QA chain
│   ├── evaluation/
│   │   └── eval_qa.py             # Evaluation script
│   └── ui/
│       └── app.py                 # Streamlit UI
├── data/
│   ├── documents/                 # Sample financial documents
│   └── portfolios/                # Portfolio CSV files
├── .env.example                   # Environment variables template
├── requirements.txt               # Python dependencies
└── README.md                      # This file
```

## Prerequisites

- Python 3.11 or higher
- macOS (tested on macOS, but should work on Linux/Windows)
- `uv` or `pip` for package management
- (Optional) OpenAI API key or Anthropic API key for LLM features

## Setup Instructions

### 1. Create and Activate Virtual Environment

Using `uv` (recommended):
```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Create virtual environment
uv venv

# Activate virtual environment
source .venv/bin/activate
```

Or using `pip`:
```bash
# Create virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate
```

### 2. Install Dependencies

Using `uv`:
```bash
uv pip install -r requirements.txt
```

Or using `pip`:
```bash
pip install -r requirements.txt
```

### 3. Configure Environment Variables

Create a `.env` file in the project root (you can use `.env.example` as a template if it exists):
```bash
# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_key_here
ANTHROPIC_API_KEY=your_key_here
EOF
```

Or manually create `.env` and add your API keys (optional):
```bash
# For OpenAI (embeddings and LLM)
OPENAI_API_KEY=your_key_here

# For Anthropic (LLM)
ANTHROPIC_API_KEY=your_key_here
```

**Note**: If you don't provide API keys, the system will:
- Use HuggingFace sentence-transformers for embeddings (free, runs locally)
- Use a dummy echo model for LLM responses (for testing purposes)

### 4. Run Document Ingestion

First, ingest documents into the vector store:

```bash
python -m app.ingestion.load_documents
```

Or create a simple ingestion script:

```bash
python -c "from app.ingestion.load_documents import load_documents; from app.retrieval.vector_store import get_vector_store; docs = load_documents(); vs = get_vector_store(); vs.add_documents(docs)"
```

### 5. Start the UI

Run the Streamlit application:

```bash
streamlit run app/ui/app.py
```

The UI will open in your browser at `http://localhost:8501`

### 6. Run Evaluation (Optional)

Test the system with the evaluation script:

```bash
python -m app.evaluation.eval_qa
```

Or run it through the UI: Navigate to the "Evaluation" page and click "Run Evaluation"

## Usage

### Through Streamlit UI

1. **Ask Questions**: Navigate to "Ask Questions" page
   - Enter your question (e.g., "What are the main risk factors for Fund A?")
   - Optionally select a portfolio
   - Click "Ask" to get an answer with sources

2. **Portfolio Info**: View portfolio data and summaries

3. **Evaluation**: Run evaluation tests and view metrics

4. **System Status**: Check vector store status and configuration

### Through Python API

```python
from app.retrieval.vector_store import get_vector_store
from app.llm.qa_chain import QAChain
from app.ingestion.load_portfolios import PortfolioLoader

# Initialize components
vector_store = get_vector_store()
portfolio_loader = PortfolioLoader()
qa_chain = QAChain(vector_store=vector_store, portfolio_loader=portfolio_loader)

# Ask a question
result = qa_chain.answer_question("What are the main risk factors?")
print(result["answer"])
```

## Adding Your Own Data

### Documents

Place your financial documents (PDF, markdown, or HTML) in `data/documents/`:
- PDF files: `*.pdf`
- Markdown files: `*.md`
- HTML files: `*.html`

Then re-run the ingestion step.

### Portfolios

Place CSV files in `data/portfolios/`. Expected format:
```csv
ticker,shares,price,date
AAPL,100,175.50,2024-01-15
MSFT,80,380.25,2024-01-15
```

The filename (without extension) will be used as the portfolio ID.

## Evaluation Metrics

The evaluation script measures:

- **Recall@k**: Percentage of expected keywords found in top-k retrieved documents
- **LLM-Judge Score**: Quality score (0.0-1.0) from an LLM judge evaluating answer relevance and completeness

## Troubleshooting

### Vector Store Issues

If you encounter issues with the vector store:
```bash
# Delete and recreate (WARNING: deletes all data)
rm -rf chroma_db
```

### Import Errors

Make sure you're running commands from the project root directory and the virtual environment is activated.

### API Key Issues

If you get API errors:
1. Check that your `.env` file exists and has correct keys
2. Verify API keys are valid and have sufficient credits
3. The system will fall back to local models if keys are missing

## Dependencies

Key dependencies:
- `langchain`: LLM orchestration and RAG
- `chromadb`: Vector database
- `streamlit`: Web UI
- `pypdf`: PDF processing
- `pandas`: Data processing
- `sentence-transformers`: Local embeddings (fallback)

See `requirements.txt` for the complete list.

## License

This is a sample project for demonstration purposes.

## Contributing

This is a minimal implementation. Feel free to extend it with:
- Additional document formats
- More sophisticated retrieval strategies
- Advanced evaluation metrics
- API endpoints (FastAPI)
- Authentication and user management
