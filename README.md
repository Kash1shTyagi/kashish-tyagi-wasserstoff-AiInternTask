
# Document Research & Theme Identification Chatbot

Welcome to the **Document Research & Theme Identification Chatbot**, a Generative AI system developed as part of the AI Internship Task at Wasserstoff.

This application enables users to upload diverse documents (PDFs, scanned images, and text files), query them in natural language, extract precise answers with citations, and summarize common themes across documents. It includes a React-based frontend and a FastAPI backend, integrated with OCR, vector databases, and large language models.

## 🔍 Key Features

- Upload and manage 75+ documents (PDFs, scans, images, etc.)
- Perform OCR on scanned images using Tesseract
- Semantic search using Qdrant vector database
- Natural language Q&A over documents
- Paragraph-level citations (Doc ID, Page, Paragraph/Sentence)
- Thematic summarization of answers with document references
- Easy-to-use web interface with document preview
- Downloadable results and citations

## 🛠️ Tech Stack

### Frontend

- **Framework**: React + TypeScript
- **UI Components**: Tailwind CSS, Custom React Components
- **Features**:
  - File upload (Drag-and-drop + Preview)
  - Chat-style question submission
  - Theme summary and tabular view of answers
  - Responsive and minimal UI

### Backend

- **Framework**: FastAPI
- **OCR**: Tesseract
- **Vector Search**: Qdrant
- **LLMs**: Gemini-1.5 Pro (via `google.generativeai`)
- **PDF/Text Extraction**: PyMuPDF, pdfminer.six
- **Embeddings**: Sentence Transformers / Gemini Embeddings
- **Chunking**: Recursive and page-wise segmentation
- **Storage**: Filesystem + Qdrant + Metadata DB

## 📁 Project Structure

```
chatbot_theme_identifier/
├── backend/
│   ├── app/
│   │   ├── api/
│   │   ├── services/
│   │   ├── models/
│   │   ├── core/
│   │   ├── config.py
│   │   └── main.py
│   ├── data/ (uploads, embeddings)
│   └── requirements.txt
├── frontend/
│   ├── components/
│   ├── pages/
│   ├── public/
│   └── styles/
├── docs/
│   └── (design notes, architecture diagrams, etc.)
├── tests/
├── demo/ (video or screenshots)
└── README.md
```

## ⚙️ Installation & Setup

### Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # On Windows use `venv\Scripts\activate`
pip install -r requirements.txt
uvicorn app.main:app --reload
```

### Frontend

```bash
cd frontend
npm install
npm run dev
```

### Qdrant Setup

- Self-hosted: run with Docker (`qdrant/qdrant`)
- Or use [Qdrant Cloud](https://qdrant.tech/)

### Environment Variables

Create `.env` in the backend with:

```
GOOGLE_API_KEY=your_gemini_key
QDRANT_URL=http://localhost:6333
EMBEDDING_MODEL=gemini-embedding-001
```

## 🧪 Example Workflow

1. Upload 75+ documents via UI.
2. Ask a question like "What are the major issues raised?"
3. System extracts top 3 chunks per document and cites them.
4. Themes are extracted using Gemini and grouped.
5. View themes in a chat format with citations.
6. Optionally, download or export citations.

## 🛡️ Error Handling

- OCR fallback for scanned pages
- Upload format checks (PDF, PNG, JPG, TXT)
- Retry on embedding or LLM failures
- Clean status messages for UI

## 📦 Deployment

- **Backend**: Render / Railway / Replit
- **Frontend**: Vercel / Netlify
- **Vector DB**: Qdrant (Docker or Cloud)

## 🎯 Evaluation Checklist

- ✅ Upload 75+ documents (PDF/Scans/Text)
- ✅ Extract answers with citations per document
- ✅ Show tabular results and chat theme synthesis
- ✅ Use OCR, vector search, and LLMs
- ✅ Frontend-Backend integration
- ✅ Well-documented code and README

## 👤 Author

Kshitiz Pandey  
AI Intern Candidate – Wasserstoff  
Email: [your email here]  
GitHub: [https://github.com/Kash1shTyagi](https://github.com/Kash1shTyagi)

---

> 🚀 Ready to build real-world Generative AI tools with citations and reasoning.
