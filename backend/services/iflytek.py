# v2
"""讯飞语音识别"""
import hashlib, hmac, base64, json, time, os
import asyncio
import websockets
from urllib.parse import quote

AID = os.getenv("IFLYTEK_APP_ID", "e57f643b")
AKEY = os.getenv("IFLYTEK_API_KEY", "74c7e81dcc5355a47e9b75292e7e3389")
ASEC = os.getenv("IFLYTEK_API_SECRET", "YTEwM2Y0YWEzYmY5MTUxMjVjNTMzNjI0")
HOST = "iat-api.xfyun.cn"
HAS = bool(AID and AKEY and ASEC)

def _auth_url():
    d = time.strftime("%a, %d %b %Y %H:%M:%S GMT", time.gmtime())
    so = "host: " + HOST + "\ndate: " + d + "\nGET /v2/iat HTTP/1.1"
    sig = base64.b64encode(hmac.new(ASEC.encode(), so.encode(), hashlib.sha256).digest()).decode()
    ao = 'api_key="' + AKEY + '", algorithm="hmac-sha256", headers="host date request-line", signature="' + sig + '"'
    a = base64.b64encode(ao.encode()).decode()
    return "wss://iat-api.xfyun.cn/v2/iat?authorization=" + quote(a) + "&date=" + quote(d) + "&host=" + quote(HOST)

async def recognize_audio(audio_data: bytes):
    if not HAS:
        return "", "mock"
    try:
        raw = audio_data
        if raw[:4] == b"RIFF":
            raw = raw[44:]
        
        sz = len(raw)
        ns = sum(1 for i in range(0, sz, 2) if i+2 <= sz and raw[i:i+2] != b'\x00\x00')
        print("[XF] PCM size=" + str(sz) + " non-zero=" + str(ns) + "/" + str(sz//2))

        if sz < 100:
            print("[XF] Audio too short")
            return "", "error"

        u = _auth_url()
        async with websockets.connect(u, ping_interval=5, close_timeout=5) as ws:
            b64 = base64.b64encode(raw).decode()
            await ws.send(json.dumps({
                "common": {"app_id": AID},
                "business": {"language": "zh_cn", "domain": "iat", "accent": "mandarin", "vad_eos": 5000},
                "data": {"status": 0, "format": "audio/L16;rate=16000", "encoding": "raw", "audio": b64},
            }))
            await ws.send(json.dumps({"data": {"status": 2, "format": "audio/L16;rate=16000", "encoding": "raw", "audio": ""}}))

            text = ""
            for i in range(10):
                try:
                    msg = await asyncio.wait_for(ws.recv(), timeout=3)
                    r = json.loads(msg)
                    print("[XF] msg " + str(i) + ": code=" + str(r.get("code")) + " type=" + str(r.get("data",{}).get("status","?")))
                    if r.get("code") != 0:
                        print("[XF] err: " + str(r.get("message","")))
                        break
                    rd = r.get("data", {}).get("result", {})
                    for seg in rd.get("ws", []):
                        for cw in seg.get("cw", []):
                            text += cw.get("w", "")
                    if r.get("data", {}).get("status") == 2:
                        break
                except asyncio.TimeoutError:
                    print("[XF] timeout waiting for msg " + str(i))
                    break
                except Exception:
                    break

            print("[XF] final text: " + repr(text))
            return (text, "success") if text else ("", "error")
    except Exception as e:
        print("[XF] exc: " + type(e).__name__ + ": " + str(e)[:100])
        return "", "error"