from setuptools import setup

setup(
    name='JARVIS',
    version='0.0.1',
    packages=['gui', 'core', 'audio', 'audio.stt_providers', 'audio.tts_providers', 'utils', 'utils.models',
              'utils.internals', 'deepface', 'deepface.api', 'deepface.api.src', 'deepface.api.src.modules',
              'deepface.api.src.modules.core', 'deepface.models', 'deepface.models.spoofing',
              'deepface.models.demography', 'deepface.models.face_detection', 'deepface.models.facial_recognition',
              'deepface.commons', 'deepface.modules', 'speedtest', 'interpreter', 'interpreter.core',
              'interpreter.core.llm', 'interpreter.core.utils', 'interpreter.core.computer',
              'interpreter.core.computer.ai', 'interpreter.core.computer.os', 'interpreter.core.computer.sms',
              'interpreter.core.computer.docs', 'interpreter.core.computer.mail', 'interpreter.core.computer.files',
              'interpreter.core.computer.mouse', 'interpreter.core.computer.vision',
              'interpreter.core.computer.browser', 'interpreter.core.computer.display',
              'interpreter.core.computer.calendar', 'interpreter.core.computer.contacts',
              'interpreter.core.computer.keyboard', 'interpreter.core.computer.terminal',
              'interpreter.core.computer.terminal.languages', 'interpreter.core.computer.clipboard',
              'interpreter.computer_use', 'interpreter.computer_use.tools', 'interpreter.terminal_interface'],
    url='',
    license='',
    author='Dawood Touseef',
    author_email='tdawood140@gmail.com',
    description='Just a Rather Very Intelligent System'
)
