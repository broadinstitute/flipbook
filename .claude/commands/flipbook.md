---
description: Run flipbook image viewer with the given parameters
argument-hint: [directory or options]
allowed-tools: Bash, Read
---

<objective>
Run the flipbook image viewer server in the background and open browser to view images.

Flipbook provides a browser-based interface for viewing and annotating images.
</objective>

<process>
1. Parse user arguments to check if a port was specified with `-p` or `--port`
2. If no port specified, find an available port starting from 8080:
   - Check if port is in use: `lsof -i :PORT`
   - If in use, try next port (8081, 8082, etc.)
3. Start flipbook server in background with the available port:
   - Run: `python3 -m flipbook $ARGUMENTS -p PORT &`
   - Use Bash tool with `run_in_background: true`
4. Wait briefly for server to start (1-2 seconds)
5. Open browser to `http://127.0.0.1:PORT`:
   - macOS: `open http://127.0.0.1:PORT`
6. Report the server URL and background process info to user

Note: If user already specified `-p` or `--port` in their arguments, use that port and don't search for available ports.
</process>

<success_criteria>
- Available port found (or user-specified port used)
- Flipbook server starts in background
- Browser opens to correct URL
- User informed of URL and how to stop the server
</success_criteria>
