import freetype
import numpy as np
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import  QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *
import random

class FontRenderer:
    def __init__(self, font_path="E:\\jarvis\\Client\\JARVIS2\\fonts\\Monomakh\\Monomakh-Regular.ttf", font_size=18):
        """Initialize FreeType font rendering."""
        self.face = freetype.Face(font_path)
        self.face.set_char_size(font_size * 64)
        self.text_texture = None

    def create_texture_from_text(self, text):
        """Creates a texture from rendered FreeType text."""
        max_height = 0
        total_width = 0

        # Calculate the total width and max height for text rendering
        for char in text:
            self.face.load_char(char)
            max_height = max(max_height, self.face.glyph.bitmap.rows)
            total_width += self.face.glyph.bitmap.width + 2

        if max_height == 0 or total_width == 0:
            return 1, 1  # Avoid division by zero in OpenGL texture generation

        # Create blank image
        image = np.zeros((max_height, total_width), dtype=np.uint8)

        x_offset = 0
        for char in text:
            self.face.load_char(char)
            bitmap = self.face.glyph.bitmap
            w, h = bitmap.width, bitmap.rows

            if h > 0 and w > 0:
                buffer = np.array(bitmap.buffer, dtype=np.uint8).reshape(h, w)
                image[:h, x_offset:x_offset + w] = buffer
            x_offset += w + 2

        # Generate OpenGL Texture
        if self.text_texture is None:
            self.text_texture = glGenTextures(1)

        glBindTexture(GL_TEXTURE_2D, self.text_texture)
        glTexImage2D(GL_TEXTURE_2D, 0, GL_ALPHA, total_width, max_height, 0, GL_ALPHA, GL_UNSIGNED_BYTE, image)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_LINEAR)
        glTexParameterf(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)

        return total_width, max_height

    def render_text(self, text, x, y, opacity=1.0):
        """Render text using the generated texture."""
        width, height = self.create_texture_from_text(text)

        glEnable(GL_TEXTURE_2D)
        glBindTexture(GL_TEXTURE_2D, self.text_texture)
        glColor4f(0.0, 0.0, 0.0, opacity)  # **Very Dark Black Text**

        glBegin(GL_QUADS)
        glTexCoord2f(0, 0); glVertex2f(x, y)
        glTexCoord2f(1, 0); glVertex2f(x + width / 800, y)
        glTexCoord2f(1, 1); glVertex2f(x + width / 800, y + height / 800)
        glTexCoord2f(0, 1); glVertex2f(x, y + height / 800)
        glEnd()

        glDisable(GL_TEXTURE_2D)



class AssistantOpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(650, 800)

        self.base_color = QColor(100, 150, 255)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)

        self.light_mode = True

        self.animation_running = False
        self.smoke_particles = []
        self.angle = 0
        self.dragging = False
        self.offset = QPoint()

        # **Text Animation Variables**
        self.font_renderer = FontRenderer("E:\\jarvis\\Client\\JARVIS2\\fonts\\Monomakh\\Monomakh-Regular.ttf", 18)  # **Font size set to 18px**
        self.text_opacity = 0.0
        self.fade_in = True
        self.text_timer = QTimer(self)
        self.text_timer.timeout.connect(self.update_text_opacity)
        self.text_timer.start(50)

    def initializeGL(self):
        """Initialize OpenGL settings."""
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)
        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 0.0, 1.0, 0.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.0, 1.0, 1.0, 1.0])

    def resizeGL(self, w, h):
        """Resize OpenGL viewport."""
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def paintGL(self):
        """Render OpenGL scene."""
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0.0, 0.0, 2.5, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)

        # Transparent Background
        glClearColor(0.0, 0.0, 0.0, 0.0)

        self.draw_3d_sphere()
        self.draw_smoke_effect()
        self.font_renderer.render_text("Hello, I am JARVIS", -0.3, -0.8, self.text_opacity)  # Positioned below the sphere

    def draw_3d_sphere(self):
        """Draw the rotating 3D sphere."""
        glPushMatrix()
        glRotatef(self.angle, 0, 1, 0)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [self.base_color.redF(), self.base_color.greenF(), self.base_color.blueF(), 1.0])
        quadric = gluNewQuadric()
        gluSphere(quadric, 0.5, 50, 50)
        gluDeleteQuadric(quadric)
        glPopMatrix()

    def draw_smoke_effect(self):
        """Draw animated smoke particles."""
        glPushMatrix()
        for particle in self.smoke_particles:
            x, y, z, size, alpha = particle
            glColor4f(self.base_color.redF(), self.base_color.greenF(), self.base_color.blueF(), alpha)
            glBegin(GL_QUADS)
            glVertex3f(x - size, y - size, z)
            glVertex3f(x + size, y - size, z)
            glVertex3f(x + size, y + size, z)
            glVertex3f(x - size, y + size, z)
            glEnd()
        glPopMatrix()
    def generate_particles(self):
        particles = []
        for _ in range(100):
            x = random.uniform(-0.5, 0.5)
            y = random.uniform(-0.5, 0.5)
            z = random.uniform(-0.5, 0.5)
            size = random.uniform(0.01, 0.03)
            alpha = random.uniform(0.3, 0.6)
            particles.append([x, y, z, size, alpha])
        return particles

    def update_particles(self):
        for particle in self.smoke_particles:
            particle[1] += 0.01  # Move upwards
            particle[4] -= 0.01  # Fade out
            if particle[4] <= 0:
                particle[0] = random.uniform(-0.5, 0.5)
                particle[1] = random.uniform(-0.5, 0.5)
                particle[2] = random.uniform(-0.5, 0.5)
                particle[3] = random.uniform(0.01, 0.03)
                particle[4] = random.uniform(0.3, 0.6)

    def update_animation(self):
        """Update animation states."""
        self.angle += 1
        if self.angle >= 360:
            self.angle = 0

        self.update_particles()
        self.update()

    def update_text_opacity(self):
        """Animate text opacity for fade in/out effect."""
        if self.fade_in:
            self.text_opacity += 0.02
            if self.text_opacity >= 1.0:
                self.text_opacity = 1.0
                self.fade_in = False
        else:
            self.text_opacity -= 0.02
            if self.text_opacity <= 0.0:
                self.text_opacity = 0.0
                self.fade_in = True

        self.update()

    def toggle_animation(self):
        self.animation_running = not self.animation_running
        if self.animation_running:
            self.smoke_particles = self.generate_particles()  # Regenerate smoke particles
            self.timer.start(30)  # Restart the animation if it's stopped
        else:
            self.smoke_particles = []  # Clear smoke particles
            self.timer.stop()