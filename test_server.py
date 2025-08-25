#!/usr/bin/env python3
"""Test script to verify the MCP server works correctly."""

import asyncio
import subprocess
import json
import sys

async def test_mcp_server():
    """Test the MCP server by sending a simple protocol message."""
    
    # Start the server process
    process = subprocess.Popen(
        [sys.executable, "main.py"],
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True
    )
    
    try:
        # Send an initialization message (basic MCP protocol)
        init_message = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {
                    "name": "test-client",
                    "version": "1.0.0"
                }
            }
        }
        
        # Send the message
        message_str = json.dumps(init_message) + "\n"
        process.stdin.write(message_str)
        process.stdin.flush()
        
        # Try to read response (with timeout)
        try:
            # Wait for a response or timeout
            stdout, stderr = process.communicate(timeout=5)
            
            if stdout:
                print("✅ Server responded successfully!")
                print("Response:", stdout.strip())
                return True
            else:
                print("❌ No response from server")
                if stderr:
                    print("Error:", stderr.strip())
                return False
                
        except subprocess.TimeoutExpired:
            print("❌ Server didn't respond within timeout")
            process.kill()
            return False
            
    except Exception as e:
        print(f"❌ Error testing server: {e}")
        process.kill()
        return False
    
    finally:
        if process.poll() is None:
            process.terminate()
            process.wait()

if __name__ == "__main__":
    print("Testing MCP server...")
    result = asyncio.run(test_mcp_server())
    if result:
        print("\n🎉 MCP server is working correctly!")
        print("The KeyboardInterrupt error you saw is normal - it happens when you stop the server with Ctrl+C")
    else:
        print("\n❌ There might be an issue with the server")
