#!/usr/bin/env python3
"""
Product Embeddings Manager
Handles creation, saving, and loading of product embeddings with smart caching
"""

import json
import os
import hashlib
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from typing import List, Dict, Tuple

class ProductEmbeddingsManager:
    """
    Manages product embeddings with intelligent caching based on catalog hash
    """
    
    def __init__(self, catalog_path: str = 'data/product_catalog.json'):
        self.catalog_path = catalog_path
        self.embeddings_dir = 'data/embeddings'
        self.model_name = 'all-MiniLM-L6-v2'
        
        # Files for caching
        self.hash_file = os.path.join(self.embeddings_dir, 'catalog_hash.txt')
        self.embeddings_file = os.path.join(self.embeddings_dir, 'product_embeddings.npy')
        self.index_file = os.path.join(self.embeddings_dir, 'faiss_index.bin')
        
        # Runtime data
        self.products = []
        self.product_texts = []
        self.embeddings = None
        self.faiss_index = None
        self.sentence_model = None
    
    def _calculate_catalog_hash(self) -> str:
        """Calculate hash of the product catalog file"""
        with open(self.catalog_path, 'rb') as f:
            content = f.read()
        return hashlib.md5(content).hexdigest()
    
    def _get_saved_hash(self) -> str:
        """Get the saved catalog hash"""
        if os.path.exists(self.hash_file):
            with open(self.hash_file, 'r') as f:
                return f.read().strip()
        return ""
    
    def _save_hash(self, hash_value: str):
        """Save the catalog hash"""
        os.makedirs(self.embeddings_dir, exist_ok=True)
        with open(self.hash_file, 'w') as f:
            f.write(hash_value)
    
    def _create_product_text(self, product: Dict) -> str:
        """Create searchable text representation of a product"""
        text_parts = [
            product['name'],
            product['type'],
            product['brand'],
            f"€{product['price_eur']}",
            ' '.join(product['intended_use']),
            product['frame_material'],
            product['suspension'],
            f"{product['gears']} gears",
            f"{product['weight_kg']} kg"
        ]
        
        # Add e-bike specific info
        if 'motor_power_w' in product:
            text_parts.extend([
                f"{product['motor_power_w']}W motor",
                f"{product['battery_capacity_wh']}Wh battery",
                f"{product['range_km']}km range"
            ])
            
        if 'max_load_kg' in product:
            text_parts.append(f"{product['max_load_kg']}kg max load")
            
        return " ".join(text_parts)
    
    def _needs_rebuild(self) -> bool:
        """Check if embeddings need to be rebuilt"""
        current_hash = self._calculate_catalog_hash()
        saved_hash = self._get_saved_hash()
        
        # Check if files exist
        files_exist = (
            os.path.exists(self.embeddings_file) and 
            os.path.exists(self.index_file) and
            os.path.exists(self.hash_file)
        )
        
        return not files_exist or current_hash != saved_hash
    
    def _load_products(self):
        """Load products from catalog"""
        with open(self.catalog_path, 'r') as f:
            self.products = json.load(f)
        
        # Create text representations
        self.product_texts = []
        for product in self.products:
            text = self._create_product_text(product)
            self.product_texts.append(text)
    
    def _create_embeddings(self):
        """Create embeddings and FAISS index"""
        print("🔄 Creating product embeddings...")
        
        # Initialize sentence transformer if not already done
        if self.sentence_model is None:
            print("📥 Loading sentence transformer model...")
            self.sentence_model = SentenceTransformer(self.model_name)
        
        # Create embeddings
        self.embeddings = self.sentence_model.encode(self.product_texts)
        
        # Create FAISS index
        dimension = self.embeddings.shape[1]
        self.faiss_index = faiss.IndexFlatIP(dimension)
        
        # Normalize and add to index
        faiss.normalize_L2(self.embeddings)
        self.faiss_index.add(self.embeddings.astype('float32'))
        
        print(f"✅ Created embeddings for {len(self.products)} products")
    
    def _save_embeddings(self):
        """Save embeddings and index to disk"""
        try:
            os.makedirs(self.embeddings_dir, exist_ok=True)
            
            # Save embeddings and index
            np.save(self.embeddings_file, self.embeddings)
            faiss.write_index(self.faiss_index, self.index_file)
            
            # Save hash
            current_hash = self._calculate_catalog_hash()
            self._save_hash(current_hash)
            
            print("💾 Saved embeddings to disk")
            
        except Exception as e:
            print(f"⚠️ Failed to save embeddings: {e}")
    
    def _load_embeddings(self):
        """Load embeddings and index from disk"""
        try:
            self.embeddings = np.load(self.embeddings_file)
            self.faiss_index = faiss.read_index(self.index_file)
            print("📂 Loaded embeddings from cache")
            return True
        except Exception as e:
            print(f"⚠️ Failed to load embeddings: {e}")
            return False
    
    async def initialize(self) -> Tuple[List[Dict], np.ndarray, faiss.Index, SentenceTransformer]:
        """
        Initialize embeddings system
        Returns: (products, embeddings, faiss_index, sentence_model)
        """
        print("🔍 Initializing product embeddings...")
        
        # Load products
        self._load_products()
        print(f"✅ Loaded {len(self.products)} products")
        
        # Initialize sentence transformer
        if self.sentence_model is None:
            print("📥 Loading sentence transformer...")
            self.sentence_model = SentenceTransformer(self.model_name)
        
        # Check if we need to rebuild
        if self._needs_rebuild():
            print("🔄 Product catalog changed or no cache found")
            self._create_embeddings()
            self._save_embeddings()
        else:
            print("📂 Loading cached embeddings...")
            if not self._load_embeddings():
                print("🔄 Cache loading failed, creating new embeddings...")
                self._create_embeddings()
                self._save_embeddings()
        
        print("✅ Embeddings ready!")
        return self.products, self.embeddings, self.faiss_index, self.sentence_model
    
    def search_products(self, query: str, limit: int = 5) -> List[Dict]:
        """Search products using vector similarity"""
        if self.sentence_model is None or self.faiss_index is None:
            return []
        
        # Convert query to vector
        query_embedding = self.sentence_model.encode([query])
        faiss.normalize_L2(query_embedding)
        
        # Search
        scores, indices = self.faiss_index.search(query_embedding.astype('float32'), limit)
        
        results = []
        for score, idx in zip(scores[0], indices[0]):
            if idx < len(self.products):
                product = self.products[idx].copy()
                product['similarity_score'] = float(score)
                results.append(product)
        
        return results