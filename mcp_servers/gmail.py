"""
Gmail MCP Server

This MCP server provides tools and resources for Gmail API interactions.
It handles email fetching, attachment management, and email operations.
"""

import os
import base64
import json
from typing import Any, Sequence
from pathlib import Path

from mcp.server import Server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError

# Gmail API scopes
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/gmail.send'
]

# Initialize MCP server
app = Server("gmail-server")

# Global Gmail service
gmail_service = None


def get_gmail_service():
    """Get or create Gmail API service."""
    global gmail_service
    
    if gmail_service is not None:
        return gmail_service
    
    creds = None
    credentials_path = os.getenv('GMAIL_CREDENTIALS', 'credentials.json')
    token_path = os.getenv('GMAIL_TOKEN', 'token.json')
    
    # Load existing token
    if os.path.exists(token_path):
        creds = Credentials.from_authorized_user_file(token_path, SCOPES)
    
    # If no valid credentials, authenticate
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file(credentials_path, SCOPES)
            creds = flow.run_local_server(port=0)
        
        # Save credentials
        with open(token_path, 'w') as token:
            token.write(creds.to_json())
    
    gmail_service = build('gmail', 'v1', credentials=creds)
    return gmail_service


@app.list_tools()
async def list_tools() -> list[Tool]:
    """List available Gmail tools."""
    return [
        Tool(
            name="fetch_emails",
            description="Fetch emails from Gmail with optional filters",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query (e.g., 'is:unread', 'from:example@gmail.com')",
                        "default": "is:unread"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum number of emails to fetch",
                        "default": 50
                    },
                    "include_body": {
                        "type": "boolean",
                        "description": "Include email body in response",
                        "default": True
                    }
                }
            }
        ),
        Tool(
            name="get_attachment",
            description="Download an email attachment",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID"
                    },
                    "attachment_id": {
                        "type": "string",
                        "description": "Attachment ID"
                    },
                    "save_path": {
                        "type": "string",
                        "description": "Path to save attachment",
                        "default": "/tmp"
                    }
                },
                "required": ["message_id", "attachment_id"]
            }
        ),
        Tool(
            name="mark_as_read",
            description="Mark an email as read",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID"
                    }
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="mark_as_unread",
            description="Mark an email as unread",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID"
                    }
                },
                "required": ["message_id"]
            }
        ),
        Tool(
            name="add_label",
            description="Add a label to an email",
            inputSchema={
                "type": "object",
                "properties": {
                    "message_id": {
                        "type": "string",
                        "description": "Gmail message ID"
                    },
                    "label": {
                        "type": "string",
                        "description": "Label name to add"
                    }
                },
                "required": ["message_id", "label"]
            }
        ),
        Tool(
            name="search_emails",
            description="Search emails with Gmail query syntax",
            inputSchema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Gmail search query"
                    },
                    "max_results": {
                        "type": "integer",
                        "description": "Maximum results",
                        "default": 100
                    }
                },
                "required": ["query"]
            }
        ),
    ]


@app.call_tool()
async def call_tool(name: str, arguments: Any) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
    """Handle tool calls."""
    service = get_gmail_service()
    
    try:
        if name == "fetch_emails":
            return await fetch_emails(service, arguments)
        elif name == "get_attachment":
            return await get_attachment(service, arguments)
        elif name == "mark_as_read":
            return await mark_as_read(service, arguments)
        elif name == "mark_as_unread":
            return await mark_as_unread(service, arguments)
        elif name == "add_label":
            return await add_label(service, arguments)
        elif name == "search_emails":
            return await search_emails(service, arguments)
        else:
            return [TextContent(type="text", text=f"Unknown tool: {name}")]
    except Exception as e:
        return [TextContent(type="text", text=f"Error: {str(e)}")]


async def fetch_emails(service, args):
    """Fetch emails from Gmail."""
    query = args.get('query', 'is:unread')
    max_results = args.get('max_results', 50)
    include_body = args.get('include_body', True)
    
    # List messages
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    
    if not messages:
        return [TextContent(type="text", text="No messages found")]
    
    # Fetch full message details
    emails = []
    for msg in messages:
        message = service.users().messages().get(
            userId='me',
            id=msg['id'],
            format='full' if include_body else 'metadata'
        ).execute()
        
        email_data = parse_email(message, include_body)
        emails.append(email_data)
    
    return [TextContent(
        type="text",
        text=json.dumps(emails, indent=2)
    )]


