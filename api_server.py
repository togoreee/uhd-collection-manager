import csv
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app)

CSV_FILE = "digiraw_movies_full_merged.csv"
LOCAL_MOVIE_CSV = "local_tmdb_path_from_emby.csv"
EMBY_MAP_CSV = "emby_tmdb_itemid_map.csv"
EMBY_BASE_URL = "http://10.0.6.2:8096"
EMBY_SERVER_ID = "98239b65922740e796b15765c9a4d82a"

import sqlite3
import uuid
import os

def check_emby_update():
    """检查Emby电影数量有没有变，变了就重新加载CSV"""
    global all_rows, local_tmdb_set, emby_map
    
    try:
        # 读Emby数据库
        uri = "file:/volume3/docker/emby/config/data/library.db?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT guid, ProviderIds FROM MediaItems WHERE type=5")
        rows = cursor.fetchall()
        conn.close()
        
        # 统计有多少个tmdb_id
        new_count = 0
        new_emby_map = {}
        for guid_blob, provider_ids in rows:
            if not provider_ids:
                continue
            for part in provider_ids.split('|'):
                if part.startswith('Tmdb='):
                    tmdb_id = part.replace('Tmdb=', '')
                    if tmdb_id.isdigit():
                        new_count += 1
                        try:
                            new_emby_map[tmdb_id] = str(uuid.UUID(bytes_le=guid_blob))
                        except:
                            pass
                    break
        
        # 对比旧的
        old_count = len(emby_map)
        if new_count != old_count:
            print(f"检测到新电影！{old_count} -> {new_count}")
            
            # 更新emby_map
            emby_map = new_emby_map
            
            # 保存映射文件
            with open('emby_tmdb_itemid_map.csv', 'w', encoding='utf-8', newline='') as f:
                writer = csv.writer(f)
                writer.writerow(['tmdb_id', 'emby_item_id'])
                for tmdb, itemid in emby_map.items():
                    writer.writerow([tmdb, itemid])
            
            # 找出新电影
            existing_tmdb = set(r['tmdb_id'] for r in all_rows)
            new_movies = [tid for tid in emby_map.keys() if tid not in existing_tmdb]
            
            if new_movies:
                print(f"合并 {len(new_movies)} 部新电影...")
                API_KEY = "59d058b7c533142ae6f8aa04a2af8da8"
                import requests
                import time
                
                for tid in new_movies:
                    print(f"  拉取 {tid}...")
                    try:
                        url = f"https://api.themoviedb.org/3/movie/{tid}?api_key={API_KEY}&language=zh-CN"
                        resp = requests.get(url, timeout=10)
                        if resp.status_code == 200:
                            data = resp.json()
                            all_rows.append({
                                'tmdb_id': tid,
                                'title': data.get('title', ''),
                                'year': str(data.get('release_date', ''))[:4],
                                'native_4k': '0',
                                'mastering': 'Upscaled 4K',
                                'hdr': 'HDR10',
                                'dolby_vision': 'Dolby Vision',
                                'audio': 'TBC',
                                'tmdb_rating': str(data.get('vote_average', '')),
                                'cn_title': data.get('title', ''),
                                'genre': '/'.join([g['name'] for g in data.get('genres', [])])
                            })
                    except:
                        pass
                    time.sleep(0.2)
                
                # 保存总表
                fieldnames = list(all_rows[0].keys())
                with open('digiraw_movies_full_merged.csv', 'w', encoding='utf-8-sig', newline='') as f:
                    writer = csv.DictWriter(f, fieldnames=fieldnames)
                    writer.writeheader()
                    writer.writerows(all_rows)
            
            # 更新本地馆藏集合
            local_tmdb_set = set(emby_map.keys())
            
    except Exception as e:
        print(f"自动检查失败: {e}")


import sqlite3
import uuid
import os
import requests as req

