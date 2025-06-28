import importlib
import os

def load_plugins(config: dict):
    """
    自动加载所有插件，并支持黑名单。
    
    Args:
        config (dict): 从 config.yml 加载的配置字典。
    """
    blacklist = config.get('plugins', {}).get('blacklist', [])
    loaded_plugins = {}
    
    plugins_dir = "Plugins"
    if not os.path.exists(plugins_dir):
        return loaded_plugins

    for plugin_name in os.listdir(plugins_dir):
        plugin_path = os.path.join(plugins_dir, plugin_name)
        # 确保是文件夹并且不在黑名单中
        if os.path.isdir(plugin_path) and plugin_name not in blacklist:
            try:
                # 假设每个插件文件夹下都有一个同名的 .py 文件作为入口
                module = importlib.import_module(f"Plugins.{plugin_name}.{plugin_name}")
                loaded_plugins[plugin_name] = module
                print(f"插件 '{plugin_name}' 加载成功。")
            except ImportError as e:
                print(f"错误：无法找到或加载插件 '{plugin_name}'。错误信息: {e}")
            except Exception as e:
                print(f"加载插件 '{plugin_name}' 时发生未知错误: {e}")
                
    return loaded_plugins