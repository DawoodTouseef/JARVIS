import sqlite3
import json

try:
    from mendeleev import element as mendeleev_element
except ImportError:
    mendeleev_element = None
import numpy as np
import pandas as pd
import pyperclip
import wikipediaapi
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
                             QLineEdit, QPushButton, QTextEdit, QProgressBar, QLabel, QSplitter, QGroupBox,
                             QFormLayout, QSlider, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox, QTableWidget,
                             QTableWidgetItem, QFileDialog, QInputDialog, QTextBrowser, QMessageBox,
                             QStackedWidget,)
from PyQt5.QtCore import Qt, QThread, pyqtSignal
from PyQt5.QtGui import QFont
from crewai import Agent, Task, Crew, Process
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas as pdf_canvas

try:
    from rdkit import Chem
    from rdkit.Chem import Lipinski, Descriptors
except ImportError:
    Chem = None
try:
    import pubchempy as pcp
except ImportError:
    pcp = None
try:
    from chempy import balance_stoichiometry
except ImportError:
    balance_stoichiometry = None
try:
    from mendeleev import element
except ImportError:
    element = None
try:
    from pymol import cmd
except ImportError:
    cmd = None
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None
from core.Agent_models import get_model_from_database


class QueryThread(QThread):
    result = pyqtSignal(object)

    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args

    def run(self):
        try:
            result = self.func(*self.args)
            self.result.emit(result)
        except Exception as e:
            self.result.emit(f"Error: {str(e)}")


