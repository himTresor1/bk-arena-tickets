"""Call the Blender MCP server from the command line.

  blender_call.py tools                        list the server's tools
  blender_call.py call <tool> '<json args>'    call one tool
  blender_call.py exec <file.py>               run a Python file inside Blender
  blender_call.py shot <out.png> [tool]        save a screenshot of the Blender window (or another image tool)

Run with: ~/.blender-mcp/venv/bin/python scripts/blender_call.py ...
Blender must be open with the MCP add-on running (it listens on localhost:9876).
"""
import asyncio, base64, json, os, sys
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

SERVER = StdioServerParameters(command=os.path.expanduser("~/.blender-mcp/venv/bin/blender-mcp"), args=[])


async def run(argv):
    async with stdio_client(SERVER) as (read, write):
        async with ClientSession(read, write) as session:
            await session.initialize()
            cmd = argv[0]
            if cmd == "tools":
                for t in (await session.list_tools()).tools:
                    props = list((t.inputSchema or {}).get("properties", {}).keys())
                    print(f"{t.name}({', '.join(props)})")
                return 0
            image_out = None
            if cmd == "exec":
                tool, args = "execute_blender_code", {"code": open(argv[1]).read()}
            elif cmd == "shot":
                image_out = argv[1]
                tool, args = (argv[2] if len(argv) > 2 else "get_screenshot_of_window_as_image"), (json.loads(argv[3]) if len(argv) > 3 else {})
            else:
                tool, args = argv[1], (json.loads(argv[2]) if len(argv) > 2 else {})
            result = await session.call_tool(tool, args)
            for item in result.content:
                if item.type == "text":
                    print(item.text)
                elif item.type == "image":
                    path = image_out or "blender_image.png"
                    open(path, "wb").write(base64.b64decode(item.data))
                    print(f"[image saved to {path}]")
            return 1 if result.isError else 0


sys.exit(asyncio.run(run(sys.argv[1:])))
