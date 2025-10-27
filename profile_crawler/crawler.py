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
    
    def click_view_more(self):
        """点击最新上线的查看更多按钮"""
        from selenium.webdriver.common.by import By
        from selenium.webdriver.support.ui import WebDriverWait
        from selenium.webdriver.support import expected_conditions as EC
        
        logger.info("="*60)
        logger.info("开始查找并点击'查看更多'按钮")
        logger.info("="*60)
        
        try:
            # 等待页面加载完成
            time.sleep(3)
            
            # 保存点击前的页面HTML用于调试
            timestamp_before = datetime.now().strftime('%Y%m%d_%H%M%S')
            html_before = os.path.join(self.config.get('output_directory', './output'), f'before_click_{timestamp_before}.html')
            with open(html_before, 'w', encoding='utf-8') as f:
                f.write(self.driver.page_source)
            logger.info(f"点击前页面HTML已保存: {html_before}")
            
            # 查找"查看更多"按钮的多种方式
            view_more_button = None
            
            # 方法1: 查找包含"查看更多"文本的元素，特别针对最新上线区域
            try:
                logger.info("方法1: 查找包含'查看更多'文本的元素...")
                elements = self.driver.find_elements(By.XPATH, "//*[contains(text(), '查看更多')]")
                logger.info(f"找到 {len(elements)} 个包含'查看更多'的元素")
                
                for i, elem in enumerate(elements):
                    logger.info(f"元素 {i+1}: 标签={elem.tag_name}, 文本='{elem.text}', 可见={elem.is_displayed()}")
                    
                    # 获取元素的完整HTML结构
                    try:
                        element_html = elem.get_attribute('outerHTML')
                        logger.info(f"元素HTML: {element_html[:200]}...")
                    except Exception as e:
                        logger.warning(f"获取元素HTML失败: {e}")
                    
                    if elem.is_displayed():
                        # 检查是否在"最新上线"区域 - 通过查找父级容器
                        try:
                            # 查找包含"最新上线"标题的父容器
                            parent_container = elem.find_element(By.XPATH, "./ancestor::div[contains(@class, 'w_containt_item')]")
                            parent_html = parent_container.get_attribute('outerHTML')
                            
                            if "最新上线" in parent_html:
                                view_more_button = elem
                                logger.info("✅ 找到'最新上线'区域的'查看更多'按钮")
                                logger.info(f"父容器HTML片段: {parent_html[:300]}...")
                                break
                            else:
                                logger.info(f"元素 {i+1} 不在'最新上线'区域")
                                
                        except Exception as e:
                            logger.warning(f"检查父容器失败: {e}")
                            
                            # 备用方法：检查元素的父级文本
                            try:
                                parent = elem.find_element(By.XPATH, "./..")
                                grandparent = elem.find_element(By.XPATH, "./../..")
                                if "最新上线" in parent.text or "最新上线" in grandparent.text:
                                    view_more_button = elem
                                    logger.info("✅ 通过父级文本找到'最新上线'区域的'查看更多'按钮")
                                    break
                            except Exception as e2:
                                logger.warning(f"备用检查方法失败: {e2}")
            except Exception as e:
                logger.warning(f"方法1失败: {e}")
            
            # 方法2: 查找红色按钮（根据图片描述，最新上线的查看更多是红色的）
            if not view_more_button:
                try:
                    logger.info("方法2: 查找红色按钮...")
                    # 查找具有红色样式的按钮
                    red_buttons = self.driver.find_elements(By.XPATH, "//button[contains(@style, 'red') or contains(@class, 'red') or contains(@class, 'btn-red')]")
                    logger.info(f"找到 {len(red_buttons)} 个红色按钮")
                    
                    for btn in red_buttons:
                        if btn.is_displayed() and btn.is_enabled() and "查看更多" in btn.text:
                            view_more_button = btn
                            logger.info("✅ 找到红色'查看更多'按钮")
                            break
                except Exception as e:
                    logger.warning(f"方法2失败: {e}")
            
            # 方法3: 查找所有按钮，然后筛选
            if not view_more_button:
                try:
                    logger.info("方法3: 查找所有按钮并筛选...")
                    all_buttons = self.driver.find_elements(By.TAG_NAME, "button")
                    all_links = self.driver.find_elements(By.TAG_NAME, "a")
                    all_elements = all_buttons + all_links
                    
                    logger.info(f"找到 {len(all_elements)} 个按钮和链接")
                    
                    for elem in all_elements:
                        if elem.is_displayed() and elem.is_enabled():
                            text = elem.text.strip()
                            if "查看更多" in text:
                                logger.info(f"找到'查看更多'元素: {text}")
                                # 检查是否在最新上线区域
                                try:
                                    # 向上查找父元素，看是否包含"最新上线"
                                    parent = elem.find_element(By.XPATH, "./..")
                                    grandparent = elem.find_element(By.XPATH, "./../..")
                                    if "最新上线" in parent.text or "最新上线" in grandparent.text:
                                        view_more_button = elem
                                        logger.info("✅ 确认是'最新上线'区域的'查看更多'按钮")
                                        break
                                except:
                                    # 如果无法确定位置，选择第一个
                                    if not view_more_button:
                                        view_more_button = elem
                                        logger.info("✅ 找到'查看更多'按钮（位置未确认）")
                except Exception as e:
                    logger.warning(f"方法3失败: {e}")
            
            if view_more_button:
                logger.info("准备点击'查看更多'按钮...")
                logger.info(f"按钮信息: 标签={view_more_button.tag_name}, 文本='{view_more_button.text}'")
                
                # 滚动到按钮位置
                self.driver.execute_script("arguments[0].scrollIntoView(true);", view_more_button)
                time.sleep(1)
                
                # 记录点击前的URL
                url_before = self.driver.current_url
                logger.info(f"点击前URL: {url_before}")
                
                # 由于这是一个span元素，可能需要特殊处理
                # 尝试多种点击方式
                click_success = False
                
                # 方法1: 直接点击
                try:
                    view_more_button.click()
                    logger.info("✅ 直接点击成功")
                    click_success = True
                except Exception as e:
                    logger.warning(f"直接点击失败: {e}")
                
                # 方法2: JavaScript点击
                if not click_success:
                    try:
                        self.driver.execute_script("arguments[0].click();", view_more_button)
                        logger.info("✅ JavaScript点击成功")
                        click_success = True
                    except Exception as e:
                        logger.warning(f"JavaScript点击失败: {e}")
                
                # 方法3: 模拟鼠标事件
                if not click_success:
                    try:
                        from selenium.webdriver.common.action_chains import ActionChains
                        actions = ActionChains(self.driver)
                        actions.move_to_element(view_more_button).click().perform()
                        logger.info("✅ 鼠标事件点击成功")
                        click_success = True
                    except Exception as e:
                        logger.warning(f"鼠标事件点击失败: {e}")
                
                # 方法4: 点击父元素
                if not click_success:
                    try:
                        parent_element = view_more_button.find_element(By.XPATH, "./..")
                        parent_element.click()
                        logger.info("✅ 点击父元素成功")
                        click_success = True
                    except Exception as e:
                        logger.warning(f"点击父元素失败: {e}")
                
                if click_success:
                    # 等待页面跳转
                    time.sleep(5)
                    
                    # 检查是否成功跳转到文献列表页面
                    current_url = self.driver.current_url
                    logger.info(f"点击后URL: {current_url}")
                    
                    # 保存点击后的页面HTML用于调试
                    timestamp_after = datetime.now().strftime('%Y%m%d_%H%M%S')
                    html_after = os.path.join(self.config.get('output_directory', './output'), f'after_click_{timestamp_after}.html')
                    with open(html_after, 'w', encoding='utf-8') as f:
                        f.write(self.driver.page_source)
                    logger.info(f"点击后页面HTML已保存: {html_after}")
                    
                    # 检查页面标题变化
                    page_title = self.driver.title
                    logger.info(f"点击后页面标题: {page_title}")
                    
                    # 检查是否有新窗口或标签页
                    if len(self.driver.window_handles) > 1:
                        logger.info("检测到新窗口/标签页，切换到新窗口")
                        self.driver.switch_to.window(self.driver.window_handles[-1])
                        current_url = self.driver.current_url
                        logger.info(f"新窗口URL: {current_url}")
                    
                    if "latest_online" in current_url or "检索结果" in self.driver.title or url_before != current_url:
                        logger.info("✅ 成功进入文献列表页面")
                        return True
                    else:
                        logger.warning("⚠️ 可能未成功跳转到文献列表页面")
                        logger.info("请检查保存的HTML文件进行调试")
                        return False
                else:
                    logger.error("❌ 所有点击方法都失败了")
                    return False
            else:
                logger.error("❌ 未找到'查看更多'按钮")
                logger.info("请检查页面是否正确加载，或手动点击按钮")
                return False
                
        except Exception as e:
            logger.error(f"点击'查看更多'按钮过程出错: {e}")
            return False

    def analyze_html_for_debug(self, html_file_path):
        """分析HTML文件，查找查看更多按钮的详细信息"""
        try:
            with open(html_file_path, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            logger.info(f"分析HTML文件: {html_file_path}")
            
            # 查找所有包含"查看更多"的元素
            import re
            view_more_patterns = [
                r'<[^>]*>查看更多[^<]*</[^>]*>',
                r'查看更多',
                r'最新上线.*?查看更多',
            ]
            
            for pattern in view_more_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE | re.DOTALL)
                if matches:
                    logger.info(f"找到匹配模式 '{pattern}': {len(matches)} 个")
                    for i, match in enumerate(matches[:3]):  # 只显示前3个
                        logger.info(f"  匹配 {i+1}: {match[:100]}...")
            
            # 查找可能的链接
            link_patterns = [
                r'href="[^"]*latest[^"]*"',
                r'href="[^"]*online[^"]*"',
                r'href="[^"]*更多[^"]*"',
            ]
            
            for pattern in link_patterns:
                matches = re.findall(pattern, html_content, re.IGNORECASE)
                if matches:
                    logger.info(f"找到链接模式 '{pattern}': {len(matches)} 个")
                    for i, match in enumerate(matches[:3]):
                        logger.info(f"  链接 {i+1}: {match}")
            
        except Exception as e:
            logger.error(f"分析HTML文件失败: {e}")

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
            
            # 点击"查看更多"按钮进入文献列表
            click_result = self.click_view_more()
            if click_result:
                # 保存跳转后的页面
                timestamp_after = datetime.now().strftime('%Y%m%d_%H%M%S')
                screenshot_after = os.path.join(self.config.get('output_directory', './output'), f'literature_list_{timestamp_after}.png')
                self.driver.save_screenshot(screenshot_after)
                logger.info(f"文献列表页面截图已保存: {screenshot_after}")
                
                html_file_after = os.path.join(self.config.get('output_directory', './output'), f'literature_list_{timestamp_after}.html')
                with open(html_file_after, 'w', encoding='utf-8') as f:
                    f.write(self.driver.page_source)
                logger.info(f"文献列表页面HTML已保存: {html_file_after}")
                
                logger.info(f"文献列表页面标题: {self.driver.title}")
                logger.info(f"文献列表页面URL: {self.driver.current_url}")
            else:
                # 点击失败，分析HTML文件进行调试
                logger.info("="*60)
                logger.info("点击失败，开始分析HTML文件进行调试")
                logger.info("="*60)
                
                # 分析点击前的HTML文件
                html_files = [f for f in os.listdir(self.config.get('output_directory', './output')) if f.startswith('before_click_') and f.endswith('.html')]
                if html_files:
                    latest_html = max(html_files)
                    html_path = os.path.join(self.config.get('output_directory', './output'), latest_html)
                    self.analyze_html_for_debug(html_path)
                
                # 分析点击后的HTML文件
                html_files_after = [f for f in os.listdir(self.config.get('output_directory', './output')) if f.startswith('after_click_') and f.endswith('.html')]
                if html_files_after:
                    latest_html_after = max(html_files_after)
                    html_path_after = os.path.join(self.config.get('output_directory', './output'), latest_html_after)
                    self.analyze_html_for_debug(html_path_after)
            
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