async def get_attachment(service, args):
    """Download email attachment."""
    message_id = args['message_id']
    attachment_id = args['attachment_id']
    save_path = args.get('save_path', '/tmp')
    
    # Get attachment
    attachment = service.users().messages().attachments().get(
        userId='me',
        messageId=message_id,
        id=attachment_id
    ).execute()
    
    # Decode and save
    file_data = base64.urlsafe_b64decode(attachment['data'])
    
    # Create save path
    Path(save_path).mkdir(parents=True, exist_ok=True)
    file_path = Path(save_path) / f"{attachment_id}.bin"
    
    with open(file_path, 'wb') as f:
        f.write(file_data)
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "success": True,
            "file_path": str(file_path),
            "size": len(file_data)
        })
    )]


async def mark_as_read(service, args):
    """Mark email as read."""
    message_id = args['message_id']
    
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'removeLabelIds': ['UNREAD']}
    ).execute()
    
    return [TextContent(
        type="text",
        text=json.dumps({"success": True, "message_id": message_id})
    )]


async def mark_as_unread(service, args):
    """Mark email as unread."""
    message_id = args['message_id']
    
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'addLabelIds': ['UNREAD']}
    ).execute()
    
    return [TextContent(
        type="text",
        text=json.dumps({"success": True, "message_id": message_id})
    )]


async def add_label(service, args):
    """Add label to email."""
    message_id = args['message_id']
    label = args['label']
    
    # Get or create label
    labels = service.users().labels().list(userId='me').execute()
    label_id = None
    
    for lbl in labels.get('labels', []):
        if lbl['name'] == label:
            label_id = lbl['id']
            break
    
    if not label_id:
        # Create label
        label_obj = service.users().labels().create(
            userId='me',
            body={'name': label}
        ).execute()
        label_id = label_obj['id']
    
    # Add label to message
    service.users().messages().modify(
        userId='me',
        id=message_id,
        body={'addLabelIds': [label_id]}
    ).execute()
    
    return [TextContent(
        type="text",
        text=json.dumps({"success": True, "label": label, "label_id": label_id})
    )]


async def search_emails(service, args):
    """Search emails."""
    query = args['query']
    max_results = args.get('max_results', 100)
    
    results = service.users().messages().list(
        userId='me',
        q=query,
        maxResults=max_results
    ).execute()
    
    messages = results.get('messages', [])
    
    return [TextContent(
        type="text",
        text=json.dumps({
            "count": len(messages),
            "messages": [{"id": m['id'], "threadId": m['threadId']} for m in messages]
        })
    )]


def parse_email(message, include_body=True):
    """Parse Gmail message into structured format."""
    headers = {h['name']: h['value'] for h in message['payload']['headers']}
    
    email_data = {
        'id': message['id'],
        'thread_id': message['threadId'],
        'subject': headers.get('Subject', ''),
        'from': headers.get('From', ''),
        'to': headers.get('To', ''),
        'date': headers.get('Date', ''),
        'labels': message.get('labelIds', []),
        'snippet': message.get('snippet', ''),
        'attachments': []
    }
    
    if include_body:
        email_data['body'] = get_email_body(message['payload'])
    
    # Extract attachments info
    if 'parts' in message['payload']:
        for part in message['payload']['parts']:
            if part.get('filename'):
                email_data['attachments'].append({
                    'filename': part['filename'],
                    'mimeType': part['mimeType'],
                    'size': part['body'].get('size', 0),
                    'attachmentId': part['body'].get('attachmentId')
                })
    
    return email_data


def get_email_body(payload):
    """Extract email body from payload."""
    if 'body' in payload and 'data' in payload['body']:
        return base64.urlsafe_b64decode(payload['body']['data']).decode('utf-8')
    
    if 'parts' in payload:
        for part in payload['parts']:
            if part['mimeType'] == 'text/plain':
                if 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
            elif part['mimeType'] == 'text/html':
                if 'data' in part['body']:
                    return base64.urlsafe_b64decode(part['body']['data']).decode('utf-8')
    
    return ""


async def main():
    """Run the Gmail MCP server."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            app.create_initialization_options()
        )


if __name__ == "__main__":
    import asyncio
    asyncio.run(main())

# Made with Bob
