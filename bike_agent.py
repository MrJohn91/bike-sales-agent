#!/usr/bin/env python3
"""
Bike Sales Agent - Core Business Logic
Handles RAG, Ollama integration, and conversation flow
"""

import json
import uuid
import httpx
import asyncio
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from pydantic import BaseModel
from dotenv import load_dotenv
from embeddings import ProductEmbeddingsManager
from database import db_manager

# Load environment variables
load_dotenv()

# ============================================================================
# DATA MODELS
# ============================================================================

class CustomerContext(BaseModel):
    name: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None

class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[str] = None
    customer_context: Optional[CustomerContext] = None

class ChatResponse(BaseModel):
    response: str
    conversation_id: str
    customer_context: CustomerContext
    recommended_products: List[Dict] = []
    action_taken: Optional[str] = None

# ============================================================================
# BIKE SHOP AGENT CLASS
# ============================================================================

class BikeShopAgent:
    """
    Core business logic for the bike shop sales agent
    Handles RAG, AI responses, and conversation management
    """
    
    def __init__(self, ollama_url: str = None, model_name: str = "llama3.2:3b"):
        # Configuration
        self.ollama_url = ollama_url or os.getenv("OLLAMA_URL")
        self.model_name = model_name
        
        # Storage
        self.conversations = {}  # Keep in-memory cache for performance
        self.products = []
        self.faq_content = ""
        
        # AI Components
        self.embeddings_manager = ProductEmbeddingsManager()
        self.sentence_model = None
        self.faiss_index = None
    
    async def initialize(self):
        """Load data and initialize AI components"""
        print("🚴 Initializing Bike Shop Agent...")
        
        # Initialize embeddings (handles products loading too)
        self.products, _, self.faiss_index, self.sentence_model = await self.embeddings_manager.initialize()
        
        # Load FAQ
        with open('data/faq.txt', 'r') as f:
            self.faq_content = f.read()
        print("Loaded FAQ content")
        
        print("Vector search ready")
        
        # Test Ollama connection
        await self._test_ollama()
        print("🚴 Agent ready!")
    

    
    async def _test_ollama(self):
        """Test Ollama connection"""
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                response = await client.get(f"{self.ollama_url}/api/tags")
                if response.status_code == 200:
                    print("Ollama connected")
                else:
                    print("⚠️ Ollama connection issue")
        except Exception as e:
            print(f"⚠️ Ollama not available: {e}")
    
    def get_all_products(self) -> List[Dict]:
        """Get all products"""
        return self.products
    
    def search_products(self, query: str, limit: int = 3) -> List[Dict]:
        """RAG: Find relevant products using vector similarity"""
        return self.embeddings_manager.search_products(query, limit)
    
    def detect_intent(self, message: str, context: CustomerContext) -> str:
        """Simple intent detection"""
        msg_lower = message.lower()
        
        # Check for contact info
        if any(word in msg_lower for word in ["email", "phone", "@", "call"]):
            return "contact_sharing"
        
        # Check for purchase interest
        if any(word in msg_lower for word in ["buy", "interested", "want", "need"]):
            if context.name and context.email and context.phone:
                return "ready_to_buy"
            return "showing_interest"
        
        # Check for FAQ topics
        if any(word in msg_lower for word in ["warranty", "delivery", "repair", "return"]):
            return "faq_question"
        
        return "general_inquiry"
    
    def extract_contact_info(self, message: str, context: CustomerContext) -> CustomerContext:
        """Extract customer contact information"""
        import re
        
        # Extract email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', message)
        if email_match and not context.email:
            context.email = email_match.group()
        
        # Extract phone
        phone_match = re.search(r'[\+]?[0-9]{8,15}', message)
        if phone_match and not context.phone:
            context.phone = phone_match.group()
        
        # Extract name (simple)
        if "name is" in message.lower() and not context.name:
            words = message.split()
            for i, word in enumerate(words):
                if word.lower() == "is" and i + 1 < len(words):
                    context.name = words[i + 1].strip('.,!?').title()
                    break
        
        return context
    
    def find_faq_answer(self, message: str) -> str:
        """Find relevant FAQ content"""
        msg_lower = message.lower()
        faq_lower = self.faq_content.lower()
        
        keywords = ["warranty", "delivery", "repair", "return", "payment", "test"]
        for keyword in keywords:
            if keyword in msg_lower and keyword in faq_lower:
                # Find relevant FAQ section
                lines = self.faq_content.split('\n')
                for i, line in enumerate(lines):
                    if keyword in line.lower():
                        # Return this line and next few lines
                        result = [line]
                        for j in range(1, 3):
                            if i + j < len(lines) and lines[i + j].strip():
                                result.append(lines[i + j])
                        return '\n'.join(result)
        return ""
    
    async def generate_response(self, message: str, history: List[Dict], 
                              context: CustomerContext, products: List[Dict], 
                              faq_answer: str) -> str:
        """Generate response using Ollama"""
        
        # System prompt
        system_prompt = f"""You are a friendly bike shop sales assistant. Help customers find the perfect bike.

Customer Info: Name={context.name or 'Unknown'}, Email={context.email or 'Not provided'}

Available Products:"""
        
        for product in products[:2]:
            system_prompt += f"\n- {product['name']} ({product['type']}) - €{product['price_eur']} - {', '.join(product['intended_use'])}"
        
        if faq_answer:
            system_prompt += f"\n\nFAQ Info: {faq_answer}"
        
        system_prompt += "\n\nBe helpful, enthusiastic but not pushy. Ask for contact info if customer shows interest."
        
        # Build conversation
        conversation = f"System: {system_prompt}\n\n"
        for msg in history[-4:]:  # Last 4 messages
            role = "Customer" if msg["role"] == "user" else "Assistant"
            conversation += f"{role}: {msg['content']}\n"
        conversation += f"Customer: {message}\nAssistant:"
        
        # Try Ollama
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    f"{self.ollama_url}/api/generate",
                    json={
                        "model": self.model_name,
                        "prompt": conversation,
                        "stream": False,
                        "options": {"temperature": 0.7, "max_tokens": 200}
                    }
                )
                
                if response.status_code == 200:
                    return response.json().get("response", "").strip()
        
        except Exception as e:
            print(f"Ollama error: {e}")
        
        # Fallback response
        if products:
            product_names = [p['name'] for p in products[:2]]
            return f"I found some great bikes for you: {', '.join(product_names)}. Would you like more details?"
        
        if faq_answer:
            return f"Here's what I found: {faq_answer[:200]}... Would you like more information?"
        
        return "I'm here to help you find the perfect bike! What are you looking for?"
    
    async def create_lead(self, context: CustomerContext, conversation_id: str, 
                         products: List[Dict] = None) -> str:
        """Create a lead in database"""
        if context.email:  # Email is minimum requirement
            try:
                # Save customer info
                await db_manager.save_customer(context.dict())
                
                # Create lead
                lead_id = await db_manager.create_lead(
                    conversation_id=conversation_id,
                    customer_context=context.dict(),
                    products_interested=products or []
                )
                
                if lead_id:
                    return f"Lead created: {lead_id}"
                else:
                    return "Lead creation failed"
            except Exception as e:
                print(f"❌ Lead creation error: {e}")
                return "Lead creation failed"
        return None
    
    async def process_message(self, message: str, conversation_id: Optional[str] = None,
                            customer_context: Optional[CustomerContext] = None) -> ChatResponse:
        """Main message processing orchestration"""
        
        # Initialize
        if not conversation_id:
            conversation_id = str(uuid.uuid4())
        
        if not customer_context:
            customer_context = CustomerContext()
        
        # Get conversation history (try database first, then memory cache)
        history = []
        
        # Try to load from database
        try:
            conversation_data = await db_manager.load_conversation(conversation_id)
            if conversation_data:
                history = conversation_data["messages"]
                # Update customer context from database if available
                if conversation_data["customer_context"] and not customer_context:
                    customer_context = CustomerContext(**conversation_data["customer_context"])
        except Exception as e:
            print(f"⚠️ Database load failed, using memory: {e}")
        
        # Fallback to memory cache
        if not history and conversation_id in self.conversations:
            history = self.conversations[conversation_id]
        
        # Initialize empty history if needed
        if not history:
            history = []
        
        # Add user message
        history.append({"role": "user", "content": message})
        
        # Extract contact info
        customer_context = self.extract_contact_info(message, customer_context)
        
        # Detect intent
        intent = self.detect_intent(message, customer_context)
        
        # Search products (RAG)
        products = self.search_products(message, limit=3)
        
        # Find FAQ answer
        faq_answer = self.find_faq_answer(message)
        
        # Generate AI response
        response_text = await self.generate_response(
            message, history, customer_context, products, faq_answer
        )
        
        # Handle lead creation
        action_taken = None
        if intent == "ready_to_buy":
            action_taken = await self.create_lead(customer_context, conversation_id, products)
        
        # Add assistant response to history
        history.append({"role": "assistant", "content": response_text})
        
        # Keep only last 10 messages for performance
        history = history[-10:]
        
        # Save to database and memory cache
        try:
            await db_manager.save_conversation(conversation_id, history, customer_context.dict())
        except Exception as e:
            print(f"⚠️ Database save failed: {e}")
        
        # Always keep in memory cache as backup
        self.conversations[conversation_id] = history
        
        return ChatResponse(
            response=response_text,
            conversation_id=conversation_id,
            customer_context=customer_context,
            recommended_products=products,
            action_taken=action_taken
        )