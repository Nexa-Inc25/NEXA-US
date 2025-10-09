"""
Week 2: Redis Cache Manager for Spec Lookups
Speeds up audit analysis by caching spec cross-references
"""
import redis
import os
import json
import hashlib
import pickle
from typing import Any, Optional, Dict
import logging
from datetime import datetime

logger = logging.getLogger(__name__)

class RedisCacheManager:
    """Manages Redis caching for spec lookups and audit analysis"""
    
    def __init__(self):
        # Get Redis URL from Render environment
        self.redis_url = os.getenv('REDIS_URL', 'redis://localhost:6379/0')
        
        try:
            self.client = redis.from_url(
                self.redis_url,
                decode_responses=False,  # For binary data
                socket_connect_timeout=5,
                socket_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            # Test connection
            self.client.ping()
            logger.info(f"✅ Redis connected: {self.redis_url.split('@')[-1]}")
            self.enabled = True
        except Exception as e:
            logger.warning(f"⚠️ Redis not available: {e}. Using memory cache only.")
            self.enabled = False
            self.memory_cache = {}  # Fallback
    
    def get_cache_key(self, query: str, cache_type: str = "spec_lookup") -> str:
        """Generate cache key from query"""
        query_hash = hashlib.sha256(query.encode()).hexdigest()[:16]
        return f"{cache_type}:{query_hash}"
    
    def get(self, query: str, cache_type: str = "spec_lookup") -> Optional[Any]:
        """Get cached result for query"""
        if not self.enabled:
            # Fallback to memory cache
            key = self.get_cache_key(query, cache_type)
            return self.memory_cache.get(key)
        
        try:
            key = self.get_cache_key(query, cache_type)
            cached = self.client.get(key)
            
            if cached:
                logger.debug(f"Cache hit: {key}")
                # Try to deserialize
                try:
                    return json.loads(cached)
                except:
                    return pickle.loads(cached)
            
            logger.debug(f"Cache miss: {key}")
            return None
            
        except Exception as e:
            logger.error(f"Redis get error: {e}")
            return None
    
    def set(self, query: str, value: Any, cache_type: str = "spec_lookup", ttl: int = 3600):
        """Cache result with TTL (default 1 hour)"""
        if not self.enabled:
            # Fallback to memory cache
            key = self.get_cache_key(query, cache_type)
            self.memory_cache[key] = value
            return
        
        try:
            key = self.get_cache_key(query, cache_type)
            
            # Serialize based on type
            try:
                serialized = json.dumps(value)
            except:
                serialized = pickle.dumps(value)
            
            self.client.setex(key, ttl, serialized)
            logger.debug(f"Cached: {key} (TTL: {ttl}s)")
            
        except Exception as e:
            logger.error(f"Redis set error: {e}")
    
    def delete_pattern(self, pattern: str):
        """Delete all keys matching pattern (e.g., 'spec_lookup:*')"""
        if not self.enabled:
            # Clear memory cache
            self.memory_cache = {k: v for k, v in self.memory_cache.items() if not k.startswith(pattern.replace('*', ''))}
            return
        
        try:
            cursor = 0
            deleted = 0
            
            while True:
                cursor, keys = self.client.scan(cursor, match=pattern, count=100)
                if keys:
                    deleted += self.client.delete(*keys)
                if cursor == 0:
                    break
            
            logger.info(f"Deleted {deleted} keys matching {pattern}")
            
        except Exception as e:
            logger.error(f"Redis delete pattern error: {e}")
    
    def get_stats(self) -> Dict:
        """Get cache statistics"""
        if not self.enabled:
            return {
                "enabled": False,
                "type": "memory",
                "keys": len(self.memory_cache)
            }
        
        try:
            info = self.client.info("stats")
            memory = self.client.info("memory")
            
            return {
                "enabled": True,
                "type": "redis",
                "total_connections": info.get("total_connections_received", 0),
                "commands_processed": info.get("total_commands_processed", 0),
                "hit_rate": info.get("keyspace_hits", 0) / max(1, info.get("keyspace_hits", 0) + info.get("keyspace_misses", 0)),
                "memory_used_mb": memory.get("used_memory", 0) / 1024 / 1024,
                "keys": self.client.dbsize()
            }
            
        except Exception as e:
            logger.error(f"Redis stats error: {e}")
            return {"enabled": False, "error": str(e)}
    
    def invalidate_spec_cache(self):
        """Clear all spec-related cache when specs are updated"""
        self.delete_pattern("spec_lookup:*")
        self.delete_pattern("audit_analysis:*")
        logger.info("Spec cache invalidated")

# Global cache instance
cache = RedisCacheManager()

# Helper functions for easy integration
def cached_spec_lookup(query: str, compute_fn=None, ttl: int = 3600):
    """Decorator-style caching for spec lookups"""
    # Check cache
    result = cache.get(query, "spec_lookup")
    if result is not None:
        return result
    
    # Compute if not cached
    if compute_fn:
        result = compute_fn(query)
        cache.set(query, result, "spec_lookup", ttl)
        return result
    
    return None

def cached_audit_analysis(audit_hash: str, compute_fn=None, ttl: int = 7200):
    """Cache audit analysis results for 2 hours"""
    result = cache.get(audit_hash, "audit_analysis")
    if result is not None:
        return result
    
    if compute_fn:
        result = compute_fn(audit_hash)
        cache.set(audit_hash, result, "audit_analysis", ttl)
        return result
    
    return None
