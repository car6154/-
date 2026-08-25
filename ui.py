# ui.py
import pandas as pd
import webbrowser
from PySide6.QtGui import QClipboard
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                               QPushButton, QLabel, QLineEdit, QComboBox, 
                               QTableView, QGroupBox, QStatusBar, QFileDialog, QMessageBox, QDialog, QInputDialog)
from PySide6.QtCore import QAbstractTableModel, Qt, QThread, Signal
from excel import DataLoader
from database import db
from analysis import PriceAnalyzer
from scraper import EncarScraper
import matplotlib.backends.backend_qtagg as plt_backend

class ScraperThread(QThread):
    progress_signal = Signal(str)
    finished_signal = Signal(object)
    error_signal = Signal(str)

    def __init__(self, target_url):
        super().__init__()
        self.target_url = target_url

    def run(self):
        try:
            df = EncarScraper.run_scan(self.target_url, lambda msg: self.progress_signal.emit(msg))
            self.finished_signal.emit(df)
        except Exception as e:
            self.error_signal.emit(str(e))

class ChartDialog(QDialog):
    def __init__(self, fig, parent=None):
        super().__init__(parent)
        self.setWindowTitle("시세 분석 시각화 리포트")
        self.resize(600, 450)
        layout = QVBoxLayout(self)
        canvas = plt_backend.FigureCanvasQTAgg(fig)
        layout.addWidget(canvas)

