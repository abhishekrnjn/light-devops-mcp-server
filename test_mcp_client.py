#!/usr/bin/env python3
"""
Test MCP Client for DevOps MCP Server

This client demonstrates how to:
1. Connect to the MCP server
2. Discover available resources
3. Read resource data
4. List available tools
5. Call tools to perform DevOps operations
"""

import asyncio
import json
import subprocess
from typing import Any, Dict, List

from mcp.client.session import ClientSession
from mcp.client.stdio import stdio_client

async def test_mcp_server():
    """Test the DevOps MCP server functionality."""
    print("🚀 Starting MCP Client Test...")
    
    # Start the MCP server as a subprocess
    server_process = subprocess.Popen([
        "python", "mcp_server.py"
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        # Connect to the server
        async with stdio_client(server_process) as (read, write):
            async with ClientSession(read, write) as session:
                print("✅ Connected to MCP server")
                
                # Initialize the session
                await session.initialize()
                print("✅ Session initialized")
                
                # Test 1: List available resources
                print("\n📋 Testing resource discovery...")
                resources = await session.list_resources()
                print(f"Found {len(resources.resources)} resources:")
                for resource in resources.resources:
                    print(f"  - {resource.name}: {resource.uri}")
                    print(f"    Description: {resource.description}")
                    print(f"    MIME Type: {resource.mimeType}")
                    print()
                
                # Test 2: Read a specific resource
                print("📖 Testing resource reading...")
                if resources.resources:
                    test_resource = resources.resources[0]  # Read first resource
                    print(f"Reading resource: {test_resource.uri}")
                    try:
                        content = await session.read_resource(test_resource.uri)
                        print(f"✅ Resource content received:")
                        print(f"   Type: {type(content)}")
                        if hasattr(content, 'contents'):
                            for item in content.contents:
                                if hasattr(item, 'text'):
                                    print(f"   Content: {item.text[:200]}...")
                                else:
                                    print(f"   Content: {str(item)[:200]}...")
                    except Exception as e:
                        print(f"❌ Error reading resource: {e}")
                
                # Test 3: List available tools
                print("\n🔧 Testing tool discovery...")
                tools = await session.list_tools()
                print(f"Found {len(tools.tools)} tools:")
                for tool in tools.tools:
                    print(f"  - {tool.name}")
                    print(f"    Description: {tool.description}")
                    if hasattr(tool, 'inputSchema'):
                        required_params = tool.inputSchema.get('required', [])
                        print(f"    Required parameters: {required_params}")
                    print()
                
                # Test 4: Call a simple tool
                print("🛠️  Testing tool execution...")
                try:
                    # Test health check tool
                    health_result = await session.call_tool("check_health", {"detailed": True})
                    print("✅ Health check result:")
                    for content in health_result.content:
                        if hasattr(content, 'text'):
                            print(f"   {content.text}")
                        else:
                            print(f"   {content}")
                except Exception as e:
                    print(f"❌ Error calling health check tool: {e}")
                
                # Test 5: Call logs tool
                print("\n📝 Testing logs tool...")
                try:
                    logs_result = await session.call_tool("get_logs", {"level": "ERROR", "limit": 5})
                    print("✅ Logs result:")
                    for content in logs_result.content:
                        if hasattr(content, 'text'):
                            print(f"   {content.text}")
                        else:
                            print(f"   {content}")
                except Exception as e:
                    print(f"❌ Error calling logs tool: {e}")
                
                # Test 6: Call metrics tool
                print("\n📊 Testing metrics tool...")
                try:
                    metrics_result = await session.call_tool("get_metrics", {"metric_type": "system", "limit": 5})
                    print("✅ Metrics result:")
                    for content in metrics_result.content:
                        if hasattr(content, 'text'):
                            print(f"   {content.text}")
                        else:
                            print(f"   {content}")
                except Exception as e:
                    print(f"❌ Error calling metrics tool: {e}")
                
                print("\n🎉 MCP Client Test completed successfully!")
                
    except Exception as e:
        print(f"❌ Error during MCP client test: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        # Clean up the server process
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()
        print("🧹 Server process cleaned up")

async def test_resource_discovery():
    """Test just the resource discovery functionality."""
    print("🔍 Testing Resource Discovery Only...")
    
    server_process = subprocess.Popen([
        "python", "mcp_server.py"
    ], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    
    try:
        async with stdio_client(server_process) as (read, write):
            async with ClientSession(read, write) as session:
                await session.initialize()
                
                # List resources
                resources = await session.list_resources()
                print(f"\n📋 Available Resources ({len(resources.resources)}):")
                print("=" * 60)
                
                for i, resource in enumerate(resources.resources, 1):
                    print(f"{i}. {resource.name}")
                    print(f"   URI: {resource.uri}")
                    print(f"   Description: {resource.description}")
                    print(f"   MIME Type: {resource.mimeType}")
                    print()
                
                # List tools
                tools = await session.list_tools()
                print(f"\n🔧 Available Tools ({len(tools.tools)}):")
                print("=" * 60)
                
                for i, tool in enumerate(tools.tools, 1):
                    print(f"{i}. {tool.name}")
                    print(f"   Description: {tool.description}")
                    if hasattr(tool, 'inputSchema') and 'properties' in tool.inputSchema:
                        params = list(tool.inputSchema['properties'].keys())
                        required = tool.inputSchema.get('required', [])
                        print(f"   Parameters: {params}")
                        print(f"   Required: {required}")
                    print()
    
    finally:
        server_process.terminate()
        try:
            server_process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            server_process.kill()

if __name__ == "__main__":
    print("Choose test mode:")
    print("1. Full MCP test (resource discovery + tool calling)")
    print("2. Resource discovery only")
    
    choice = input("Enter choice (1 or 2): ").strip()
    
    if choice == "2":
        asyncio.run(test_resource_discovery())
    else:
        asyncio.run(test_mcp_server())
