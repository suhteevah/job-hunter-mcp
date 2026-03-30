"""
Wraith MCP Client — Spawn openclaw-browser and send MCP JSON-RPC calls from Python.
Enables autonomous Wraith CDP apply swarm without a Claude session.
"""
import sys
sys.stdout.reconfigure(encoding='utf-8', errors='replace')

import json
import os
import subprocess
import threading
import time


class WraithMCPClient:
    """Communicate with Wraith browser via MCP stdio protocol."""

    def __init__(self, binary_path=None, chrome_path=None, flaresolverr_url=None):
        self.binary = binary_path or r"J:\wraith-browser\target\release\openclaw-browser.exe"
        self.chrome = chrome_path or r"C:\Program Files\Google\Chrome\Application\chrome.exe"
        self.flaresolverr = flaresolverr_url or "http://localhost:8191"
        self.proc = None
        self.request_id = 0
        self._response_buf = b""
        self._responses = {}
        self._reader_thread = None
        self._running = False

    def start(self):
        """Spawn the Wraith MCP server process."""
        env = os.environ.copy()
        env["WRAITH_FLARESOLVERR"] = self.flaresolverr
        env["WRAITH_CDP_CHROME"] = self.chrome
        env["WRAITH_CDP_AUTO"] = "true"

        self.proc = subprocess.Popen(
            [self.binary, "serve", "--transport", "stdio"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            env=env,
        )
        self._running = True
        self._reader_thread = threading.Thread(target=self._read_stdout, daemon=True)
        self._reader_thread.start()

        # Send initialize
        self._send_request("initialize", {
            "protocolVersion": "2024-11-05",
            "capabilities": {},
            "clientInfo": {"name": "mega-pipeline", "version": "1.0"}
        })
        time.sleep(1)  # Let it start up
        # Send initialized notification
        self._send_notification("notifications/initialized", {})
        time.sleep(0.5)

    def stop(self):
        """Shutdown the Wraith process."""
        self._running = False
        if self.proc:
            try:
                self.proc.stdin.close()
                self.proc.terminate()
                self.proc.wait(timeout=5)
            except Exception:
                try:
                    self.proc.kill()
                except Exception:
                    pass

    def _read_stdout(self):
        """Background thread reading JSON-RPC responses from stdout."""
        while self._running and self.proc and self.proc.poll() is None:
            try:
                line = self.proc.stdout.readline()
                if not line:
                    break
                line = line.strip()
                if not line:
                    continue
                try:
                    msg = json.loads(line)
                    if "id" in msg:
                        self._responses[msg["id"]] = msg
                except json.JSONDecodeError:
                    pass
            except Exception:
                break

    def _send_request(self, method: str, params: dict, timeout: int = 60) -> dict:
        """Send a JSON-RPC request and wait for response."""
        self.request_id += 1
        rid = self.request_id
        msg = {
            "jsonrpc": "2.0",
            "id": rid,
            "method": method,
            "params": params,
        }
        raw = json.dumps(msg) + "\n"
        self.proc.stdin.write(raw.encode())
        self.proc.stdin.flush()

        # Wait for response
        deadline = time.time() + timeout
        while time.time() < deadline:
            if rid in self._responses:
                resp = self._responses.pop(rid)
                if "error" in resp:
                    return {"error": resp["error"]}
                return resp.get("result", {})
            time.sleep(0.1)
        return {"error": {"message": f"Timeout after {timeout}s"}}

    def _send_notification(self, method: str, params: dict):
        """Send a JSON-RPC notification (no response expected)."""
        msg = {
            "jsonrpc": "2.0",
            "method": method,
            "params": params,
        }
        raw = json.dumps(msg) + "\n"
        self.proc.stdin.write(raw.encode())
        self.proc.stdin.flush()

    def call_tool(self, tool_name: str, arguments: dict = None, timeout: int = 60) -> dict:
        """Call an MCP tool and return the result."""
        result = self._send_request("tools/call", {
            "name": tool_name,
            "arguments": arguments or {},
        }, timeout=timeout)
        if "error" in result:
            return {"error": result["error"]}
        # Extract text content from MCP response
        content = result.get("content", [])
        texts = []
        for item in content:
            if isinstance(item, dict) and item.get("type") == "text":
                texts.append(item.get("text", ""))
        return {"text": "\n".join(texts), "raw": result}

    # ─── Convenience methods ────────────────────────────────────────

    def navigate(self, url: str) -> str:
        """Navigate to URL, return snapshot text."""
        r = self.call_tool("browse_navigate", {"url": url}, timeout=30)
        return r.get("text", r.get("error", {}).get("message", "error"))

    def snapshot(self) -> str:
        """Get current page snapshot."""
        r = self.call_tool("browse_snapshot", {}, timeout=15)
        return r.get("text", "")

    def click(self, ref: str) -> str:
        """Click element by @ref ID."""
        r = self.call_tool("browse_click", {"ref": ref}, timeout=15)
        return r.get("text", "")

    def fill(self, ref: str, value: str) -> str:
        """Fill input by @ref ID."""
        r = self.call_tool("browse_fill", {"ref": ref, "value": value}, timeout=15)
        return r.get("text", "")

    def select(self, ref: str, value: str) -> str:
        """Select dropdown value by @ref ID."""
        r = self.call_tool("browse_select", {"ref": ref, "value": value}, timeout=15)
        return r.get("text", "")

    def custom_dropdown(self, ref: str, value: str) -> str:
        """Handle React Select / custom dropdown by @ref ID."""
        r = self.call_tool("browse_custom_dropdown", {"ref": ref, "value": value}, timeout=15)
        return r.get("text", "")

    def upload_file(self, ref: str, file_path: str) -> str:
        """Upload file to input by @ref ID."""
        r = self.call_tool("browse_upload_file", {"ref": ref, "path": file_path}, timeout=15)
        return r.get("text", "")

    def submit_form(self, ref: str = None) -> str:
        """Submit form, optionally by clicking a specific @ref."""
        if ref:
            return self.click(ref)
        r = self.call_tool("browse_submit_form", {}, timeout=15)
        return r.get("text", "")

    def eval_js(self, script: str) -> str:
        """Execute JavaScript on the page."""
        r = self.call_tool("browse_eval_js", {"script": script}, timeout=15)
        return r.get("text", "")

    def extract(self, format: str = "markdown") -> str:
        """Extract page content."""
        r = self.call_tool("browse_extract", {"format": format}, timeout=15)
        return r.get("text", "")

    def engine_status(self) -> str:
        """Check current engine status (native/cdp)."""
        r = self.call_tool("browse_engine_status", {}, timeout=10)
        return r.get("text", "")

    def navigate_cdp(self, url: str) -> str:
        """Navigate using CDP (Chrome) engine for React SPAs. Returns snapshot text."""
        r = self.call_tool("browse_navigate_cdp", {"url": url}, timeout=30)
        return r.get("text", r.get("error", {}).get("message", "error"))

    def dedup_check(self, url: str) -> str:
        """Check if URL already applied."""
        r = self.call_tool("swarm_dedup_check", {"url": url}, timeout=10)
        return r.get("text", "")

    def dedup_record(self, url: str, company: str, title: str, platform: str) -> str:
        """Record application in dedup tracker."""
        r = self.call_tool("swarm_dedup_record", {
            "url": url, "company": company, "title": title, "platform": platform
        }, timeout=10)
        return r.get("text", "")

    def verify_submission(self) -> str:
        """Verify if form submission succeeded."""
        r = self.call_tool("swarm_verify_submission", {}, timeout=15)
        return r.get("text", "")


if __name__ == "__main__":
    # Quick test
    client = WraithMCPClient()
    print("Starting Wraith MCP client...")
    client.start()
    print("Engine status:", client.engine_status())
    print("Navigating to test page...")
    snap = client.navigate("https://boards.greenhouse.io/anthropic/jobs/4178191008")
    print(f"Got {len(snap)} chars")
    print(snap[:500])
    client.stop()
    print("Done.")
