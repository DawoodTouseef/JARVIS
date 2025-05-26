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
from InquirerPy import inquirer
from components.coder.core.llm import LLM_TYPE
import requests


def fetch_openai_models(base_url: str, api_key: str):
    headers = {
        "Authorization": f"Bearer {api_key}"
    }
    try:
        response = requests.get(f"{base_url.rstrip('/')}/v1/models", headers=headers)
        response.raise_for_status()
        data = response.json()
        models = data.get("data", [])
        return sorted([model.get("id") for model in models]) if models else []
    except Exception as e:
        print(f"❌ Error: {e}")
        return []


def llm(console):
    while True:
        llm_type_str = inquirer.select(
            message="LLM Type",
            choices=[
                {"name": name.replace("_", " ").title(), "value": value.value}
                for name, value in LLM_TYPE.__members__.items()
            ],
            default=LLM_TYPE.OPENAI.value,
        ).execute()

        llm_type = LLM_TYPE(llm_type_str)
        base_url, api_key, selected_model = None, None, None

        if llm_type == LLM_TYPE.OPENAI:
            base_url, api_key, selected_model = openai_llm(console)
        elif llm_type == LLM_TYPE.OLLAMA:
            base_url, api_key, selected_model = ollama_llm(console)
        elif llm_type == LLM_TYPE.GROQ:
            api_key, selected_model = grok_llm(console)
        elif llm_type == LLM_TYPE.ANTHROPIC:
            api_key, selected_model = anthropic_llm(console)
        elif llm_type == LLM_TYPE.AZURE_OPENAI:
            base_url, api_key, selected_model = azure_openai_llm(console)

        confirm = inquirer.confirm(
            message="Is this configuration correct?",
            default=True
        ).execute()

        if confirm and api_key and selected_model:
            return llm_type, base_url, api_key, selected_model
        else:
            console.print("Re-select the configuration!")


def openai_llm(console):
    while True:
        base_url = inquirer.text(message="Enter OpenAI Endpoint (optional):").execute()
        api_key = inquirer.secret(message="Enter OpenAI API KEY :").execute()
        model_list = fetch_openai_models(base_url, api_key)
        if model_list:
            selected_model = inquirer.select(message="📦 Choose a model:", choices=model_list).execute()
            console.print(f"\n✅ You selected: {selected_model}")
            return base_url, api_key, selected_model
        else:
            console.print("Invalid base_url or API Key")


def ollama_llm(console):
    while True:
        base_url = inquirer.text(message="Enter Ollama Endpoint (optional):").execute()
        api_key = "ollama"
        model_list = fetch_openai_models(base_url, api_key)
        if model_list:
            selected_model = inquirer.select(message="📦 Choose a model:", choices=model_list).execute()
            console.print(f"\n✅ You selected: {selected_model}")
            return base_url, api_key, selected_model
        else:
            console.print("Invalid base_url or API Key")


def grok_llm(console):
    from groq import Groq
    while True:
        api_key = inquirer.secret(message="Enter GROQ API KEY :").execute()
        groq = Groq(api_key=api_key)
        model_list = groq.models.list().data
        if model_list:
            choices = [model.id for model in model_list]
            selected_model = inquirer.select(message="📦 Choose a model:", choices=choices).execute()
            console.print(f"\n✅ You selected: {selected_model}")
            return api_key, selected_model
        else:
            console.print("Invalid API Key")


def anthropic_llm(console):
    import anthropic
    while True:
        api_key = inquirer.secret(message="Enter Anthropic API KEY :").execute()
        client = anthropic.Anthropic(api_key=api_key)
        try:
            models = client.models.list()
            choices = [model.id for model in models.data]
            selected_model = inquirer.select(message="📦 Choose a model:", choices=choices).execute()
            console.print(f"\n✅ You selected: {selected_model}")
            return api_key, selected_model
        except Exception as e:
            console.print(f"❌ Failed to fetch models: {e}")


def azure_openai_llm(console):
    while True:
        base_url = inquirer.text(message="Enter Azure OpenAI Endpoint:").execute()
        api_key = inquirer.secret(message="Enter Azure OpenAI API Key:").execute()
        api_version = inquirer.text(message="Enter Azure API Version (e.g. 2023-05-15):").execute()

        try:
            headers = {"api-key": api_key}
            params = {"api-version": api_version}
            response = requests.get(f"{base_url.rstrip('/')}/openai/deployments", headers=headers, params=params)
            response.raise_for_status()
            deployments = response.json().get("data", [])
            choices = [d.get("model") for d in deployments]
            selected_model = inquirer.select(message="📦 Choose a deployed Azure model:", choices=choices).execute()
            console.print(f"\n✅ You selected: {selected_model}")
            return base_url, api_key, selected_model
        except Exception as e:
            console.print(f"❌ Azure OpenAI Error: {e}")
