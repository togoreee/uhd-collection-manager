#!/bin/bash
# 自动检测新电影，不用停Emby

cd /volume3/tools

# 读Emby数据库（只读模式，不用停容器）
python3 << 'PYEOF'
import sqlite3
import csv
import uuid
import os

# 只读模式打开数据库
uri = "file:/volume3/docker/emby/config/data/library.db?mode=ro"
conn = sqlite3.connect(uri, uri=True)
cursor = conn.cursor()

cursor.execute("SELECT guid, ProviderIds, Path FROM MediaItems WHERE type=5")
rows = cursor.fetchall()
conn.close()

tmdb_to_item = {}
tmdb_to_path = {}
for guid_blob, provider_ids, path in rows:
    if not provider_ids:
        continue
    
    try:
        guid_str = str(uuid.UUID(bytes_le=guid_blob))
    except:
        continue
    
    for part in provider_ids.split('|'):
        if part.startswith('Tmdb='):
            tmdb_id = part.replace('Tmdb=', '')
            if tmdb_id.isdigit():
                tmdb_to_item[tmdb_id] = guid_str
                tmdb_to_path[tmdb_id] = path
            break

# 读旧的映射
old_count = 0
if os.path.exists('emby_tmdb_itemid_map.csv'):
    with open('emby_tmdb_itemid_map.csv', 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        old_count = sum(1 for _ in reader)

new_count = len(tmdb_to_item)

# 如果数量没变，直接退出
if old_count == new_count:
    print("没有新电影")
    exit(0)

print(f"发现新电影！旧: {old_count} -> 新: {new_count}")

# 导出新映射
with open('emby_tmdb_itemid_map.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['tmdb_id', 'emby_item_id'])
    for tmdb, itemid in tmdb_to_item.items():
        writer.writerow([tmdb, itemid])

# 导出路径
path_map = {}
for tmdb, path in tmdb_to_path.items():
    host_path = path
    if path.startswith('/movie16T/'):
        host_path = '/volume2/media16/PTCHDBITS.UHD.BLU-RAY/' + path[len('/movie16T/'):]
    elif path.startswith('/movie8T/'):
        host_path = '/volume1/BDVol01/' + path[len('/movie8T/'):]
    elif path.startswith('/SGNB4K/'):
        host_path = '/volume1/115mount/istoreOS_mount/SGNB4K/' + path[len('/SGNB4K/'):]
    elif path.startswith('/media/4K电影/'):
        host_path = '/volume1/115mount/istoreOS_mount/4K电影/' + path[len('/media/4K电影/'):]
    elif path.startswith('/media/华语电影/'):
        host_path = '/volume1/115mount/istoreOS_mount/华语电影/' + path[len('/media/华语电影/'):]
    path_map[tmdb] = host_path

with open('local_tmdb_path_from_emby.csv', 'w', encoding='utf-8', newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['tmdb_id', 'path'])
    for tmdb, p in path_map.items():
        writer.writerow([tmdb, p])

# 合并新电影到总表
import requests
import time

API_KEY = "59d058b7c533142ae6f8aa04a2af8da8"

all_rows = []
existing_tmdb = set()
fieldnames = []
with open('digiraw_movies_full_merged.csv', 'r', encoding='utf-8-sig') as f:
    reader = csv.DictReader(f)
    fieldnames = reader.fieldnames
    if 'genre' not in fieldnames:
        fieldnames.append('genre')
    for r in reader:
        all_rows.append(r)
        existing_tmdb.add(r['tmdb_id'])

new_movies = [tmdb for tmdb in tmdb_to_item.keys() if tmdb not in existing_tmdb]
print(f"需要合并 {len(new_movies)} 部新电影")

for i, tid in enumerate(new_movies):
    print(f"  [{i+1}/{len(new_movies)}] 拉取 {tid}...")
    
    cn_title = ''
    title = ''
    year = ''
    genres = []
    rating = ''
    
    try:
        url = f"https://api.themoviedb.org/3/movie/{tid}?api_key={API_KEY}&language=zh-CN"
        resp = requests.get(url, timeout=10)
        if resp.status_code == 200:
            data = resp.json()
            title = data.get('title', '')
            cn_title = data.get('title', '')
            year = str(data.get('release_date', ''))[:4]
            rating = str(data.get('vote_average', ''))
            genres = [g['name'] for g in data.get('genres', [])]
    except:
        pass
    
    all_rows.append({
        'tmdb_id': tid,
        'title': title,
        'year': year,
        'native_4k': '0',
        'mastering': 'Upscaled 4K',
        'hdr': 'HDR10',
        'dolby_vision': 'Dolby Vision',
        'audio': 'TBC',
        'tmdb_rating': rating,
        'cn_title': cn_title,
        'genre': '/'.join(genres)
    })
    time.sleep(0.2)

# 保存总表
with open('digiraw_movies_full_merged.csv', 'w', encoding='utf-8-sig', newline='') as f:
    writer = csv.DictWriter(f, fieldnames=fieldnames)
    writer.writeheader()
    writer.writerows(all_rows)

# 重启后端
os.system("pkill -f api_server.py 2>/dev/null; sleep 1; nohup python3 api_server.py > api_server.log 2>&1 &")

print("✅ 更新完成！")
PYEOF
