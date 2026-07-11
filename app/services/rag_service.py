
"""
RAG Pipeline Service
IBM Watsonx.ai + ChromaDB + LangChain
"""

import os
import logging
import traceback
from typing import List, Dict, Optional, Tuple
from dotenv import load_dotenv

# Resolve absolute path to .env file relative to the project root (two levels up from this app/services/ directory)
_current_dir = os.path.dirname(os.path.abspath(__file__))
_project_root = os.path.dirname(os.path.dirname(_current_dir))
_env_path = os.path.join(_project_root, ".env")
load_dotenv(_env_path)
logger = logging.getLogger(__name__)

# Ensure the logger always emits at DEBUG+ in development so failures are visible.
if not logger.handlers:
    _h = logging.StreamHandler()
    _h.setFormatter(logging.Formatter("[RAG] %(levelname)s %(message)s"))
    logger.addHandler(_h)
logger.setLevel(logging.DEBUG)


class RAGPipeline:
    """
    Retrieval-Augmented Generation pipeline using:
    - IBM Watsonx.ai (Llama / Granite) for LLM inference via the chat API
    - IBM Granite Embedding for vector embeddings
    - ChromaDB as vector store
    - LangChain for orchestration
    """

    def __init__(self):
        self.enabled = os.getenv("ENABLE_RAG", "True").lower() == "true"
        self.vectorstore = None
        self.llm = None
        self.embeddings = None
        self.retriever = None
        self._initialized = False
        self._retrieval_ready = False
        self.init_error = None

        if self.enabled:
            self._initialize()

    # ── Initialization ─────────────────────────────────────────

    def _initialize(self) -> None:
        """Initialize all RAG components.

        Each sub-step is attempted independently so a failure in one
        step does not hide the actual error in another, and partial
        initialisation is still reported accurately.
        """
        llm_ok = emb_ok = vs_ok = False
        self.init_error = None

        # ── Step 1: Watsonx LLM ────────────────────────────────
        try:
            self._init_watsonx_llm()
            llm_ok = True
        except Exception as e:
            self.init_error = f"Watsonx LLM Init Error: {e}\n{traceback.format_exc()}"
            logger.error(
                "❌ Watsonx LLM init failed — chatbot will use fallback responses.\n"
                "  Check IBM_CLOUD_API_KEY and IBM_WATSONX_PROJECT_ID in .env\n"
                f"  Error: {e}\n"
                f"  {traceback.format_exc()}"
            )

        # ── Step 2: Embeddings ─────────────────────────────────
        try:
            self._init_embeddings()
            emb_ok = True
        except Exception as e:
            err_msg = f"Embeddings Init Error: {e}\n{traceback.format_exc()}"
            self.init_error = (self.init_error + "\n" + err_msg) if self.init_error else err_msg
            logger.error(
                "❌ Embeddings init failed — retrieval will be disabled.\n"
                f"  Error: {e}\n"
                f"  {traceback.format_exc()}"
            )

        # ── Step 3: Vector store (only if embeddings succeeded) ─
        if emb_ok:
            try:
                self._init_vectorstore()
                vs_ok = True
            except Exception as e:
                err_msg = f"Vector Store Init Error: {e}\n{traceback.format_exc()}"
                self.init_error = (self.init_error + "\n" + err_msg) if self.init_error else err_msg
                logger.error(
                    "❌ ChromaDB init failed — retrieval will be disabled.\n"
                    f"  Error: {e}\n"
                    f"  {traceback.format_exc()}"
                )

        self._initialized = llm_ok  # generation works as long as LLM is up
        self._retrieval_ready = emb_ok and vs_ok

        if self._initialized:
            logger.info(
                f"✅ RAG Pipeline ready  |  LLM={llm_ok}  "
                f"Embeddings={emb_ok}  VectorStore={vs_ok}"
            )
        else:
            logger.warning(
                "⚠️  RAG Pipeline running in FALLBACK mode "
                "(LLM unavailable — returning static responses). "
                "Fix IBM credentials and restart."
            )

    def _init_watsonx_llm(self) -> None:
        """Initialize IBM Watsonx.ai LLM using the chat (non-deprecated) API."""
        from ibm_watsonx_ai import Credentials, APIClient
        from ibm_watsonx_ai.foundation_models import ModelInference
        from ibm_watsonx_ai.metanames import GenTextParamsMetaNames as GenParams

        self._ibm_url = os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com")
        self._ibm_apikey = os.getenv("IBM_CLOUD_API_KEY")
        self._ibm_project_id = os.getenv("IBM_WATSONX_PROJECT_ID")
        self.model_id = os.getenv(
            "GRANITE_CHAT_MODEL",
            "meta-llama/llama-3-3-70b-instruct",
        )

        # Build a ModelInference client for direct chat() calls
        credentials = Credentials(url=self._ibm_url, api_key=self._ibm_apikey)
        client = APIClient(credentials)
        client.set.default_project(self._ibm_project_id)

        self.watsonx_model = ModelInference(
            model_id=self.model_id,
            api_client=client,
        )

        # LangChain wrapper — use url/apikey/project_id (api_client is not accepted)
        from langchain_ibm import WatsonxLLM

        max_response_tokens = int(os.getenv("MAX_RESPONSE_TOKENS", 1024))
        self.llm = WatsonxLLM(
            model_id=self.model_id,
            url=self._ibm_url,
            apikey=self._ibm_apikey,
            project_id=self._ibm_project_id,
            params={
                GenParams.MAX_NEW_TOKENS: max_response_tokens,
                GenParams.TEMPERATURE: 0.3,
                GenParams.TOP_P: 0.9,
            },
        )

        logger.info(f"✅ IBM Watsonx LLM initialized: {self.model_id}")

    def _init_embeddings(self) -> None:
        """Initialize embedding model.

        Tries IBM Granite embeddings first; falls back to a local
        sentence-transformer model.  Raises on total failure so the
        caller can log it properly.
        """
        ibm_err = None
        try:
            from langchain_ibm import WatsonxEmbeddings
            self.embeddings = WatsonxEmbeddings(
                model_id=os.getenv("GRANITE_EMBEDDING_MODEL", "ibm/slate-125m-english-rtrvr"),
                url=os.getenv("IBM_WATSONX_URL", "https://us-south.ml.cloud.ibm.com"),
                apikey=os.getenv("IBM_CLOUD_API_KEY"),
                project_id=os.getenv("IBM_WATSONX_PROJECT_ID"),
            )
            logger.info("✅ IBM Granite Embeddings initialized")
            return
        except Exception as e:
            ibm_err = e
            logger.warning(f"IBM embeddings unavailable ({e}), trying local fallback…")

        try:
            from langchain_community.embeddings import HuggingFaceEmbeddings
            self.embeddings = HuggingFaceEmbeddings(
                model_name="sentence-transformers/all-MiniLM-L6-v2"
            )
            logger.info("✅ Fallback: HuggingFace Embeddings initialized")
        except Exception as e:
            raise RuntimeError(
                f"All embedding initialisations failed.\n"
                f"  IBM error: {ibm_err}\n"
                f"  HuggingFace error: {e}"
            ) from e

    def _init_vectorstore(self) -> None:
        """Initialize ChromaDB vector store.

        Resolves CHROMA_PERSIST_DIR to an absolute path so it works
        regardless of the process working directory.
        """
        from langchain_chroma import Chroma

        _project_root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), "..", "..")
        )
        _raw_dir = os.getenv("CHROMA_PERSIST_DIR", "data/chroma_db")
        persist_dir = (
            _raw_dir if os.path.isabs(_raw_dir)
            else os.path.join(_project_root, _raw_dir)
        )
        os.makedirs(persist_dir, exist_ok=True)

        collection_name = os.getenv("CHROMA_COLLECTION_NAME", "financial_knowledge")

        self.vectorstore = Chroma(
            collection_name=collection_name,
            embedding_function=self.embeddings,
            persist_directory=persist_dir,
        )
        self.retriever = self.vectorstore.as_retriever(
            search_type="similarity",
            search_kwargs={
                "k": int(os.getenv("RAG_TOP_K_RESULTS", 3)),
            },
        )
        logger.info(f"✅ ChromaDB vector store initialized at: {persist_dir}")

    # ── Document Indexing ──────────────────────────────────────

    def index_document(self, file_path: str, metadata: Dict) -> Tuple[bool, int]:
        """Index a document into the vector store. Returns (success, chunk_count)."""
        if not self._initialized:
            return False, 0

        try:
            docs = self._load_document(file_path)
            chunks = self._split_documents(docs, metadata)
            self.vectorstore.add_documents(chunks)
            logger.info(f"✅ Indexed {len(chunks)} chunks from {file_path}")
            return True, len(chunks)
        except Exception as e:
            logger.error(f"❌ Document indexing failed: {e}")
            return False, 0

    def _load_document(self, file_path: str) -> List:
        """Load document using appropriate loader."""
        from langchain_community.document_loaders import (
            PyPDFLoader, TextLoader, Docx2txtLoader
        )

        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".pdf":
            loader = PyPDFLoader(file_path)
        elif ext in [".doc", ".docx"]:
            loader = Docx2txtLoader(file_path)
        else:
            loader = TextLoader(file_path, encoding="utf-8")

        return loader.load()

    def _split_documents(self, docs: List, metadata: Dict) -> List:
        """Split documents into chunks."""
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", 512)),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", 64)),
            separators=["\n\n", "\n", ".", "!", "?", " "],
        )
        chunks = splitter.split_documents(docs)
        for chunk in chunks:
            chunk.metadata.update(metadata)
        return chunks

    def index_text(self, text: str, metadata: Dict) -> Tuple[bool, int]:
        """Index raw text into the vector store."""
        if not self._initialized:
            return False, 0
        try:
            from langchain_core.documents import Document
            from langchain_text_splitters import RecursiveCharacterTextSplitter

            splitter = RecursiveCharacterTextSplitter(
                chunk_size=int(os.getenv("RAG_CHUNK_SIZE", 512)),
                chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", 64)),
            )
            doc = Document(page_content=text, metadata=metadata)
            chunks = splitter.split_documents([doc])
            self.vectorstore.add_documents(chunks)
            return True, len(chunks)
        except Exception as e:
            logger.error(f"❌ Text indexing failed: {e}")
            return False, 0

    # ── Query & Generation ─────────────────────────────────────

    def retrieve(self, query: str, k: Optional[int] = None) -> List[Dict]:
        """Retrieve relevant documents for a query, filtered by similarity threshold."""
        if not getattr(self, "_retrieval_ready", False) or self.vectorstore is None:
            return []

        if k is None:
            k = int(os.getenv("RAG_TOP_K_RESULTS", 3))

        threshold = float(os.getenv("RAG_SIMILARITY_THRESHOLD", 0.7))

        try:
            # Attempt to retrieve with relevance scores
            docs_and_scores = self.vectorstore.similarity_search_with_relevance_scores(query, k=k)
            logger.debug(f"Retrieved {len(docs_and_scores)} raw chunks with scores.")

            docs = []
            for doc, score in docs_and_scores:
                logger.debug(f"Chunk from '{doc.metadata.get('source_name')}' score: {score:.4f} (threshold: {threshold})")
                if score >= threshold:
                    docs.append(doc)
                else:
                    logger.info(f"Skipping chunk from '{doc.metadata.get('source_name')}' due to low relevance score: {score:.4f}")
            
            # Fallback to the top chunk if no chunks pass the strict similarity threshold
            if not docs and docs_and_scores:
                top_doc, top_score = docs_and_scores[0]
                logger.info(f"[RAG] No chunks met threshold {threshold}. Falling back to highest score chunk: {top_score:.4f}")
                docs.append(top_doc)
        except Exception as e:
            logger.warning(f"similarity_search_with_relevance_scores failed ({e}). Falling back to similarity_search without threshold filtering.")
            docs = self.vectorstore.similarity_search(query, k=k)

        results = []
        for doc in docs:
            results.append({
                "content": doc.page_content,
                "source": doc.metadata.get("source_name", "Knowledge Base"),
                "url": doc.metadata.get("source_url", ""),
                "category": doc.metadata.get("category", "general"),
                "title": doc.metadata.get("title", "Document"),
            })
        return results

    def generate(
        self,
        user_message: str,
        system_prompt: str,
        chat_history: List[Dict],
        language: str = "en",
    ) -> Dict:
        """
        Full RAG pipeline: retrieve + generate.
        Returns dict with 'response', 'retrieved_docs', 'tokens_used'.

        Uses the IBM Watsonx chat() API (non-deprecated) with proper
        system / user / assistant message structure.
        """
        from app.agent_instructions import is_scam_message, AGENT_INSTRUCTIONS

        # Lazy-initialization retry if it failed at startup
        if not self._initialized and self.enabled:
            logger.info("[RAG] Pipeline not initialized. Retrying initialization on-demand...")
            try:
                self._initialize()
            except Exception as e:
                logger.error(f"[RAG] On-demand initialization failed: {e}")

        # ── Scam detection ──────────────────────────────────────
        if is_scam_message(user_message):
            return {
                "response": self._scam_alert_response(language),
                "retrieved_docs": [],
                "tokens_used": 0,
                "is_scam_alert": True,
                "fallback": False,
            }

        # ── Retrieve context (Bypass for short greetings/conversational inputs to make it faster) ──
        clean_msg = user_message.lower().strip("?.! ")
        common_conversational = {
            "hi", "hello", "hey", "greetings", "good morning", "good afternoon", "good evening", "howdy", "namaste",
            "thank you", "thanks", "ok", "okay", "bye", "goodbye", "cool", "yes", "no", "sure", "fine", "awesome",
            "great", "no problem", "you're welcome", "welcome"
        }
        is_greeting = clean_msg in common_conversational or len(user_message.strip()) < 5

        if is_greeting:
            retrieved_docs = []
            logger.info("⚡ Greeting/Short query detected: Bypassing ChromaDB retrieval to speed up response.")
        else:
            k_val = int(os.getenv("RAG_TOP_K_RESULTS", 3))
            retrieved_docs = self.retrieve(user_message, k=k_val)

        context_block = ""
        if retrieved_docs:
            context_block = "\n\n📚 RETRIEVED KNOWLEDGE BASE CONTEXT:\n"
            for i, doc in enumerate(retrieved_docs, 1):
                context_block += f"\n[Doc {i}] Source: {doc['source']}\n{doc['content']}\n"

        # ── Language instruction ────────────────────────────────
        lang_instruction = ""
        lang_name = AGENT_INSTRUCTIONS["multilingual"]["supported_languages"].get(language, "English")
        if language != "en":
            lang_instruction = f"\n\nIMPORTANT: Respond in {lang_name}. Use {lang_name} script."

        # ── Build chat messages list ────────────────────────────
        # System message includes the prompt + retrieved context
        system_content = system_prompt + lang_instruction
        if context_block:
            system_content += context_block

        messages = [{"role": "system", "content": system_content}]

        # Append recent conversation history (sliced by MAX_CHAT_HISTORY_TURNS)
        max_history_turns = int(os.getenv("MAX_CHAT_HISTORY_TURNS", 6))
        for msg in chat_history[-max_history_turns:]:
            role = msg["role"]  # "user" or "assistant"
            messages.append({"role": role, "content": msg["content"]})

        # Current user turn
        messages.append({"role": "user", "content": user_message})

        # ── Fallback if LLM not ready ───────────────────────────
        if not self._initialized or not getattr(self, "watsonx_model", None):
            logger.warning(
                "RAG pipeline not initialised — returning fallback response. "
                "Check IBM credentials and restart the server."
            )
            return {
                "response": self._fallback_response(user_message, retrieved_docs, language),
                "retrieved_docs": retrieved_docs,
                "tokens_used": 0,
                "is_scam_alert": False,
                "fallback": True,
            }

        # ── Generate via chat() API ─────────────────────────────
        try:
            max_resp_tokens = int(os.getenv("MAX_RESPONSE_TOKENS", 1024))
            raw = self.watsonx_model.chat(
                messages=messages,
                params={"max_tokens": max_resp_tokens, "temperature": 0.3, "top_p": 0.9},
            )
            logger.debug(f"Watsonx raw response: {raw}")

            # chat() response shape: raw['choices'][0]['message']['content']
            choices = raw.get("choices") if isinstance(raw, dict) else None
            if not choices:
                raise ValueError(f"Unexpected Watsonx chat response shape: {raw}")

            generated = choices[0].get("message", {}).get("content", "").strip()
            if not generated:
                raise ValueError(
                    f"Watsonx returned empty content. "
                    f"Finish reason: {choices[0].get('finish_reason')}"
                )

            usage = raw.get("usage", {})
            tokens_used = usage.get("completion_tokens", 0)
            logger.info(f"✅ Generated {tokens_used} tokens for query: {user_message[:60]!r}")

            return {
                "response": generated,
                "retrieved_docs": retrieved_docs,
                "tokens_used": tokens_used,
                "is_scam_alert": False,
                "fallback": False,
            }

        except Exception as e:
            logger.error(
                f"❌ Generation failed for query {user_message[:60]!r}\n"
                f"  Error: {e}\n"
                f"  {traceback.format_exc()}"
            )
            return {
                "response": self._error_response(language),
                "retrieved_docs": retrieved_docs,
                "tokens_used": 0,
                "is_scam_alert": False,
                "fallback": True,
            }

    def _scam_alert_response(self, language: str) -> str:
        responses = {
            "en": "🚨 **FRAUD ALERT!** This message shows signs of a financial scam. NEVER share your OTP, PIN, or bank details with anyone. Call **1930** (Cyber Crime Helpline) immediately if you've already shared information.",
            "hi": "🚨 **धोखाधड़ी चेतावनी!** यह संदेश वित्तीय घोटाले के संकेत दिखाता है। कभी भी अपना OTP, PIN या बैंक विवरण किसी के साथ साझा न करें। तुरंत **1930** (साइबर क्राइम हेल्पलाइन) पर कॉल करें।",
            "ta": "🚨 **மோசடி எச்சரிக்கை!** இந்த செய்தி நிதி மோசடியின் அறிகுறிகளை காட்டுகிறது. உங்கள் OTP, PIN அல்லது வங்கி விவரங்களை யாரிடமும் பகிர்ந்துகொள்ள வேண்டாம். **1930** என்ற எண்ணை உடனடியாக அழைக்கவும்.",
        }
        return responses.get(language, responses["en"])

    def _fallback_response(self, query: str, docs: List[Dict], language: str) -> str:
        """Generate a fallback response when Watsonx is unavailable."""
        if docs:
            content = docs[0]["content"][:300]
            return f"Based on our knowledge base: {content}\n\n💡 For accurate and up-to-date information, please visit rbi.org.in or contact your bank."
        return "I'm your Fin-Lit-Tutor financial literacy assistant. I can help you with UPI payments, banking, savings, investments, and government schemes. How can I assist you today?"

    def _error_response(self, language: str) -> str:
        responses = {
            "en": "I apologize for the technical issue. Please try again in a moment. For urgent financial matters, contact your bank's helpline or visit rbi.org.in",
            "hi": "तकनीकी समस्या के लिए क्षमा करें। कृपया थोड़ी देर बाद पुनः प्रयास करें। तत्काल मामलों के लिए अपने बैंक की हेल्पलाइन से संपर्क करें।",
        }
        return responses.get(language, responses["en"])

    def get_collection_stats(self) -> Dict:
        """Get vector store statistics."""
        if not getattr(self, "_retrieval_ready", False) or self.vectorstore is None:
            return {
                "status": "offline",
                "document_count": 0,
                "llm_ready": self._initialized,
            }
        try:
            collection = self.vectorstore._collection
            count = collection.count()
            return {"status": "online", "document_count": count}
        except Exception:
            return {"status": "error", "document_count": 0}

    def delete_document_chunks(self, document_id: str) -> bool:
        """Delete all chunks for a specific document."""
        if not self._initialized:
            return False
        try:
            self.vectorstore._collection.delete(
                where={"document_id": str(document_id)}
            )
            return True
        except Exception as e:
            logger.error(f"Delete chunks failed: {e}")
            return False


# ── Singleton instance ─────────────────────────────────────────
import threading

_rag_lock = threading.Lock()
_rag_instance: Optional[RAGPipeline] = None


def get_rag_pipeline() -> RAGPipeline:
    """Get or create the singleton RAG pipeline with thread safety."""
    global _rag_instance
    with _rag_lock:
        if _rag_instance is None:
            _rag_instance = RAGPipeline()
    return _rag_instance
