import warnings
from pydantic import Field,BaseModel
from typing_extensions import TypedDict,Type
from core.Agent_models import get_model
from langchain.tools import BaseTool
from langgraph.graph import StateGraph, END, START
from standard_tools import *
from langchain_community.tools import YouTubeSearchTool
from langchain_community.agent_toolkits.openapi.toolkit import RequestsToolkit
from langchain_community.utilities.requests import TextRequestsWrapper
from langgraph.graph.message import AnyMessage
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from config import stop_event,  ALLOW_DANGEROUS_REQUEST,loggers
from core.planner_agent import VisionRouter, AgentConfig
from core.vision_agents import vision_agent
from concurrent.futures import ThreadPoolExecutor
import logging
from langchain_community.tools import ShellTool
from langchain_community.utilities import OpenWeatherMapAPIWrapper
from langchain_community.tools.openweathermap.tool import OpenWeatherMapQueryRun
from langchain.agents import AgentType, initialize_agent
from crewai import Agent, Task, Crew, LLM
from crewai.tools.base_tool import BaseTool as CrewAIBaseTool, Tool as CrewAITool
import schedule
import os
import re
import json
from typing import Union, List, Dict, Any
from datetime import datetime, timedelta
from config import SESSION_PATH
from utils.models.users import Users
from core.Agent_models import get_model_from_database
import threading
import time
import winreg
import requests
import ctypes
import shutil
import platform
from functools import lru_cache
import asyncio
import psutil
import language_tool_python
import lancedb
from sentence_transformers import SentenceTransformer
from transformers import pipeline, AutoModelForCausalLM, AutoTokenizer
import speech_recognition as sr
import easyocr
from PIL import Image
from mem0 import Memory,MemoryClient
import socket
import netifaces
from config import JARVIS_DIR
from langchain_community.tools.yahoo_finance_news import YahooFinanceNewsTool


def stop_conversation():
    stop_event.set()
    return "Conversation stopped. You may start a new request."

class StopTool(BaseTool):
    name: str = "Stop Assistant"
    description: str = "Stops the current conversation or action."
    def _run(self) -> str:
        return stop_conversation()