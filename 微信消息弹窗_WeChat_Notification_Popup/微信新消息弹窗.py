import os
import re
import time
import hashlib
import glob
import sys
import threading
import pystray
from PIL import Image, ImageTk
import uiautomation as auto

# 尝试导入Tkinter并处理可能的导入错误
try:
    import tkinter as tk
    from tkinter import PhotoImage
    HAS_GUI = True
except ImportError:
    HAS_GUI = False
    print("警告: Tkinter库未安装，无法显示图形界面弹窗")
    print("请确保Python安装时已勾选Tcl/Tk组件")

class WeChatNotifier:
    def __init__(self):
        # ==================== 配置区域 ====================
        # 微信安装路径（用户可在此处修改）
        self.wechat_install_path = r"D:\APP\WeChat"  # <-- 这里是微信安装路径
        # ================================================
        
        self.last_message = None
        self.wxid = self.get_wxid()
        self.avatar_cache_path = self.get_avatar_cache_path()
        self.running = True
        self.tray_icon = None
        
        # 获取当前脚本所在目录
        self.script_dir = os.path.dirname(os.path.abspath(__file__))
        self.logo_path = os.path.join(self.script_dir, "WCLogo.png")
        
        if HAS_GUI:
            self.root = tk.Tk()
            self.root.withdraw()  # 隐藏主窗口
            self.screen_width = self.root.winfo_screenwidth()
        else:
            self.screen_width = 1920

    def get_wxid(self):
        """获取当前登录用户的wxid"""
        try:
            # 微信数据目录可能的位置，优先使用安装路径下的用户数据
            possible_paths = [
                os.path.join(self.wechat_install_path, 'WeChat Files'),
                os.path.join(os.environ['USERPROFILE'], 'Documents', 'WeChat Files'),
                os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'Tencent', 'WeChat', 'WeChat Files')
            ]
            
            for path in possible_paths:
                if os.path.exists(path):
                    # 查找以wxid_开头的文件夹
                    for item in os.listdir(path):
                        if item.startswith('wxid_'):
                            return item
            return None
        except Exception as e:
            print(f"获取wxid失败: {e}")
            return None

    def get_avatar_cache_path(self):
        """获取头像缓存路径"""
        if self.wxid:
            # 尝试不同位置的头像缓存，优先使用安装路径
            possible_paths = [
                os.path.join(self.wechat_install_path, 'WeChat Files', self.wxid, 'Avatar'),
                os.path.join(os.environ['USERPROFILE'], 'Documents', 'WeChat Files', self.wxid, 'Avatar'),
                os.path.join(os.environ['USERPROFILE'], 'AppData', 'Roaming', 'Tencent', 'WeChat', 'WeChat Files', self.wxid, 'Avatar')
            ]
            for path in possible_paths:
                if os.path.exists(path):
                    return path
        return None

    def get_avatar_path(self, wxid):
        """根据wxid获取头像路径"""
        if not self.avatar_cache_path or not os.path.exists(self.avatar_cache_path):
            return None
            
        # 计算wxid的MD5值，用于查找头像文件
        md5_hash = hashlib.md5(wxid.encode()).hexdigest()
        # 查找匹配的头像文件
        for ext in ['jpg', 'png', 'jpeg']:
            avatar_pattern = os.path.join(self.avatar_cache_path, f'*{md5_hash}*.{ext}')
            avatar_files = glob.glob(avatar_pattern)
            if avatar_files:
                return avatar_files[0]
        return None

    def create_popup(self, nickname, content):
        """创建消息弹窗"""
        if not HAS_GUI:
            print(f"新消息来自 {nickname}: {content}")
            return
            
        try:
            # 创建顶层窗口
            popup = tk.Toplevel()
            popup.title("微信新消息")
            popup.overrideredirect(True)  # 无边框窗口
            
            # 设置窗口位置在右上角
            window_width = 300
            window_height = 100
            x = self.screen_width - window_width - 20
            y = 20
            popup.geometry(f"{window_width}x{window_height}+{x}+{y}")
            
            # 设置窗口背景为白色
            popup.configure(bg='white')
            
            # 添加微信图标
            if os.path.exists(self.logo_path):
                try:
                    img = Image.open(self.logo_path).resize((40, 40), Image.LANCZOS)
                    logo_img = ImageTk.PhotoImage(img)
                    logo_label = tk.Label(popup, image=logo_img, bg='white')
                    logo_label.image = logo_img
                    logo_label.place(x=10, y=10)
                except Exception as e:
                    print(f"加载Logo失败: {e}")
                    # 使用绿色方块作为替代
                    icon_label = tk.Label(popup, bg='#2DC100', width=6, height=3)
                    icon_label.place(x=10, y=10)
            else:
                # 使用绿色方块作为替代
                icon_label = tk.Label(popup, bg='#2DC100', width=6, height=3)
                icon_label.place(x=10, y=10)
            
            # 添加"新的消息"文本
            title_label = tk.Label(popup, text="新的消息", font=("微软雅黑", 10, "bold"), bg='white')
            title_label.place(x=60, y=10)
            
            # 添加时间标签
            current_time = time.strftime("%H:%M", time.localtime())
            time_label = tk.Label(popup, text=current_time, font=("微软雅黑", 8), fg='gray', bg='white')
            time_label.place(x=window_width - 60, y=10)
            
            # 添加昵称标签
            nickname_label = tk.Label(popup, text=nickname, font=("微软雅黑", 10), bg='white')
            nickname_label.place(x=60, y=40)
            
            # 添加消息内容标签
            content_label = tk.Label(popup, text=content, font=("微软雅黑", 9), bg='white', wraplength=200)
            content_label.place(x=60, y=65)
            
            # 5秒后自动关闭
            popup.after(5000, popup.destroy)
            
            # 显示窗口
            popup.attributes('-topmost', True)  # 置顶显示
            popup.update()
            
        except Exception as e:
            print(f"创建弹窗失败: {e}")
            print(f"新消息来自 {nickname}: {content}")

    def monitor_wechat(self):
        """监控微信新消息"""
        print("微信新消息监控已启动... (在系统托盘中运行)")
        print(f"使用微信安装路径: {self.wechat_install_path}")
        while self.running:
            try:
                # 获取微信窗口
                wechat_win = auto.WindowControl(Name="微信", ClassName="WeChatMainWndForPC")
                if not wechat_win.Exists():
                    # print("未找到微信窗口，等待中...")
                    time.sleep(5)
                    continue
                
                # 获取会话列表
                session_list = wechat_win.ListControl(Name="会话")
                if not session_list.Exists():
                    time.sleep(2)
                    continue
                
                # 遍历会话查找未读消息
                for session in session_list.GetChildren():
                    if "条新消息" in session.Name:
                        # 提取发送者和消息数量
                        match = re.match(r'(.+?)(\d+)条新消息', session.Name)
                        if match:
                            nickname = match.group(1).strip()
                            message_count = int(match.group(2))
                            
                            # 点击进入会话
                            session.Click()
                            time.sleep(0.5)
                            
                            # 获取消息列表
                            message_list = wechat_win.ListControl(Name="消息")
                            if message_list.Exists():
                                messages = message_list.GetChildren()
                                if messages:
                                    last_msg = messages[-1].Name
                                    
                                    # 检查是否为新消息
                                    if last_msg != self.last_message:
                                        self.last_message = last_msg
                                        # 创建弹窗
                                        self.create_popup(nickname, last_msg)
                
                time.sleep(2)  # 每2秒检查一次
                
            except Exception as e:
                # 忽略找不到窗口的异常
                if "comtypes" not in str(e):
                    print(f"监控出错: {e}")
                time.sleep(2)

    def stop(self, icon=None, item=None):
        """停止监控"""
        self.running = False
        if self.tray_icon:
            self.tray_icon.stop()
        print("程序已退出")
        if HAS_GUI:
            self.root.destroy()
        sys.exit(0)
    
    def create_tray_icon(self):
        """创建系统托盘图标"""
        if not HAS_GUI or not os.path.exists(self.logo_path):
            return
            
        try:
            # 加载托盘图标
            image = Image.open(self.logo_path)
            
            # 创建托盘菜单
            menu = pystray.Menu(
                pystray.MenuItem('退出', self.stop)
            )
            
            # 创建托盘图标
            self.tray_icon = pystray.Icon(
                "wechat_notifier", 
                image, 
                "微信消息通知", 
                menu
            )
            
            # 在单独的线程中启动托盘图标
            threading.Thread(target=self.tray_icon.run, daemon=True).start()
            
        except Exception as e:
            print(f"创建系统托盘图标失败: {e}")

if __name__ == "__main__":
    notifier = WeChatNotifier()
    
    # 创建系统托盘图标
    if HAS_GUI and os.path.exists(notifier.logo_path):
        notifier.create_tray_icon()
        print("程序已在后台运行，请查看系统托盘图标...")
    else:
        print("警告: 未找到WCLogo.png或GUI不可用，程序将在控制台运行")
    
    # 启动监控
    try:
        notifier.monitor_wechat()
    except KeyboardInterrupt:
        notifier.stop()