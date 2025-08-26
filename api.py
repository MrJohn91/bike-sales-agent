#!/usr/bin/env python3
"""
FastAPI Server for Bike Shop Sales Agent
Clean separation between API layer and business logic
"""

from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from bike_agent import BikeShopAgent, ChatRequest, ChatResponse
from database import init_database, close_database, db_manager

# ============================================================================
# FASTAPI APP
# ============================================================================

app = FastAPI(
    title="Bike Sales Agent", 
    version="1.0.0",
    description="AI-powered sales agent for bike shop with RAG and Ollama integration"
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize the bike shop agent
agent = BikeShopAgent()

# ============================================================================
# STARTUP
# ============================================================================

@app.on_event("startup")
async def startup_event():
    """Initialize the agent and database on server startup"""
    await init_database()
    await agent.initialize()

@app.on_event("shutdown")
async def shutdown_event():
    """Clean up database connection on server shutdown"""
    await close_database()

# ============================================================================
# API ENDPOINTS
# ============================================================================

@app.get("/")
async def root():
    """Root endpoint with basic info"""
    return {
        "message": "Bike Shop Sales Agent API", 
        "status": "ready",
        "features": ["RAG product search", "Ollama Llama3", "Lead generation", "FAQ support"],
        "conversation_info": {
            "usage": "Use /chat with or without conversation_id",
            "new_chat": "POST /chat without conversation_id starts new chat",
            "continue_chat": "POST /chat with conversation_id continues existing chat"
        }
    }

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    """
    Main chat endpoint for customer conversations
    
    Handles:
    - Product recommendations using RAG
    - Customer context tracking
    - Lead generation
    - FAQ responses
    - Auto-generates conversation_id
    """
    try:
        # Auto-generate conversation_id if not provided
        conversation_id = request.conversation_id
        if not conversation_id:
            import uuid
            conversation_id = str(uuid.uuid4())
            print(f"New conversation started: {conversation_id}")
        else:
            print(f"📞 Continuing conversation: {conversation_id}")
        
        return await agent.process_message(
            message=request.message,
            conversation_id=conversation_id,
            customer_context=request.customer_context
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Chat processing failed: {str(e)}")

@app.get("/products")
async def get_products():
    """Get all available bike products"""
    try:
        return {
            "products": agent.get_all_products(),
            "total": len(agent.get_all_products())
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get products: {str(e)}")

@app.get("/search")
async def search_products(query: str, limit: int = 5):
    """
    Search products using vector similarity (RAG)
    
    Args:
        query: Search query (e.g., "mountain bike for trails")
        limit: Maximum number of results to return
    """
    try:
        if not query.strip():
            raise HTTPException(status_code=400, detail="Query cannot be empty")
            
        results = agent.search_products(query, limit)
        return {
            "query": query,
            "results": results,
            "total_found": len(results)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Search failed: {str(e)}")



@app.get("/leads")
async def get_leads(limit: int = 20, status: str = None):
    """Get recent leads from database"""
    try:
        leads = await db_manager.get_leads(limit=limit, status=status)
        return {
            "leads": leads,
            "total": len(leads),
            "timestamp": datetime.utcnow().isoformat()
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get leads: {str(e)}")

@app.get("/analytics")
async def get_analytics():
    """Get business analytics and metrics"""
    try:
        analytics = await db_manager.get_analytics()
        return analytics
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get analytics: {str(e)}")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Test database connection
        conversation_stats = await db_manager.get_conversation_stats()
        db_healthy = True
    except:
        conversation_stats = {}
        db_healthy = False
    
    return {
        "status": "healthy" if db_healthy else "degraded", 
        "timestamp": datetime.utcnow().isoformat(),
        "agent_ready": agent.sentence_model is not None,
        "products_loaded": len(agent.products) > 0,
        "database_connected": db_healthy,
        "conversation_stats": conversation_stats
    }

# ============================================================================
# RUN SERVER
# ============================================================================

if __name__ == "__main__":
    import uvicorn
    print("Starting Bike Sales Agent...")
    print("API docs will be available at: http://localhost:8000/docs")
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)