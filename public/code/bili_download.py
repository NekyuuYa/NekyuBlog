import socket
import threading
import json
import time
import requests
import os
import subprocess
import logging
from urllib.parse import urlparse
from collections import deque
from dataclasses import dataclass

HOST = '0.0.0.0'
PORT = 17899

# 合并输出目录，需要你填写
OUTPUT_DIR = ""

# 本地脚本能访问到的下载目录，默认工作目录下的 `bilicache`
LOCAL_DOWNLOAD_DIR = os.path.join(os.getcwd(), "bilicache")

# 默认的 User-Agent（当捕获的数据中没有 userAgent 可用时使用）
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/143.0.0.0 Safari/537.36 Edg/143.0.0.0"

# 等待配对的数据（tabId 唯一）
pending = deque()
index = {}  # { tabId: Item }


@dataclass
class Item:
    tabId: str
    data: dict
    timestamp: float


# 触发下一步处理
def handle_pair(pair_list):
    # pair_list contains two Item objects (来自 process_incoming_json)
    left = pair_list[0]
    right = pair_list[1]

    url1 = left.data.get("url")
    url2 = right.data.get("url")
    filename1 = left.data.get("fullFileName")
    filename2 = right.data.get("fullFileName")
    source = left.data.get("origin", "")
    title = left.data.get("title", "")
    subtitle = left.data.get("webUrl", "")

    # 固定 Referer 为 bilibili，并强制使用默认 User-Agent；不发送 Origin
    headers_list = [
        "Referer: https://www.bilibili.com",
        f"User-Agent: {DEFAULT_USER_AGENT}"
    ]

    # 直接在后台线程下载两个文件并合并
    t = threading.Thread(target=download_and_merge_thread, args=(url1, url2, filename1, filename2, title, subtitle, headers_list))
    t.daemon = True
    t.start()



def download_direct(url: str, filename: str, headers_list) -> str:
    """直接使用 requests 下载到 LOCAL_DOWNLOAD_DIR，返回本地路径或空字符串"""
    if not url:
        return ''
    try:
        os.makedirs(LOCAL_DOWNLOAD_DIR, exist_ok=True)
    except Exception as e:
        print(f"无法创建本地下载目录 {LOCAL_DOWNLOAD_DIR}: {e}")
        return ''

    filename = filename or os.path.basename(urlparse(url).path)
    filename = sanitize_filename(filename)
    out_path = os.path.join(LOCAL_DOWNLOAD_DIR, filename)

    # headers_list is a list like ['Referer: ...', 'User-Agent: ...']
    headers = {}
    for h in headers_list or []:
        if ':' in h:
            k, v = h.split(':', 1)
            headers[k.strip()] = v.strip()

    try:
        with requests.get(url, headers=headers, stream=True, timeout=30) as r:
            r.raise_for_status()
            with open(out_path, 'wb') as f:
                for chunk in r.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
        print(f"下载完成: {out_path}")
        return out_path
    except Exception as e:
        print(f"下载失败 ({url}): {e}")
        return ''


def download_and_merge_thread(url1, url2, filename1, filename2, title, weburl, headers_list):
    """后台线程：依次下载两个文件并合并，合并后删除源文件。"""
    path1 = download_direct(url1, filename1, headers_list)
    path2 = download_direct(url2, filename2, headers_list)
    if not path1 or not path2:
        print("至少有一个下载失败，跳过合并")
        return

    output_base = build_output_name(title, weburl)
    # 确保输出目录存在并写入到 OUTPUT_DIR
    try:
        os.makedirs(OUTPUT_DIR, exist_ok=True)
    except Exception as e:
        print(f"创建输出目录失败 {OUTPUT_DIR}: {e}")
        output_dir = os.getcwd()
    else:
        output_dir = OUTPUT_DIR

    output_file_name = f"{output_base}.mkv"
    output_file = os.path.join(output_dir, output_file_name)
    ok = merge_with_ffmpeg(path1, path2, output=output_file)
    if ok:
        for p in (path1, path2):
            try:
                if os.path.exists(p):
                    os.remove(p)
                    print(f"已删除源文件: {p}")
            except Exception as e:
                print(f"删除文件失败 {p}: {e}")


