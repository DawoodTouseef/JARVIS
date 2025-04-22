from PyQt5.QtWidgets import QApplication
import sys
from jarvis_integration.window import JarvisWindow

def validate_file(path):
    if not path:
        return "Please select a file"
    valid_extensions = ('.txt', '.pdf', '.jpg', '.png')
    if not path.lower().endswith(valid_extensions):
        return "Only .txt, .pdf, .jpg, or .png files are allowed"
    return True

def show_dialog():
    dialog = (JarvisWindow()
              .dialog(title="User Details", width=400, height=250, modal=True)
              .set_style({"background-color": "#f5f5f5", "padding": "10px"})
              .add_layout("vertical", spacing=10)
              .add_text("Enter Additional Info", font_size=16, style={"color": "#333", "font-weight": "bold"}, align="center")
              .add_file_field(label="Document", placeholder="Select a document", select_type="file", file_filter="Documents (*.txt *.pdf *.jpg *.png)", id="document", full_width=True, color="primary", validate_func=validate_file)
              .add_layout("horizontal", spacing=10)
              .add_button(text="Save", on_click=lambda: print(f"Document: {dialog.widgets['document'].text()}"), style={"background-color": "#4caf50", "color": "white", "padding": "8px"}, color="success")
              .add_button(text="Cancel", on_click=lambda: dialog.window.reject(), style={"background-color": "#f44336", "color": "white", "padding": "8px"}, color="error")
              .end_layout()
              .end_layout())
    dialog.show()

def main():
    app = QApplication(sys.argv)
    window = (JarvisWindow()
              .main_window(title="JARVIS App", width=600, height=600)
              .set_style({"background-color": "#f5f5f5", "padding": "15px"})
              .add_layout("vertical", spacing=10)
              .add_text("Welcome to JARVIS", font_size=18, style={"color": "#333", "font-weight": "bold"}, align="center")
              .add_text_field(label="Username", placeholder="Enter username", id="username", full_width=True, color="primary", default_value="user123", draggable=True)
              .add_text_field(label="Email", placeholder="Enter email", type="email", icon="✉️", full_width=True, color="primary", id="email", draggable=True)
              .add_text_field(label="Password", placeholder="Enter password", type="password", icon="🔒", full_width=True, color="error", id="password", draggable=True)
              .add_file_field(label="Profile Picture", placeholder="Select an image", select_type="file", file_filter="Images (*.jpg *.png)", id="picture", full_width=True, color="secondary", draggable=True, validate_func=validate_file)
              .add_file_field(label="Project Folder", placeholder="Select a folder", select_type="folder", id="folder", full_width=True, color="success", draggable=True)
              .add_select(label="Role", options=["User", "Admin", "Developer"], default_value="User", id="role", style={"border": "1px solid #3f51b5"}, draggable=True)
              .add_button(text="Show Details", on_click=show_dialog, style={"background-color": "#4caf50", "color": "white", "padding": "10px"}, id="submit")
              .end_layout())
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()