class CheExplorer(QMainWindow):
    def __init__(self,parent=None):
        super().__init__(parent=parent)
        self.setWindowTitle("Chemistry Explorer Ultimate")
        self.setMinimumSize(1600, 1000)
        self.cache_db = sqlite3.connect("chem_explorer_cache.db", check_same_thread=False)
        self.init_cache()
        self.package_properties = self.get_package_properties()
        self.element_data = self.get_element_data()
        self.wikipedia = wikipediaapi.Wikipedia(language="en", user_agent="Mozilla/5.0") if wikipediaapi else None
        self.educational_mode = False
        self.panel_sizes = {'left': 800, 'right': 800}
        self.theme = 'dark'
        self.font_size = 14
        self.recent_queries = []
        self.max_recent_queries = 10
        self.init_crewai()
        self.init_openai()
        self.setup_advanced_features()
        self.init_ui()
        self.init_chat_interface()
        self.add_auto_save_toggle_to_advanced_tab()
        self.load_panel_sizes()
        self.selected_reactants = []
        self.selected_products = []

    def init_cache(self):
        cursor = self.cache_db.cursor()
        cursor.execute("""CREATE TABLE IF NOT EXISTS cache (
            query TEXT, result TEXT, mode TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
            PRIMARY KEY (query, mode))""")
        cursor.execute("""CREATE TABLE IF NOT EXISTS reactions (
            reaction TEXT PRIMARY KEY, result TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)""")
        self.cache_db.commit()

    def get_package_properties(self):
        return {
            "mendeleev": ["atomic_weight", "density", "melting_point", "boiling_point", "electronegativity",
                          "atomic_radius", "oxidation_states", "ionization_energies"],
            "chemicals": ["molecular_weight", "boiling_point", "melting_point", "critical_temperature", "heat_capacity",
                          "vapor_pressure", "enthalpy_formation"],
            "chemlib": ["atomic_mass", "density", "melting_point", "boiling_point", "electronegativity",
                        "ionization_energy", "electron_affinity", "atomic_number"],
            "chempy": ["molar_mass", "composition", "equilibrium_constant", "reaction_rate", "gibbs_free_energy"],
            "pubchempy": ["molecular_weight", "iupac_name", "exact_mass", "canonical_smiles", "molecular_formula"],
            "periodictable": ["mass", "density", "number", "neutron_cross_section", "ionization", "atomic_volume"],
            "pymatgen": ["atomic_mass", "electronegativity", "atomic_radius", "is_metalloid", "molar_volume",
                         "thermal_conductivity"],
            "NistChemPy": ["molecular_weight", "thermodynamic_properties", "spectral_data", "heat_formation",
                           "entropy"],
            "pyEQL": ["activity_coefficient", "ionic_strength", "osmotic_coefficient", "conductivity",
                      "diffusion_coefficient"],
            "ChemSpiPy": ["molecular_weight", "common_name", "smiles", "predicted_properties", "log_p"]
        }

    def get_element_group(self, elem):
        if elem.atomic_number in [1, 6, 7, 8, 15, 16, 34]:
            return "nonmetal"
        elif elem.atomic_number in [2, 10, 18, 36, 54, 86]:
            return "noble_gas"
        elif elem.atomic_number in [3, 11, 19, 37, 55, 87]:
            return "alkali_metal"
        elif elem.atomic_number in [4, 12, 20, 38, 56, 88]:
            return "alkaline_earth"
        elif elem.atomic_number in [5, 14, 32, 33, 51, 52, 84]:
            return "metalloid"
        elif elem.atomic_number in [13, 30, 31, 48, 49, 50, 81, 82, 83]:
            return "post_transition_metal"
        elif elem.atomic_number in [9, 17, 35, 53, 85]:
            return "halogen"
        elif 57 <= elem.atomic_number <= 71:
            return "lanthanide"
        elif 89 <= elem.atomic_number <= 103:
            return "actinide"
        else:
            return "transition_metal"

    def get_periodic_position(self, atomic_number):
        periods = [
            (1, 1, 1), (2, 1, 18),
            (3, 2, 1), (4, 2, 2), (5, 2, 13), (6, 2, 14), (7, 2, 15), (8, 2, 16), (9, 2, 17), (10, 2, 18),
            (11, 3, 1), (12, 3, 2), (13, 3, 13), (14, 3, 14), (15, 3, 15), (16, 3, 16), (17, 3, 17), (18, 3, 18),
            (19, 4, 1), (20, 4, 2), (21, 4, 3), (22, 4, 4), (23, 4, 5), (24, 4, 6), (25, 4, 7), (26, 4, 8),
            (27, 4, 9), (28, 4, 10), (29, 4, 11), (30, 4, 12), (31, 4, 13), (32, 4, 14), (33, 4, 15), (34, 4, 16),
            (35, 4, 17), (36, 4, 18),
            (37, 5, 1), (38, 5, 2), (39, 5, 3), (40, 5, 4), (41, 5, 5), (42, 5, 6), (43, 5, 7), (44, 5, 8),
            (45, 5, 9), (46, 5, 10), (47, 5, 11), (48, 5, 12), (49, 5, 13), (50, 5, 14), (51, 5, 15), (52, 5, 16),
            (53, 5, 17), (54, 5, 18),
            (55, 6, 1), (56, 6, 2), (72, 6, 4), (73, 6, 5), (74, 6, 6), (75, 6, 7), (76, 6, 8), (77, 6, 9),
            (78, 6, 10), (79, 6, 11), (80, 6, 12), (81, 6, 13), (82, 6, 14), (83, 6, 15), (84, 6, 16), (85, 6, 17),
            (86, 6, 18),
            (87, 7, 1), (88, 7, 2), (104, 7, 4), (105, 7, 5), (106, 7, 6), (107, 7, 7), (108, 7, 8), (109, 7, 9),
            (110, 7, 10), (111, 7, 11), (112, 7, 12), (113, 7, 13), (114, 7, 14), (115, 7, 15), (116, 7, 16),
            (117, 7, 17),
            (118, 7, 18)
        ]
        for an, row, col in periods:
            if an == atomic_number:
                return row, col
        lanthanides = [(57 + i, 8, 3 + i) for i in range(15)]
        actinides = [(89 + i, 9, 3 + i) for i in range(15)]
        for an, row, col in lanthanides + actinides:
            if an == atomic_number:
                return row, col
        return 1, 1

    def get_element_data(self):
        elements = []
        if mendeleev_element:
            for i in range(1, 119):
                elem = mendeleev_element(i)
                symbol = elem.symbol
                group = self.get_element_group(elem)
                row, col = self.get_periodic_position(i)
                elements.append((symbol, row, col, group))
        else:
            fallback = [
                ("H", 1, 1, "nonmetal"), ("He", 1, 18, "noble_gas"),
                ("Li", 2, 1, "alkali_metal"), ("Be", 2, 2, "alkaline_earth"),
                ("B", 2, 13, "metalloid"), ("C", 2, 14, "nonmetal"),
                ("N", 2, 15, "nonmetal"), ("O", 2, 16, "nonmetal"),
                ("F", 2, 17, "halogen"), ("Ne", 2, 18, "noble_gas"),
                ("Na", 3, 1, "alkali_metal"), ("Mg", 3, 2, "alkaline_earth"),
                ("Al", 3, 13, "post_transition_metal"), ("Si", 3, 14, "metalloid"),
                ("P", 3, 15, "nonmetal"), ("S", 3, 16, "nonmetal"),
                ("Cl", 3, 17, "halogen"), ("Ar", 3, 18, "noble_gas"),
                ("K", 4, 1, "alkali_metal"), ("Ca", 4, 2, "alkaline_earth"),
                ("Sc", 4, 3, "transition_metal"), ("Ti", 4, 4, "transition_metal"),
                ("V", 4, 5, "transition_metal"), ("Cr", 4, 6, "transition_metal"),
                ("Mn", 4, 7, "transition_metal"), ("Fe", 4, 8, "transition_metal"),
                ("Co", 4, 9, "transition_metal"), ("Ni", 4, 10, "transition_metal"),
                ("Cu", 4, 11, "transition_metal"), ("Zn", 4, 12, "post_transition_metal"),
                ("Ga", 4, 13, "post_transition_metal"), ("Ge", 4, 14, "metalloid"),
                ("As", 4, 15, "metalloid"), ("Se", 4, 16, "nonmetal"),
                ("Br", 4, 17, "halogen"), ("Kr", 4, 18, "noble_gas"),
                ("Rb", 5, 1, "alkali_metal"), ("Sr", 5, 2, "alkaline_earth"),
                ("Y", 5, 3, "transition_metal"), ("Zr", 5, 4, "transition_metal"),
                ("Nb", 5, 5, "transition_metal"), ("Mo", 5, 6, "transition_metal"),
                ("Tc", 5, 7, "transition_metal"), ("Ru", 5, 8, "transition_metal"),
                ("Rh", 5, 9, "transition_metal"), ("Pd", 5, 10, "transition_metal"),
                ("Ag", 5, 11, "transition_metal"), ("Cd", 5, 12, "post_transition_metal"),
                ("In", 5, 13, "post_transition_metal"), ("Sn", 5, 14, "post_transition_metal"),
                ("Sb", 5, 15, "metalloid"), ("Te", 5, 16, "metalloid"),
                ("I", 5, 17, "halogen"), ("Xe", 5, 18, "noble_gas"),
                ("Cs", 6, 1, "alkali_metal"), ("Ba", 6, 2, "alkaline_earth"),
                ("La", 8, 3, "lanthanide"), ("Ce", 8, 4, "lanthanide"),
                ("Pr", 8, 5, "lanthanide"), ("Nd", 8, 6, "lanthanide"),
                ("Pm", 8, 7, "lanthanide"), ("Sm", 8, 8, "lanthanide"),
                ("Eu", 8, 9, "lanthanide"), ("Gd", 8, 10, "lanthanide"),
                ("Tb", 8, 11, "lanthanide"), ("Dy", 8, 12, "lanthanide"),
                ("Ho", 8, 13, "lanthanide"), ("Er", 8, 14, "lanthanide"),
                ("Tm", 8, 15, "lanthanide"), ("Yb", 8, 16, "lanthanide"),
                ("Lu", 8, 17, "lanthanide"), ("Hf", 6, 4, "transition_metal"),
                ("Ta", 6, 5, "transition_metal"), ("W", 6, 6, "transition_metal"),
                ("Re", 6, 7, "transition_metal"), ("Os", 6, 8, "transition_metal"),
                ("Ir", 6, 9, "transition_metal"), ("Pt", 6, 10, "transition_metal"),
                ("Au", 6, 11, "transition_metal"), ("Hg", 6, 12, "post_transition_metal"),
                ("Tl", 6, 13, "post_transition_metal"), ("Pb", 6, 14, "post_transition_metal"),
                ("Bi", 6, 15, "post_transition_metal"), ("Po", 6, 16, "metalloid"),
                ("At", 6, 17, "halogen"), ("Rn", 6, 18, "noble_gas"),
                ("Fr", 7, 1, "alkali_metal"), ("Ra", 7, 2, "alkaline_earth"),
                ("Ac", 9, 3, "actinide"), ("Th", 9, 4, "actinide"),
                ("Pa", 9, 5, "actinide"), ("U", 9, 6, "actinide"),
                ("Np", 9, 7, "actinide"), ("Pu", 9, 8, "actinide"),
                ("Am", 9, 9, "actinide"), ("Cm", 9, 10, "actinide"),
                ("Bk", 9, 11, "actinide"), ("Cf", 9, 12, "actinide"),
                ("Es", 9, 13, "actinide"), ("Fm", 9, 14, "actinide"),
                ("Md", 9, 15, "actinide"), ("No", 9, 16, "actinide"),
                ("Lr", 9, 17, "actinide")
            ]
            elements = fallback
        return elements

    def init_crewai(self):
        self.query_refiner = Agent(
            role="Query Parser",
            goal="Parse and refine chemistry-related queries",
            backstory="Expert in chemical terminology and query structuring."
        )
        self.data_fetcher = Agent(
            role="Data Validator",
            goal="Validate chemical data using external sources",
            backstory="Specialist in cross-referencing chemical databases."
        )
        self.analyzer = Agent(
            role="Data Synthesizer",
            goal="Synthesize and finalize query results",
            backstory="Proficient in chemical data analysis."
        )

    def init_openai(self):
        if OpenAI and get_model_from_database() is not None:
            self.openai_client = OpenAI(api_key=get_model_from_database().api_key,
                                        base_url=get_model_from_database().url)
        else:
            self.openai_client = None

    def setup_advanced_features(self):
        self.session_file = "session_data.json"
        self.batch_data = None

    def init_ui(self):
        main_layout = QHBoxLayout()
        self.setStyleSheet(self.get_stylesheet())
        splitter = QSplitter(Qt.Horizontal)
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_layout.setSpacing(15)
        left_layout.setContentsMargins(20, 20, 20, 20)
        title_label = QLabel("Chemistry Explorer")
        title_label.setFont(QFont("Inter", 24, QFont.Bold))
        title_label.setStyleSheet("color: #FFFFFF; margin-bottom: 10px;")
        left_layout.addWidget(title_label)
        query_layout = QHBoxLayout()
        self.query_input = QLineEdit()
        self.query_input.setPlaceholderText("Ask a chemistry question (e.g., 'What is the melting point of silicon?')")
        self.query_input.setFixedHeight(48)
        query_layout.addWidget(self.query_input)
        self.recent_queries_button = QPushButton("Recent")
        self.recent_queries_button.clicked.connect(self.show_recent_queries)
        self.recent_queries_button.setFixedSize(80, 48)
        query_layout.addWidget(self.recent_queries_button)
        left_layout.addLayout(query_layout)
        self.fetch_button = QPushButton("Get Answer")
        self.fetch_button.clicked.connect(self.handle_query)
        self.fetch_button.setFixedHeight(48)
        left_layout.addWidget(self.fetch_button)
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setFixedHeight(8)
        left_layout.addWidget(self.progress_bar)
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setStyleSheet("background: #181818; border-radius: 8px; padding: 15px;")
        left_layout.addWidget(QLabel("Result:"))
        left_layout.addWidget(self.result_text)
        self.figure, self.ax = plt.subplots()
        self.canvas = FigureCanvas(self.figure)
        self.canvas.setStyleSheet("background: #181818; border-radius: 8px;")
        left_layout.addWidget(self.canvas)
        export_layout = QHBoxLayout()
        self.export_pdf = QPushButton("Export PDF")
        self.export_pdf.clicked.connect(self.export_to_pdf)
        self.export_csv = QPushButton("Export CSV")
        self.export_csv.clicked.connect(self.export_to_csv)
        self.export_json = QPushButton("Export JSON")
        self.export_json.clicked.connect(self.export_to_json)
        self.share_button = QPushButton("Share QR")
        self.share_button.clicked.connect(self.share_result_qr)
        export_layout.addWidget(self.export_pdf)
        export_layout.addWidget(self.export_csv)
        export_layout.addWidget(self.export_json)
        export_layout.addWidget(self.share_button)
        left_layout.addLayout(export_layout)
        left_panel.setLayout(left_layout)
        splitter.addWidget(left_panel)
        right_panel = QWidget()
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(20, 20, 20, 20)
        size_control_group = QGroupBox("Panel Size Control")
        size_layout = QFormLayout()
        self.left_size_slider = QSlider(Qt.Horizontal)
        self.left_size_slider.setRange(400, 1200)
        self.left_size_slider.setValue(800)
        self.left_size_slider.valueChanged.connect(lambda: self.resize_panels('left'))
        self.right_size_slider = QSlider(Qt.Horizontal)
        self.right_size_slider.setRange(400, 1200)
        self.right_size_slider.setValue(800)
        self.right_size_slider.valueChanged.connect(lambda: self.resize_panels('right'))
        size_layout.addRow("Left Panel:", self.left_size_slider)
        size_layout.addRow("Right Panel:", self.right_size_slider)
        size_control_group.setLayout(size_layout)
        right_layout.addWidget(size_control_group)
        appearance_group = QGroupBox("Appearance")
        appearance_layout = QFormLayout()
        self.theme_combo = QComboBox()
        self.theme_combo.addItems(['Dark', 'Light'])
        self.theme_combo.currentTextChanged.connect(self.change_theme)
        self.font_size_spin = QSpinBox()
        self.font_size_spin.setRange(10, 20)
        self.font_size_spin.setValue(14)
        self.font_size_spin.valueChanged.connect(self.change_font_size)
        appearance_layout.addRow("Theme:", self.theme_combo)
        appearance_layout.addRow("Font Size:", self.font_size_spin)
        appearance_group.setLayout(appearance_layout)
        right_layout.addWidget(appearance_group)
        mode_layout = QHBoxLayout()
        self.edu_toggle = QCheckBox("Educational Mode")
        self.edu_toggle.stateChanged.connect(self.toggle_educational_mode)
        mode_layout.addWidget(self.edu_toggle)
        self.think_mode = QCheckBox("Think Mode")
        mode_layout.addWidget(self.think_mode)
        self.deepsearch_mode = QCheckBox("DeepSearch Mode")
        mode_layout.addWidget(self.deepsearch_mode)
        right_layout.addLayout(mode_layout)
        self.page_combo = QComboBox()
        self.page_combo.addItems(["Properties", "Reactions", "Simulation", "Database", "Thermodynamics",
                                  "Compare Elements", "Research Papers", "Advanced", "3D Visualization",
                                  "Drug Analysis", "Education Hub", "Batch Processing"])
        self.page_combo.currentTextChanged.connect(self.switch_page)
        right_layout.addWidget(self.page_combo)
        self.pages = QStackedWidget()
        self.properties_page = QWidget()
        self.reactions_page = QWidget()
        self.simulation_page = QWidget()
        self.database_page = QWidget()
        self.thermo_page = QWidget()
        self.compare_page = QWidget()
        self.papers_page = QWidget()
        self.advanced_page = QWidget()
        self.init_3d_visualization_page()
        self.init_drug_analysis_page()
        self.init_education_hub_page()
        self.init_batch_processing_page()
        self.pages.addWidget(self.properties_page)
        self.pages.addWidget(self.reactions_page)
        self.pages.addWidget(self.simulation_page)
        self.pages.addWidget(self.database_page)
        self.pages.addWidget(self.thermo_page)
        self.pages.addWidget(self.compare_page)
        self.pages.addWidget(self.papers_page)
        self.pages.addWidget(self.advanced_page)
        self.pages.addWidget(self.vis3d_page)
        self.pages.addWidget(self.drug_page)
        self.pages.addWidget(self.edu_hub_page)
        self.pages.addWidget(self.batch_page)
        right_layout.addWidget(self.pages)
        self.init_properties_page()
        self.init_reactions_page()
        self.init_simulation_page()
        self.init_database_page()
        self.init_thermo_page()
        self.init_compare_page()
        self.init_papers_page()
        self.init_advanced_page()
        self.init_semantic_search()
        self.init_local_collaboration()
        right_panel.setLayout(right_layout)
        splitter.addWidget(right_panel)
        splitter.setSizes([800, 800])
        main_layout.addWidget(splitter)
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

    def switch_page(self):
        page_name = self.page_combo.currentText()
        page_index = self.page_combo.currentIndex()
        self.pages.setCurrentIndex(page_index)

    def get_stylesheet(self):
        bg_color = "#121212" if self.theme == 'dark' else "#FFFFFF"
        text_color = "#FFFFFF" if self.theme == 'dark' else "#000000"
        input_bg = "#181818" if self.theme == 'dark' else "#F0F0F0"
        button_bg = "#0288D1" if self.theme == 'dark' else "#1976D2"
        return f"""
            QMainWindow {{ background-color: {bg_color}; }}
            QLabel {{ color: {text_color}; font-size: {self.font_size}px; }}
            QLineEdit {{ 
                background-color: {input_bg}; 
                color: {text_color}; 
                border: 1px solid #424242; 
                border-radius: 8px; 
                padding: 10px; 
                font-size: {self.font_size}px; 
            }}
            QPushButton {{ 
                background-color: {button_bg}; 
                color: #FFFFFF; 
                border-radius: 8px; 
                padding: 10px; 
                font-size: {self.font_size}px; 
                font-weight: 500; 
            }}
            QPushButton:hover {{ background-color: #03A9F4; }}
            QTextEdit {{ 
                background-color: {input_bg}; 
                color: {text_color}; 
                border-radius: 8px; 
                padding: 15px; 
                font-size: {self.font_size}px; 
            }}
            QProgressBar {{ 
                background-color: #424242; 
                border-radius: 4px; 
                text-align: center; 
                color: {text_color}; 
                font-size: {self.font_size - 2}px; 
            }}
            QProgressBar::chunk {{ background-color: #0288D1; border-radius: 4px; }}
            QComboBox, QSpinBox, QDoubleSpinBox {{ 
                background-color: {input_bg}; 
                color: {text_color}; 
                border: 1px solid #424242; 
                border-radius: 8px; 
                padding: 10px; 
                font-size: {self.font_size}px; 
            }}
            QTableWidget {{ 
                background-color: {input_bg}; 
                color: {text_color}; 
                border-radius: 8px; 
                font-size: {self.font_size}px; 
            }}
            QGroupBox {{ 
                color: {text_color}; 
                font-size: {self.font_size}px; 
                font-weight: bold; 
                border: 1px solid #424242; 
                border-radius: 8px; 
                margin-top: 10px; 
            }}
            QGroupBox::title {{ subcontrol-origin: margin; subcontrol-position: top left; padding: 0 3px; }}
            QCheckBox {{ color: {text_color}; font-size: {self.font_size}px; }}
            QSlider::groove:horizontal {{ 
                border: 1px solid #424242; 
                height: 8px; 
                background: {input_bg}; 
                border-radius: 4px; 
            }}
            QSlider::handle:horizontal {{ 
                background: {button_bg}; 
                border: 1px solid #424242; 
                width: 18px; 
                margin: -5px 0; 
                border-radius: 9px; 
            }}
            QTabWidget::pane {{ border: 1px solid #424242; border-radius: 8px; }}
            QTabBar::tab {{ 
                background: {input_bg}; 
                color: {text_color}; 
                padding: 10px; 
                border-top-left-radius: 8px; 
                border-top-right-radius: 8px; 
                font-size: {self.font_size}px; 
            }}
            QTabBar::tab:selected {{ background: {button_bg}; color: #FFFFFF; }}
        """

    def change_theme(self):
        self.theme = self.theme_combo.currentText().lower()
        self.setStyleSheet(self.get_stylesheet())

    def change_font_size(self):
        self.font_size = self.font_size_spin.value()
        self.setStyleSheet(self.get_stylesheet())

    def toggle_educational_mode(self):
        self.educational_mode = self.edu_toggle.isChecked()
        self.result_text.setText("Educational mode " + ("enabled." if self.educational_mode else "disabled."))

    def resize_panels(self, panel):
        splitter = self.findChild(QSplitter)
        sizes = splitter.sizes()
        new_size = self.__dict__[f"{panel}_size_slider"].value()
        if panel == 'left':
            sizes[0] = new_size
            sizes[1] = sum(sizes) - new_size
        else:
            sizes[1] = new_size
            sizes[0] = sum(sizes) - new_size
        splitter.setSizes(sizes)
        self.panel_sizes[panel] = new_size
        self.save_panel_sizes()

    def save_panel_sizes(self):
        with open("panel_sizes.json", "w") as f:
            json.dump(self.panel_sizes, f)

    def load_panel_sizes(self):
        try:
            with open("panel_sizes.json", "r") as f:
                self.panel_sizes = json.load(f)
            self.left_size_slider.setValue(self.panel_sizes.get('left', 800))
            self.right_size_slider.setValue(self.panel_sizes.get('right', 800))
            self.resize_panels('left')
        except:
            pass

    def agentic_parse_query(self, query):
        refine_task = Task(
            description=f"Parse the chemistry query '{query}' to identify element/compound, property, reaction, or comparison. Return JSON with 'element', 'property', 'is_compound', 'reaction', 'compare_elements', 'compare_property'.",
            agent=self.query_refiner,
            expected_output="Parsed query in JSON format."
        )
        fetch_task = Task(
            description=f"Validate parsed query components using chemical packages (chempy, pubchempy, mendeleev).",
            agent=self.data_fetcher,
            expected_output="Validated query components."
        )
        analyze_task = Task(
            description="Synthesize and refine parsed query components for accuracy.",
            agent=self.analyzer,
            expected_output="Final validated query components in JSON format."
        )
        crew = Crew(
            agents=[self.query_refiner, self.data_fetcher, self.analyzer],
            tasks=[refine_task, fetch_task, analyze_task],
            process=Process.sequential
        )
        try:
            result = crew.kickoff()
            return json.loads(result.raw)
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Query parsing failed: {str(e)}")
            return {"element": None, "property": None, "is_compound": False, "reaction": None, "compare_elements": None,
                    "compare_property": None}

    def select_best_package(self, property_name, is_compound=False):
        for package, props in self.package_properties.items():
            if property_name in props:
                if is_compound and package == "pubchempy":
                    return package
                elif not is_compound and package != "pubchempy":
                    return package
        return None

    def get_property(self, package, element_name, property_name):
        try:
            if package == "pubchempy" and pcp:
                compounds = pcp.get_compounds(element_name, 'name')
                if compounds:
                    return getattr(compounds[0], property_name, "Not available")
            elif package == "mendeleev" and element:
                elem = element(element_name)
                return getattr(elem, property_name, "Not available")
            return "Not available"
        except Exception as e:
            return f"Error: {str(e)}"

    def think_mode_process(self, query, property_name, package, is_compound=False):
        refine_task = Task(
            description=f"Refine the query '{query}' for fetching {property_name}. Determine if external sources (Arxiv, Wikipedia, DuckDuckGo) are needed.",
            agent=self.query_refiner,
            expected_output="Refined query string and list of recommended sources."
        )

        fetch_task = Task(
            description=f"Fetch {property_name} for {query} using {package} and recommended external sources.",
            agent=self.data_fetcher,
            expected_output=f"Raw data for {property_name} of {query} from multiple sources."
        )

        analyze_task = Task(
            description=f"Analyze and refine the fetched {property_name} data for {query}. Cross-reference sources and improve accuracy iteratively.",
            agent=self.analyzer,
            expected_output=f"Final validated and refined {property_name} for {query}."
        )

        crew = Crew(
            agents=[self.query_refiner, self.data_fetcher, self.analyzer],
            tasks=[refine_task, fetch_task, analyze_task],
            process=Process.sequential
        )

        return crew.kickoff()

    def deepsearch_mode_process(self, query, property_name, package, is_compound=False):
        cursor = self.cache_db.cursor()
        cursor.execute("SELECT result FROM cache WHERE query = ? AND mode = 'deepsearch'",
                       (f"{query}:{property_name}",))
        cached = cursor.fetchone()
        if cached:
            return cached[0]

        refine_task = Task(
            description=f"Generate up to 4 refined versions of the query '{query}' for fetching {property_name}. Decide which external sources (Arxiv, Wikipedia, DuckDuckGo) are relevant.",
            agent=self.query_refiner,
            expected_output="List of refined queries and recommended sources."
        )

        fetch_task = Task(
            description=f"Fetch {property_name} for each refined query using {package} and selected external sources.",
            agent=self.data_fetcher,
            expected_output=f"Consolidated data for {property_name} from multiple sources."
        )

        analyze_task = Task(
            description=f"Synthesize and validate {property_name} data for {query}. Perform iterative refinement and cross-reference sources.",
            agent=self.analyzer,
            expected_output=f"Final validated {property_name} for {query}."
        )

        crew = Crew(
            agents=[self.query_refiner, self.data_fetcher, self.analyzer],
            tasks=[refine_task, fetch_task, analyze_task],
            process=Process.sequential
        )

        result = crew.kickoff()
        cursor.execute("INSERT INTO cache (query, result, mode) VALUES (?, ?, 'deepsearch')",
                       (f"{query}:{property_name}", str(result)))
        self.cache_db.commit()
        return result

    def process_reaction(self, reaction, mode):
        try:
            if balance_stoichiometry:
                reactants, products = reaction.split("->")
                reac = {r.strip(): 1 for r in reactants.split("+")}
                prod = {p.strip(): 1 for p in products.split("+")}
                balanced = balance_stoichiometry(reac, prod)
                result = f"Balanced: {balanced[0]} -> {balanced[1]}"
                if mode == "think":
                    result += "\nThink Mode: Verified stoichiometry."
                elif mode == "deepsearch":
                    result += "\nDeepSearch Mode: Cross-referenced with chemical principles."
                return result
            return "ChemPy not available"
        except Exception as e:
            return f"Error: {str(e)}"

    def process_comparison(self, elements, property_name, mode):
        try:
            elements = [e.strip() for e in elements.split(",")]
            results = []
            for elem in elements:
                package = self.select_best_package(property_name)
                if package:
                    value = self.get_property(package, elem, property_name)
                    results.append((elem, value))
                else:
                    results.append((elem, "Not available"))
            result = "\n".join(f"{elem}: {value}" for elem, value in results)
            if mode == "think":
                result += "\nThink Mode: Compared properties systematically."
            elif mode == "deepsearch":
                result += "\nDeepSearch Mode: Validated with external sources."
            return result
        except Exception as e:
            return f"Error: {str(e)}"

    def update_external_search(self, query, result, mode):
        if self.wikipedia:
            page = self.wikipedia.page(query)
            if page.exists():
                result.append(f"Wikipedia Summary: {page.summary[:500]}...")
        if mode == "deepsearch":
            result.append("DeepSearch Mode: Additional web validation performed.")
        elif mode == "think":
            result.append("Think Mode: Query analyzed thoroughly.")
        self.update_result(None, query, result, mode)

    def handle_query(self):
        self.progress_bar.setVisible(True)
        self.progress_bar.setValue(0)
        query = self.query_input.text().strip()
        if not query:
            self.result_text.setText("Error: Please enter a query.")
            self.progress_bar.setVisible(False)
            return
        if query and query not in self.recent_queries:
            self.recent_queries.insert(0, query)
            if len(self.recent_queries) > self.max_recent_queries:
                self.recent_queries.pop()
        cursor = self.cache_db.cursor()
        mode = "deepsearch" if self.deepsearch_mode.isChecked() else "think" if self.think_mode.isChecked() else "normal"
        cursor.execute("SELECT result FROM cache WHERE query = ? AND mode = ?", (query, mode))
        cached = cursor.fetchone()
        if cached:
            self.result_text.setText(cached[0])
            self.progress_bar.setVisible(False)
            self.plot_query_result(query, cached[0])
            self.search_papers_for_query(query, mode)
            return
        parsed = self.agentic_parse_query(query)
        element = parsed.get("element")
        property_name = parsed.get("property")
        is_compound = parsed.get("is_compound", False)
        reaction = parsed.get("reaction")
        compare_elements = parsed.get("compare_elements")
        compare_property = parsed.get("compare_property")
        result = []
        if reaction:
            thread = QueryThread(self.process_reaction, reaction, mode)
            thread.result.connect(lambda res: self.update_result(res, query, result, mode))
            thread.start()
        elif compare_elements and compare_property:
            thread = QueryThread(self.process_comparison, compare_elements, compare_property, mode)
            thread.result.connect(lambda res: self.update_result(res, query, result, mode))
            thread.start()
        elif element and property_name:
            package = self.select_best_package(property_name, is_compound)
            if package:
                self.progress_bar.setValue(50)
                if mode == "think":
                    thread = QueryThread(self.think_mode_process, element, property_name, package, is_compound)
                elif mode == "deepsearch":
                    thread = QueryThread(self.deepsearch_mode_process, element, property_name, package, is_compound)
                else:
                    thread = QueryThread(self.get_property, package, element, property_name)
                thread.result.connect(lambda res: self.update_result(res, query, result, mode))
                thread.start()
            else:
                result.append("No suitable package found for this property.")
                self.update_result(None, query, result, mode)
        else:
            self.update_external_search(query, result, mode)

    def update_result(self, thread_result, query, result, mode):
        if thread_result:
            result.append(thread_result)
        result_text = "\n".join(str(r) for r in result) or "No results found."
        self.result_text.setText(result_text)
        cursor = self.cache_db.cursor()
        cursor.execute("INSERT OR REPLACE INTO cache (query, result, mode) VALUES (?, ?, ?)",
                       (query, result_text, mode))
        self.cache_db.commit()
        self.progress_bar.setValue(100)
        self.progress_bar.setVisible(False)
        self.plot_query_result(query, result_text)
        self.search_papers_for_query(query, mode)

    def plot_query_result(self, query, result):
        self.ax.clear()
        if "compare" in query.lower():
            try:
                elements = [line.split(":")[0].strip() for line in result.split("\n") if ":" in line]
                values = [float(line.split(":")[1].strip()) for line in result.split("\n") if
                          ":" in line and line.split(":")[1].strip().replace(".", "").isdigit()]
                if values:
                    self.ax.bar(elements, values)
                    self.ax.set_xlabel("Elements")
                    self.ax.set_ylabel("Value")
                    self.ax.set_title("Element Comparison")
                    self.canvas.draw()
            except:
                pass

    def search_papers_for_query(self, query, mode):
        self.paper_query.setText(query)
        self.search_papers()

    def init_properties_page(self):
        prop_layout = QVBoxLayout()
        periodic_layout = QGridLayout()
        colors = {
            "nonmetal": "#FF5252", "noble_gas": "#40C4FF", "alkali_metal": "#FFD740",
            "alkaline_earth": "#4CAF50", "metalloid": "#AB47BC", "post_transition_metal": "#B0BEC5",
            "halogen": "#FFCA28", "lanthanide": "#F06292", "actinide": "#FF5722",
            "transition_metal": "#90A4AE"
        }
        for symbol, row, col, group in self.element_data:
            btn = QPushButton(symbol)
            btn.setFixedSize(60, 60)
            btn.setStyleSheet(
                f"background-color: {colors.get(group, '#B0BEC5')}; border-radius: 8px; font-size: 14px; font-weight: 500; color: #FFFFFF;")
            btn.clicked.connect(lambda _, s=symbol: self.query_input.setText(s))
            btn.setToolTip(f"{symbol} ({group.replace('_', ' ').title()})")
            periodic_layout.addWidget(btn, row, col)
        prop_layout.addWidget(QLabel("Periodic Table:"))
        prop_layout.addLayout(periodic_layout)
        self.properties_page.setLayout(prop_layout)

    def init_reactions_page(self):
        react_layout = QVBoxLayout()
        periodic_layout = QGridLayout()
        colors = {
            "nonmetal": "#FF5252", "noble_gas": "#40C4FF", "alkali_metal": "#FFD740",
            "alkaline_earth": "#4CAF50", "metalloid": "#AB47BC", "post_transition_metal": "#B0BEC5",
            "halogen": "#FFCA28", "lanthanide": "#F06292", "actinide": "#FF5722",
            "transition_metal": "#90A4AE"
        }
        for symbol, row, col, group in self.element_data:
            btn = QPushButton(symbol)
            btn.setFixedSize(60, 60)
            btn.setStyleSheet(
                f"background-color: {colors.get(group, '#B0BEC5')}; border-radius: 8px; font-size: 14px; font-weight: 500; color: #FFFFFF;")
            btn.clicked.connect(lambda _, s=symbol: self.add_to_reaction(s))
            btn.setToolTip(f"{symbol} ({group.replace('_', ' ').title()})")
            periodic_layout.addWidget(btn, row, col)
        react_layout.addWidget(QLabel("Select Elements for Reaction:"))
        react_layout.addLayout(periodic_layout)
        self.reactant_label = QLabel("Reactants: None")
        self.product_label = QLabel("Products: None")
        react_layout.addWidget(self.reactant_label)
        react_layout.addWidget(self.product_label)
        self.side_toggle = QComboBox()
        self.side_toggle.addItems(["Reactants", "Products"])
        react_layout.addWidget(QLabel("Select Side:"))
        react_layout.addWidget(self.side_toggle)
        self.clear_reaction_button = QPushButton("Clear Reaction")
        self.clear_reaction_button.clicked.connect(self.clear_reaction)
        self.clear_reaction_button.setFixedHeight(48)
        react_layout.addWidget(self.clear_reaction_button)
        self.balance_button = QPushButton("Balance Reaction")
        self.balance_button.clicked.connect(self.balance_reaction)
        self.balance_button.setFixedHeight(48)
        react_layout.addWidget(self.balance_button)
        self.save_reaction_button = QPushButton("Save Reaction")
        self.save_reaction_button.clicked.connect(self.save_reaction)
        self.save_reaction_button.setFixedHeight(48)
        react_layout.addWidget(self.save_reaction_button)
        self.reaction_result = QTextEdit()
        self.reaction_result.setReadOnly(True)
        self.reaction_result.setStyleSheet("background: #181818; border-radius: 8px; padding: 15px;")
        react_layout.addWidget(QLabel("Balanced Reaction:"))
        react_layout.addWidget(self.reaction_result)
        self.mol_image = QLabel("Molecular structure not available")
        self.mol_image.setStyleSheet("background: #181818; border-radius: 8px; padding: 15px;")
        react_layout.addWidget(self.mol_image)
        self.reactions_page.setLayout(react_layout)

    def add_to_reaction(self, symbol):
        side = self.side_toggle.currentText()
        if side == "Reactants":
            self.selected_reactants.append(symbol)
        else:
            self.selected_products.append(symbol)
        self.update_reaction_labels()

    def update_reaction_labels(self):
        self.reactant_label.setText(
            f"Reactants: {' + '.join(self.selected_reactants) if self.selected_reactants else 'None'}")
        self.product_label.setText(
            f"Products: {' + '.join(self.selected_products) if self.selected_products else 'None'}")

    def clear_reaction(self):
        self.selected_reactants = []
        self.selected_products = []
        self.reaction_result.clear()
        self.update_reaction_labels()

    def balance_reaction(self):
        if not self.selected_reactants or not self.selected_products:
            self.reaction_result.setText("Error: Please select reactants and products.")
            return
        reaction = f"{' + '.join(self.selected_reactants)} -> {' + '.join(self.selected_products)}"
        result = self.balance_reaction_sync(reaction)
        self.reaction_result.setText(result)

    def balance_reaction_sync(self, reaction):
        try:
            if balance_stoichiometry:
                reactants, products = reaction.split("->")
                reac = {r.strip(): 1 for r in reactants.split("+")}
                prod = {p.strip(): 1 for p in products.split("+")}
                balanced = balance_stoichiometry(reac, prod)
                return f"Balanced: {balanced[0]} -> {balanced[1]}"
            return "ChemPy not available"
        except Exception as e:
            return f"Error: {str(e)}"

    def save_reaction(self):
        reaction = self.reaction_input.text().strip()
        result = self.reaction_result.toPlainText()
        if reaction and result and not result.startswith("Error"):
            cursor = self.cache_db.cursor()
            cursor.execute("INSERT OR REPLACE INTO reactions (reaction, result) VALUES (?, ?)", (reaction, result))
            self.cache_db.commit()
            QMessageBox.information(self, "Success", "Reaction saved.")
        else:
            QMessageBox.critical(self, "Error", "Cannot save invalid or empty reaction.")

    def init_simulation_page(self):
        sim_layout = QVBoxLayout()
        self.sim_reaction_input = QLineEdit()
        self.sim_reaction_input.setPlaceholderText("Enter reaction (e.g., 'H2 + O2 -> H2O')")
        self.sim_reaction_input.setFixedHeight(48)
        sim_layout.addWidget(QLabel("Reaction to Simulate:"))
        sim_layout.addWidget(self.sim_reaction_input)
        self.temp_input = QSpinBox()
        self.temp_input.setRange(100, 5000)
        self.temp_input.setValue(298)
        self.temp_input.setFixedHeight(48)
        sim_layout.addWidget(QLabel("Temperature (K):"))
        sim_layout.addWidget(self.temp_input)
        self.conc_input = QDoubleSpinBox()
        self.conc_input.setRange(0.01, 50.0)
        self.conc_input.setValue(1.0)
        self.conc_input.setDecimals(3)
        self.conc_input.setFixedHeight(48)
        sim_layout.addWidget(QLabel("Initial Concentration (mol/L):"))
        sim_layout.addWidget(self.conc_input)
        self.pressure_input = QDoubleSpinBox()
        self.pressure_input.setRange(0.1, 500.0)
        self.pressure_input.setValue(1.0)
        self.pressure_input.setDecimals(3)
        self.pressure_input.setFixedHeight(48)
        sim_layout.addWidget(QLabel("Pressure (atm):"))
        sim_layout.addWidget(self.pressure_input)
        self.simulate_button = QPushButton("Simulate Reaction")
        self.simulate_button.clicked.connect(self.simulate_reaction)
        self.simulate_button.setFixedHeight(48)
        sim_layout.addWidget(self.simulate_button)
        self.sim_result = QTextEdit()
        self.sim_result.setReadOnly(True)
        self.sim_result.setStyleSheet("background: #181818; border-radius: 8px; padding: 15px;")
        sim_layout.addWidget(QLabel("Simulation Result:"))
        sim_layout.addWidget(self.sim_result)
        self.simulation_page.setLayout(sim_layout)

    def simulate_reaction(self):
        reaction = self.sim_reaction_input.text().strip()
        temp = self.temp_input.value()
        conc = self.conc_input.value()
        pressure = self.pressure_input.value()
        if not reaction:
            self.sim_result.setText("Error: Please enter a reaction.")
            return
        try:
            result = f"Simulated {reaction} at T={temp}K, C={conc}mol/L, P={pressure}atm\n(Placeholder: Advanced simulation not implemented)"
            self.sim_result.setText(result)
        except Exception as e:
            self.sim_result.setText(f"Error: {str(e)}")

    def init_database_page(self):
        db_layout = QVBoxLayout()
        self.db_query = QLineEdit()
        self.db_query.setPlaceholderText("Search saved reactions (e.g., 'HCl')")
        self.db_query.setFixedHeight(48)
        db_layout.addWidget(QLabel("Search Reactions:"))
        db_layout.addWidget(self.db_query)
        self.db_search_button = QPushButton("Search Database")
        self.db_search_button.clicked.connect(self.search_database)
        self.db_search_button.setFixedHeight(48)
        db_layout.addWidget(self.db_search_button)
        self.db_result = QTextEdit()
        self.db_result.setReadOnly(True)
        self.db_result.setStyleSheet("background: #181818; border-radius: 8px; padding: 15px;")
        db_layout.addWidget(QLabel("Saved Reactions:"))
        db_layout.addWidget(self.db_result)
        self.database_page.setLayout(db_layout)

    def search_database(self):
        query = self.db_query.text().strip()
        cursor = self.cache_db.cursor()
        cursor.execute("SELECT reaction, result FROM reactions WHERE reaction LIKE ?", (f"%{query}%",))
        results = cursor.fetchall()
        result_text = "<br>".join(
            f"<b>Reaction</b>: {r[0]}<br><b>Result</b>: {r[1]}" for r in results) or "No reactions found."
        self.db_result.setText(result_text)

    def init_thermo_page(self):
        thermo_layout = QVBoxLayout()
        self.thermo_input = QLineEdit()
        self.thermo_input.setPlaceholderText("Enter compound for thermodynamic data (e.g., 'H2O')")
        self.thermo_input.setFixedHeight(48)
        thermo_layout.addWidget(QLabel("Compound:"))
        thermo_layout.addWidget(self.thermo_input)
        self.thermo_button = QPushButton("Fetch Thermodynamic Data")
        self.thermo_button.clicked.connect(self.fetch_thermo_data)
        self.thermo_button.setFixedHeight(48)
        thermo_layout.addWidget(self.thermo_button)
        self.thermo_result = QTextEdit()
        self.thermo_result.setReadOnly(True)
        self.thermo_result.setStyleSheet("background: #181818; border-radius: 8px; padding: 15px;")
        thermo_layout.addWidget(QLabel("Thermodynamic Data:"))
        thermo_layout.addWidget(self.thermo_result)
        self.thermo_page.setLayout(thermo_layout)

    def fetch_thermo_data(self):
        compound = self.thermo_input.text().strip()
        if not compound:
            self.thermo_result.setText("Error: Please enter a compound.")
            return
        try:
            result = f"Thermodynamic data for {compound} (Placeholder: Requires advanced database)"
            self.thermo_result.setText(result)
        except Exception as e:
            self.thermo_result.setText(f"Error: {str(e)}")

    def init_compare_page(self):
        compare_layout = QVBoxLayout()
        self.compare_elements = QLineEdit()
        self.compare_elements.setPlaceholderText("Enter elements to compare (e.g., 'H,Li,C')")
        self.compare_elements.setFixedHeight(48)
        compare_layout.addWidget(QLabel("Elements (comma-separated):"))
        compare_layout.addWidget(self.compare_elements)
        self.compare_property = QComboBox()
        self.compare_property.addItems(
            ["melting_point", "boiling_point", "atomic_weight", "electronegativity", "density", "ionization_energy",
             "atomic_radius"])
        self.compare_property.setFixedHeight(48)
        compare_layout.addWidget(QLabel("Property to Compare:"))
        compare_layout.addWidget(self.compare_property)
        self.compare_button = QPushButton("Compare Elements")
        self.compare_button.clicked.connect(self.compare_elements_data)
        self.compare_button.setFixedHeight(48)
        compare_layout.addWidget(self.compare_button)
        self.compare_table = QTableWidget()
        self.compare_table.setColumnCount(2)
        self.compare_table.setHorizontalHeaderLabels(["Element", "Value"])
        self.compare_table.setStyleSheet("background: #181818; border-radius: 8px;")
        compare_layout.addWidget(QLabel("Comparison Results:"))
        compare_layout.addWidget(self.compare_table)
        self.compare_save_button = QPushButton("Save Comparison")
        self.compare_save_button.clicked.connect(self.save_comparison)
        self.compare_save_button.setFixedHeight(48)
        compare_layout.addWidget(self.compare_save_button)
        self.compare_page.setLayout(compare_layout)

    def compare_elements_data(self):
        elements = self.compare_elements.text().strip()
        property_name = self.compare_property.currentText()
        if not elements:
            self.compare_table.setRowCount(0)
            return
        mode = "deepsearch" if self.deepsearch_mode.isChecked() else "think" if self.think_mode.isChecked() else "normal"
        thread = QueryThread(self.process_comparison, elements, property_name, mode)
        thread.result.connect(self.update_compare_table)
        thread.start()

    def update_compare_table(self, result):
        if result.startswith("Error"):
            self.compare_table.setRowCount(0)
            QMessageBox.critical(self, "Error", result)
            return
        results = [line.split(": ") for line in result.split("\n") if ": " in line and "Mode" not in line]
        self.compare_table.setRowCount(len(results))
        for i, (elem, value) in enumerate(results):
            self.compare_table.setItem(i, 0, QTableWidgetItem(elem))
            self.compare_table.setItem(i, 1, QTableWidgetItem(value))
        self.compare_table.resizeColumnsToContents()

    def save_comparison(self):
        if self.compare_table.rowCount() == 0:
            QMessageBox.critical(self, "Error", "No comparison data to save.")
            return
        data = [{"Element": self.compare_table.item(i, 0).text(), "Value": self.compare_table.item(i, 1).text()} for i
                in range(self.compare_table.rowCount())]
        cursor = self.cache_db.cursor()
        cursor.execute(
            "CREATE TABLE IF NOT EXISTS comparisons (id INTEGER PRIMARY KEY AUTOINCREMENT, data TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
        cursor.execute("INSERT INTO comparisons (data) VALUES (?)", (json.dumps(data),))
        self.cache_db.commit()
        QMessageBox.information(self, "Success", "Comparison saved.")

    def init_papers_page(self):
        papers_layout = QVBoxLayout()
        self.paper_query = QLineEdit()
        self.paper_query.setPlaceholderText("Search for research papers (e.g., 'Silicon properties')")
        self.paper_query.setFixedHeight(48)
        papers_layout.addWidget(QLabel("Search Papers:"))
        papers_layout.addWidget(self.paper_query)
        self.paper_search_button = QPushButton("Search Papers")
        self.paper_search_button.clicked.connect(self.search_papers)
        self.paper_search_button.setFixedHeight(48)
        papers_layout.addWidget(self.paper_search_button)
        self.paper_result = QTextEdit()
        self.paper_result.setReadOnly(True)
        self.paper_result.setStyleSheet("background: #181818; border-radius: 8px; padding: 15px;")
        papers_layout.addWidget(QLabel("Research Papers:"))
        papers_layout.addWidget(self.paper_result)
        self.papers_page.setLayout(papers_layout)

    def search_papers(self):
        query = self.paper_query.text().strip()
        if not query:
            self.paper_result.setText("Error: Please enter a query.")
            return
        try:
            result = f"Search results for '{query}' (Placeholder: Requires ArXiv or PubMed API)"
            self.paper_result.setText(result)
        except Exception as e:
            self.paper_result.setText(f"Error: {str(e)}")

    def init_3d_visualization_page(self):
        self.vis3d_page = QWidget()
        vis3d_layout = QVBoxLayout()
        self.vis3d_input = QLineEdit()
        self.vis3d_input.setPlaceholderText("Enter compound SMILES or name (e.g., CC(=O)O)")
        vis3d_layout.addWidget(QLabel("Compound:"))
        vis3d_layout.addWidget(self.vis3d_input)
        self.vis3d_button = QPushButton("Visualize 3D Structure")
        self.vis3d_button.clicked.connect(self.render_3d_structure)
        vis3d_layout.addWidget(self.vis3d_button)
        self.vis3d_controls = QHBoxLayout()
        self.vis3d_rotate = QPushButton("Rotate")
        self.vis3d_rotate.clicked.connect(lambda: self.adjust_3d_view('rotate'))
        self.vis3d_zoom = QDoubleSpinBox()
        self.vis3d_zoom.setRange(0.5, 2.0)
        self.vis3d_zoom.setValue(1.0)
        self.vis3d_zoom.valueChanged.connect(lambda: self.adjust_3d_view('zoom'))
        self.vis3d_annotate = QLineEdit()
        self.vis3d_annotate.setPlaceholderText("Add annotation")
        self.vis3d_annotate.returnPressed.connect(lambda: self.adjust_3d_view('annotate'))
        self.vis3d_controls.addWidget(self.vis3d_rotate)
        self.vis3d_controls.addWidget(QLabel("Zoom:"))
        self.vis3d_controls.addWidget(self.vis3d_zoom)
        self.vis3d_controls.addWidget(self.vis3d_annotate)
        vis3d_layout.addLayout(self.vis3d_controls)
        self.vis3d_export = QPushButton("Export 3D Model")
        self.vis3d_export.clicked.connect(self.export_3d_model)
        vis3d_layout.addWidget(self.vis3d_export)
        self.vis3d_page.setLayout(vis3d_layout)

    def render_3d_structure(self):
        if not cmd:
            QMessageBox.critical(self, "Error", "PyMOL not installed.")
            return
        compound = self.vis3d_input.text().strip()
        try:
            cmd.delete('all')
            mol = Chem.MolFromSmiles(compound) if Chem else None
            if mol:
                cmd.read_molstr(Chem.MolToMolBlock(mol), 'mol')
                cmd.zoom()
                cmd.show('sticks')
            else:
                compounds = pcp.get_compounds(compound, 'name')
                if compounds:
                    cmd.load(compounds[0].sdf, 'mol')
                    cmd.zoom()
                    cmd.show('sticks')
                else:
                    raise ValueError("Compound not found.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Visualization failed: {str(e)}")

    def adjust_3d_view(self, action):
        try:
            if action == 'rotate':
                cmd.rotate('y', 45)
            elif action == 'zoom':
                cmd.zoom(factor=self.vis3d_zoom.value())
            elif action == 'annotate':
                cmd.label('all', f"'{self.vis3d_annotate.text()}'")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"View adjustment failed: {str(e)}")

    def export_3d_model(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export 3D Model", "", "PNG Files (*.png);;PDB Files (*.pdb)")
        if file_name:
            try:
                cmd.png(file_name) if file_name.endswith('.png') else cmd.save(file_name)
                QMessageBox.information(self, "Success", "3D model exported.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def init_drug_analysis_page(self):
        self.drug_page = QWidget()
        drug_layout = QVBoxLayout()
        self.drug_input = QLineEdit()
        self.drug_input.setPlaceholderText("Enter SMILES or compound name (e.g., CC(=O)O)")
        drug_layout.addWidget(QLabel("Compound:"))
        drug_layout.addWidget(self.drug_input)
        self.drug_button = QPushButton("Analyze Drug Properties")
        self.drug_button.clicked.connect(self.analyze_drug_properties)
        drug_layout.addWidget(self.drug_button)
        self.drug_table = QTableWidget()
        self.drug_table.setColumnCount(2)
        self.drug_table.setHorizontalHeaderLabels(["Property", "Value"])
        drug_layout.addWidget(QLabel("Drug Properties:"))
        drug_layout.addWidget(self.drug_table)
        self.drug_export = QPushButton("Export Results")
        self.drug_export.clicked.connect(self.export_drug_results)
        drug_layout.addWidget(self.drug_export)
        self.drug_page.setLayout(drug_layout)

    def analyze_drug_properties(self):
        compound = self.drug_input.text().strip()
        try:
            mol = Chem.MolFromSmiles(compound) if Chem else None
            if not mol:
                compounds = pcp.get_compounds(compound, 'name')
                if compounds:
                    mol = Chem.MolFromSmiles(compounds[0].canonical_smiles)
                else:
                    raise ValueError("Invalid compound.")
            properties = {
                "Molecular Weight": Descriptors.MolWt(mol),
                "LogP": Descriptors.MolLogP(mol),
                "H-Bond Donors": Lipinski.NumHDonors(mol),
                "H-Bond Acceptors": Lipinski.NumHAcceptors(mol),
                "Lipinski Rule": "Pass" if Lipinski.NumHDonors(mol) <= 5 and Lipinski.NumHAcceptors(
                    mol) <= 10 and Descriptors.MolWt(mol) <= 500 and Descriptors.MolLogP(mol) <= 5 else "Fail",
                "ADMET (Placeholder)": "Requires advanced model"
            }
            self.drug_table.setRowCount(len(properties))
            for i, (prop, value) in enumerate(properties.items()):
                self.drug_table.setItem(i, 0, QTableWidgetItem(prop))
                self.drug_table.setItem(i, 1, QTableWidgetItem(str(value)))
            self.drug_table.resizeColumnsToContents()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Analysis failed: {str(e)}")

    def export_drug_results(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Drug Results", "",
                                                   "CSV Files (*.csv);;JSON Files (*.json)")
        if file_name:
            try:
                data = {self.drug_table.item(i, 0).text(): self.drug_table.item(i, 1).text() for i in
                        range(self.drug_table.rowCount())}
                if file_name.endswith('.csv'):
                    pd.DataFrame([data]).to_csv(file_name, index=False)
                else:
                    with open(file_name, 'w') as f:
                        json.dump(data, f, indent=2)
                QMessageBox.information(self, "Success", "Drug results exported.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def init_education_hub_page(self):
        self.edu_hub_page = QWidget()
        edu_layout = QVBoxLayout()
        self.tutorial_combo = QComboBox()
        self.tutorial_combo.addItems(["Reaction Balancing", "Thermodynamics", "Molecular Orbital Theory"])
        edu_layout.addWidget(QLabel("Select Tutorial:"))
        edu_layout.addWidget(self.tutorial_combo)
        self.tutorial_display = QTextBrowser()
        edu_layout.addWidget(QLabel("Tutorial Content:"))
        edu_layout.addWidget(self.tutorial_display)
        self.quiz_button = QPushButton("Start Quiz")
        self.quiz_button.clicked.connect(self.start_quiz)
        edu_layout.addWidget(self.quiz_button)
        self.quiz_answer = QLineEdit()
        self.quiz_answer.setPlaceholderText("Enter your answer")
        self.quiz_answer.returnPressed.connect(self.submit_quiz_answer)
        edu_layout.addWidget(QLabel("Quiz Answer:"))
        edu_layout.addWidget(self.quiz_answer)
        self.quiz_feedback = QTextEdit()
        self.quiz_feedback.setReadOnly(True)
        edu_layout.addWidget(QLabel("Quiz Feedback:"))
        edu_layout.addWidget(self.quiz_feedback)
        self.tutorial_combo.currentTextChanged.connect(self.load_tutorial)
        self.edu_hub_page.setLayout(edu_layout)

    def init_batch_processing_page(self):
        self.batch_page = QWidget()
        batch_layout = QVBoxLayout()
        self.batch_file_input = QPushButton("Upload CSV/JSON File")
        self.batch_file_input.clicked.connect(self.upload_batch_file)
        batch_layout.addWidget(QLabel("Input File:"))
        batch_layout.addWidget(self.batch_file_input)
        self.batch_task_combo = QComboBox()
        self.batch_task_combo.addItems(["Calculate Properties", "Balance Reactions"])
        batch_layout.addWidget(QLabel("Task:"))
        batch_layout.addWidget(self.batch_task_combo)
        self.batch_property = QComboBox()
        self.batch_property.addItems(["molecular_weight", "melting_point", "boiling_point"])
        batch_layout.addWidget(QLabel("Property (for Calculate Properties):"))
        batch_layout.addWidget(self.batch_property)
        self.batch_process_button = QPushButton("Process Batch")
        self.batch_process_button.clicked.connect(self.process_batch)
        batch_layout.addWidget(self.batch_process_button)
        self.batch_result_table = QTableWidget()
        self.batch_result_table.setColumnCount(2)
        self.batch_result_table.setHorizontalHeaderLabels(["Input", "Result"])
        batch_layout.addWidget(QLabel("Batch Results:"))
        batch_layout.addWidget(self.batch_result_table)
        self.batch_export = QPushButton("Export Batch Results")
        self.batch_export.clicked.connect(self.export_batch_results)
        batch_layout.addWidget(self.batch_export)
        self.batch_page.setLayout(batch_layout)

    def load_tutorial(self):
        topic = self.tutorial_combo.currentText()
        if not self.openai_client:
            self.tutorial_display.setText("Error: OpenAI client not available.")
            return
        try:
            response = self.openai_client.chat.completions.create(
                model=get_model_from_database().name,
                messages=[
                    {"role": "system",
                     "content": "You are a chemistry tutor. Provide a concise tutorial (100-200 words) on the given chemistry topic."},
                    {"role": "user", "content": f"Provide a tutorial on {topic}."}
                ]
            )
            tutorial_content = response.choices[0].message.content
            self.tutorial_display.setText(tutorial_content)
            cursor = self.cache_db.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS tutorials (topic TEXT PRIMARY KEY, content TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            cursor.execute("INSERT OR REPLACE INTO tutorials (topic, content) VALUES (?, ?)", (topic, tutorial_content))
            self.cache_db.commit()
        except Exception as e:
            self.tutorial_display.setText(f"Error: {str(e)}")

    def start_quiz(self):
        topic = self.tutorial_combo.currentText()
        if not self.openai_client:
            self.quiz_answer.setPlaceholderText("Error: OpenAI client not available.")
            return
        try:
            response = self.openai_client.chat.completions.create(
                model=get_model_from_database().name,
                messages=[
                    {"role": "system",
                     "content": "You are a chemistry quiz generator. Provide one quiz question with a short answer for the given topic."},
                    {"role": "user", "content": f"Generate a quiz question for {topic}."}
                ]
            )
            quiz_content = response.choices[0].message.content
            self.quiz_answer.setPlaceholderText(quiz_content)
            self.quiz_feedback.clear()
            cursor = self.cache_db.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS quizzes (topic TEXT, question TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            cursor.execute("INSERT INTO quizzes (topic, question) VALUES (?, ?)", (topic, quiz_content))
            self.cache_db.commit()
        except Exception as e:
            self.quiz_answer.setPlaceholderText(f"Error: {str(e)}")

    def submit_quiz_answer(self):
        answer = self.quiz_answer.text().strip()
        topic = self.tutorial_combo.currentText()
        if not answer or not self.openai_client:
            self.quiz_feedback.setText("Error: Please provide an answer or OpenAI client not available.")
            return
        try:
            response = self.openai_client.chat.completions.create(
                model=get_model_from_database().name,
                messages=[
                    {"role": "system",
                     "content": "You are a chemistry quiz evaluator. Check the user's answer for correctness and provide feedback."},
                    {"role": "user",
                     "content": f"Topic: {topic}\nQuestion: {self.quiz_answer.placeholderText()}\nUser Answer: {answer}"}
                ]
            )
            feedback = response.choices[0].message.content
            self.quiz_feedback.setText(feedback)
            cursor = self.cache_db.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS quiz_results (topic TEXT, question TEXT, answer TEXT, feedback TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            cursor.execute("INSERT INTO quiz_results (topic, question, answer, feedback) VALUES (?, ?, ?, ?)",
                           (topic, self.quiz_answer.placeholderText(), answer, feedback))
            self.cache_db.commit()
            self.quiz_answer.clear()
        except Exception as e:
            self.quiz_feedback.setText(f"Error: {str(e)}")

    def init_advanced_page(self):
        advanced_layout = QVBoxLayout()
        self.session_save_button = QPushButton("Save Session")
        self.session_save_button.clicked.connect(self.save_session)
        self.session_save_button.setFixedHeight(48)
        advanced_layout.addWidget(self.session_save_button)
        self.session_load_button = QPushButton("Load Session")
        self.session_load_button.clicked.connect(self.load_session)
        self.session_load_button.setFixedHeight(48)
        advanced_layout.addWidget(self.session_load_button)
        self.copy_result_button = QPushButton("Copy Result to Clipboard")
        self.copy_result_button.clicked.connect(self.copy_result)
        self.copy_result_button.setFixedHeight(48)
        advanced_layout.addWidget(self.copy_result_button)
        self.clear_cache_button = QPushButton("Clear Cache")
        self.clear_cache_button.clicked.connect(self.clear_cache)
        self.clear_cache_button.setFixedHeight(48)
        advanced_layout.addWidget(self.clear_cache_button)
        advanced_layout.addStretch()
        self.advanced_page.setLayout(advanced_layout)

    def upload_batch_file(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Upload File", "", "CSV Files (*.csv);;JSON Files (*.json)")
        if file_name:
            try:
                self.batch_data = pd.read_csv(file_name) if file_name.endswith('.csv') else pd.read_json(file_name)
                QMessageBox.information(self, "Success", "File uploaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"File upload failed: {str(e)}")

    def process_batch(self):
        if not hasattr(self, 'batch_data'):
            QMessageBox.critical(self, "Error", "No file uploaded.")
            return
        task = self.batch_task_combo.currentText()
        try:
            results = []
            if task == "Calculate Properties":
                prop = self.batch_property.currentText()
                package = self.select_best_package(prop, is_compound=True)
                for _, row in self.batch_data.iterrows():
                    compound = row['compound']
                    value = self.get_property(package, compound, prop) if package else "Not available"
                    results.append((compound, str(value)))
            else:
                for _, row in self.batch_data.iterrows():
                    reaction = row['reaction']
                    result = self.balance_reaction_sync(reaction)
                    results.append((reaction, result))
            self.batch_result_table.setRowCount(len(results))
            for i, (inp, res) in enumerate(results):
                self.batch_result_table.setItem(i, 0, QTableWidgetItem(inp))
                self.batch_result_table.setItem(i, 1, QTableWidgetItem(res))
            self.batch_result_table.resizeColumnsToContents()
            cursor = self.cache_db.cursor()
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS batch_results (id INTEGER PRIMARY KEY AUTOINCREMENT, input TEXT, result TEXT, task TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            for inp, res in results:
                cursor.execute("INSERT INTO batch_results (input, result, task) VALUES (?, ?, ?)", (inp, res, task))
            self.cache_db.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Batch processing failed: {str(e)}")

    def export_batch_results(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export Batch Results", "",
                                                   "CSV Files (*.csv);;JSON Files (*.json);;PDF Files (*.pdf)")
        if file_name:
            try:
                data = [{"Input": self.batch_result_table.item(i, 0).text(),
                         "Result": self.batch_result_table.item(i, 1).text()} for i in
                        range(self.batch_result_table.rowCount())]
                if file_name.endswith('.csv'):
                    pd.DataFrame(data).to_csv(file_name, index=False)
                elif file_name.endswith('.json'):
                    with open(file_name, 'w') as f:
                        json.dump(data, f, indent=2)
                else:
                    c = pdf_canvas.Canvas(file_name, pagesize=letter)
                    c.setFont("Helvetica", 12)
                    y = 750
                    for item in data:
                        c.drawString(50, y, f"{item['Input']}: {item['Result']}")
                        y -= 20
                    c.save()
                QMessageBox.information(self, "Success", "Batch results exported.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Export failed: {str(e)}")

    def init_semantic_search(self):
        semantic_layout = QHBoxLayout()
        self.semantic_search_input = QLineEdit()
        self.semantic_search_input.setPlaceholderText("Enter complex query (e.g., 'reactions with nitrogen compounds')")
        self.semantic_search_button = QPushButton("Semantic Search")
        self.semantic_search_button.clicked.connect(self.perform_semantic_search)
        semantic_layout.addWidget(QLabel("Semantic Search:"))
        semantic_layout.addWidget(self.semantic_search_input)
        semantic_layout.addWidget(self.semantic_search_button)
        self.database_page.layout().insertLayout(0, semantic_layout)

    def perform_semantic_search(self):
        query = self.semantic_search_input.text().strip()
        if not query:
            QMessageBox.critical(self, "Error", "Please enter a query.")
            return
        try:
            from sentence_transformers import SentenceTransformer
            model = SentenceTransformer('all-MiniLM-L6-v2')
            cursor = self.cache_db.cursor()
            cursor.execute("SELECT reaction, result FROM reactions")
            reactions = cursor.fetchall()
            reaction_texts = [f"{r[0]} -> {r[1]}" for r in reactions]
            query_embedding = model.encode(query)
            reaction_embeddings = model.encode(reaction_texts)
            similarities = np.dot(reaction_embeddings, query_embedding) / (
                        np.linalg.norm(reaction_embeddings, axis=1) * np.linalg.norm(query_embedding))
            top_indices = np.argsort(similarities)[-5:][::-1]
            results = [reactions[i] for i in top_indices]
            result_text = "<br>".join(
                f"<b>Reaction</b>: {r[0]}<br><b>Result</b>: {r[1]}" for r in results) or "No matching reactions found."
            self.db_result.setText(result_text)
            cursor.execute(
                "CREATE TABLE IF NOT EXISTS semantic_cache (query TEXT PRIMARY KEY, result TEXT, timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)")
            cursor.execute("INSERT OR REPLACE INTO semantic_cache (query, result) VALUES (?, ?)", (query, result_text))
            self.cache_db.commit()
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Semantic search failed: {str(e)}")

    def init_local_collaboration(self):
        collab_layout = QVBoxLayout()
        self.local_save_button = QPushButton("Save Session Locally")
        self.local_save_button.clicked.connect(self.save_session_locally)
        self.local_load_button = QPushButton("Load Local Session")
        self.local_load_button.clicked.connect(self.load_session_locally)
        self.local_share_button = QPushButton("Generate Shareable Session File")
        self.local_share_button.clicked.connect(self.generate_shareable_session)
        collab_layout.addWidget(self.local_save_button)
        self.local_load_button.setFixedHeight(48)
        collab_layout.addWidget(self.local_load_button)
        self.local_share_button.setFixedHeight(48)
        collab_layout.addWidget(self.local_share_button)
        self.advanced_page.layout().insertLayout(0, collab_layout)

    def save_session_locally(self):
        try:
            session_data = self.collect_session_data()
            with open(self.session_file, 'w') as f:
                json.dump(session_data, f, indent=2)
            QMessageBox.information(self, "Success", "Session saved locally.")
        except Exception as e:
            QMessageBox.critical(self, "Error", f"Local save failed: {str(e)}")

    def load_session_locally(self):
        file_name, _ = QFileDialog.getOpenFileName(self, "Load Session", "", "JSON Files (*.json)")
        if file_name:
            try:
                with open(file_name, 'r') as f:
                    session_data = json.load(f)
                self.load_session_from_data(session_data)
                QMessageBox.information(self, "Success", "Session loaded successfully.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Load failed: {str(e)}")

    def generate_shareable_session(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Save Shareable Session", "", "JSON Files (*.json)")
        if file_name:
            try:
                session_data = self.collect_session_data()
                with open(file_name, 'w') as f:
                    json.dump(session_data, f, indent=2)
                pyperclip.copy(file_name)
                QMessageBox.information(self, "Success", f"Session saved to {file_name} and path copied to clipboard.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"Shareable session generation failed: {str(e)}")

    def add_auto_save_toggle_to_advanced_tab(self):
        self.auto_save_toggle = QCheckBox("Auto-Save Session")
        self.auto_save_toggle.stateChanged.connect(self.toggle_auto_save)
        self.advanced_page.layout().insertWidget(0, self.auto_save_toggle)

    def collect_session_data(self):
        return {
            'query': self.query_input.text(),
            'result': self.result_text.toPlainText(),
            'reactants': self.selected_reactants,
            'products': self.selected_products,
            'reaction_result': self.reaction_result.toPlainText(),
            'sim_reaction': self.sim_reaction_input.text(),
            'sim_result': self.sim_result.toPlainText(),
            'thermo_input': self.thermo_input.text(),
            'thermo_result': self.thermo_result.toPlainText(),
            'compare_elements': self.compare_elements.text(),
            'compare_property': self.compare_property.currentText(),
            'paper_query': self.paper_query.text(),
            'paper_result': self.paper_result.toPlainText(),
            'vis3d_input': self.vis3d_input.text() if hasattr(self, 'vis3d_input') else '',
            'drug_input': self.drug_input.text() if hasattr(self, 'drug_input') else '',
            'tutorial_topic': self.tutorial_combo.currentText() if hasattr(self, 'tutorial_combo') else '',
            'batch_data': self.batch_data.to_dict() if hasattr(self, 'batch_data') else {},
            'panel_sizes': self.panel_sizes,
            'theme': self.theme,
            'font_size': self.font_size
        }

    def load_session_from_data(self, session_data):
        self.query_input.setText(session_data.get('query', ''))
        self.result_text.setText(session_data.get('result', ''))
        self.selected_reactants = session_data.get('reactants', [])
        self.selected_products = session_data.get('products', [])
        self.update_reaction_labels()
        self.reaction_result.setText(session_data.get('reaction_result', ''))
        self.sim_reaction_input.setText(session_data.get('sim_reaction', ''))
        self.sim_result.setText(session_data.get('sim_result', ''))
        self.thermo_input.setText(session_data.get('thermo_input', ''))
        self.thermo_result.setText(session_data.get('thermo_result', ''))
        self.compare_elements.setText(session_data.get('compare_elements', ''))
        self.compare_property.setCurrentText(session_data.get('compare_property', 'melting_point'))
        self.paper_query.setText(session_data.get('paper_query', ''))
        self.paper_result.setText(session_data.get('paper_result', ''))
        if hasattr(self, 'vis3d_input'):
            self.vis3d_input.setText(session_data.get('vis3d_input', ''))
        if hasattr(self, 'drug_input'):
            self.drug_input.setText(session_data.get('drug_input', ''))
        if hasattr(self, 'tutorial_combo'):
            self.tutorial_combo.setCurrentText(session_data.get('tutorial_topic', ''))
        if hasattr(self, 'batch_data'):
            self.batch_data = pd.DataFrame(session_data.get('batch_data', {}))
        self.panel_sizes = session_data.get('panel_sizes', {'left': 800, 'right': 800})
        self.left_size_slider.setValue(self.panel_sizes.get('left', 800))
        self.right_size_slider.setValue(self.panel_sizes.get('right', 800))
        self.theme = session_data.get('theme', 'dark')
        self.theme_combo.setCurrentText(self.theme.capitalize())
        self.font_size = session_data.get('font_size', 14)
        self.font_size_spin.setValue(self.font_size)
        self.setStyleSheet(self.get_stylesheet())

    def toggle_auto_save(self):
        if self.auto_save_toggle.isChecked():
            self.save_session_locally()

    def save_session(self):
        self.save_session_locally()

    def load_session(self):
        self.load_session_locally()

    def copy_result(self):
        pyperclip.copy(self.result_text.toPlainText())
        QMessageBox.information(self, "Success", "Result copied to clipboard.")

    def clear_cache(self):
        cursor = self.cache_db.cursor()
        cursor.execute("DELETE FROM cache")
        cursor.execute("DELETE FROM reactions")
        cursor.execute("DELETE FROM comparisons")
        cursor.execute("DELETE FROM tutorials")
        cursor.execute("DELETE FROM quizzes")
        cursor.execute("DELETE FROM quiz_results")
        cursor.execute("DELETE FROM batch_results")
        cursor.execute("DELETE FROM semantic_cache")
        self.cache_db.commit()
        QMessageBox.information(self, "Success", "Cache cleared.")

    def export_to_pdf(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export to PDF", "", "PDF Files (*.pdf)")
        if file_name:
            try:
                c = pdf_canvas.Canvas(file_name, pagesize=letter)
                c.setFont("Helvetica", 12)
                text = self.result_text.toPlainText().split("\n")
                y = 750
                for line in text:
                    c.drawString(50, y, line[:100])
                    y -= 20
                    if y < 50:
                        c.showPage()
                        y = 750
                c.save()
                QMessageBox.information(self, "Success", "Exported to PDF.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"PDF export failed: {str(e)}")

    def export_to_csv(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export to CSV", "", "CSV Files (*.csv)")
        if file_name:
            try:
                data = {"Query": self.query_input.text(), "Result": self.result_text.toPlainText()}
                pd.DataFrame([data]).to_csv(file_name, index=False)
                QMessageBox.information(self, "Success", "Exported to CSV.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"CSV export failed: {str(e)}")

    def export_to_json(self):
        file_name, _ = QFileDialog.getSaveFileName(self, "Export to JSON", "", "JSON Files (*.json)")
        if file_name:
            try:
                data = {"Query": self.query_input.text(), "Result": self.result_text.toPlainText()}
                with open(file_name, 'w') as f:
                    json.dump(data, f, indent=2)
                QMessageBox.information(self, "Success", "Exported to JSON.")
            except Exception as e:
                QMessageBox.critical(self, "Error", f"JSON export failed: {str(e)}")

    def share_result_qr(self):
        QMessageBox.information(self, "Info", "QR sharing not implemented in this version.")

    def show_recent_queries(self):
        if not self.recent_queries:
            QMessageBox.information(self, "Recent Queries", "No recent queries.")
            return
        query, ok = QInputDialog.getItem(self, "Recent Queries", "Select a query:", self.recent_queries, 0, False)
        if ok and query:
            self.query_input.setText(query)
            self.handle_query()

    def init_chat_interface(self):
        self.chat_display = QTextBrowser()
        self.chat_display.setStyleSheet("background-color: #111; color: white; padding: 8px; border-radius: 4px;")
        self.chat_input = QLineEdit()
        self.chat_input.setPlaceholderText("Ask the assistant...")
        self.chat_input.returnPressed.connect(self.handle_chat_input)
        self.chat_send_button = QPushButton("Send")
        self.chat_send_button.clicked.connect(self.handle_chat_input)

        chat_layout = QVBoxLayout()
        chat_layout.addWidget(QLabel("Assistant Chat Interface:"))
        chat_layout.addWidget(self.chat_display)
        chat_input_layout = QHBoxLayout()
        chat_input_layout.addWidget(self.chat_input)
        chat_input_layout.addWidget(self.chat_send_button)
        chat_layout.addLayout(chat_input_layout)

        self.advanced_page.layout().addLayout(chat_layout)

    def handle_chat_input(self):
        user_input = self.chat_input.text().strip()
        if user_input:
            self.chat_display.append(f"<b>You:</b> {user_input}")
            self.chat_input.clear()
            thread = QueryThread(self.generate_chat_response, user_input)
            thread.result.connect(lambda response: self.chat_display.append(f"<b>Assistant:</b> {response}"))
            thread.start()

    def generate_chat_response(self, text):
        response = self.openai_client.chat.completions.create(
            model=get_model_from_database().name,
            messages=[
                {"role": "system", "content": "You are a helpful chemistry assistant."},
                {"role": "user", "content": text}
            ]
        )
        return response.choices[0].message.content.strip()


if __name__ == "__main__":
    app = QApplication([])
    window = CheExplorer()
    window.show()
    app.exec_()