def merge_with_ffmpeg(file_a, file_b, output=None):
    """使用 ffmpeg 将两个流合并（不转码，直接拷贝）。返回 True/False。
    输出文件默认使用第一个文件名加后缀 `_merged.mkv`。
    """
    if output is None:
        base = os.path.splitext(file_a)[0]
        output = f"{base}_merged.mkv"

    cmd = [
        "ffmpeg",
        "-y",
        "-i", file_a,
        "-i", file_b,
        "-c", "copy",
        output
    ]
    try:
        print(f"运行 ffmpeg 合并: {' '.join(cmd)}")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode == 0:
            print(f"合并完成: {output}")
            return True
        else:
            print(f"ffmpeg 合并失败 (code={proc.returncode}): {proc.stderr}")
            return False
    except FileNotFoundError:
        print("ffmpeg 未找到，请先安装 ffmpeg 并确保其在 PATH 中。")
        return False


def sanitize_filename(name: str) -> str:
    # 移除或替换 Windows/Unix 不允许的文件名字符
    invalid = '<>:"/\\|?*'
    for ch in invalid:
        name = name.replace(ch, '_')
    # 额外清理控制字符
    name = ''.join(c for c in name if ord(c) >= 32)
    return name.strip()


def extract_bv_from_url(url: str) -> str:
    # 尝试从 webUrl 中提取 BV 号（例如 BV168UkBkEhc）
    try:
        # 查找 '/video/BV...' 形式
        import re
        m = re.search(r'/video/(BV[0-9A-Za-z]+)', url)
        if m:
            return m.group(1)
    except Exception:
        pass
    return ''


def build_output_name(title: str, weburl: str) -> str:
    # 去掉尾部的 "_哔哩哔哩_bilibili"
    if not title:
        title = 'output'
    clean = title
    suffix = '_哔哩哔哩_bilibili'
    if clean.endswith(suffix):
        clean = clean[: -len(suffix)]
    clean = clean.strip()
    bv = extract_bv_from_url(weburl or '')
    if bv:
        out = f"{clean}_{bv}"
    else:
        out = clean
    out = sanitize_filename(out)
    return out




def extract_json(text):
    """从文本中提取 JSON（你的格式为 {"action": ..., "data": ..., "tabId": ...} ）"""
    start = text.find('{')
    end = text.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start:end+1])
        except:
            return None
    return None


def process_incoming_json(json_packet):
    """处理已解析的 JSON 包，同时执行 tabId 配对逻辑"""

    tabId = json_packet.get("tabId")
    data = json_packet.get("data")

    if tabId is None or data is None:
        print("收到 JSON 但缺少 tabId 或 data")
        return

    # 只接受来自 https://www.bilibili.com 的 origin
    origin_val = data.get("origin") or data.get("originUrl") or data.get("Referer") or ''
    if origin_val != "https://www.bilibili.com":
        print(f"忽略非 B站来源（origin={origin_val}） tabId={tabId}")
        return

    new_item = Item(
        tabId=tabId,
        data=data,
        timestamp=time.time()
    )

    # 检查是否已有同 tabId 数据
    if tabId in index:
        old_item = index.pop(tabId)

        # 从 pending 中移除旧 item
        for item in pending:
            if item.tabId == tabId:
                pending.remove(item)
                break

        # 成对数据 → 触发事件
        handle_pair([old_item, new_item])

    else:
        # 插入新数据
        pending.append(new_item)
        index[tabId] = new_item

        print(f"已存入（等待配对） tabId={tabId}")


def handle_client(conn, addr):
    print(f"Connected by {addr}")
    buffer = ""

    with conn:
        while True:
            data = conn.recv(4096)
            if not data:
                break

            buffer += data.decode('utf-8', errors='ignore')

            json_packet = extract_json(buffer)
            if json_packet:
                print(f"收到 JSON 来自 {addr}: {json_packet}")

                process_incoming_json(json_packet)

                buffer = ""  # 清空，避免重复解析


def main():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, PORT))
        s.listen()
        print(f"Listening on port {PORT}...\n")

        while True:
            conn, addr = s.accept()
            t = threading.Thread(target=handle_client, args=(conn, addr))
            t.daemon = True
            t.start()


if __name__ == "__main__":
    main()
