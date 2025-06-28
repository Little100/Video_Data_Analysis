import asyncio
import yaml
import os
import json
import openpyxl
import time
import http.server
import socketserver
import threading
from functools import partial
from plugins_loader import load_plugins
from datetime import datetime

def format_large_number(num):
    """自动将大数字转换为万或亿为单位的字符串。"""
    if num >= 100000000:
        return f"{num / 100000000:.2f}亿"
    elif num >= 10000:
        return f"{num / 10000:.2f}万"
    else:
        return str(num)

def parse_refresh_interval(interval_str: str) -> int:
    unit = interval_str[-1].lower()
    value = int(interval_str[:-1])
    if unit == 's': return value
    if unit == 'm': return value * 60
    if unit == 'h': return value * 3600
    if unit == 'd': return value * 86400
    if unit == 'y': return value * 31536000
    return 86400

async def run_data_collection(config):
    output_dir = config.get('output', {}).get('directory', 'Excel')
    web_data_path = os.path.join('Web', 'dashboard_data.json')
    
    loaded_plugins = load_plugins(config)
    plugin_configs = config.get('plugins', {})
    
    # 用于存储所有插件返回的数据
    all_plugin_data = {}

    for plugin_name, plugin_module in loaded_plugins.items():
        if hasattr(plugin_module, 'fetch_user_videos'):
            plugin_specific_config = plugin_configs.get(plugin_name, {})
            print(f"开始使用插件 '{plugin_name}' 获取视频数据...")
            # 插件现在返回一个字典
            plugin_data = await plugin_module.fetch_user_videos(plugin_specific_config, output_dir)
            all_plugin_data[plugin_name] = plugin_data
            print(f"插件 '{plugin_name}' 处理完成。")

    summarize_data_for_dashboard(output_dir, web_data_path, all_plugin_data)

