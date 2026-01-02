"""
Database MCP Server for Financial Email Agent

This MCP server provides tools for interacting with MongoDB to store and retrieve
financial documents, emails, and extracted data.

Tools:
- save_document: Save a financial document to MongoDB
- get_document: Retrieve a document by ID
- search_documents: Search documents with filters
- update_document: Update an existing document
- delete_document: Delete a document
- get_statistics: Get database statistics
"""

import asyncio
import json
from datetime import datetime
from typing import Any, Dict, List, Optional
from bson import ObjectId
from pymongo import ASCENDING, DESCENDING

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.config.loader import load_config
from src.database.connection import MongoDBConnection
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize MCP server
app = Server("database-server")

# Global database connection
db_connection: Optional[MongoDBConnection] = None


def serialize_doc(doc: Dict[str, Any]) -> Dict[str, Any]:
    """Convert MongoDB document to JSON-serializable format."""
    if doc is None:
        return None
    
    result = {}
    for key, value in doc.items():
        if isinstance(value, ObjectId):
            result[key] = str(value)
        elif isinstance(value, datetime):
            result[key] = value.isoformat()
        elif isinstance(value, dict):
            result[key] = serialize_doc(value)
        elif isinstance(value, list):
            result[key] = [serialize_doc(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    return result


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available database tools."""
    return [
        Tool(
            name="save_document",
            description="Save a financial document to MongoDB",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name (e.g., 'emails', 'documents', 'transactions')",
                    },
                    "document": {
                        "type": "object",
                        "description": "Document data to save",
                    },
                },
                "required": ["collection", "document"],
            },
        ),
        Tool(
            name="get_document",
            description="Retrieve a document by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Document ID (ObjectId as string)",
                    },
                },
                "required": ["collection", "document_id"],
            },
        ),
        Tool(
            name="search_documents",
            description="Search documents with filters and sorting",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "query": {
                        "type": "object",
                        "description": "MongoDB query filter (e.g., {'status': 'pending'})",
                    },
                    "sort": {
                        "type": "object",
                        "description": "Sort specification (e.g., {'created_at': -1})",
                    },
                    "limit": {
                        "type": "integer",
                        "description": "Maximum number of documents to return",
                        "default": 100,
                    },
                    "skip": {
                        "type": "integer",
                        "description": "Number of documents to skip",
                        "default": 0,
                    },
                },
                "required": ["collection"],
            },
        ),
        Tool(
            name="update_document",
            description="Update an existing document",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Document ID (ObjectId as string)",
                    },
                    "update": {
                        "type": "object",
                        "description": "Update operations (e.g., {'$set': {'status': 'processed'}})",
                    },
                },
                "required": ["collection", "document_id", "update"],
            },
        ),
        Tool(
            name="delete_document",
            description="Delete a document by ID",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name",
                    },
                    "document_id": {
                        "type": "string",
                        "description": "Document ID (ObjectId as string)",
                    },
                },
                "required": ["collection", "document_id"],
            },
        ),
        Tool(
            name="get_statistics",
            description="Get database statistics and counts",
            inputSchema={
                "type": "object",
                "properties": {
                    "collection": {
                        "type": "string",
                        "description": "Collection name (optional, if not provided returns stats for all collections)",
                    },
                },
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls."""
    global db_connection
    
    try:
        # Initialize database connection if needed
        if db_connection is None:
            config = load_config()
            db_connection = MongoDBConnection(config.mongodb)
            db_connection.connect()
        
        db = db_connection.get_database()
        
        if name == "save_document":
            collection_name = arguments["collection"]
            document = arguments["document"]
            
            # Add metadata
            document["created_at"] = datetime.utcnow()
            document["updated_at"] = datetime.utcnow()
            
            collection = db[collection_name]
            result = collection.insert_one(document)
            
            logger.info(f"Saved document to {collection_name}: {result.inserted_id}")
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "document_id": str(result.inserted_id),
                        "collection": collection_name,
                    }, indent=2)
                )
            ]
        
        elif name == "get_document":
            collection_name = arguments["collection"]
            document_id = arguments["document_id"]
            
            collection = db[collection_name]
            document = collection.find_one({"_id": ObjectId(document_id)})
            
            if document:
                logger.info(f"Retrieved document from {collection_name}: {document_id}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "document": serialize_doc(document),
                        }, indent=2)
                    )
                ]
            else:
                logger.warning(f"Document not found in {collection_name}: {document_id}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": "Document not found",
                        }, indent=2)
                    )
                ]
        
        elif name == "search_documents":
            collection_name = arguments["collection"]
            query = arguments.get("query", {})
            sort_spec = arguments.get("sort", {})
            limit = arguments.get("limit", 100)
            skip = arguments.get("skip", 0)
            
            collection = db[collection_name]
            
            # Build sort list
            sort_list = []
            for field, direction in sort_spec.items():
                sort_list.append((field, DESCENDING if direction == -1 else ASCENDING))
            
            # Execute query
            cursor = collection.find(query)
            if sort_list:
                cursor = cursor.sort(sort_list)
            cursor = cursor.skip(skip).limit(limit)
            
            documents = [serialize_doc(doc) for doc in cursor]
            count = collection.count_documents(query)
            
            logger.info(f"Found {len(documents)} documents in {collection_name} (total: {count})")
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "documents": documents,
                        "count": len(documents),
                        "total": count,
                    }, indent=2)
                )
            ]
        
        elif name == "update_document":
            collection_name = arguments["collection"]
            document_id = arguments["document_id"]
            update = arguments["update"]
            
            # Add updated_at timestamp
            if "$set" not in update:
                update["$set"] = {}
            update["$set"]["updated_at"] = datetime.utcnow()
            
            collection = db[collection_name]
            result = collection.update_one(
                {"_id": ObjectId(document_id)},
                update
            )
            
            if result.matched_count > 0:
                logger.info(f"Updated document in {collection_name}: {document_id}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "matched_count": result.matched_count,
                            "modified_count": result.modified_count,
                        }, indent=2)
                    )
                ]
            else:
                logger.warning(f"Document not found for update in {collection_name}: {document_id}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": "Document not found",
                        }, indent=2)
                    )
                ]
        
        elif name == "delete_document":
            collection_name = arguments["collection"]
            document_id = arguments["document_id"]
            
            collection = db[collection_name]
            result = collection.delete_one({"_id": ObjectId(document_id)})
            
            if result.deleted_count > 0:
                logger.info(f"Deleted document from {collection_name}: {document_id}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": True,
                            "deleted_count": result.deleted_count,
                        }, indent=2)
                    )
                ]
            else:
                logger.warning(f"Document not found for deletion in {collection_name}: {document_id}")
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": "Document not found",
                        }, indent=2)
                    )
                ]
        
        elif name == "get_statistics":
            collection_name = arguments.get("collection")
            
            if collection_name:
                # Stats for specific collection
                collection = db[collection_name]
                count = collection.count_documents({})
                
                stats = {
                    "collection": collection_name,
                    "document_count": count,
                }
                
                logger.info(f"Retrieved statistics for {collection_name}")
            else:
                # Stats for all collections
                collections = db.list_collection_names()
                stats = {
                    "database": db.name,
                    "collections": {},
                }
                
                for coll_name in collections:
                    collection = db[coll_name]
                    stats["collections"][coll_name] = {
                        "document_count": collection.count_documents({}),
                    }
                
                logger.info(f"Retrieved statistics for all collections")
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "statistics": stats,
                    }, indent=2)
                )
            ]
        
        else:
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": False,
                        "error": f"Unknown tool: {name}",
                    }, indent=2)
                )
            ]
    
    except Exception as e:
        logger.error(f"Error executing tool {name}: {e}")
        return [
            TextContent(
                type="text",
                text=json.dumps({
                    "success": False,
                    "error": str(e),
                }, indent=2)
            )
        ]


async def main():
    """Run the database MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    asyncio.run(main())

# Made with Bob
