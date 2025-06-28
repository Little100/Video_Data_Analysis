import asyncio
from bilibili_api import user, video, sync
import openpyxl
from datetime import datetime
import os
import re

def get_suffix():
    """
    返回此插件的文件名后缀。
    """
    return "_bilibili_fetcher"

async def fetch_user_videos(plugin_config: dict, output_dir: str):
    """
    获取指定B站用户的所有视频信息，并按年份和视频存入Excel文件。

    Args:
        plugin_config (dict): 插件的特定配置。
        output_dir (str): Excel文件的输出目录。
    """
    uid = plugin_config.get('uid')
    if not uid:
        print("错误：在config.yml中未找到bilibili_fetcher插件的UID配置。")
        return

    try:
        u = user.User(uid)
        
        # 获取粉丝数
        relation_info = await u.get_relation_info()
        follower_count = relation_info.get('follower', 0)

        # 获取用户投稿的所有视频信息
        page = 1
        all_videos = []
        
        # 统一使用 get_videos 方法获取视频
        print("使用 get_videos 方法获取视频...")
        while True:
            try:
                res = await u.get_videos(pn=page, ps=30)
                if not res.get('list', {}).get('vlist', []):
                    break
                all_videos.extend(res['list']['vlist'])
                page += 1
                # 为防止风控，添加短暂延时
                await asyncio.sleep(0.5)
            except Exception as e:
                print(f"获取第 {page} 页视频时出错: {e}")
                break

        print(f"获取到 {len(all_videos)} 个视频的基本信息")
        
        # 将粉丝数附加到返回结果中，以便main.py使用
        result = {
            'videos': [],
            'follower_count': follower_count
        }

        # 按年份和月份对视频进行分组
        videos_by_year_month = {}
        successful_count = 0
        failed_count = 0
        
        for video_item in all_videos:
            bvid = video_item['bvid']
            title = video_item.get('title', '未知标题')
            
            # 有些视频可能不可用，需要做异常处理
            try:
                v = video.Video(bvid=bvid)
                detail = await v.get_info()
                
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
                    # 获取弹幕
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
                    'fan_growth': '无法获取',  # B站API目前不直接提供单视频涨粉量
                    'danmakus': danmakus
                }
                # print(f"视频 {detail['title']} 播放量: {view_count}")  # 调试输出
                videos_by_year_month[year][month].append(video_details)
                result['videos'].append(video_details)
                successful_count += 1

            except Exception as e:
                print(f"获取视频 {bvid} ({title}) 详情失败: {e}")
                failed_count += 1
                
                # 即使详情获取失败，也要保留基本信息用于统计
                # 使用video_item中的基本信息
                try:
                    # 从video_item获取发布时间（时间戳格式）
                    pubdate = datetime.fromtimestamp(video_item.get('created', 0))
                    year = pubdate.year
                    month = pubdate.month
                    
                    if year not in videos_by_year_month:
                        videos_by_year_month[year] = {}
                    if month not in videos_by_year_month[year]:
                        videos_by_year_month[year][month] = []
                    
                    # 创建简化的视频信息
                    video_details = {
                        'title': title,
                        'link': f"https://www.bilibili.com/video/{bvid}",
                        'duration': '未知',
                        'publish_time': pubdate.strftime('%Y-%m-%d %H:%M:%S'),
                        'view_count': video_item.get('play', 0),
                        'like_count': 0,
                        'danmaku_count': 0,
                        'comment_count': 0,
                        'description': '详情获取失败',
                        'fan_growth': '无法获取'
                    }
                    videos_by_year_month[year][month].append(video_details)
                    result['videos'].append(video_details)
                    
                except Exception as e2:
                    print(f"保存视频 {bvid} 基本信息也失败: {e2}")
                    # 如果连基本信息都无法保存，至少要计入总数
                    current_time = datetime.now()
                    year = current_time.year
                    month = current_time.month
                    
                    if year not in videos_by_year_month:
                        videos_by_year_month[year] = {}
                    if month not in videos_by_year_month[year]:
                        videos_by_year_month[year][month] = []
                    
                    fallback_video = {
                        'title': title,
                        'link': f"https://www.bilibili.com/video/{bvid}",
                        'duration': '未知',
                        'publish_time': current_time.strftime('%Y-%m-%d %H:%M:%S'),
                        'view_count': 0,
                        'like_count': 0,
                        'danmaku_count': 0,
                        'comment_count': 0,
                        'description': '视频信息获取失败',
                        'fan_growth': '无法获取'
                    }
                    videos_by_year_month[year][month].append(fallback_video)
                    result['videos'].append(fallback_video)

        # 为每一年创建一个文件夹，并将视频数据存入Excel
        if not os.path.exists(output_dir):
            os.makedirs(output_dir)

        for year, months in videos_by_year_month.items():
            year_dir = os.path.join(output_dir, str(year))
            if not os.path.exists(year_dir):
                os.makedirs(year_dir)

            for month, videos in months.items():
                month_dir = os.path.join(year_dir, f"{month:02d}")
                if not os.path.exists(month_dir):
                    os.makedirs(month_dir)

                for video_data in videos:
                    # 清理标题中的非法字符，使其可作为文件名
                    safe_title = re.sub(r'[\\/*?:"<>|]', "", video_data['title'])
                    excel_filename = os.path.join(month_dir, f"{safe_title}{get_suffix()}.xlsx")
                
                wb = openpyxl.Workbook()
                ws = wb.active
                ws.title = "视频信息"

                # 写入格式要求的行列数据
                ws.cell(row=1, column=1, value="视频名称")
                ws.cell(row=1, column=2, value=video_data['title'])
                ws.cell(row=2, column=1, value="视频链接")
                ws.cell(row=2, column=2, value=video_data['link'])
                ws.cell(row=3, column=1, value="视频时长")
                ws.cell(row=3, column=2, value=video_data['duration'])
                ws.cell(row=4, column=1, value="视频发布时间")
                ws.cell(row=4, column=2, value=video_data['publish_time'])
                ws.cell(row=5, column=1, value="视频观看次数")
                ws.cell(row=5, column=2, value=video_data['view_count'])
                ws.cell(row=6, column=1, value="视频点赞次数")
                ws.cell(row=6, column=2, value=video_data['like_count'])
                ws.cell(row=7, column=1, value="视频弹幕数量")
                ws.cell(row=7, column=2, value=video_data['danmaku_count'])
                ws.cell(row=8, column=1, value="视频评论数量")
                ws.cell(row=8, column=2, value=video_data['comment_count'])
                ws.cell(row=9, column=1, value="视频简介")
                ws.cell(row=9, column=2, value=video_data['description'])
                ws.cell(row=10, column=1, value="视频涨粉量")
                ws.cell(row=10, column=2, value=video_data['fan_growth'])


                wb.save(excel_filename)
                # print(f"已将视频 '{video_data['title']}' 的数据保存到 '{excel_filename}'")
        
        # 输出最终统计信息
        # total_view_count = sum(video.get('view_count', 0) for video in result['videos'])
        # print(f"\n=== 数据获取完成 ===")
        # print(f"成功获取详情: {successful_count} 个视频")
        # print(f"获取失败: {failed_count} 个视频")
        # print(f"总视频数量: {len(result['videos'])} 个")
        # print(f"总播放量: {total_view_count:,}")
        # print(f"平均播放量: {total_view_count // len(result['videos']) if result['videos'] else 0}")
        # print(f"粉丝数: {follower_count}")
        
        return result

    except Exception as e:
        print(f"获取视频数据时出错: {e}")
        # 即使出错，也返回一个空/错误字典，以避免主程序出错
        return {'videos': [], 'follower_count': 'Error'}

# 方便直接运行测试
if __name__ == '__main__':
    test_uid = "12345678" 
    test_output_dir = "Excel_test"
    asyncio.run(fetch_user_videos(test_uid, test_output_dir))