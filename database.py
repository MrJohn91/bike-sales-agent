#!/usr/bin/env python3
"""
MongoDB Database Manager for Bike Shop Sales Agent
Handles persistent storage of conversations, leads, and customer data
"""

import os
from datetime import datetime, timezone
from typing import Dict, List, Optional, Any
from motor.motor_asyncio import AsyncIOMotorClient
from pymongo.errors import ConnectionFailure
import asyncio
from dotenv import load_dotenv

# env variables
load_dotenv()

class DatabaseManager:
    """
    Manages MongoDB operations for the bike shop sales agent
    """
    
    def __init__(self):
        self.client = None
        self.db = None
        self.conversations_collection = None
        self.leads_collection = None
        self.customers_collection = None
        
        # Get connection string from environment
        self.connection_string = os.getenv('DB_CONNECTION_STRING')
        if not self.connection_string:
            raise ValueError("DB_CONNECTION_STRING not found in environment variables")
    
    async def connect(self):
        """Connect to MongoDB Atlas"""
        try:
            print("🔌 Connecting to MongoDB Atlas...")
            self.client = AsyncIOMotorClient(self.connection_string)
            
            # Test connection
            await self.client.admin.command('ping')
            print("MongoDB connection successful")
            
            # Get database and collections
            self.db = self.client.bike_sales_agent
            self.conversations_collection = self.db.conversations
            self.leads_collection = self.db.leads
            self.customers_collection = self.db.customers
            
            # Creating indexes for better performance
            await self._create_indexes()
            
        except ConnectionFailure as e:
            print(f"MongoDB connection failed: {e}")
            raise
        except Exception as e:
            print(f"Database setup error: {e}")
            raise
    
    async def _create_indexes(self):
        """Create database indexes for better performance"""
        try:
            # Conversation indexes
            await self.conversations_collection.create_index("conversation_id", unique=True)
            await self.conversations_collection.create_index("updated_at")
            
            # Lead indexes
            await self.leads_collection.create_index("email")
            await self.leads_collection.create_index("created_at")
            await self.leads_collection.create_index("conversation_id")
            
            # Customer indexes
            await self.customers_collection.create_index("email", unique=True, sparse=True)
            await self.customers_collection.create_index("phone", sparse=True)
            
            print("Database indexes created")
        except Exception as e:
            print(f"⚠️ Index creation warning: {e}")
    
    async def disconnect(self):
        """Close database connection"""
        if self.client:
            self.client.close()
            print("🔌 MongoDB connection closed")
    
    # ============================================================================
    # CONVERSATION MANAGEMENT
    # ============================================================================
    
    async def save_conversation(self, conversation_id: str, messages: List[Dict], 
                               customer_context: Dict = None):
        """Save or update conversation in database"""
        try:
            conversation_data = {
                "conversation_id": conversation_id,
                "messages": messages,
                "customer_context": customer_context or {},
                "updated_at": datetime.now(timezone.utc),
                "message_count": len(messages)
            }
            
            # Upsert (update if exists, insert if not)
            await self.conversations_collection.replace_one(
                {"conversation_id": conversation_id},
                conversation_data,
                upsert=True
            )
            
            print(f"💾 Conversation {conversation_id} saved ({len(messages)} messages)")
            
        except Exception as e:
            print(f" Failed to save conversation: {e}")
    
    async def load_conversation(self, conversation_id: str) -> Optional[Dict]:
        """Load conversation from database"""
        try:
            conversation = await self.conversations_collection.find_one(
                {"conversation_id": conversation_id}
            )
            
            if conversation:
                print(f"📂 Loaded conversation {conversation_id} ({conversation.get('message_count', 0)} messages)")
                return {
                    "messages": conversation.get("messages", []),
                    "customer_context": conversation.get("customer_context", {}),
                    "updated_at": conversation.get("updated_at")
                }
            else:
                print(f"🆕 New conversation: {conversation_id}")
                return None
                
        except Exception as e:
            print(f" Failed to load conversation: {e}")
            return None
    
    async def get_conversation_stats(self) -> Dict:
        """Get conversation statistics"""
        try:
            total_conversations = await self.conversations_collection.count_documents({})
            
            # Get recent conversations (last 24 hours)
            yesterday = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            recent_conversations = await self.conversations_collection.count_documents({
                "updated_at": {"$gte": yesterday}
            })
            
            return {
                "total_conversations": total_conversations,
                "recent_conversations": recent_conversations
            }
        except Exception as e:
            print(f"Failed to get conversation stats: {e}")
            return {"total_conversations": 0, "recent_conversations": 0}
    
    # ============================================================================
    # LEAD MANAGEMENT
    # ============================================================================
    
    async def create_lead(self, conversation_id: str, customer_context: Dict, 
                         products_interested: List[Dict] = None) -> str:
        """Create a new sales lead"""
        try:
            lead_data = {
                "conversation_id": conversation_id,
                "customer_name": customer_context.get("name"),
                "email": customer_context.get("email"),
                "phone": customer_context.get("phone"),
                "products_interested": products_interested or [],
                "status": "new",
                "created_at": datetime.now(timezone.utc),
                "updated_at": datetime.now(timezone.utc),
                "source": "ai_chat"
            }
            
            result = await self.leads_collection.insert_one(lead_data)
            lead_id = str(result.inserted_id)
            
            print(f"Lead created: {lead_id} for {customer_context.get('email', 'unknown')}")
            return lead_id
            
        except Exception as e:
            print(f"Failed to create lead: {e}")
            return None
    
    async def update_lead_status(self, lead_id: str, status: str, notes: str = None):
        """Update lead status"""
        try:
            update_data = {
                "status": status,
                "updated_at": datetime.now(timezone.utc)
            }
            if notes:
                update_data["notes"] = notes
            
            await self.leads_collection.update_one(
                {"_id": lead_id},
                {"$set": update_data}
            )
            
            print(f"Lead {lead_id} updated to status: {status}")
            
        except Exception as e:
            print(f" Failed to update lead: {e}")
    
    async def get_leads(self, limit: int = 50, status: str = None) -> List[Dict]:
        """Get recent leads"""
        try:
            query = {}
            if status:
                query["status"] = status
            
            cursor = self.leads_collection.find(query).sort("created_at", -1).limit(limit)
            leads = await cursor.to_list(length=limit)
            
            # Convert ObjectId to string for JSON serialization
            for lead in leads:
                lead["_id"] = str(lead["_id"])
            
            return leads
            
        except Exception as e:
            print(f"Failed to get leads: {e}")
            return []
    
    # ============================================================================
    # CUSTOMER MANAGEMENT
    # ============================================================================
    
    async def save_customer(self, customer_context: Dict):
        """Save or update customer information"""
        try:
            if not customer_context.get("email"):
                return  # Need email as unique identifier
            
            customer_data = {
                "name": customer_context.get("name"),
                "email": customer_context.get("email"),
                "phone": customer_context.get("phone"),
                "updated_at": datetime.now(timezone.utc),
                "last_interaction": datetime.now(timezone.utc)
            }
            
            # Upsert customer
            await self.customers_collection.replace_one(
                {"email": customer_context["email"]},
                customer_data,
                upsert=True
            )
            
            print(f"Customer saved: {customer_context['email']}")
            
        except Exception as e:
            print(f"Failed to save customer: {e}")
    
    async def get_customer_by_email(self, email: str) -> Optional[Dict]:
        """Get customer by email"""
        try:
            customer = await self.customers_collection.find_one({"email": email})
            if customer:
                customer["_id"] = str(customer["_id"])
            return customer
        except Exception as e:
            print(f"Failed to get customer: {e}")
            return None
    
    # ============================================================================
    # ANALYTICS
    # ============================================================================
    
    async def get_analytics(self) -> Dict:
        """Get basic analytics"""
        try:
            # Get counts
            total_conversations = await self.conversations_collection.count_documents({})
            total_leads = await self.leads_collection.count_documents({})
            total_customers = await self.customers_collection.count_documents({})
            
            # Get recent activity (last 7 days)
            week_ago = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
            week_ago = week_ago.replace(day=week_ago.day - 7)
            
            recent_conversations = await self.conversations_collection.count_documents({
                "updated_at": {"$gte": week_ago}
            })
            
            recent_leads = await self.leads_collection.count_documents({
                "created_at": {"$gte": week_ago}
            })
            
            return {
                "totals": {
                    "conversations": total_conversations,
                    "leads": total_leads,
                    "customers": total_customers
                },
                "last_7_days": {
                    "conversations": recent_conversations,
                    "leads": recent_leads
                },
                "timestamp": datetime.now(timezone.utc).isoformat()
            }
            
        except Exception as e:
            print(f"Failed to get analytics: {e}")
            return {}

# ============================================================================
# GLOBAL DATABASE INSTANCE
# ============================================================================

# Global database manager instance
db_manager = DatabaseManager()

async def init_database():
    """Initialize database connection"""
    await db_manager.connect()

async def close_database():
    """Close database connection"""
    await db_manager.disconnect()