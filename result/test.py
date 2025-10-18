# ...existing code...
import base64
from pathlib import Path

try:
    from PIL import Image
except Exception:
    raise SystemExit("请先安装 Pillow：pip install --user pillow")

out = Path("/workspaces/MCP-SEE-Client/result/generated.png")
out.parent.mkdir(parents=True, exist_ok=True)

# 生成 200x100 红色图片
img = Image.new("RGB", (200, 100), (220, 50, 50))
img.save(out, "PNG")

# 打印二进制的 Base64 编码（在终端中更安全）
b = out.read_bytes()
print(base64.b64encode(b).decode("ascii"))
# ...existing code...