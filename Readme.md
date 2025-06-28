# 视频数据分析系统

本项目用于采集、分析 B 站用户视频数据，并通过 Web 仪表板进行可视化展示。支持插件扩展，目前已集成 Bilibili 数据采集插件。如果您有自己的动手能力可以增加插件去支持其他的视频平台。

## 快速开始

1. **安装依赖**

   需预先安装 Python 3.12 及以下依赖（部分依赖需根据插件实际需求补充）：
   ```
   pip install bilibili-api-python openpyxl pyyaml
   ```

2. **配置参数**

   编辑 `config.yml`，填写 B 站 UID 及相关参数：
   ```yaml
   plugins:
     bilibili_fetcher:
       uid: "你的B站UID"
   output:
     directory: "Excel"
   server:
     port: 100
     refresh_interval: "1d"
   ```
> 内有详细的注释介绍

3. **运行主程序**

   ```
   python main.py
   ```
> 或者直接使用release的打包程序

   程序会定时采集数据，并在 `Web/dashboard_data.json` 生成仪表板数据。

4. **访问仪表板**

   启动后访问 [http://localhost:100/](http://localhost:100/)(默认是这个链接) 查看可视化页面。

## 插件机制

- 插件需放置于 `Plugins/` 目录下，每个插件为一个子文件夹。
- 插件需实现 `fetch_user_videos(plugin_config: dict, output_dir: str)` 异步方法，返回采集到的数据。
- 插件可通过 `get_suffix()` 返回自定义文件名后缀。

## 主要功能

- 支持 B 站用户视频数据采集（粉丝数、视频信息、弹幕等）
- 数据自动写入 Excel，按年/月/日分类
- Web 仪表板实时展示数据，支持弹幕动态效果
- 支持插件扩展，便于后续集成更多平台

如需扩展插件或自定义仪表板，请参考现有代码与配置说明。

GPL v3.0 许可证