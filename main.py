import os
import sys
import requests
from bs4 import BeautifulSoup
import time
import re
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                             QLabel, QLineEdit, QPushButton, QListWidget, QTextEdit,
                             QComboBox, QFrame, QSplitter, QStatusBar, QAction, QFileDialog,
                             QMessageBox, QListWidgetItem, QProgressBar, QGroupBox)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont, QIcon, QPixmap, QColor
from siliconflow_ai import siliconflow_ts
from viki import viki_translate_text


class ArxivFetcher(QThread):
    progress_updated = pyqtSignal(int, str)
    papers_fetched = pyqtSignal(list)
    paper_details_fetched = pyqtSignal(dict)

    def __init__(self, url, parent=None):
        super().__init__(parent)
        self.url = url
        self.fetch_details_for = None

    def run(self):
        if self.fetch_details_for:
            self.fetch_paper_details(self.fetch_details_for)
        else:
            self.fetch_paper_list()

    def fetch_paper_list(self):
        self.progress_updated.emit(0, "正在获取论文列表...")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(self.url, headers=headers)

            if response.status_code != 200:
                self.progress_updated.emit(0, f"请求失败，状态码: {response.status_code}")
                return

            soup = BeautifulSoup(response.text, 'html.parser')
            dt_tags = soup.find_all('dt')
            papers = []

            self.progress_updated.emit(30, "解析论文数据...")
            time.sleep(0.5)  # 模拟延迟

            for i, dt in enumerate(dt_tags):
                abstract_link = dt.find('a', title="Abstract")
                if abstract_link:
                    relative_url = abstract_link.get('href')
                    full_url = f"https://arxiv.org{relative_url}"

                    # 尝试从列表页提取标题（避免后续单独请求）
                    next_dd = dt.find_next_sibling('dd')
                    if next_dd:
                        title_div = next_dd.find('div', class_='list-title')
                        if title_div:
                            title = title_div.text.replace('Title:', '').strip()
                        else:
                            title = "未找到标题"
                    else:
                        title = "未找到标题"

                    papers.append({
                        'title': title,
                        'url': full_url
                    })

                # 更新进度
                progress = 30 + int(70 * i / len(dt_tags))
                self.progress_updated.emit(progress, f"处理论文 {i + 1}/{len(dt_tags)}")

            self.papers_fetched.emit(papers)
            self.progress_updated.emit(100, f"成功获取 {len(papers)} 篇论文")

        except Exception as e:
            self.progress_updated.emit(0, f"发生错误: {str(e)}")

    def fetch_paper_details(self, url):
        self.progress_updated.emit(0, f"获取论文详情: {url}")
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers)

            if response.status_code != 200:
                self.progress_updated.emit(0, f"请求失败，状态码: {response.status_code}")
                return

            soup = BeautifulSoup(response.text, 'html.parser')

            # 提取标题
            title_tag = soup.find('h1', class_='title')
            title = title_tag.text.replace('Title:', '').strip() if title_tag else "未找到标题"

            # 提取作者
            authors_div = soup.find('div', class_='authors')
            if authors_div:
                authors_text = authors_div.text.replace('Authors:', '').strip()
                authors = re.sub(r'\s+', ' ', authors_text)
            else:
                authors = "未找到作者"

            # 提取摘要
            abstract_block = soup.find('blockquote', class_='abstract')
            if abstract_block:
                abstract_text = abstract_block.text.replace('Abstract:', '').strip()
                abstract = re.sub(r'\s+', ' ', abstract_text)
            else:
                abstract = "未找到摘要"

            # 提取提交日期
            submission_div = soup.find('div', class_='submission-history')
            date_text = "未知日期"
            if submission_div:
                dates = re.findall(r'\d{1,2}\s\w{3}\s\d{4}', submission_div.text)
                if dates:
                    date_text = dates[-1]  # 取最近的日期

            # 提取PDF链接
            pdf_link = soup.find('a', text='pdf')
            pdf_url = f"https://arxiv.org{pdf_link['href']}" if pdf_link else ""

            # 提取类别
            subjects = []
            subjects_div = soup.find('td', class_='tablecell subjects')
            if subjects_div:
                subjects = [sub.strip() for sub in subjects_div.text.split(';') if sub.strip()]

            details = {
                'Title': title,
                'Authors': authors,
                'Abstract': abstract,
                'Date': date_text,
                'PDF': pdf_url,
                'Subjects': subjects
            }

            self.paper_details_fetched.emit(details)
            self.progress_updated.emit(100, "论文详情获取完成")

        except Exception as e:
            self.progress_updated.emit(0, f"获取详情时出错: {str(e)}")


