"""
Health Check Script for Financial Email Agent

This script verifies that all required services are accessible and working.
"""

import sys
from src.config.loader import load_config
from src.database.connection import MongoDBConnection
from src.llm.client import LLMClient

def check_health():
    """Run health checks on all services."""
    print("=" * 60)
    print("Financial Email Agent - Health Check")
    print("=" * 60)
    
    all_ok = True
    
    try:
        # Load configuration
        print("\n[1/3] Loading configuration...")
        config = load_config()
        print("[OK] Configuration loaded successfully")
        
        # Check MongoDB
        print("\n[2/3] Checking MongoDB connection...")
        db = MongoDBConnection(config.mongodb)
        db.connect()
        
        if db.health_check():
            print(f"[OK] MongoDB connected: {config.mongodb.database}")
        else:
            print("[FAIL] MongoDB health check failed")
            all_ok = False
        
        db.disconnect()
        
        # Check LLM
        print("\n[3/3] Checking Ollama/LLM connection...")
        llm = LLMClient(config=config.llama)
        
        if llm.health_check():
            print(f"[OK] Ollama connected: {config.llama.model}")
        else:
            print("[FAIL] Ollama health check failed")
            all_ok = False
        
        llm.close()
        
        # Summary
        print("\n" + "=" * 60)
        if all_ok:
            print("[SUCCESS] All systems operational")
            print("=" * 60)
            return True
        else:
            print("[FAILED] Some systems failed health check")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n[ERROR] Health check failed with error: {e}")
        print("=" * 60)
        return False


if __name__ == "__main__":
    success = check_health()
    sys.exit(0 if success else 1)

# Made with Bob
