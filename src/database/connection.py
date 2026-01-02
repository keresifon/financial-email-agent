"""
MongoDB connection manager for the Financial Email Agent.

This module handles MongoDB connections with connection pooling,
retry logic, and health checks.
"""

from typing import Optional, Dict, Any
from pymongo import MongoClient
from pymongo.database import Database
from pymongo.collection import Collection
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase

from ..config.models import MongoDBConfig
from ..utils.logger import get_logger
from ..utils.retry import retry

logger = get_logger(__name__)


class MongoDBConnection:
    """Synchronous MongoDB connection manager."""

    def __init__(self, config: MongoDBConfig):
        """
        Initialize MongoDB connection.

        Args:
            config: MongoDB configuration
        """
        self.config = config
        self._client: Optional[MongoClient] = None
        self._db: Optional[Database] = None

    @retry(max_attempts=3, delay=1.0, exceptions=(ConnectionFailure, ServerSelectionTimeoutError))
    def connect(self) -> Database:
        """
        Establish connection to MongoDB.

        Returns:
            Database instance

        Raises:
            ConnectionFailure: If connection fails
        """
        if self._client is None:
            logger.info(f"Connecting to MongoDB: {self.config.database}")
            
            self._client = MongoClient(
                self.config.connection_string,
                serverSelectionTimeoutMS=self.config.timeout_ms,
                connectTimeoutMS=self.config.timeout_ms,
                socketTimeoutMS=self.config.timeout_ms,
            )
            
            # Test connection
            self._client.admin.command('ping')
            logger.success("Successfully connected to MongoDB")
            
            self._db = self._client[self.config.database]
        
        return self._db

    def disconnect(self):
        """Close MongoDB connection."""
        if self._client:
            logger.info("Closing MongoDB connection")
            self._client.close()
            self._client = None
            self._db = None

    def get_database(self) -> Database:
        """
        Get database instance.

        Returns:
            Database instance
        """
        if self._db is None:
            return self.connect()
        return self._db

    def get_collection(self, collection_name: str) -> Collection:
        """
        Get collection instance.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection instance
        """
        db = self.get_database()
        return db[collection_name]

    def health_check(self) -> bool:
        """
        Check if database connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if self._client:
                self._client.admin.command('ping')
                return True
        except Exception as e:
            logger.error(f"Database health check failed: {e}")
        return False

    def create_indexes(self):
        """Create indexes for all collections."""
        db = self.get_database()
        
        # Emails collection indexes
        emails = db[self.config.collections.emails]
        emails.create_index("message_id", unique=True)
        emails.create_index("received_date")
        emails.create_index("sender")
        emails.create_index("classification")
        emails.create_index([("subject", "text"), ("body", "text")])
        
        # Invoices collection indexes
        invoices = db[self.config.collections.invoices]
        invoices.create_index("invoice_number", unique=True)
        invoices.create_index("vendor")
        invoices.create_index("date")
        invoices.create_index("total_amount")
        
        # Receipts collection indexes
        receipts = db[self.config.collections.receipts]
        receipts.create_index("receipt_number")
        receipts.create_index("merchant")
        receipts.create_index("date")
        receipts.create_index("total_amount")
        
        # Bank statements collection indexes
        statements = db[self.config.collections.bank_statements]
        statements.create_index("account_number")
        statements.create_index("statement_date")
        statements.create_index("bank_name")
        
        # Expense reports collection indexes
        expenses = db[self.config.collections.expense_reports]
        expenses.create_index("report_id")
        expenses.create_index("employee")
        expenses.create_index("date")
        expenses.create_index("total_amount")
        
        logger.info("Database indexes created successfully")

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


class AsyncMongoDBConnection:
    """Asynchronous MongoDB connection manager."""

    def __init__(self, config: MongoDBConfig):
        """
        Initialize async MongoDB connection.

        Args:
            config: MongoDB configuration
        """
        self.config = config
        self._client: Optional[AsyncIOMotorClient] = None
        self._db: Optional[AsyncIOMotorDatabase] = None

    async def connect(self) -> AsyncIOMotorDatabase:
        """
        Establish async connection to MongoDB.

        Returns:
            Database instance

        Raises:
            ConnectionFailure: If connection fails
        """
        if self._client is None:
            logger.info(f"Connecting to MongoDB (async): {self.config.database}")
            
            self._client = AsyncIOMotorClient(
                self.config.connection_string,
                serverSelectionTimeoutMS=self.config.timeout_ms,
                connectTimeoutMS=self.config.timeout_ms,
                socketTimeoutMS=self.config.timeout_ms,
            )
            
            # Test connection
            await self._client.admin.command('ping')
            logger.success("Successfully connected to MongoDB (async)")
            
            self._db = self._client[self.config.database]
        
        return self._db

    async def disconnect(self):
        """Close async MongoDB connection."""
        if self._client:
            logger.info("Closing MongoDB connection (async)")
            self._client.close()
            self._client = None
            self._db = None

    async def get_database(self) -> AsyncIOMotorDatabase:
        """
        Get async database instance.

        Returns:
            Database instance
        """
        if self._db is None:
            return await self.connect()
        return self._db

    async def get_collection(self, collection_name: str):
        """
        Get async collection instance.

        Args:
            collection_name: Name of the collection

        Returns:
            Collection instance
        """
        db = await self.get_database()
        return db[collection_name]

    async def health_check(self) -> bool:
        """
        Check if async database connection is healthy.

        Returns:
            True if healthy, False otherwise
        """
        try:
            if self._client:
                await self._client.admin.command('ping')
                return True
        except Exception as e:
            logger.error(f"Async database health check failed: {e}")
        return False

    async def __aenter__(self):
        """Async context manager entry."""
        await self.connect()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit."""
        await self.disconnect()


# Global connection instances
_sync_connection: Optional[MongoDBConnection] = None
_async_connection: Optional[AsyncMongoDBConnection] = None


def get_sync_connection(config: MongoDBConfig) -> MongoDBConnection:
    """
    Get or create synchronous MongoDB connection.

    Args:
        config: MongoDB configuration

    Returns:
        MongoDBConnection instance
    """
    global _sync_connection
    
    if _sync_connection is None:
        _sync_connection = MongoDBConnection(config)
        _sync_connection.connect()
    
    return _sync_connection


def get_async_connection(config: MongoDBConfig) -> AsyncMongoDBConnection:
    """
    Get or create asynchronous MongoDB connection.

    Args:
        config: MongoDB configuration

    Returns:
        AsyncMongoDBConnection instance
    """
    global _async_connection
    
    if _async_connection is None:
        _async_connection = AsyncMongoDBConnection(config)
    
    return _async_connection


def close_connections():
    """Close all database connections."""
    global _sync_connection, _async_connection
    
    if _sync_connection:
        _sync_connection.disconnect()
        _sync_connection = None
    
    if _async_connection:
        # Note: This is synchronous, should be called from async context
        _async_connection = None

# Made with Bob
