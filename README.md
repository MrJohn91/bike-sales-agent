# 🚴 Bike AI Sales Assistant

An intelligent sales assistant for bike shops powered by AI, featuring RAG (Retrieval-Augmented Generation), conversation persistence, and automatic lead generation.

## ✨ Features

- **Smart Product Search**: AI-powered product recommendations using vector similarity
- **Natural Conversations**: Chat naturally about bikes and get personalized recommendations
- **Persistent Memory**: Conversations saved to MongoDB - customers can return anytime
- **Automatic Lead Generation**: Captures customer interest and contact information
- **Business Analytics**: Track conversations, leads, and customer insights
- **24/7 Availability**: Always ready to help customers find the perfect bike

## 🚀 Quick Start

### Prerequisites

- Python 3.8+
- [Ollama](https://ollama.ai/) installed and running
- MongoDB Atlas account (free tier available)

### Installation

1. **Clone the repository**:
   ```bash
   git clone https://github.com/MrJohn91/bike-sales-agent.git
   cd bike-sales-agent
   ```

2. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Setup Ollama**:
   ```bash
   # Install Ollama (if not already installed)
   curl -fsSL https://ollama.ai/install.sh | sh
   
   # Start Ollama server
   ollama serve
   
   # Pull the required model
   ollama pull llama3.2:3b
   ```

4. **Configure environment variables**:
   Create a `.env` file in the project root:
   ```env
   # MongoDB Atlas connection
   DB_CONNECTION_STRING=mongodb+srv://username:password@cluster.mongodb.net/?retryWrites=true&w=majority
   DB_NAME=bike_sales_agent
   
   # Ollama server
   OLLAMA_URL=http://localhost:11434
   ```

5. **Run the application**:
   ```bash
   uvicorn api:app --host 0.0.0.0 --port 8000 --reload
   ```

6. **Access the API**:
   - API Documentation: http://localhost:8000/docs
   - Health Check: http://localhost:8000/health

## 📡 API Endpoints

### Core Endpoints
- `POST /chat` - Main conversation endpoint
  - With `conversation_id`: Continue existing chat
  - Without `conversation_id`: Start new chat (auto-generates ID)
- `GET /products` - Get all available bikes
- `GET /search?query=mountain bike` - AI-powered product search

### Business Intelligence
- `GET /leads` - View captured sales leads
- `GET /analytics` - Business metrics and insights
- `GET /health` - System health and database status

## 🏗️ Architecture

### Core Components

- **`api.py`** - FastAPI web server with all endpoints
- **`bike_agent.py`** - AI conversation logic and business rules
- **`database.py`** - MongoDB integration for persistence
- **`embeddings.py`** - Vector search engine for product recommendations

### Data Storage

- **`data/product_catalog.json`** -  Bike inventory
- **`data/faq.txt`** - Common questions and answers
- **`data/embeddings/`** - Cached AI vectors for fast search

## 💬 Example Usage

### Starting a Conversation
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "I need a bike for weekend trail riding",
    "customer_context": {"name": "John"}
  }'
```

### Continuing a Conversation
```bash
curl -X POST "http://localhost:8000/chat" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What about something under $2000?",
    "conversation_id": "uuid-from-previous-response"
  }'
```

## 🔧 Customization

### Adding New Bikes
Update `data/product_catalog.json` with your inventory. The AI will automatically learn about new products.

### Modifying Responses
Edit `data/faq.txt` to customize answers for common questions about warranties, delivery, etc.

### Changing AI Personality
Modify the system prompts in `bike_agent.py` to match your brand voice.

## 📊 Business Benefits

- **Higher Conversion**: AI finds exactly what customers want
- **24/7 Lead Capture**: Never miss a potential sale
- **Customer Intelligence**: Build relationships across multiple visits
- **Staff Efficiency**: Handle routine inquiries automatically
- **Scalable Growth**: Cloud database grows with your business

## 🛠️ Development

### Project Structure
```
bike-sales-agent/
├── api.py                    # FastAPI web server
├── bike_agent.py            # AI conversation logic
├── database.py              # MongoDB integration
├── embeddings.py            # Vector search engine
├── requirements.txt         # Python dependencies
├── .env                     # Environment variables (create this)
├── data/
│   ├── product_catalog.json # Bike inventory
│   ├── faq.txt             # Q&A content
│   └── embeddings/         # AI search cache
└── README.md               # This file
```

### Running Tests
```bash
# Test the AI search engine
python test_embeddings.py

# Test the conversation agent
python test_agent.py

# Test database connectivity
python test_database.py
```

## 📝 License

This project is licensed under the MIT License - see the LICENSE file for details.

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## �  Documentation

- **README.md** - Quick start and API reference (this file)
- **SOLUTION.md** - Complete technical and business documentation with detailed examples

## 📞 Support

For questions or support, please open an issue on GitHub or contact the development team.

---

**Built with ❤️ for bike shops everywhere**