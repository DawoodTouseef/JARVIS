import os
from enum import Enum

import openai
from langchain_anthropic import ChatAnthropic
from langchain_core.language_models.chat_models import BaseChatModel
from langchain_openai import AzureChatOpenAI, ChatOpenAI
from langchain_groq import ChatGroq

class LLM_TYPE(str, Enum):
    OPENAI = "OPENAI"
    AZURE = "AZURE"
    ANTHROPIC = "ANTHROPIC"
    GROQ = "GROQ"


def create_llm(llm_name: LLM_TYPE) -> BaseChatModel:
    if llm_name == LLM_TYPE.OPENAI:
        return _create_chat_openai(
            model_name=os.getenv("OPENAI_API_MODEL", "gpt-4o"),
            temperature=0.1,
            base_url=os.getenv("OPENAI_API_BASE"),
        )
    elif llm_name == LLM_TYPE.AZURE:
        return _create_azure_chat_openai(
            api_key=os.getenv("AZURE_OPENAI_API_KEY"),
            azure_endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
            openai_api_version=os.getenv(
                "AZURE_OPENAI_API_VERSION", "2024-05-01-preview"
            ),
            deployment_name=os.getenv("AZURE_OPENAI_DEPLOYMENT_NAME", "gpt-4o"),
            model_name=os.getenv("AZURE_OPENAI_API_MODEL", "gpt-4o"),
            temperature=0.1,
        )
    elif llm_name == LLM_TYPE.ANTHROPIC:
        return _create_chat_anthropic(
            anthropic_api_key=os.getenv("ANTHROPIC_API_KEY"),
            model_name=os.getenv("ANTHROPIC_API_MODEL", "claude-3-opus-20240229"),
            temperature=0.1,
        )
    elif llm_name == LLM_TYPE.GROQ:
        return _create_chat_groq(
            model_name=os.getenv("GROQ_API_MODEL"),
            temperature=0.1,
            groq_api_key=os.getenv("GROQ_API_KEY")
        )
    else:
        raise ValueError(f"Unsupported LLM type: {llm_name}")


def _create_chat_openai(
    model_name: str, temperature: float, base_url: str | None
) -> ChatOpenAI:
    openai.api_type = "openai"
    return ChatOpenAI(
        model_name=model_name,
        temperature=temperature,
        streaming=True,
        client=openai.chat.completions,
        openai_api_base=base_url,
    )


def _create_azure_chat_openai(
    api_key: str,
    azure_endpoint: str,
    openai_api_version: str,
    deployment_name: str,
    model_name: str,
    temperature: float,
) -> AzureChatOpenAI:
    openai.api_type = "azure"
    return AzureChatOpenAI(
        api_key=api_key,
        azure_endpoint=azure_endpoint,
        openai_api_version=openai_api_version,
        deployment_name=deployment_name,
        model_name=model_name,
        temperature=temperature,
        streaming=True,
    )


def _create_chat_anthropic(
    anthropic_api_key: str, model_name: str, temperature: float
) -> ChatAnthropic:
    return ChatAnthropic(
        anthropic_api_key=anthropic_api_key,
        model=model_name,
        temperature=temperature,
        streaming=True,
    )

def _create_chat_groq(
    model_name: str, temperature: float, groq_api_key: str | None
) -> ChatGroq:
    openai.api_type = "openai"
    return ChatGroq(
        model=model_name,
        streaming=True,
        temperature=temperature,
        groq_api_key=groq_api_key,
    )
