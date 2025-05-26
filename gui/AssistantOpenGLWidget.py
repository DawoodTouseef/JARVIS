# Copyright 2025 Dawood Thouseef
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
import os.path
import freetype
import numpy as np
from PyQt5.QtCore import Qt, QTimer, QPoint
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import  QOpenGLWidget
from OpenGL.GL import *
from OpenGL.GLU import *
import random

class FontRenderer:
    def __init__(self, font_path=None, font_size=18):
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







# Add this at the top
import colorsys
import math

class AssistantOpenGLWidget(QOpenGLWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(650, 800)

        self.angle = 0
        self.pulse_intensity = 0.0
        self.text_opacity = 0.0
        self.fade_in = True
        self.smoke_particles = []
        self.orbit_angle = 0
        self.hue = 0
        self.animation_running=False

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_animation)
        self.timer.start(30)

        from config import JARVIS_DIR
        self.font_renderer = FontRenderer(
            os.path.join(JARVIS_DIR,"assests", "fonts", "Monomakh", "Monomakh-Regular.ttf"), 18
        )

        self.text_timer = QTimer(self)
        self.text_timer.timeout.connect(self.update_text_opacity)
        self.text_timer.start(50)

    def initializeGL(self):
        glEnable(GL_DEPTH_TEST)
        glEnable(GL_BLEND)
        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA)
        glEnable(GL_LIGHTING)
        glEnable(GL_LIGHT0)

        glLightfv(GL_LIGHT0, GL_POSITION, [0.0, 0.0, 2.0, 1.0])
        glLightfv(GL_LIGHT0, GL_AMBIENT, [0.3, 0.3, 0.3, 1.0])
        glLightfv(GL_LIGHT0, GL_DIFFUSE, [1.5, 1.5, 1.5, 1.0])

    def resizeGL(self, w, h):
        glViewport(0, 0, w, h)
        glMatrixMode(GL_PROJECTION)
        glLoadIdentity()
        gluPerspective(45, w / h, 0.1, 50.0)
        glMatrixMode(GL_MODELVIEW)

    def get_current_color(self):
        self.hue = (self.hue + 1) % 360
        r, g, b = colorsys.hsv_to_rgb(self.hue / 360.0, 1, 1)
        return [r, g, b]

    def draw_3d_sphere(self):
        glPushMatrix()
        glRotatef(self.angle, 0, 1, 0)
        r, g, b = self.get_current_color()
        intensity = 0.5 + 0.5 * math.sin(self.angle * math.pi / 180)
        glMaterialfv(GL_FRONT, GL_DIFFUSE, [r * intensity, g * intensity, b * intensity, 1.0])
        quadric = gluNewQuadric()
        gluSphere(quadric, 0.5, 64, 64)
        gluDeleteQuadric(quadric)
        glPopMatrix()

    def draw_orbiting_ring(self):
        glPushMatrix()
        glRotatef(self.orbit_angle, 0, 0, 1)
        glColor4f(1.0, 1.0, 1.0, 0.3)
        glBegin(GL_LINE_LOOP)
        for i in range(100):
            angle = 2.0 * math.pi * i / 100
            x = 0.8 * math.cos(angle)
            y = 0.8 * math.sin(angle)
            glVertex3f(x, y, 0)
        glEnd()
        glPopMatrix()

    def draw_rotating_light_pulses(self):
        glPushMatrix()
        glRotatef(self.angle * 2, 0, 1, 0)
        glColor4f(1.0, 1.0, 1.0, 0.15 + 0.15 * math.sin(self.angle * math.pi / 90))
        gluDisk(gluNewQuadric(), 0.6, 0.7, 50, 1)
        glPopMatrix()

    def draw_smoke_effect(self):
        glPushMatrix()
        for x, y, z, size, alpha in self.smoke_particles:
            glColor4f(1.0, 1.0, 1.0, alpha)
            glBegin(GL_QUADS)
            glVertex3f(x - size, y - size, z)
            glVertex3f(x + size, y - size, z)
            glVertex3f(x + size, y + size, z)
            glVertex3f(x - size, y + size, z)
            glEnd()
        glPopMatrix()

    def paintGL(self):
        glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
        glLoadIdentity()
        gluLookAt(0.0, 0.0, 2.5, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)
        glClearColor(0.0, 0.0, 0.0, 0.0)

        self.draw_3d_sphere()
        self.draw_orbiting_ring()
        self.draw_rotating_light_pulses()
        self.draw_smoke_effect()
        self.font_renderer.render_text("Hello, I am JARVIS", -0.3, -0.8, self.text_opacity)

    def generate_particles(self):
        return [
            [random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5),
             random.uniform(0.01, 0.03), random.uniform(0.2, 0.5)] for _ in range(100)
        ]

    def update_particles(self):
        for p in self.smoke_particles:
            p[1] += 0.005
            p[4] -= 0.01
            if p[4] <= 0:
                p[:] = [random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5), random.uniform(-0.5, 0.5),
                        random.uniform(0.01, 0.03), random.uniform(0.3, 0.6)]

    def update_animation(self):
        self.angle = (self.angle + 1) % 360
        self.orbit_angle = (self.orbit_angle + 1.5) % 360
        self.update_particles()
        self.update()

    def update_text_opacity(self):
        if self.fade_in:
            self.text_opacity += 0.02
            if self.text_opacity >= 1.0:
                self.fade_in = False
        else:
            self.text_opacity -= 0.02
            if self.text_opacity <= 0.0:
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