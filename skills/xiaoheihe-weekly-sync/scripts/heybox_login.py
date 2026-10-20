#!/usr/bin/env python3
"""Open the Xiaoheihe MCP browser once so the user can scan the QR code and refresh cookies.

Usage:
    HEYBOX_DLL=/abs/path/XiaoheiheMcpServer.Stdio.dll \
    HEYBOX_COOKIE=/abs/path/account-cookie.json \
    python3 heybox_login.py [wait_seconds]

The MCP server writes the refreshed cookies back to HEYBOX_COOKIE_PATH, so the same file keeps
working for scripts/publish_weekly.cjs. The old file is backed up next to it before login.
"""
import json
import os
import shutil
import subprocess
import sys
import time

DLL = os.environ.get("HEYBOX_DLL", "")
COOKIE_FILE = os.environ.get("HEYBOX_COOKIE", "")
CHROME = os.environ.get("XIAOHEIHE_CHROMIUM_PATH", "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome")
DOTNET = os.environ.get("DOTNET", shutil.which("dotnet") or os.path.expanduser("~/.dotnet/dotnet"))
WAIT = int(sys.argv[1]) if len(sys.argv) > 1 else 240

if not DLL or not os.path.exists(DLL):
    sys.exit("HEYBOX_DLL must point to XiaoheiheMcpServer.Stdio.dll")
if not COOKIE_FILE:
    sys.exit("HEYBOX_COOKIE must point to the cookie json path")

backup = COOKIE_FILE + ".bak-before-login"
if os.path.exists(COOKIE_FILE) and not os.path.exists(backup):
    shutil.copy2(COOKIE_FILE, backup)
    print(f"backup saved: {backup}", flush=True)

env = dict(os.environ)
env["XIAOHEIHE_CHROMIUM_PATH"] = CHROME
env["XIAOHEIHE_COOKIE_PATH"] = COOKIE_FILE

proc = subprocess.Popen(
    [DOTNET, DLL, "--no-headless"],
    stdin=subprocess.PIPE,
    stdout=subprocess.PIPE,
    stderr=open("/tmp/xiaoheihe_login_stderr.log", "w"),
    env=env,
    text=True,
    bufsize=1,
)


def send(obj):
    proc.stdin.write(json.dumps(obj) + "\n")
    proc.stdin.flush()


def read_msg():
    while True:
        line = proc.stdout.readline()
        if not line:
            return None
        line = line.strip()
        if not line:
            continue
        try:
            return json.loads(line)
        except Exception:
            continue


send({"jsonrpc": "2.0", "id": 1, "method": "initialize",
      "params": {"protocolVersion": "2024-11-05", "capabilities": {},
                 "clientInfo": {"name": "xiaoheihe-login", "version": "1.0"}}})
print("init ok:", bool(read_msg()), flush=True)
send({"jsonrpc": "2.0", "method": "notifications/initialized"})
time.sleep(1)
print(f">>> browser opened, scan the QR code as the target account (waiting {WAIT}s)", flush=True)
send({"jsonrpc": "2.0", "id": 2, "method": "tools/call",
      "params": {"name": "interactive_login", "arguments": {"waitTimeoutSeconds": WAIT}}})
login = read_msg()
print("LOGIN RESULT:", json.dumps(login, ensure_ascii=False)[:600] if login else "None", flush=True)
time.sleep(1)
send({"jsonrpc": "2.0", "id": 3, "method": "tools/call",
      "params": {"name": "check_login_status", "arguments": {}}})
status = read_msg()
print("STATUS:", json.dumps(status, ensure_ascii=False)[:600] if status else "None", flush=True)
try:
    proc.terminate()
except Exception:
    pass
