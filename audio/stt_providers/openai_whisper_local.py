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

model_ = None


def model():
    global model_
    if model_ is None:
        import whisper

        model_ = whisper.load_model("tiny")
    return model_


def preload_stt_openai_whisper_local():
    model()


def stt_openai_whisper_local(audio_file):
    result = model().transcribe(audio_file)
    return result["text"]