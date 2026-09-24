# UHD 蓝光片单管理系统

## 这是什么？

自托管的 4K UHD 蓝光电影收藏管理系统。用 Emby 管理电影库，同时追踪每部电影的母版质量、评分、类型，帮你决定哪些值得收藏。

## 系统架构

浏览器 -> Flask后端(8081) -> 读CSV文件
                     -> TMDB API（补全中文信息）
             
Emby数据库 -> 导出你的本地收藏列表

## CSV 文件之间的关系

1. digiraw_movies_full.csv（总表，2700+部）
   - 所有发行过 UHD 蓝光的电影
   - 记录：片名、年份、评分、母版类型、HDR、音轨
   - 主键：tmdb_id

2. local_tmdb_path_from_emby.csv（你下载好的电影，emby管理刮削）
   - 从 Emby 数据库导出
   - 记录：tmdb_id + 本地文件路径
   - 和总表通过 tmdb_id 关联

3. emby_tmdb_itemid_map.csv（Emby跳转映射）
   - 从 Emby 数据库导出
   - 记录：tmdb_id + Emby内部ID
   - 用来生成跳转到 Emby 详情页的链接

## 数据怎么拼出来的？

总表里每一行数据来源：
- 英文原名、年份、母版类型：来自 Digiraw UHD 总表
- 中文译名、片子类型：来自 TMDB API
- 是否已收藏：对比 local_tmdb_path_from_emby.csv 里的 tmdb_id
- Emby跳转链接：从 emby_tmdb_itemid_map.csv 查 Emby 内部ID
- 加入日期：从 Emby 数据库读 DateCreated 字段

## 快速开始

1. 安装依赖：pip install -r requirements.txt
2. 配置：cp config.example.py config.py，编辑填 Emby 地址和 TMDB API Key
3. 初始化：docker stop emby && python3 export_from_emby.py && docker start emby
4. 运行：python3 api_server.py（后端）+ python3 -m http.server 8080（前端）

浏览器打开 http://你的IP:8080/uhd_backend_paged.html

## 文件说明

- api_server.py：Flask后端API
- uhd_backend_paged.html：前端页面
- export_from_emby.py：从Emby导出数据
- auto_update.sh：自动更新新电影
- config.py：私人配置（不公开）
- config.example.py：配置模板
- requirements.txt：Python依赖

## License

MIT
