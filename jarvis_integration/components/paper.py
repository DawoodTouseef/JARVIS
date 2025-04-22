from PyQt5.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QLabel
from typing import List, Dict, Callable, Optional
from jarvis_integration.components.button import JarvisButton
from jarvis_integration.components.button_group import JarvisButtonGroup
from jarvis_integration.components.text_field import JarvisTextField
from jarvis_integration.components.select_field import JarvisSelectField
from jarvis_integration.components.card import JarvisCard
from jarvis_integration.layout.box import JarvisBoxLayout
from jarvis_integration.themes.theme_manager import ThemeManager


class JarvisPaper(QWidget):
    def __init__(self, theme: str = "default",
                 sx: Optional[Dict[str, str]] = None, className: Optional[str] = None, id: Optional[str] = None):
        super().__init__()
        self.theme_manager = ThemeManager(theme)
        self.main_layout = QVBoxLayout()
        self.setLayout(self.main_layout)
        self.className = className
        self.id = id
        self.sx = sx or {}

        if id:
            self.setObjectName(id)

        # Page management
        self.pages: Dict[str, JarvisBoxLayout] = {}
        self.page_widgets: Dict[str, QWidget] = {}
        self.page_components: Dict[str, List[QWidget]] = {}
        self.page_actions: Dict[str, List[Callable]] = {}
        self.current_page: Optional[str] = None
        self.page_stack = None

        self.apply_theme()

    def apply_theme(self):
        """Apply the current theme to the paper and all pages."""
        theme_styles = self.theme_manager.get_styles("paper")
        style = theme_styles
        if self.className:
            class_style = self.theme_manager.get_class_styles(self.className)
            style += f"\nJarvisPaper {{ {class_style} }}"
        if self.id:
            id_style = self.theme_manager.get_id_styles(self.id)
            style += f"\nJarvisPaper#{self.id} {{ {id_style} }}"
        if self.sx:
            sx_style = "; ".join(f"{key}: {value}" for key, value in self.sx.items())
            style += f"\nJarvisPaper {{ {sx_style}; }}"
        self.setStyleSheet(style)

        # Reapply styles to all page widgets
        for page_id, page_widget in self.page_widgets.items():
            background_color = self.theme_manager.get_color("background")
            page_style = f"""
                background-color: {background_color};
                border-radius: 8px;
                padding: 10px;
            """
            if self.className:
                page_style += f"\nQWidget {{ {self.theme_manager.get_class_styles(self.className)} }}"
            if self.id:
                page_style += f"\nQWidget#{self.id} {{ {self.theme_manager.get_id_styles(self.id)} }}"
            page_widget.setStyleSheet(page_style)
            # Update title labels if they exist
            for component in self.page_components.get(page_id, []):
                if isinstance(component, QLabel) and component.text() in [page_id, "Sign Up"]:
                    component.setStyleSheet(self.theme_manager.get_styles("title"))

    def set_theme(self, theme: str):
        """Dynamically switch the theme and reapply styles."""
        self.theme_manager = ThemeManager(theme)
        self.apply_theme()

    def add_page(self, page_layout: Optional[JarvisBoxLayout] = None, page_id: str = None,
                 title: str = "", background_color: str = None) -> None:
        """Add a new page with a JarvisBoxLayout or create an empty page."""
        if not page_id:
            page_id = f"page_{len(self.pages) + 1}"

        if page_id in self.pages:
            raise ValueError(f"Page with ID {page_id} already exists")

        # Create a new layout if none provided
        if page_layout is None:
            page_layout = JarvisBoxLayout()
            page_widget = QWidget()
            page_widget.setLayout(page_layout.layout)
        else:
            page_widget = page_layout

        # Apply styling
        background_color = background_color or self.theme_manager.get_color("background")
        page_style = f"""
            background-color: {background_color};
            border-radius: 8px;
            padding: 10px;
        """
        if self.className:
            page_style += f"\nQWidget {{ {self.theme_manager.get_class_styles(self.className)} }}"
        if self.id:
            page_style += f"\nQWidget#{self.id} {{ {self.theme_manager.get_id_styles(self.id)} }}"
        page_widget.setStyleSheet(page_style)

        # Add title if provided
        if title:
            title_label = QLabel(title)
            title_label.setStyleSheet(self.theme_manager.get_styles("title"))
            page_layout.add_widget(title_label)

        # Store page information
        self.pages[page_id] = page_layout
        self.page_widgets[page_id] = page_widget
        self.page_components[page_id] = []
        self.page_actions[page_id] = []

        # If this is the first page, display it directly
        if not self.page_stack:
            self.main_layout.addWidget(page_widget)
            self.current_page = page_id
        else:
            self.page_stack.addWidget(page_widget)
            if not self.current_page:
                self.current_page = page_id
                self.page_stack.setCurrentWidget(page_widget)

    def enable_page_switching(self, nav_labels: Dict[str, str] = None):
        """Enable page switching with a navigation bar."""
        if not self.page_stack:
            self.page_stack = QStackedWidget()

            # Move existing page to stack
            if self.current_page:
                current_widget = self.main_layout.itemAt(0).widget()
                self.main_layout.removeWidget(current_widget)
                self.page_stack.addWidget(current_widget)
                self.main_layout.addWidget(self.page_stack)

            # Add navigation bar
            self.nav_bar = QWidget()
            self.nav_layout = QHBoxLayout()
            self.nav_bar.setLayout(self.nav_layout)
            self.main_layout.insertWidget(0, self.nav_bar)

            # Add navigation buttons for existing pages
            for page_id in self.pages:
                label = nav_labels.get(page_id, page_id) if nav_labels else page_id
                nav_button = JarvisButton(
                    text=label,
                    on_click=lambda: self.switch_page(page_id),
                    variant="outlined",
                    color="secondary",
                    size="small"
                )
                self.nav_layout.addWidget(nav_button)

    def add_component(self, page_id: str, component: QWidget) -> None:
        """Add a component to a specific page."""
        if page_id not in self.pages:
            raise ValueError(f"Page {page_id} does not exist")

        self.pages[page_id].add_widget(component)
        self.page_components[page_id].append(component)

    def add_card(self, page_id: str, title: str, content: str = "") -> JarvisCard:
        """Add a card component to a page."""
        card = JarvisCard(title=title, content=content)
        self.add_component(page_id, card)
        return card

    def add_button(self, page_id: str, text: str, on_click: Callable = None, **kwargs) -> JarvisButton:
        """Add a button to a page."""
        button = JarvisButton(text=text, on_click=on_click, **kwargs)
        self.add_component(page_id, button)
        return button

    def add_button_group(self, page_id: str, labels: List[str], on_change: Callable = None,
                         **kwargs) -> JarvisButtonGroup:
        """Add a button group to a page."""
        button_group = JarvisButtonGroup(labels=labels, on_change=on_change, **kwargs)
        self.add_component(page_id, button_group)
        return button_group

    def add_text_field(self, page_id: str, label: str = "", placeholder: str = "", **kwargs) -> JarvisTextField:
        """Add a text field to a page."""
        text_field = JarvisTextField(label=label, placeholder=placeholder, **kwargs)
        self.add_component(page_id, text_field)
        return text_field

    def add_select_field(self, page_id: str, label: str = "", options: List[str] = None) -> JarvisSelectField:
        """Add a select field to a page."""
        select_field = JarvisSelectField(label=label, options=options)
        self.add_component(page_id, select_field)
        return select_field

    def switch_page(self, page_id: str) -> None:
        """Switch to a specific page and execute its actions."""
        if not self.page_stack:
            raise ValueError("Page switching is not enabled. Call enable_page_switching() first.")

        if page_id not in self.pages:
            raise ValueError(f"Page {page_id} does not exist")

        self.current_page = page_id
        self.page_stack.setCurrentWidget(self.page_widgets[page_id])

        # Execute page actions
        for action in self.page_actions.get(page_id, []):
            action()

    def add_page_action(self, page_id: str, action: Callable) -> None:
        """Add a custom action to be executed when switching to a page."""
        if page_id not in self.pages:
            raise ValueError(f"Page {page_id} does not exist")
        self.page_actions[page_id].append(action)

    def customize_page(self, page_id: str, background_color: str = None, padding: int = None,
                      border_radius: int = None, **kwargs) -> None:
        """Customize page appearance."""
        if page_id not in self.pages:
            raise ValueError(f"Page {page_id} does not exist")

        page_widget = self.page_widgets[page_id]
        style = page_widget.styleSheet()
        new_styles = []

        if background_color:
            new_styles.append(f"background-color: {background_color}")
        if padding is not None:
            new_styles.append(f"padding: {padding}px")
        if border_radius is not None:
            new_styles.append(f"border-radius: {border_radius}px")

        if new_styles:
            style = "; ".join(new_styles) + ";"
            page_widget.setStyleSheet(style)

    def link_pages(self, from_page_id: str, to_page_id: str, button_text: str = "Next",
                   condition: Callable = None, **kwargs) -> JarvisButton:
        """Create a button that links two pages with an optional condition."""
        def navigate():
            if condition is None or condition():
                self.switch_page(to_page_id)

        button = self.add_button(
            from_page_id,
            text=button_text,
            on_click=navigate,
            **kwargs
        )
        return button