class TranslationThread(QThread):
    translation_completed = pyqtSignal(str)
    progress_updated = pyqtSignal(int, str)

    def __init__(self, text, target_lang, method, api_key=None, model_id=None, parent=None):
        super().__init__(parent)
        self.text = text
        self.target_lang = target_lang
        self.method = method
        self.api_key = api_key
        self.model_id = model_id

    def run(self):
        self.progress_updated.emit(0, "正在翻译摘要...")

        if self.method == "硅基流动API":
            self.progress_updated.emit(30, "正在处理文本...")
            self.progress_updated.emit(60, f"正在使用 {self.method} ({self.model_id}) 翻译成 {self.target_lang}...")
            try:
                translation = siliconflow_ts(
                    text=self.text,
                    target_lang=self.target_lang,
                    api_key=self.api_key,
                    model_id=self.model_id
                )
            except Exception as e:
                translation = f"[翻译错误]\n\n错误信息: {str(e)}\n\n原始文本:\n{self.text}"
        elif self.method == "有道翻译":
            self.progress_updated.emit(30, "正在处理文本...")
            self.progress_updated.emit(60, f"正在使用 {self.method} 翻译成 {self.target_lang}...")
            try:
                lang_code_map = {
                    "中文": "zh-CHS",
                    # "英文": "en",
                    "日文": "ja",
                    "中文繁体": "zh-CHT",
                }
                to_lang_code = lang_code_map.get(self.target_lang, "zh")

                # 调用有道翻译函数
                translation = viki_translate_text(self.text, to_lang=to_lang_code)
            except Exception as e:
                translation = f"[翻译错误]\n\n错误信息: {str(e)}\n\n原始文本:\n{self.text}"
        else:
            # 其他翻译方式
            self.progress_updated.emit(60, f"使用 {self.method} 翻译成 {self.target_lang}...")
            time.sleep(1)
            translation = f"[使用 {self.method} 翻译]\n 当前并非配置该翻译方法..."

        self.translation_completed.emit(translation)
        self.progress_updated.emit(100, "翻译完成")