def check_new_movies():
    """自动检查Emby有没有新电影"""
    try:
        uri = "file:/volume3/docker/emby/config/data/library.db?mode=ro"
        conn = sqlite3.connect(uri, uri=True)
        cursor = conn.cursor()
        cursor.execute("SELECT guid, ProviderIds, Path FROM MediaItems WHERE type=5")
        rows = cursor.fetchall()
        conn.close()
        
        tmdb_count = 0
        for guid_blob, provider_ids, path in rows:
            if not provider_ids:
                continue
            for part in provider_ids.split('|'):
                if part.startswith('Tmdb='):
                    tmdb_count += 1
                    break
        
        # 读旧的映射数量
        old_count = 0
        if os.path.exists('emby_tmdb_itemid_map.csv'):
            with open('emby_tmdb_itemid_map.csv', 'r', encoding='utf-8') as f:
                import csv
                reader = csv.DictReader(f)
                old_count = sum(1 for _ in reader)
        
        # 如果数量变了，跑更新
        if tmdb_count != old_count:
            print(f"检测到新电影！{old_count} -> {tmdb_count}")
            os.system("cd /volume3/tools && python3 auto_update.py")
    except Exception as e:
        print(f"自动检查失败: {e}")


all_rows = []
with open(CSV_FILE, "r", encoding="utf-8-sig") as f:
    reader = csv.DictReader(f)
    for r in reader:
        all_rows.append(r)

local_tmdb_set = set()
with open(LOCAL_MOVIE_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        if r["tmdb_id"].isdigit():
            local_tmdb_set.add(r["tmdb_id"])

emby_map = {}
with open(EMBY_MAP_CSV, "r", encoding="utf-8") as f:
    reader = csv.DictReader(f)
    for r in reader:
        emby_map[r["tmdb_id"]] = r["emby_item_id"]

@app.route('/')
def index():
    check_emby_update()
    check_new_movies()
    page = int(request.args.get("page",1))
    q = request.args.get("q","").lower()
    decade = request.args.get("decade","")
    min_score = request.args.get("min_score","")
    onlynative = request.args.get("onlynative","0")
    has_local_filter = request.args.get("has_local","")
    genre_filter = request.args.get("genre","")
    sort = request.args.get("sort","year")
    dire = int(request.args.get("dir",-1))

    filtered = []
    for row in all_rows:
        tid = row["tmdb_id"]
        ttl = row["title"].lower()
        cn_ttl = row.get("cn_title","").lower()
        yr = row["year"]
        rating = row.get("tmdb_rating","")
        native4k = row["native_4k"]

        if q:
            if q not in tid and q not in ttl and q not in cn_ttl:
                continue
        if decade:
            try:
                yr_num = int(yr)
                decade_num = int(decade)
                if not (decade_num <= yr_num <= decade_num + 9):
                    continue
            except:
                continue
        if min_score:
            try:
                if float(rating) < float(min_score):
                    continue
            except Exception:
                pass
        if onlynative == "1":
            if native4k != "1":
                continue
        if has_local_filter:
            if has_local_filter == "1" and tid not in local_tmdb_set:
                continue
            if has_local_filter == "0" and tid in local_tmdb_set:
                continue
        if genre_filter:
            if genre_filter not in row.get("genre", ""):
                continue

        row["has_local"] = "1" if tid in local_tmdb_set else "0"
        if tid in emby_map:
            item_id = emby_map[tid]
            row["emby_url"] = f"{EMBY_BASE_URL}/web/index.html#!/item?id={item_id}&serverId={EMBY_SERVER_ID}"
        else:
            row["emby_url"] = ""
        filtered.append(row)

    def sort_key(r):
        v = r.get(sort, "")
        try:
            return (0, float(v))
        except:
            return (1, str(v))

    filtered.sort(key=sort_key, reverse=(dire == -1))

    page_size = 50
    total = len(filtered)
    total_page = (total + page_size -1) // page_size
    start = (page-1)*page_size
    page_data = filtered[start:start+page_size]

    return jsonify({
        "total": total,
        "total_page": total_page,
        "current_page": page,
        "list": page_data
    })

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=8081, debug=False)
