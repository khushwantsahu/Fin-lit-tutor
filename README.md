# Fin-Lit-Tutor 🇮🇳💰

**India's most advanced AI-powered Financial Literacy Learning Platform built on Meta Llama 3.3 70B Instruct (via IBM watsonx) models**

[![Built with IBM Watsonx.ai](https://img.shields.io/badge/IBM-Watsonx.ai-blue?style=flat-square)](https://www.ibm.com/watsonx)
[![Flask](https://img.shields.io/badge/Flask-3.0-green?style=flat-square)](https://flask.palletsprojects.com/)
[![RAG](https://img.shields.io/badge/RAG-ChromaDB-purple?style=flat-square)](https://www.trychroma.com/)
[![Multilingual](https://img.shields.io/badge/Languages-10-orange?style=flat-square)](#)

---

## 🚀 Overview

**Fin-Lit-Tutor** is a digital learning application designed to empower citizens with trusted, accessible, and AI-powered financial literacy. Built as a full-stack Flask application, the platform helps users master banking concepts, UPI payments, budgeting, savings, investments, and government schemes in their own languages. 

The application utilizes state-of-the-art AI technology to ground all learning and query responses in official regulatory guidelines:
- **Meta Llama 3.3 70B Instruct (via IBM watsonx)** for natural, multilingual conversational AI responses.
- **IBM Slate / Granite Embeddings** for vector encoding and semantic retrieval.
- **RAG (Retrieval-Augmented Generation)** querying RBI, NPCI, SEBI, IRDAI, and 10+ official government portals.
- **Glassmorphic Interactive Dashboard** displaying calculated stats, levels, and gamified progress.
- **10 Indian languages** (English, Hindi, Tamil, Telugu, Kannada, Malayalam, Marathi, Gujarati, Bengali, Punjabi).

---

## ✨ Features

* **🤖 AI Financial Tutor**: Conversational companion answering questions grounded in official financial guidelines. Includes native **Text-to-Speech (TTS)** voice guides with human-sounding female profiles and dynamic translation.
* **📚 Retrieval-Augmented Generation (RAG)**: Integration of ChromaDB and LangChain to fetch contextual, accurate data from trusted portals, mitigating LLM hallucinations.
* **📊 Financial Score widget**: Evaluates savings rate, debt ratio, and emergency funds to assign a 0–100 wellness rating, giving actionable recommendations.
* **💰 50-30-20 Budget Planner**: Dynamic visualizer that divides monthly income into needs, wants, and savings, syncing to the main dashboard.
* **🏦 Loan & EMI Calculator**: Calculates repayments and builds full amortization tables with interactive Chart.js visualizations.
* **🛡️ Scam Awareness Center**: Text scam checker using semantic analysis to detect digital fraud attempts, with direct integration to the Cyber Crime Helpline (1930).
* **🏛️ Government Scheme Library**: Categorized portal matching 12+ schemes (PMJDY, APY, MUDRA, Sukanya Samriddhi) to the user's demographic profile.
* **🎓 Gamified Learning Paths**: Personalization of recommendations based on user XP milestones. Includes digital badge awards and certificate unlock thresholds.
* **⚙️ Admin Console**: Upload PDF resources, manage knowledge base indexing, and view telemetry metrics.

---

## 🛠️ Technology Stack

* **Backend**: Flask (Python 3.11+), SQLAlchemy, LangChain.
* **Frontend**: HTML5, Vanilla CSS3 (Custom design system), JavaScript (GSAP animations, Chart.js, Three.js 3D landing page).
* **Vector Store**: ChromaDB.
* **Generative AI / LLM**: IBM Watsonx.ai (Meta Llama 3.3 70B Instruct & Slate/Granite Embeddings).
* **Database**: SQLite / PostgreSQL.

---

## 🏗️ Folder Structure

```
Fin-Lit-Tutor/
├── app/
│   ├── __init__.py           # Flask app factory & config
│   ├── agent_instructions.py  # System prompt & AI personality settings
│   ├── models/               # SQLAlchemy schema definitions
│   │   ├── user.py
│   │   ├── chat.py
│   │   ├── document.py
│   │   ├── feedback.py
│   │   └── progress.py
│   ├── routes/               # Flask Blueprints
│   │   ├── main.py           # Home and dashboard
│   │   ├── auth.py           # Session management
│   │   ├── chat.py           # Conversational AI
│   │   ├── api.py            # Calculators & stats API
│   │   ├── admin.py          # Portal management
│   │   └── modules.py        # Module loaders
│   └── services/             # Core logic services
│       ├── rag_service.py    # Watsonx connection & ChromaDB logic
│       └── financial_service.py # Core calculations & analytics
├── templates/                # Jinja2 HTML views
│   ├── index.html            # Landing page
│   ├── chat.html             # Conversational screen
│   ├── auth/                 # Sign in & Sign up
│   ├── dashboard/            # Profile panel
│   ├── modules/              # Tools & Scam awareness
│   └── admin/                # Management console
├── static/
│   ├── css/
│   │   ├── main.css          # Core design tokens
│   │   └── dashboard.css     # Dashboard layouts
│   └── js/                   # Frontend helpers
├── data/
│   ├── knowledge_base/       # Regulatory PDFs
│   ├── uploads/              # Dynamic admin files
│   └── chroma_db/            # SQLite vector space
├── app.py                    # Application runner
├── requirements.txt          # Python dependencies
├── .env.example              # Environment variables template
├── Dockerfile                # Image instructions
└── docker-compose.yml        # Orchestration script
```

---

## ⚙️ Setup & Installation

### Prerequisites
- Python 3.11+ installed.
- IBM Cloud account with Watsonx.ai service credentials.
- A Watsonx Project ID.

### 1. Clone & Set Up Directory
```bash
git clone https://github.com/your-username/Fin-Lit-Tutor.git
cd Fin-Lit-Tutor
python -m venv venv

# Windows:
venv\Scripts\activate
# macOS/Linux:
source venv/bin/activate

pip install -r requirements.txt
```

### 2. Configure Environment Variables
Create a `.env` file in the root directory:
```bash
cp .env.example .env
```
Open `.env` and fill in your details:
```env
SECRET_KEY=your-flask-secret-key-32-chars-long
IBM_CLOUD_API_KEY=your-ibm-cloud-api-key
IBM_WATSONX_PROJECT_ID=your-watsonx-project-id
IBM_WATSONX_URL=https://us-south.ml.cloud.ibm.com
```

### 3. Initialize & Run
```bash
python app.py
```
Open [http://localhost:5000](http://localhost:5000) in your browser.

### 4. Admin Seeding
1. Access the app and sign in with default credentials:
   - **Email**: `REDACTED_EMAIL`
   - **Password**: `REDACTED_PASSWORD`
2. Navigate to the **Admin Dashboard** (`/admin`) → **Knowledge Base**.
3. Click **Seed Built-in Financial Knowledge** to ingest standard financial literacy literature into ChromaDB.
4. You can upload custom RBI or SEBI PDF flyers using the dynamic upload form.

---

## 🧬 AI & RAG Architecture

```
                 +-------------------+
                 |    User Query     |
                 +---------+---------+
                           |
                           v
              +------------+------------+
              |  Granite Embeddings API |
              +------------+------------+
                           |
                           v
              +------------+------------+
              |  ChromaDB Vector Store  |
              +------------+------------+
                           |
                           v
              +------------+------------+
              | Retrieved Context (k=3) |
              +------------+------------+
                           |
                           v
              +------------+------------+
              |  Llama-3.3-70B-Instruct  |
              +------------+------------+
                           |
                           v
                +----------+----------+
                | Multilingual Answer |
                +---------------------+
```

* **Conversational Speed Rule**: To optimize response times, common conversational greetings (like "hi" or "hello") bypass embedding generation and DB lookup entirely, generating responses instantly. LLM completions are capped at 450 tokens to keep answers screen-friendly.

---

## 📸 Screenshots

*(Placeholders for presentation)*
* **Homepage**: Interactive 3D particle banner with language selection.
* **Dashboard**: Glassmorphic widgets showing XP roadmap, dynamic Financial Score, and emergency warning panels.
* **AI Chat**: Multilingual chatbot with bubble TTS triggers and glowing audio cues.

---

## 🔮 Future Enhancements

* **Voice-to-Voice AI**: Integrate Web Speech Recognition directly to allow users to ask questions by voice.
* **WhatsApp Chatbot**: Expand RAG service endpoints to allow SMS/WhatsApp educational queries.
* **Unified Payments Sandbox**: Simulated digital sandbox for UPI/POS mock trials to train elderly citizens safely.
* **Micro-Courses**: Expand achievements to award formal certifications upon completing mini-modules.

---

## 📄 License

Distributed under the MIT License. See [LICENSE](LICENSE) for more information.

---

## 👤 Author

* **Khushwnat Sahu** - Lead Frontend & AI Integration Engineer.
* Project built with Watsonx.ai for IBM Hackathon Showcase.
