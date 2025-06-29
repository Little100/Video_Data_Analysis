import threading
import asyncio
from bilibili_api import user, video, sync
import openpyxl
from datetime import datetime
import os
import re

def get_suffix():
    return "_bilibili_fetcher"

def fetch_video_details(video_items, videos_by_year_month, successful_count, failed_count):
    for video_item in video_items:
        bvid = video_item['bvid']
        title = video_item.get('title', '未知标题')
        
        try:
            v = video.Video(bvid=bvid)
            detail = asyncio.run(v.get_info())
            
            pubdate = datetime.fromtimestamp(detail['pubdate'])
            year = pubdate.year
            month = pubdate.month
            
            if year not in videos_by_year_month:
                videos_by_year_month[year] = {}
            if month not in videos_by_year_month[year]:
                videos_by_year_month[year][month] = []
            
            view_count = detail.get('stat', {}).get('view', 0)
            if view_count == 0:
                view_count = detail.get('stat', {}).get('play', 0)
            
            danmakus = []
            try:
                dms = sync(v.get_danmakus(0))
                danmakus = [dm.text for dm in dms]
            except Exception as dm_e:
                print(f"获取视频 {bvid} 的弹幕失败: {dm_e}")

            video_details = {
                'title': detail['title'],
                'link': f"https://www.bilibili.com/video/{bvid}",
                'duration': f"{detail['duration'] // 60}:{detail['duration'] % 60:02d}",
                'publish_time': pubdate.strftime('%Y-%m-%d %H:%M:%S'),
                'view_count': view_count,
                'like_count': detail['stat']['like'],
                'danmaku_count': detail['stat']['danmaku'],
                'comment_count': detail['stat']['reply'],
                'description': detail['desc'],
                'fan_growth': '无法获取',
                'danmakus': danmakus
            }
            videos_by_year_month[year][month].append(video_details)
            successful_count[0] += 1

        except Exception as e:
            print(f"获取视频 {bvid} ({title}) 详情失败: {e}")
            failed_count[0] += 1

async def fetch_user_videos(plugin_config: dict, output_dir: str):
    uid = plugin_config.get('uid')
    if not uid:
        print("错误：在config.yml中未找到bilibili_fetcher插件的UID配置。")
        return {'videos': [], 'follower_count': 'Error'}

    try:
        u = user.User(uid)
        relation_info = await u.get_relation_info()
        follower_count = relation_info.get('follower', 0)

        page = 1
        all_videos = []
        while True:
            try:
                res = await u.get_videos(pn=page, ps=30)
                if not res.get('list', {}).get('vlist', []):
                    break
                all_videos.extend(res['list']['vlist'])
                page += 1
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"获取第 {page} 页视频时出错: {e}")
                break

        print(f"获取到 {len(all_videos)} 个视频的基本信息")
        
        result = {
            'videos': [],
            'follower_count': follower_count
        }

        videos_by_year_month = {}
        successful_count = [0]
        failed_count = [0]

        # 将视频分割成8个部分
        num_threads = 8
        video_chunks = [all_videos[i::num_threads] for i in range(num_threads)]
        threads = []

        for chunk in video_chunks:
            thread = threading.Thread(target=fetch_video_details, args=(chunk, videos_by_year_month, successful_count, failed_count))
            threads.append(thread)
            thread.start()

        for thread in threads:
            thread.join()

        print(f"成功获取 {successful_count[0]} 个视频详情，失败 {failed_count[0]} 个")
        
        # 将 videos_by_year_month 中的视频数据添加到 result['videos']
        for year in sorted(videos_by_year_month.keys()):
            for month in sorted(videos_by_year_month[year].keys()):
                result['videos'].extend(videos_by_year_month[year][month])
        
        # 处理结果并保存到Excel文件的逻辑...

        return result

    except Exception as e:
        print(f"获取视频数据时出错: {e}")
        return {'videos': [], 'follower_count': 'Error'}

if __name__ == '__main__':
    test_uid = "388596277" 
    test_output_dir = "Excel_test"
    asyncio.run(fetch_user_videos({'uid': test_uid}, test_output_dir))