def summarize_data_for_dashboard(excel_dir, web_data_path, all_plugin_data):
    # 直接使用插件返回的数据，而不是从Excel文件重新读取
    print("开始处理仪表板数据...")
    
    # 从插件数据中获取视频数据和粉丝数
    bilibili_data = all_plugin_data.get('bilibili_fetcher', {})
    all_videos = bilibili_data.get('videos', [])
    follower_count = bilibili_data.get('follower_count', 'N/A')
    
    print(f"从插件获取到 {len(all_videos)} 个视频数据")

    # 如果获取到的视频数量为0，则不更新仪表板数据，以保留上一次的有效数据
    if not all_videos:
        print("警告：未从插件获取到任何视频数据，仪表板数据将不会更新。")
        return
    
    # 数据聚合
    total_views = sum(int(v.get('view_count', 0)) for v in all_videos)
    total_videos = len(all_videos)
    
    print(f"总视频数: {total_videos}")
    print(f"总播放量: {total_views}")

    # 按月份统计
    monthly_stats = {}
    for video in all_videos:
        try:
            pub_time = datetime.strptime(video['publish_time'], '%Y-%m-%d %H:%M:%S')
            month_key = pub_time.strftime('%Y-%m')
            if month_key not in monthly_stats:
                monthly_stats[month_key] = {'videos': 0, 'views': 0, 'likes': 0}
            monthly_stats[month_key]['videos'] += 1
            monthly_stats[month_key]['views'] += int(video.get('view_count', 0))
            monthly_stats[month_key]['likes'] += int(video.get('like_count', 0))
        except (ValueError, KeyError) as e:
            print(f"处理视频时间数据失败: {e}, 视频: {video.get('title', 'Unknown')}")
            continue

    sorted_months = sorted(monthly_stats.keys())
    print(f"按月统计结果: {monthly_stats}")
    
    # 改进标签格式，包含年份信息
    trend_labels = []
    for m in sorted_months:
        year, month = m.split('-')
        trend_labels.append(f"{year}.{month}")
    
    # 准备累计和单月数据
    cumulative_videos, cumulative_views, cumulative_likes = 0, 0, 0
    trend_video_data, trend_views_data, trend_likes_data = [], [], []
    monthly_video_data, monthly_views_data, monthly_likes_data = [], [], []
    
    for month in sorted_months:
        # 累计数据
        cumulative_videos += monthly_stats[month]['videos']
        cumulative_views += monthly_stats[month]['views']
        cumulative_likes += monthly_stats[month]['likes']
        trend_video_data.append(cumulative_videos)
        trend_views_data.append(cumulative_views)
        trend_likes_data.append(cumulative_likes)
        
        # 单月数据
        monthly_video_data.append(monthly_stats[month]['videos'])
        monthly_views_data.append(monthly_stats[month]['views'])
        monthly_likes_data.append(monthly_stats[month]['likes'])

    # 计算近一个月数据和变化
    last_month_views = 0
    last_month_videos = 0
    last_month_likes = 0
    last_month_views_change = "N/A"
    last_month_videos_change = "N/A"
    last_month_likes_change = "N/A"

    if len(sorted_months) >= 1:
        last_month_key = sorted_months[-1]
        last_month_stats = monthly_stats[last_month_key]
        last_month_views = last_month_stats['views']
        last_month_videos = last_month_stats['videos']
        last_month_likes = last_month_stats['likes']

        # 计算相对于上个月的变化
        if len(sorted_months) >= 2:
            prev_month_key = sorted_months[-2]
            prev_month_stats = monthly_stats[prev_month_key]
            prev_month_views = prev_month_stats['views']
            prev_month_videos = prev_month_stats['videos']
            prev_month_likes = prev_month_stats['likes']

            # 播放量变化
            if prev_month_views > 0:
                views_change_percent = (last_month_views - prev_month_views) / prev_month_views * 100
                last_month_views_change = f"+{views_change_percent:.1f}%" if views_change_percent >= 0 else f"{views_change_percent:.1f}%"

            # 视频数量变化
            videos_change = last_month_videos - prev_month_videos
            if videos_change != 0:
                last_month_videos_change = f"+{videos_change}" if videos_change > 0 else str(videos_change)
            else:
                last_month_videos_change = "持平"

            # 点赞量变化
            if prev_month_likes > 0:
                likes_change_percent = (last_month_likes - prev_month_likes) / prev_month_likes * 100
                last_month_likes_change = f"+{likes_change_percent:.1f}%" if likes_change_percent >= 0 else f"{likes_change_percent:.1f}%"

    # 输出最终统计信息用于调试
    # print(f"\n=== 仪表板数据统计 ===")
    # print(f"总视频数: {total_videos}")
    # print(f"总播放量: {total_views:,}")
    # print(f"粉丝数: {follower_count}")
    # print(f"最近一个月播放量: {last_month_views:,}")
    # print(f"平均播放量: {total_views // total_videos if total_videos > 0 else 0:,}")
    # print(f"月份统计: {len(monthly_stats)} 个月")
    
    # 构建最终的JSON
    # 计算总点赞量
    total_likes = sum(int(v.get('like_count', 0)) for v in all_videos)
    print(f"总点赞量: {total_likes}")
    
    
    # 准备视频表现数据
    video_performance = []
    for v in all_videos:
        views = int(v.get('view_count', 0))
        if views >= 10000:
            likes = int(v.get('like_count', 0))
            video_performance.append({
                'title': v.get('title', '未知标题'),
                'views': views,
                'likes': likes,
                'like_rate': (likes / views) * 100 if views > 0 else 0
            })

    # 按点赞率排序
    video_performance.sort(key=lambda x: x['like_rate'], reverse=True)

    # 汇总所有弹幕，并附带视频标题
    all_danmakus = []
    for v in all_videos:
        if 'danmakus' in v and v['danmakus']:
            video_title = v.get('title', '未知视频')
            for dm_text in v['danmakus']:
                all_danmakus.append({'text': dm_text, 'video_title': video_title})

    dashboard_data = {
        "summary": {
            "total_fans": f"{follower_count:,}" if isinstance(follower_count, int) else follower_count,
            "total_views": format_large_number(total_views),
            "total_videos": total_videos,
            "total_likes": format_large_number(total_likes),
            "last_month_views": format_large_number(last_month_views),
            "last_month_views_change": last_month_views_change,
            "last_month_videos": last_month_videos,
            "last_month_videos_change": last_month_videos_change,
            "last_month_likes": format_large_number(last_month_likes),
            "last_month_likes_change": last_month_likes_change
        },
        "trend_chart": {
            "labels": trend_labels,
            "datasets": [
                { "label": "累计视频发布数", "data": trend_video_data },
                { "label": "累计播放量", "data": trend_views_data },
                { "label": "累计点赞量", "data": trend_likes_data },
                { "label": "每月视频发布数", "data": monthly_video_data },
                { "label": "每月播放量", "data": monthly_views_data },
                { "label": "每月点赞量", "data": monthly_likes_data }
            ]
        },
        "video_performance": video_performance,
        "follower_chart": {
            "labels": ["2022年", "2023年", "2024年", "2025年"],
            "datasets": [ {
                "label": "B站粉丝数量",
                "data": [
                    max(0, follower_count - 30) if isinstance(follower_count, int) else 0,
                    max(0, follower_count - 20) if isinstance(follower_count, int) else 0,
                    max(0, follower_count - 10) if isinstance(follower_count, int) else 0,
                    follower_count if isinstance(follower_count, int) else 0
                ]
            } ]
        },
        "additional_stats": {
            "videos_published_1": total_videos,
            "views_total_1": format_large_number(total_views),
            "videos_published_2": "N/A",
            "views_total_2": "N/A",
            "average_views": f"{total_views / total_videos:,.0f}" if total_videos > 0 else 0,
            "average_views_change_monthly": "N/A"
        },
        "all_videos": all_videos,
        "all_danmakus": all_danmakus
    }

    with open(web_data_path, 'w', encoding='utf-8') as f:
        json.dump(dashboard_data, f, ensure_ascii=False, indent=4)
    print(f"已将仪表板数据写入到 '{web_data_path}'")

def start_web_server(port: int):
    handler = partial(http.server.SimpleHTTPRequestHandler, directory='Web')
    httpd = socketserver.TCPServer(("", port), handler)
    print(f"Web服务器已在 http://localhost:{port} 启动")
    httpd.serve_forever()

async def main():
    try:
        with open('config.yml', 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except FileNotFoundError:
        print("错误：找不到 config.yml 文件。")
        return
    except Exception as e:
        print(f"读取配置文件时出错: {e}")
        return

    server_config = config.get('server', {})
    port = server_config.get('port', 100)
    refresh_interval_str = server_config.get('refresh_interval', '1d')
    refresh_seconds = parse_refresh_interval(refresh_interval_str)

    web_config_path = os.path.join('Web', 'web_config.json')
    with open(web_config_path, 'w', encoding='utf-8') as f:
        json.dump(config.get('web', {}), f, ensure_ascii=False, indent=4)

    server_thread = threading.Thread(target=start_web_server, args=(port,))
    server_thread.daemon = True
    server_thread.start()
    
    while True:
        print("开始执行数据刷新...")
        await run_data_collection(config)
        print(f"数据刷新完成。下一次刷新将在 {refresh_interval_str} 后进行。")
        await asyncio.sleep(refresh_seconds)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n服务已停止。")