class ArxivBrowser(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("arXiv论文浏览器")
        self.setGeometry(70, 70, 1400, 900)  # 增加窗口宽度以适应第三列

        # 硅基流动-初始化模型列表
        self.model_list = {
            "DeepSeek-V3": "deepseek-ai/DeepSeek-V3",
            "DeepSeek-R1": "deepseek-ai/DeepSeek-R1",
            "kimi": "moonshotai/Kimi-K2-Instruct"
        }
        
        # 设置应用图标
        # self.setWindowIcon(QIcon(self.create_icon()))
        icon_path = "F:/python/MC/爬虫/640x640.ico"
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        else:
            print(f"图标不存在: {icon_path}")

        # 初始化UI
        self.init_ui()

        # 初始化变量
        self.current_papers = []
        self.favorites = []
        self.current_category = "cs.CV"  # 默认类别
        self.current_abstract = ""  # 存储当前摘要

        # 初始化类别
        self.init_categories()

    def create_icon(self):
        # 创建一个简单的应用图标
        pixmap = QPixmap(64, 64)
        pixmap.fill(Qt.transparent)
        return pixmap

    def init_categories(self):
        # 初始化论文类别
        self.categories = {
            "计算机视觉": "cs.CV",
            "机器学习": "cs.LG",
            "人工智能": "cs.AI",
            "自然语言处理": "cs.CL",
            "机器人技术": "cs.RO",
            "计算生物学": "q-bio.QM",
            "物理学": "physics",
            "数学": "math",
            "统计学": "stat"
        }

        # 添加到类别选择框
        for name in self.categories.keys():
            self.category_combo.addItem(name)

    def init_ui(self):
        # 创建主部件和布局
        main_widget = QWidget()
        main_layout = QVBoxLayout()
        main_widget.setLayout(main_layout)
        self.setCentralWidget(main_widget)


        # 创建顶部控制面板
        control_panel = QFrame()
        control_panel.setFrameShape(QFrame.StyledPanel)
        control_panel.setStyleSheet("""
            QFrame {
                background-color: #f0f0f0;
                border-radius: 12px;  /* 增加圆角半径 */
                padding: 10px;
            }
            QLabel {
                font-weight: bold;
                color: #333;
            }
            QPushButton {
                background-color: #4a86e8;
                color: white;
                border-radius: 8px;  /* 增加按钮圆角 */
                padding: 8px 16px;   /* 增加内边距 */
                font-weight: bold;
                font-size: 14px;
            }
            QPushButton:hover {
                background-color: #3a76d8;
            }
            QPushButton:pressed {
                background-color: #2a66c8;
            }
            QComboBox {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 8px;  /* 增加下拉框圆角 */
                background-color: lightsteelblue;
                font-size: 14px;
            }
            QComboBox::drop-down {
                border-radius: 8px;
            }
            QLineEdit {
                padding: 8px;
                border: 1px solid #ccc;
                border-radius: 8px;  /* 增加输入框圆角 */
                background-color: white;
                font-size: 14px;
            }
        """)

        control_layout = QHBoxLayout()
        control_panel.setLayout(control_layout)

        # 类别选择
        category_label = QLabel("选择类别:")
        self.category_combo = QComboBox()
        self.category_combo.setMinimumWidth(150)

        # 搜索框
        search_label = QLabel("搜索:")
        self.search_edit = QLineEdit()
        self.search_edit.setPlaceholderText("从搜索到的标题中进行相关的关键词搜索, 如果没有的话就直接不输入...")
        self.search_edit.setMinimumWidth(500)

        # 按钮
        self.fetch_btn = QPushButton("获取论文")
        self.fetch_btn.clicked.connect(self.fetch_papers)

        self.favorites_btn = QPushButton("收藏夹")
        self.favorites_btn.clicked.connect(self.show_favorites)

        # 添加到控制面板
        control_layout.addWidget(category_label)
        control_layout.addWidget(self.category_combo)
        control_layout.addStretch(1)
        control_layout.addWidget(search_label)
        control_layout.addWidget(self.search_edit)
        control_layout.addWidget(self.fetch_btn)
        control_layout.addWidget(self.favorites_btn)

        # 创建主分割布局
        splitter = QSplitter(Qt.Horizontal)

        # 第一列翻译面板
        translation_control_panel = QFrame()
        translation_control_panel.setFrameShape(QFrame.StyledPanel)
        translation_control_panel.setStyleSheet("""
            QFrame {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 12px;
                padding: 15px;
            }
            QGroupBox {
                border: 1px solid #ddd;
                border-radius: 12px;
                margin-top: 1ex;
                padding: 15px;
                font-weight: bold;
                font-size: 14px;
                background-color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                subcontrol-position: top center;
                padding: 0 10px;
                background-color: white;
                border-radius: 6px;
            }
        """)

        translation_control_layout = QVBoxLayout()
        translation_control_panel.setLayout(translation_control_layout)

        # 翻译控制区域
        translation_control = QGroupBox("摘要翻译")
        translation_control_layout.addWidget(translation_control)

        translation_control_inner_layout = QVBoxLayout()
        translation_control.setLayout(translation_control_inner_layout)

        # 目标语言选择
        lang_layout = QHBoxLayout()
        lang_label = QLabel("目标语言:")
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["中文", "日文","中文繁体"])
        self.lang_combo.setCurrentIndex(0)
        lang_layout.addWidget(lang_label)
        lang_layout.addWidget(self.lang_combo)
        translation_control_inner_layout.addLayout(lang_layout)

        # 翻译方式选择
        method_layout = QHBoxLayout()
        method_label = QLabel("翻译方式:")
        self.method_combo = QComboBox()
        self.method_combo.addItems(["有道翻译", "硅基流动API"])
        self.method_combo.setCurrentIndex(0)
        self.method_combo.currentIndexChanged.connect(self.toggle_api_settings)
        method_layout.addWidget(method_label)
        method_layout.addWidget(self.method_combo)
        translation_control_inner_layout.addLayout(method_layout)

        # API设置区域
        self.api_settings_group = QGroupBox("API设置")
        self.api_settings_group.setVisible(False)
        api_settings_layout = QVBoxLayout()
        self.api_settings_group.setLayout(api_settings_layout)
        translation_control_inner_layout.addWidget(self.api_settings_group)

        # 模型选择
        model_layout = QHBoxLayout()
        model_label = QLabel("模型:")
        self.model_combo = QComboBox()
        for display_name, model_id in self.model_list.items():
            self.model_combo.addItem(f"{display_name}", userData=model_id)
        model_layout.addWidget(model_label)
        model_layout.addWidget(self.model_combo)
        api_settings_layout.addLayout(model_layout)

        # API密钥输入
        api_key_layout = QHBoxLayout()
        api_key_label = QLabel("API密钥:")
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setPlaceholderText("请输入API密钥...")
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        api_key_layout.addWidget(api_key_label)
        api_key_layout.addWidget(self.api_key_edit)
        api_settings_layout.addLayout(api_key_layout)

        # 翻译按钮
        self.translate_btn = QPushButton("翻译摘要")
        self.translate_btn.setStyleSheet("""
            QPushButton {
                background-color: #5bc0de;
                color: white;
                border-radius: 4px;
                padding: 8px 16px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #46b8da;
            }
            QPushButton:pressed {
                background-color: #31b0d5;
            }
            QPushButton:disabled {
                background-color: #cccccc;
            }
        """)
        self.translate_btn.clicked.connect(self.translate_abstract)
        translation_control_inner_layout.addWidget(self.translate_btn)


        # 论文列表
        self.paper_list = QListWidget()
        self.paper_list.setMinimumWidth(300)
        self.paper_list.setStyleSheet("""
            QListWidget {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 12px;  /* 增加圆角 */
                padding: 5px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #eee;
                border-radius: 8px;  /* 增加列表项圆角 */
                margin: 3px;
            }
            QListWidget::item:selected {
                background-color: #e0e0ff;
                color: #333;
                border-radius: 8px;  /* 增加选中项圆角 */
            }
        """)
        self.paper_list.itemSelectionChanged.connect(self.show_paper_details)

        # 第二列详情面板
        details_panel = QFrame()
        details_panel.setFrameShape(QFrame.StyledPanel)
        details_panel.setStyleSheet("""
            QFrame {
                background-color: white;
                border: 1px solid #ddd;
                border-radius: 12px;  /* 增加圆角 */
                padding: 15px;
            }
            QLabel {
                font-weight: bold;
                color: #444;
            }
            #titleLabel {
                font-size: 18px;
                color: #003366;
            }
            #authorLabel {
                color: #555;
                font-size: 14px;
            }
            #dateLabel {
                color: #777;
                font-size: 12px;
            }
            #abstractLabel {
                color: #333;
                font-size: 14px;
            }
            QTextEdit {
                border-radius: 8px;  /* 增加摘要框圆角 */
            }
        """)

        details_layout = QVBoxLayout()
        details_panel.setLayout(details_layout)

        # 标题
        self.title_label = QLabel()
        self.title_label.setObjectName("titleLabel")
        self.title_label.setWordWrap(True)
        self.title_label.setStyleSheet("margin-bottom: 10px;")

        # 作者和日期
        author_date_layout = QHBoxLayout()
        self.author_label = QLabel()
        self.author_label.setObjectName("authorLabel")
        self.author_label.setWordWrap(True)

        self.date_label = QLabel()
        self.date_label.setObjectName("dateLabel")
        self.date_label.setAlignment(Qt.AlignRight)

        author_date_layout.addWidget(self.author_label)
        author_date_layout.addWidget(self.date_label)

        # 类别
        self.subjects_label = QLabel()
        self.subjects_label.setStyleSheet("color: #555; font-size: 12px; margin-top: 5px;")

        # 分隔线
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        separator.setStyleSheet("margin: 10px 0;")

        # 摘要标题
        abstract_title = QLabel("摘要:")
        abstract_title.setStyleSheet("font-weight: bold; color: #444; margin-top: 10px;")

        # 摘要内容
        self.abstract_text = QTextEdit()
        self.abstract_text.setReadOnly(True)
        self.abstract_text.setObjectName("abstractLabel")
        self.abstract_text.setStyleSheet("""
            QTextEdit {
                background-color: #f8f8f8;
                border: 1px solid #eee;
                border-radius: 4px;
                padding: 10px;
                font-size: 14px;
            }
        """)

        # PDF链接
        self.pdf_btn = QPushButton("查看PDF")
        self.pdf_btn.setStyleSheet("""
            QPushButton {
                background-color: #d9534f;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #c9302c;
            }
        """)
        self.pdf_btn.clicked.connect(self.open_pdf)
        self.pdf_btn.hide()

        # 收藏按钮
        self.favorite_btn = QPushButton("添加到收藏夹")
        self.favorite_btn.setStyleSheet("""
            QPushButton {
                background-color: #5cb85c;
                color: white;
                border-radius: 4px;
                padding: 6px 12px;
                font-weight: bold;
                margin-top: 10px;
            }
            QPushButton:hover {
                background-color: #4cae4c;
            }
        """)
        self.favorite_btn.clicked.connect(self.add_to_favorites)

        # 添加到详情布局
        details_layout.addWidget(self.title_label)
        details_layout.addLayout(author_date_layout)
        details_layout.addWidget(self.subjects_label)
        details_layout.addWidget(separator)
        details_layout.addWidget(abstract_title)
        details_layout.addWidget(self.abstract_text, 1)
        details_layout.addWidget(self.pdf_btn)
        details_layout.addWidget(self.favorite_btn)


        # 第四列: 翻译结果面板
        translation_result_panel = QFrame()
        translation_result_panel.setFrameShape(QFrame.StyledPanel)
        translation_result_panel.setStyleSheet("""
            QFrame {
                background-color: #f8f8f8;
                border: 1px solid #ddd;
                border-radius: 12px;
                padding: 15px;
            }
            QLabel {
                font-weight: bold;
                color: #444;
            }
        """)

        translation_result_layout = QVBoxLayout()
        translation_result_panel.setLayout(translation_result_layout)

        # 翻译结果标题
        translation_title = QLabel("翻译结果:")
        translation_title.setStyleSheet("font-weight: bold; color: #444; margin-top: 5px;")

        # 翻译结果标题
        translation_title = QLabel("翻译结果:")
        translation_title.setStyleSheet("font-weight: bold; color: #444; margin-bottom: 10px;")
        translation_result_layout.addWidget(translation_title)

        # 翻译结果显示区域 - 现在更大
        self.translation_result = QTextEdit()
        self.translation_result.setReadOnly(True)
        self.translation_result.setStyleSheet("""
            QTextEdit {
                background-color: #ffffff;
                border: 1px solid #eee;
                border-radius: 8px;
                padding: 15px;
                font-size: 14px;
            }
        """)
        self.translation_result.setPlaceholderText("翻译结果将显示在这里...")
        translation_result_layout.addWidget(self.translation_result, 1)

        # 四列分割器
        splitter.addWidget(self.paper_list)
        splitter.addWidget(details_panel)
        splitter.addWidget(translation_result_panel)
        splitter.addWidget(translation_control_panel)
        # 设置四列的初始宽度比例
        splitter.setSizes([250, 400, 550,100])

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setStyleSheet("""
            QProgressBar {
                border: 1px solid #ccc;
                border-radius: 8px;  /* 增加圆角 */
                text-align: center;
                height: 20px;
                font-size: 12px;
            }
            QProgressBar::chunk {
                background-color: #5cb85c;
                border-radius: 8px;  /* 增加进度块圆角 */
            }
        """)
        self.progress_bar.setVisible(False)

        # 状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_label = QLabel("就绪")
        self.status_bar.addWidget(self.status_label)
        self.status_bar.addPermanentWidget(self.progress_bar)

        # 添加到主布局
        main_layout.addWidget(control_panel)
        main_layout.addWidget(splitter, 1)

        # 创建菜单栏
        self.create_menu()

        # 设置样式
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f5f5f5;
            }
            QSplitter::handle {
                background-color: #e0e0e0;
                width: 6px;
                border-radius: 3px;
            }
            /* 增加菜单栏圆角 */
            QMenuBar {
                background-color: #e0e0e0;
                padding: 8px;
                border-bottom: 1px solid #ccc;
                border-radius: 8px;
            }
            /* 增加菜单圆角 */
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                border-radius: 8px;
                padding: 5px;
            }
            QMenu::item {
                padding: 8px 30px 8px 20px;
                border-radius: 4px;
            }
        """)

        # 初始加载示例数据
        self.load_sample_data()

    def create_menu(self):
        # 创建菜单栏
        menubar = self.menuBar()
        menubar.setStyleSheet("""
            QMenuBar {
                background-color: #e0e0e0;
                padding: 5px;
                border-bottom: 1px solid #ccc;
            }
            QMenuBar::item {
                padding: 5px 10px;
                background: transparent;
            }
            QMenuBar::item:selected {
                background: #d0d0d0;
            }
            QMenu {
                background-color: white;
                border: 1px solid #ccc;
                padding: 5px;
            }
            QMenu::item {
                padding: 5px 30px 5px 20px;
            }
            QMenu::item:selected {
                background-color: #e0e0ff;
            }
        """)

        # 文件菜单
        file_menu = menubar.addMenu('文件')

        export_action = QAction('导出收藏夹', self)
        export_action.triggered.connect(self.export_favorites)
        file_menu.addAction(export_action)

        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助')

        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def load_sample_data(self):
        # 加载示例数据
        sample_papers = [
            {'title': 'Attention Is All You Need', 'url': 'https://arxiv.org/abs/1706.03762'},
        ]

        self.current_papers = sample_papers
        self.update_paper_list()

    def fetch_papers(self):
        # 获取选中的类别
        category_name = self.category_combo.currentText()
        self.current_category = self.categories.get(category_name, "cs.CV")
        # 构建URL
        url = f"https://arxiv.org/list/{self.current_category}/recent?skip=0&show=100"

        # 创建并启动获取线程
        self.fetcher = ArxivFetcher(url)
        self.fetcher.progress_updated.connect(self.update_progress)
        self.fetcher.papers_fetched.connect(self.handle_papers_fetched)
        self.fetcher.start()

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"正在获取 {category_name} 类别的论文...")
        self.fetch_btn.setEnabled(False)

    def update_progress(self, value, message):
        self.progress_bar.setValue(value)
        self.status_label.setText(message)

        if value == 100:
            self.progress_bar.setVisible(False)
            self.fetch_btn.setEnabled(True)

    def handle_papers_fetched(self, papers):
        self.current_papers = papers
        self.update_paper_list()

        # 应用搜索过滤
        search_text = self.search_edit.text().strip()
        if search_text:
            self.filter_papers(search_text)

    def update_paper_list(self):
        self.paper_list.clear()

        for paper in self.current_papers:
            item = QListWidgetItem(paper['title'])
            item.setData(Qt.UserRole, paper['url'])
            self.paper_list.addItem(item)

    def filter_papers(self, text):
        text = text.lower()

        for i in range(self.paper_list.count()):
            item = self.paper_list.item(i)
            item_text = item.text().lower()
            item.setHidden(text not in item_text)

    def show_paper_details(self):
        selected_items = self.paper_list.selectedItems()
        if not selected_items:
            return

        selected_item = selected_items[0]
        paper_url = selected_item.data(Qt.UserRole)

        # 创建并启动获取详情的线程
        self.fetcher = ArxivFetcher(paper_url)
        self.fetcher.fetch_details_for = paper_url
        self.fetcher.progress_updated.connect(self.update_progress)
        self.fetcher.paper_details_fetched.connect(self.display_paper_details)
        self.fetcher.start()

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"正在获取论文详情...")

    def display_paper_details(self, details):
        self.title_label.setText(f"标题: {details['Title']}")
        self.author_label.setText(f"作者信息: {details['Authors']}")
        self.date_label.setText(f"最近提交日期: {details['Date']}")

        # 显示类别
        if details['Subjects']:
            subjects = ", ".join(details['Subjects'])
            self.subjects_label.setText(f"类别: {subjects}")
        else:
            self.subjects_label.setText("")

        # 显示摘要
        self.abstract_text.setPlainText(details['Abstract'])
        self.current_abstract = details['Abstract']  # 保存当前摘要用于翻译
        self.translation_result.clear()  # 清除之前的翻译结果

        # 启用翻译按钮
        self.translate_btn.setEnabled(True)

        # 显示PDF按钮
        if details['PDF']:
            self.pdf_btn.show()
            self.pdf_btn.setProperty("pdf_url", details['PDF'])
        else:
            self.pdf_btn.hide()

        # 更新收藏按钮状态
        current_url = details.get('url', '')
        if any(fav['url'] == current_url for fav in self.favorites):
            self.favorite_btn.setText("从收藏夹移除")
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d9534f;
                    color: white;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #c9302c;
                }
            """)
        else:
            self.favorite_btn.setText("添加到收藏夹")
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5cb85c;
                    color: white;
                    border-radius: 4px;
                    padding: 6px 12px;
                    font-weight: bold;
                    margin-top: 10px;
                }
                QPushButton:hover {
                    background-color: #4cae4c;
                }
            """)

    def open_pdf(self):
        pdf_url = self.pdf_btn.property("pdf_url")
        if pdf_url:
            QMessageBox.information(self, "打开PDF", f"将在浏览器中打开PDF:\n{pdf_url}")
            # 在实际应用中，这里可以使用QDesktopServices打开URL
        else:
            QMessageBox.warning(self, "错误", "PDF链接无效")

    def add_to_favorites(self):
        selected_items = self.paper_list.selectedItems()
        if not selected_items:
            QMessageBox.warning(self, "错误", "请先选择一篇论文")
            return

        selected_item = selected_items[0]
        paper_title = selected_item.text()
        paper_url = selected_item.data(Qt.UserRole)

        # 检查是否已在收藏夹
        if any(fav['url'] == paper_url for fav in self.favorites):
            # 移除收藏
            self.favorites = [fav for fav in self.favorites if fav['url'] != paper_url]
            self.favorite_btn.setText("添加到收藏夹")
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #5cb85c;
                    color: white;
                }
            """)
            QMessageBox.information(self, "收藏夹", f"已从收藏夹移除: {paper_title}")
        else:
            # 添加到收藏
            self.favorites.append({
                'title': paper_title,
                'url': paper_url
            })
            self.favorite_btn.setText("从收藏夹移除")
            self.favorite_btn.setStyleSheet("""
                QPushButton {
                    background-color: #d9534f;
                    color: white;
                }
            """)
            QMessageBox.information(self, "收藏夹", f"已添加到收藏夹: {paper_title}")

    def show_favorites(self):
        if not self.favorites:
            QMessageBox.information(self, "收藏夹", "收藏夹为空")
            return

        # 临时显示收藏夹中的论文
        self.current_papers = self.favorites
        self.update_paper_list()
        self.status_label.setText(f"显示收藏夹中的 {len(self.favorites)} 篇论文")

    def export_favorites(self):
        if not self.favorites:
            QMessageBox.warning(self, "导出收藏夹", "收藏夹为空")
            return

        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出收藏夹", "", "文本文件 (*.txt);;所有文件 (*)"
        )

        if not file_path:
            return

        try:
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write("arXiv论文收藏夹\n")
                f.write("=" * 40 + "\n\n")

                for i, paper in enumerate(self.favorites, 1):
                    f.write(f"{i}. {paper['title']}\n")
                    f.write(f"   链接: {paper['url']}\n\n")

            QMessageBox.information(self, "导出成功", "收藏夹已成功导出")
        except Exception as e:
            QMessageBox.critical(self, "导出错误", f"导出失败: {str(e)}")

    def toggle_api_settings(self):
        """根据选择的翻译方法显示或隐藏API设置"""
        method = self.method_combo.currentText()
        if method == "硅基流动API":
            self.api_settings_group.setVisible(True)
        else:
            self.api_settings_group.setVisible(False)

    def translate_abstract(self):
        if not self.current_abstract:
            QMessageBox.warning(self, "翻译错误", "没有可翻译的摘要内容")
            return

        target_lang = self.lang_combo.currentText()
        method = self.method_combo.currentText()

        # 获取API设置
        api_key = None
        model_id = None
        if method == "硅基流动API":
            api_key = self.api_key_edit.text().strip()
            model_id = self.model_combo.currentData()

            if not api_key:
                QMessageBox.warning(self, "API密钥缺失", "请提供有效的API密钥")
                return
        # 创建并启动翻译线程
        self.translator = TranslationThread(
            self.current_abstract,
            target_lang,
            method,
            api_key=api_key,
            model_id=model_id
        )

        self.translator.progress_updated.connect(self.update_progress)
        self.translator.translation_completed.connect(self.display_translation)
        self.translator.start()

        # 显示进度条
        self.progress_bar.setVisible(True)
        self.status_label.setText(f"正在翻译摘要到{target_lang}...")
        self.translate_btn.setEnabled(False)

    def display_translation(self, result):
        self.translation_result.setPlainText(result)
        self.translate_btn.setEnabled(True)
        self.progress_bar.setVisible(False)
        self.status_label.setText("翻译完成")

    def show_about(self):
        about_text = """
        <h2>arXiv论文摘要速览</h2>
        <p>版本: 1.0</p>
        <p>功能包括：</p>
        <ul>
            <li>浏览不同领域的论文</li>
            <li>查看论文详细信息</li>
            <li>搜索和过滤论文</li>
            <li>收藏感兴趣的论文</li>
            <li>导出收藏夹</li>
            <li>摘要翻译</li>
        </ul>
        <p>翻译功能支持：</p>
        <ul>
            <li>目标语言：中文简体, 日文, 中文繁体</li>
            <li>翻译方式：有道翻译, 硅基流动API</li>
        </ul>
        """
        QMessageBox.about(self, "关于 arXiv论文摘要速览", about_text)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")

    # 设置应用字体
    font = QFont("微软雅黑", 10)
    app.setFont(font)

    browser = ArxivBrowser()
    browser.show()
    sys.exit(app.exec_())
