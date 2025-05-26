class ThemeManager:
    def __init__(self, theme: str = "default"):
        self.theme = theme
        self.themes = {
            "default": {
                "primary": "#3f51b5",
                "secondary": "#f50057",
                "success": "#4caf50",
                "error": "#d32f2f",
                "text": "#333",
                "background": "#f5f5f5"
            },
            "dark": {
                "primary": "#90caf9",
                "secondary": "#f48fb1",
                "success": "#81c784",
                "error": "#ef5350",
                "text": "#fff",
                "background": "#212121"
            }
        }

    def get_color(self, color: str) -> str:
        return self.themes.get(self.theme, self.themes["default"]).get(color, "#000")

    def get_class_styles(self, class_name: str) -> str:
        return ""

    def get_id_styles(self, id: str) -> str:
        return ""

    def get_styles(self, component: str) -> str:
        if component == "paper":
            return f"""
                QWidget {{
                    background-color: {self.get_color('background')};
                    padding: 10px;
                }}
            """
        elif component == "title":
            return f"""
                QLabel {{
                    color: {self.get_color('text')};
                    font-size: 18px;
                    font-weight: bold;
                }}
            """
        return ""