class PandasModel(QAbstractTableModel):
    def __init__(self, data):
        super().__init__()
        self._data = data
    def rowCount(self, parent=None): return self._data.shape[0]
    def columnCount(self, parent=None): return self._data.shape[1]
    def data(self, index, role=Qt.DisplayRole):
        if index.isValid() and role == Qt.DisplayRole:
            return str(self._data.iloc[index.row(), index.column()])
        return None
    def headerData(self, col, orientation, role):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole:
            return str(self._data.columns[col])
        return None

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("J-PRO: Advanced Auto Valuation System")
        self.resize(1350, 850)
        self.original_data = pd.DataFrame()
        self.current_data = pd.DataFrame()
        self.model = None 
        self.scraper_thread = None
        self.setup_ui()

    def setup_ui(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        title_label = QLabel("🏅 J-PRO : Advanced Auto Valuation System")
        title_label.setStyleSheet("font-size: 22px; font-weight: bold; color: #2C3E50; margin: 10px 0px;")
        main_layout.addWidget(title_label)

        top_layout = QHBoxLayout()
        self.btn_load_excel = QPushButton("📁 엑셀/CSV 불러오기")
        self.btn_save_db = QPushButton("💾 DB에 저장하기")
        self.btn_load_db = QPushButton("🗄️ DB에서 불러오기")
        self.btn_save_db.setStyleSheet("color: white; background-color: #2E86C1; font-weight: bold;")
        
        self.btn_web_scanner = QPushButton("🌐 실시간 엔카 정밀 스캔")
        self.btn_web_scanner.setStyleSheet("background-color: #E67E22; color: white; font-weight: bold; font-size: 14px; padding: 5px;")
        self.btn_web_scanner.clicked.connect(self.action_run_scanner)
        
        self.btn_load_excel.clicked.connect(self.action_load_file)
        self.btn_save_db.clicked.connect(self.action_save_db)
        self.btn_load_db.clicked.connect(self.action_load_db)
        
        top_layout.addWidget(self.btn_load_excel)
        top_layout.addWidget(self.btn_save_db)
        top_layout.addWidget(self.btn_load_db)
        top_layout.addStretch()
        top_layout.addWidget(self.btn_web_scanner)

        search_group = QGroupBox("차량 정밀 검색")
        grid_layout = QGridLayout()
        
        self.combo_brand = QComboBox()
        self.combo_brand.addItem("전체")
        self.combo_model = QComboBox()
        self.combo_model.addItem("전체")
        self.combo_sub_model = QComboBox()
        self.combo_sub_model.addItem("전체")
        
        self.combo_brand.currentTextChanged.connect(self.update_model_list)
        self.combo_model.currentTextChanged.connect(self.update_sub_model_list)
        
        grid_layout.addWidget(QLabel("제조사/브랜드:"), 0, 0)
        grid_layout.addWidget(self.combo_brand, 0, 1)
        grid_layout.addWidget(QLabel("모델명:"), 0, 2)
        grid_layout.addWidget(self.combo_model, 0, 3)
        grid_layout.addWidget(QLabel("세부모델:"), 0, 4)
        grid_layout.addWidget(self.combo_sub_model, 0, 5)
        
        grid_layout.setColumnStretch(1, 2)
        grid_layout.setColumnStretch(3, 3)
        grid_layout.setColumnStretch(5, 7)

        self.combo_status = QComboBox()
        self.combo_status.addItems(["전체", "판매중", "판매완료", "계약", "실시간(엔카)"])
        
        self.input_mileage = QLineEdit()
        self.input_mileage.setPlaceholderText("타겟 주행거리")
        self.input_mileage.setFixedWidth(120) 
        
        self.input_year = QLineEdit()
        self.input_year.setPlaceholderText("연식 (예: 2017)")
        self.input_year.setFixedWidth(100)
        
        grid_layout.addWidget(QLabel("판매상태:"), 1, 0)
        grid_layout.addWidget(self.combo_status, 1, 1)
        
        year_km_layout = QHBoxLayout()
        year_km_layout.addWidget(QLabel("연식:"))
        year_km_layout.addWidget(self.input_year)
        year_km_layout.addWidget(QLabel("주행거리(km):"))
        year_km_layout.addWidget(self.input_mileage)
        year_km_layout.addStretch()
        
        grid_layout.addLayout(year_km_layout, 1, 2, 1, 4)

        btn_layout = QVBoxLayout()
        self.btn_search = QPushButton("🔍 검색")
        self.btn_search.setStyleSheet("background-color: #34495E; color: white; font-weight: bold; height: 35px;")
        self.btn_reset = QPushButton("🔄 초기화")
        btn_layout.addWidget(self.btn_search)
        btn_layout.addWidget(self.btn_reset)
        
        self.btn_search.clicked.connect(self.action_search)
        self.input_mileage.returnPressed.connect(self.action_search)
        self.input_year.returnPressed.connect(self.action_search)
        self.btn_reset.clicked.connect(self.action_reset)
        
        grid_layout.addLayout(btn_layout, 0, 6, 2, 1)
        search_group.setLayout(grid_layout)

        content_layout = QHBoxLayout()
        table_group = QGroupBox("데이터 목록 (더블클릭 시 링크 열림)")
        table_layout = QVBoxLayout()
        self.table_view = QTableView()
        self.table_view.setAlternatingRowColors(True)
        self.table_view.doubleClicked.connect(self.action_double_click_table)
        table_layout.addWidget(self.table_view)
        table_group.setLayout(table_layout)

        analysis_group = QGroupBox("현재 조건 시세 분석 (단위: 만원)")
        analysis_layout = QVBoxLayout()
        
        self.label_total_count = QLabel("조회된 데이터: 0건")
        self.label_min_price = QLabel("최저가: -")
        self.label_max_price = QLabel("최고가: -")
        self.label_mean_price = QLabel("평균가: -")
        self.label_median_price = QLabel("중앙값: -")
        self.label_suggested_price = QLabel("추천 매입가: -")
        
        font = self.label_suggested_price.font()
        font.setBold(True)
        font.setPointSize(14)
        self.label_suggested_price.setFont(font)
        self.label_suggested_price.setStyleSheet("color: #C0392B; margin-top: 10px;")
        
        self.btn_show_chart = QPushButton("📊 시세 분포 그래프 보기")
        self.btn_show_chart.setStyleSheet("background-color: #27AE60; color: white; font-weight: bold; padding: 6px;")
        self.btn_show_chart.clicked.connect(self.action_show_chart)

        analysis_layout.addWidget(self.label_total_count)
        analysis_layout.addWidget(QLabel("------------------"))
        analysis_layout.addWidget(self.label_min_price)
        analysis_layout.addWidget(self.label_max_price)
        analysis_layout.addWidget(self.label_mean_price)
        analysis_layout.addWidget(self.label_median_price)
        analysis_layout.addWidget(self.label_suggested_price)
        analysis_layout.addSpacing(15)
        analysis_layout.addWidget(self.btn_show_chart)
        analysis_layout.addStretch()
        analysis_group.setLayout(analysis_layout)

        content_layout.addWidget(table_group, 7)
        content_layout.addWidget(analysis_group, 3)

        main_layout.addLayout(top_layout)
        main_layout.addWidget(search_group)
        main_layout.addLayout(content_layout)

        self.statusBar = QStatusBar()
        self.setStatusBar(self.statusBar)
        self.statusBar.showMessage("프로그램 준비 완료")

    def _update_table_and_ui(self, df, msg="완료", target_mileage=None):
        self.current_data = df
        self.model = PandasModel(self.current_data)
        self.table_view.setModel(self.model)
        self.label_total_count.setText(f"조회된 데이터: {len(df):,}건")
        self.statusBar.showMessage(msg)
        self.run_price_analysis(df, target_mileage)

    def action_run_scanner(self):
        clipboard_text = QApplication.clipboard().text().strip()
        default_url = clipboard_text if "encar.com" in clipboard_text else ""
        
        url, ok = QInputDialog.getText(
            self, 
            "엔카 실시간 스캔", 
            "스캔할 엔카 주소를 넣어주세요:\n(방금 주소를 복사하셨다면 이미 입력되어 있습니다. 엔터만 누르세요!)",
            QLineEdit.Normal,
            default_url
        )
        if ok and url:
            self.statusBar.showMessage("실시간 스캔을 시작합니다... (창을 닫지 마세요)")
            self.btn_web_scanner.setEnabled(False)
            self.btn_web_scanner.setText("⏳ 스캔 진행 중...")
            
            self.scraper_thread = ScraperThread(url)
            self.scraper_thread.progress_signal.connect(self.on_scanner_progress)
            self.scraper_thread.finished_signal.connect(self.on_scanner_finished)
            self.scraper_thread.error_signal.connect(self.on_scanner_error)
            self.scraper_thread.start()

    def on_scanner_progress(self, msg):
        self.statusBar.showMessage(msg)

    def on_scanner_finished(self, new_df):
        self.btn_web_scanner.setEnabled(True)
        self.btn_web_scanner.setText("🌐 실시간 엔카 정밀 스캔")
        
        if not new_df.empty:
            new_df = self._inject_virtual_brand(new_df)
            
            if self.original_data.empty:
                self.original_data = new_df
            else:
                self.original_data = pd.concat([self.original_data, new_df], ignore_index=True)
            
            self.populate_dropdowns(self.original_data)
            self.action_reset() 
            QMessageBox.information(self, "스캔 완료", f"실시간 매물 {len(new_df)}건이 기존 데이터에 병합되었습니다.\n(판매상태: '실시간(엔카)'로 필터링 가능)")
        else:
            QMessageBox.warning(self, "결과 없음", "조건에 맞는 실매물을 가져오지 못했습니다.")

    def on_scanner_error(self, error_msg):
        self.btn_web_scanner.setEnabled(True)
        self.btn_web_scanner.setText("🌐 실시간 엔카 정밀 스캔")
        self.statusBar.showMessage("스캔 실패")
        QMessageBox.critical(self, "스캔 에러", f"크롤링 중 오류가 발생했습니다:\n{error_msg}")

    def _inject_virtual_brand(self, df):
        brand_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['브랜드', '제조사', 'brand'])), None)
        if brand_col: return df
        brand_mapping = {
            '현대': ['아반떼', '쏘나타', '그랜저', '싼타페', '투싼', '팰리세이드', '코나', '베뉴', '아이오닉', '스타리아', '포터', '캐스퍼'],
            '기아': ['K3', 'K5', 'K7', 'K8', 'K9', '모닝', '레이', '쏘렌토', '스포티지', '카니발', '셀토스', '니로', '모하비', 'EV6', '봉고'],
            '제네시스': ['G70', 'G80', 'G90', 'GV60', 'GV70', 'GV80', 'EQ900'],
            '쉐보레(GM)': ['스파크', '말리부', '트랙스', '이쿼녹스', '콜로라도', '트래버스', '크루즈'],
            '르노코리아': ['SM3', 'SM5', 'SM6', 'QM3', 'QM6', 'XM3'],
            'KG(쌍용)': ['티볼리', '코란도', '토레스', '렉스턴'],
            'BMW': ['BMW', '520', '320', 'X5'],
            '벤츠': ['벤츠', 'E-클래스', 'C-클래스', 'S-클래스', 'GLC', 'GLE']
        }
        def get_brand(model_name):
            name = str(model_name).upper()
            for brand, keywords in brand_mapping.items():
                if any(kw.upper() in name for kw in keywords): return brand
            return "기타 수입/국산"
        model_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['차량명', '모델', 'model'])), None)
        if model_col: df['가상_브랜드'] = df[model_col].apply(get_brand)
        return df

    def _get_unique_values(self, df, column_keywords):
        target_col = next((c for c in df.columns if any(k in str(c).lower() for k in column_keywords)), None)
        if target_col: return sorted([str(x) for x in df[target_col].dropna().unique() if str(x).strip() != ""])
        return []

    def populate_dropdowns(self, df):
        self.combo_brand.blockSignals(True)
        self.combo_brand.clear()
        self.combo_brand.addItem("전체")
        brands = self._get_unique_values(df, ['브랜드', '제조사', 'brand', '가상_브랜드'])
        if brands: self.combo_brand.addItems(brands)
        self.combo_brand.blockSignals(False)
        self.update_model_list(self.combo_brand.currentText())

    def update_model_list(self, brand):
        self.combo_model.blockSignals(True)
        self.combo_model.clear()
        self.combo_model.addItem("전체")
        df = self.original_data
        if not df.empty:
            if brand != "전체":
                brand_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['브랜드', '제조사', 'brand', '가상_브랜드'])), None)
                if brand_col: df = df[df[brand_col].astype(str) == brand]
            models = self._get_unique_values(df, ['차량명', '모델', 'model'])
            self.combo_model.addItems(models)
        self.combo_model.blockSignals(False)
        self.update_sub_model_list(self.combo_model.currentText())

    def update_sub_model_list(self, model):
        self.combo_sub_model.blockSignals(True)
        self.combo_sub_model.clear()
        self.combo_sub_model.addItem("전체")
        df = self.original_data
        if not df.empty and model != "전체":
            model_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['차량명', '모델', 'model'])), None)
            if model_col: df = df[df[model_col].astype(str) == model]
            sub_models = self._get_unique_values(df, ['세부', '등급', 'sub'])
            self.combo_sub_model.addItems(sub_models)
        self.combo_sub_model.blockSignals(False)

    def run_price_analysis(self, df, target_mileage):
        stats = PriceAnalyzer.analyze(df, target_mileage)
        if stats:
            self.label_min_price.setText(f"최저가: {stats['min']:,}")
            self.label_max_price.setText(f"최고가: {stats['max']:,}")
            self.label_mean_price.setText(f"평균가: {stats['mean']:,}")
            self.label_median_price.setText(f"중앙값: {stats['median']:,}")
            self.label_suggested_price.setText(f"추천 매입가: {stats['suggested']:,}")
        else:
            self.label_min_price.setText("최저가: -")
            self.label_max_price.setText("최고가: -")
            self.label_mean_price.setText("평균가: -")
            self.label_median_price.setText("중앙값: -")
            self.label_suggested_price.setText("추천 매입가: 분석 불가")

    def action_show_chart(self):
        if self.current_data.empty: return
        fig = PriceAnalyzer.draw_price_distribution_chart(self.current_data)
        if fig:
            dialog = ChartDialog(fig, self)
            dialog.exec()

    def action_load_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "파일 선택", "", "Excel/CSV (*.csv *.xls *.xlsx)")
        if file_path:
            df = DataLoader.load_file(file_path)
            if df is not None:
                trash_keywords = ['pid', '이전차량', '자사몰', 'e광고', '매입유형', '광고']
                cols_to_drop = [col for col in df.columns if any(k in str(col).lower() for k in trash_keywords)]
                df = df.drop(columns=cols_to_drop, errors='ignore') 
                
                df = self._inject_virtual_brand(df)
                self.original_data = df.copy()
                self.populate_dropdowns(self.original_data)
                self._update_table_and_ui(df, f"데이터 로드 및 자동 정제 완료! (총 {len(df):,}건)")

    # ★ 방금 전에 추가했던 [누적 저장 로직]이 완벽하게 결합되어 있습니다!
    def action_save_db(self):
        if self.original_data.empty:
            QMessageBox.warning(self, "경고", "저장할 데이터가 없습니다.")
            return
            
        existing_df = db.load_all_data()
        
        if not existing_df.empty:
            merged_df = pd.concat([existing_df, self.original_data], ignore_index=True)
            merged_df = merged_df.drop_duplicates(keep='last')
        else:
            merged_df = self.original_data

        if db.save_raw_data(merged_df):
            QMessageBox.information(self, "저장 성공", f"과거 데이터 증발 없이 총 {len(merged_df)}건이 누적 저장되었습니다.")
            self.original_data = merged_df 
            self.populate_dropdowns(self.original_data)

    def action_load_db(self):
        df = db.load_all_data()
        if not df.empty:
            df = self._inject_virtual_brand(df)
            self.original_data = df.copy()
            self.populate_dropdowns(self.original_data)
            self._update_table_and_ui(df, "DB 데이터 로드 완료!")

    def action_search(self):
        if self.original_data.empty: return
        df = self.original_data.copy()
        
        brand = self.combo_brand.currentText()
        model = self.combo_model.currentText()
        sub_model = self.combo_sub_model.currentText()
        status = self.combo_status.currentText()
        target_mileage = self.input_mileage.text().strip()
        target_year = self.input_year.text().strip()

        if brand != "전체":
            brand_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['브랜드', '제조사', 'brand', '가상_브랜드'])), None)
            if brand_col: df = df[df[brand_col].astype(str) == brand]
            
        if model != "전체":
            model_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['차량명', '모델', 'model'])), None)
            if model_col: df = df[df[model_col].astype(str) == model]
            
        if sub_model != "전체":
            sub_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['세부', '등급', 'sub'])), None)
            if sub_col: df = df[df[sub_col].astype(str) == sub_model]

        if status != "전체":
            mask = df.astype(str).apply(lambda x: x.str.contains(status, case=False, na=False)).any(axis=1)
            df = df[mask]
            
        if target_year:
            year_col = next((c for c in df.columns if any(k in str(c).lower() for k in ['연식', '최초등록', 'year', '년식'])), None)
            if year_col:
                mask = df[year_col].astype(str).str.contains(target_year, na=False)
                df = df[df.index.isin(df[mask].index)]

        self._update_table_and_ui(df, f"복합 검색 완료: {len(df):,}건 조회됨", target_mileage)

    def action_reset(self):
        self.combo_brand.setCurrentIndex(0)
        self.combo_model.setCurrentIndex(0)
        self.combo_sub_model.setCurrentIndex(0)
        self.combo_status.setCurrentIndex(0)
        self.input_mileage.clear()
        self.input_year.clear()
        if not self.original_data.empty:
            self._update_table_and_ui(self.original_data, "검색 초기화 완료")

    def action_double_click_table(self, index):
        if not index.isValid(): return
        row = index.row()
        url_cols = [col for col in self.current_data.columns if 'url' in str(col).lower() or '링크' in str(col)]
        if url_cols:
            url = str(self.current_data.iloc[row][url_cols[0]])
            if url.startswith('http'): webbrowser.open(url)