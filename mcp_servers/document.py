"""
Document MCP Server for Financial Email Agent

This MCP server provides tools for processing various document types including
PDFs, images (OCR), Excel files, and Word documents.

Tools:
- extract_pdf_text: Extract text from PDF files
- extract_image_text: Extract text from images using OCR
- parse_excel: Parse Excel/CSV files
- extract_docx_text: Extract text from Word documents
- analyze_document: Analyze document structure and metadata
"""

import asyncio
import json
import os
from pathlib import Path
from typing import Any, Dict, List, Optional

from mcp.server import Server
from mcp.types import Tool, TextContent

from src.utils.helpers import (
    extract_text_from_pdf,
    extract_text_from_image,
    parse_excel_file,
    extract_text_from_docx,
    get_file_metadata,
)
from src.utils.logger import get_logger

logger = get_logger(__name__)

# Initialize MCP server
app = Server("document-server")


@app.list_tools()
async def list_tools() -> List[Tool]:
    """List available document processing tools."""
    return [
        Tool(
            name="extract_pdf_text",
            description="Extract text content from PDF files",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the PDF file",
                    },
                    "pages": {
                        "type": "array",
                        "items": {"type": "integer"},
                        "description": "Specific pages to extract (optional, extracts all if not provided)",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="extract_image_text",
            description="Extract text from images using OCR (Tesseract)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the image file (PNG, JPG, JPEG, etc.)",
                    },
                    "language": {
                        "type": "string",
                        "description": "OCR language code (default: 'eng' for English)",
                        "default": "eng",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="parse_excel",
            description="Parse Excel or CSV files and extract data",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the Excel/CSV file",
                    },
                    "sheet_name": {
                        "type": "string",
                        "description": "Sheet name to parse (for Excel files, optional)",
                    },
                    "max_rows": {
                        "type": "integer",
                        "description": "Maximum number of rows to return",
                        "default": 1000,
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="extract_docx_text",
            description="Extract text from Word documents (.docx)",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the DOCX file",
                    },
                },
                "required": ["file_path"],
            },
        ),
        Tool(
            name="analyze_document",
            description="Analyze document metadata and structure",
            inputSchema={
                "type": "object",
                "properties": {
                    "file_path": {
                        "type": "string",
                        "description": "Path to the document file",
                    },
                },
                "required": ["file_path"],
            },
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> List[TextContent]:
    """Handle tool calls."""
    try:
        if name == "extract_pdf_text":
            file_path = arguments["file_path"]
            pages = arguments.get("pages")
            
            if not os.path.exists(file_path):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"File not found: {file_path}",
                        }, indent=2)
                    )
                ]
            
            logger.info(f"Extracting text from PDF: {file_path}")
            text = extract_text_from_pdf(file_path, pages)
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "file_path": file_path,
                        "text": text,
                        "length": len(text),
                        "pages_extracted": pages if pages else "all",
                    }, indent=2)
                )
            ]
        
        elif name == "extract_image_text":
            file_path = arguments["file_path"]
            language = arguments.get("language", "eng")
            
            if not os.path.exists(file_path):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"File not found: {file_path}",
                        }, indent=2)
                    )
                ]
            
            logger.info(f"Extracting text from image: {file_path}")
            text = extract_text_from_image(file_path, language)
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "file_path": file_path,
                        "text": text,
                        "length": len(text),
                        "language": language,
                    }, indent=2)
                )
            ]
        
        elif name == "parse_excel":
            file_path = arguments["file_path"]
            sheet_name = arguments.get("sheet_name")
            max_rows = arguments.get("max_rows", 1000)
            
            if not os.path.exists(file_path):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"File not found: {file_path}",
                        }, indent=2)
                    )
                ]
            
            logger.info(f"Parsing Excel/CSV file: {file_path}")
            data = parse_excel_file(file_path, sheet_name, max_rows)
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "file_path": file_path,
                        "data": data,
                        "row_count": len(data) if isinstance(data, list) else 0,
                        "sheet_name": sheet_name,
                    }, indent=2)
                )
            ]
        
        elif name == "extract_docx_text":
            file_path = arguments["file_path"]
            
            if not os.path.exists(file_path):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"File not found: {file_path}",
                        }, indent=2)
                    )
                ]
            
            logger.info(f"Extracting text from DOCX: {file_path}")
            text = extract_text_from_docx(file_path)
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "file_path": file_path,
                        "text": text,
                        "length": len(text),
                    }, indent=2)
                )
            ]
        
        elif name == "analyze_document":
            file_path = arguments["file_path"]
            
            if not os.path.exists(file_path):
                return [
                    TextContent(
                        type="text",
                        text=json.dumps({
                            "success": False,
                            "error": f"File not found: {file_path}",
                        }, indent=2)
                    )
                ]
            
            logger.info(f"Analyzing document: {file_path}")
            metadata = get_file_metadata(file_path)
            
            # Determine document type and extract basic info
            file_ext = Path(file_path).suffix.lower()
            analysis = {
                "file_path": file_path,
                "file_name": Path(file_path).name,
                "file_extension": file_ext,
                "file_size": metadata.get("size", 0),
                "created_at": metadata.get("created", ""),
                "modified_at": metadata.get("modified", ""),
            }
            
            # Add type-specific analysis
            if file_ext == ".pdf":
                try:
                    text = extract_text_from_pdf(file_path)
                    analysis["page_count"] = text.count("\f") + 1  # Form feed indicates page break
                    analysis["character_count"] = len(text)
                    analysis["word_count"] = len(text.split())
                except Exception as e:
                    analysis["error"] = f"Could not analyze PDF: {str(e)}"
            
            elif file_ext in [".xlsx", ".xls", ".csv"]:
                try:
                    data = parse_excel_file(file_path, max_rows=10)
                    if isinstance(data, list):
                        analysis["row_count"] = len(data)
                        analysis["column_count"] = len(data[0]) if data else 0
                        analysis["columns"] = list(data[0].keys()) if data else []
                except Exception as e:
                    analysis["error"] = f"Could not analyze Excel: {str(e)}"
            
            elif file_ext == ".docx":
                try:
                    text = extract_text_from_docx(file_path)
                    analysis["character_count"] = len(text)
                    analysis["word_count"] = len(text.split())
                    analysis["paragraph_count"] = text.count("\n\n") + 1
                except Exception as e:
                    analysis["error"] = f"Could not analyze DOCX: {str(e)}"
            
            elif file_ext in [".png", ".jpg", ".jpeg", ".gif", ".bmp"]:
                try:
                    from PIL import Image
                    with Image.open(file_path) as img:
                        analysis["image_size"] = img.size
                        analysis["image_mode"] = img.mode
                        analysis["image_format"] = img.format
                except Exception as e:
                    analysis["error"] = f"Could not analyze image: {str(e)}"
            
            return [
                TextContent(
                    type="text",
                    text=json.dumps({
                        "success": True,
                        "analysis": analysis,
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
    """Run the document MCP server."""
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
