"""
使用Chrome Profile访问页面的爬虫脚本
"""

import json
import logging
import os
import time
from datetime import datetime
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import TimeoutException, WebDriverException

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('crawler.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class Crawler:
    def __init__(self, config_path='config.json'):
        """初始化爬虫"""
        with open(config_path, 'r', encoding='utf-8') as f:
            self.config = json.load(f)
        self.driver = None
        
        # 创建输出目录
        output_dir = self.config.get('output_directory', './output')
        Path(output_dir).mkdir(parents=True, exist_ok=True)
    
    def migrate_chrome_profile(self):
        """从Chrome目录迁移CrawlerProfile（如果存在）"""
        chrome_user_data = os.path.expanduser(r'~\AppData\Local\Google\Chrome\User Data')
        source_profile = os.path.join(chrome_user_data, 'CrawlerProfile')
        temp_profile_dir = os.path.join(os.getcwd(), 'chrome_profile')
        dest_profile = os.path.join(temp_profile_dir, 'CrawlerProfile')
        
        # 如果目标已存在
        if os.path.exists(dest_profile):
            logger.info("✅ Profile已存在于项目目录")
            logger.info(f"路径: {dest_profile}")
            return True
        
        # 如果源Profile存在，复制它
        if os.path.exists(source_profile):
            logger.info(f"检测到Chrome中的CrawlerProfile，正在复制...")
            logger.info(f"源: {source_profile}")
            logger.info(f"目标: {dest_profile}")
            
            try:
                import shutil
                shutil.copytree(source_profile, dest_profile, dirs_exist_ok=True)
                logger.info("✅ Profile复制成功！")
                return True
            except Exception as e:
                logger.error(f"复制Profile失败: {e}")
                return False
        else:
            logger.info("Chrome中未找到CrawlerProfile，将创建全新Profile")
            return False
    
    def setup_driver(self):
        """设置Chrome驱动"""
        logger.info("正在设置Chrome...")
        
        options = Options()
        
        # 使用独立的临时目录 + 指定Profile名称
        temp_profile_dir = os.path.join(os.getcwd(), 'chrome_profile')
        profile_name = 'CrawlerProfile'
        os.makedirs(temp_profile_dir, exist_ok=True)
        
        # 尝试迁移Chrome中已有的Profile
        profile_exists = self.migrate_chrome_profile()
        
        # 如果Profile不存在，提示用户先手动登录
        dest_profile = os.path.join(temp_profile_dir, profile_name)
        if not profile_exists and not os.path.exists(dest_profile):
            logger.info("")
            logger.info("="*60)
            logger.info("⚠️  首次使用，需要先完成登录")
            logger.info("="*60)
            logger.info("")
            logger.info("请按以下步骤操作：")
            logger.info("1. 双击运行 open_chrome.bat")
            logger.info("2. 在打开的Chrome中访问目标网站并完成登录")
            logger.info("3. 关闭Chrome")
            logger.info("4. 重新运行此脚本")
            logger.info("")
            logger.info("="*60)
            return None
        
        logger.info(f"使用Profile目录")
        logger.info(f"基础目录: {temp_profile_dir}")
        logger.info(f"Profile名称: {profile_name}")
        
        options.add_argument(f'--user-data-dir={temp_profile_dir}')
        options.add_argument(f'--profile-directory={profile_name}')
        
        # 反反爬虫设置
        options.add_argument(f'user-agent={self.config.get("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")}')
        options.add_argument('--disable-blink-features=AutomationControlled')
        options.add_experimental_option("excludeSwitches", ["enable-automation"])
        options.add_experimental_option('useAutomationExtension', False)
        
        # 解决启动问题的关键选项
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        options.add_argument('--disable-software-rasterizer')
        
        if self.config.get('headless', False):
            options.add_argument('--headless=new')
        
        try:
            logger.info("正在启动Chrome浏览器...")
            logger.info("⚠️  如果长时间无响应，请检查是否有Chrome进程卡住")
            
            # 先检查Chrome进程
            import subprocess
            result = subprocess.run(['tasklist', '/FI', 'IMAGENAME eq chrome.exe'], 
                                  capture_output=True, text=True)
            if 'chrome.exe' in result.stdout:
                logger.warning("⚠️  检测到Chrome进程正在运行！")
                logger.warning("   建议关闭所有Chrome窗口后重试")
                logger.warning("   或者运行: taskkill /F /IM chrome.exe /T")
                time.sleep(2)
            
            self.driver = webdriver.Chrome(options=options)
            
            # 移除WebDriver特征
            self.driver.execute_cdp_cmd('Page.addScriptToEvaluateOnNewDocument', {
                'source': 'Object.defineProperty(navigator, "webdriver", {get: () => undefined})'
            })
            
            self.driver.set_page_load_timeout(self.config.get('page_load_timeout', 30))
            self.driver.implicitly_wait(self.config.get('implicit_wait', 10))
            
            logger.info("✅ Chrome启动成功")
            return True  # 返回成功标志
        except Exception as e:
            logger.error(f"❌ 设置Chrome失败: {e}")
            logger.error("\n可能的解决方案:")
            logger.error("1. 确保关闭了所有Chrome浏览器窗口")
            logger.error("2. 检查Chrome浏览器是否正常安装")
            logger.error("3. 尝试重启电脑")
            raise
    
    def auto_login(self):
        """自动登录流程"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        target_url = self.config.get('target_url')
        
        logger.info("="*60)
        logger.info("开始自动登录流程")
        logger.info("="*60)
        
        # 1. 访问目标页面（处理超时问题）
        logger.info(f"访问目标页面: {target_url}")
        try:
            self.driver.get(target_url)
        except Exception as e:
            logger.warning(f"页面加载超时，尝试停止加载: {e}")
            try:
                # 停止页面加载
                self.driver.execute_script("window.stop();")
                logger.info("已停止页面加载，继续执行")
            except:
                pass
        
        time.sleep(3)
        
        try:
            # 2. 等待页面加载完成
            logger.info("等待页面元素加载...")
            time.sleep(2)
            
            # 2. 查找登录按钮并点击（使用固定的选择器）
            logger.info("查找登录按钮...")
            
            login_button = None
            try:
                # 使用已验证有效的选择器
                elements = self.driver.find_elements(By.XPATH, "//*[text()='登录']")
                logger.info(f"找到 {len(elements)} 个'登录'元素")
                
                for elem in elements:
                    if elem.is_displayed():
                        login_button = elem
                        logger.info(f"✅ 找到可见的登录按钮")
                        break
            except Exception as e:
                logger.error(f"查找登录按钮失败: {e}")
            
            if login_button:
                logger.info("点击登录按钮...")
                login_button.click()
                
                # 等待登录跳转或完成
                logger.info("等待登录完成...")
                time.sleep(5)
                
                # 检查是否已登录
                try:
                    current_url = self.driver.current_url
                    page_source = self.driver.page_source
                    
                    # 检查是否已登录
                    if any(keyword in page_source for keyword in ["退出", "注销", "logout"]):
                        logger.info("✅ 自动登录成功！")
                        return True
                    else:
                        logger.warning("⚠️  未检测到登录状态，可能需要手动操作")
                        logger.info("如需手动登录，请在浏览器中操作")
                        input("\n完成后按Enter继续...")
                        return True
                except:
                    # 如果页面跳转导致窗口关闭，等待并重新获取
                    logger.info("页面可能已跳转，等待稳定...")
                    time.sleep(3)
                    return True
            else:
                logger.warning("⚠️  未找到登录按钮")
                logger.info("页面可能已经是登录状态，或需要手动操作")
                
                # 检查是否已经登录
                page_source = self.driver.page_source
                if any(keyword in page_source for keyword in ["退出", "注销", "logout", "个人中心"]):
                    logger.info("✅ 页面已是登录状态！")
                    return True
                else:
                    logger.info("如需登录，请手动操作")
                    input("\n完成后按Enter继续...")
                    return True
                    
        except Exception as e:
            logger.error(f"登录过程出错: {e}")
            logger.info("请手动完成登录")
            input("\n完成登录后按Enter继续...")
            return True
    
    def access_page(self):
        """访问目标页面"""
        target_url = self.config.get('target_url')
        
        try:
            # 检查当前URL，如果已经在目标页面就不重复访问
            try:
                current_url = self.driver.current_url
                if target_url in current_url:
                    logger.info(f"已在目标页面: {current_url}")
                else:
                    logger.info(f"访问页面: {target_url}")
                    self.driver.get(target_url)
            except:
                logger.info(f"访问页面: {target_url}")
                self.driver.get(target_url)
            
            time.sleep(self.config.get('wait_time', 3))
            
            # 保存截图
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            screenshot = os.path.join(self.config.get('output_directory', './output'), f'page_{timestamp}.png')
            self.driver.save_screenshot(screenshot)
            logger.info(f"截图已保存: {screenshot}")
            
            # 保存HTML
            html_file = os.path.join(self.config.get('output_directory', './output'), f'page_{timestamp}.html')
            with open(html_file, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"HTML已保存: {html_file}")
            
            logger.info(f"页面标题: {self.driver.title}")
            logger.info(f"当前URL: {self.driver.current_url}")
            
        except Exception as e:
            logger.error(f"访问页面失败: {e}")
            raise
    
    def run(self, need_login=True):
        """运行爬虫"""
        try:
            result = self.setup_driver()
            if result is None:
                # Profile不存在，已提示用户手动设置
                return
            
            if need_login:
                if not self.auto_login():
                    logger.error("登录失败")
                    return
            
            self.access_page()
            
            logger.info("="*60)
            logger.info("✅ 成功使用本地Profile访问页面！")
            logger.info("="*60)
            
            # 保持浏览器打开以便查看
            input("\n按Enter键关闭浏览器...")
            
        except Exception as e:
            logger.error(f"运行失败: {e}")
        finally:
            if self.driver:
                self.driver.quit()
                logger.info("浏览器已关闭")


if __name__ == '__main__':
    logger.info("启动爬虫...")
    crawler = Crawler('config.json')
    crawler.run(need_login=True)

