import os.path
from pandasai.llm.langchain import LangchainLLM
from duckduckgo_search import DDGS
from core.Agent_models import get_model
import pandas as pd
from config import JARVIS_DIR
from sqlalchemy import inspect
from sqlalchemy import create_engine
from pandasai import SmartDataframe
from pandasai.skills import Skill
from pandasai.schemas.df_config import Config

llm=LangchainLLM(get_model())

class TaskStore:
    def __init__(self):
        self.database=[os.path.join(JARVIS_DIR,"data","jarvis.db"),os.path.join(JARVIS_DIR,"data","assistant_data.db")]
        self.engine = [create_engine(f"sqlite:///{db_path}") for db_path in self.database]
        self.inspector = [inspect(engine) for engine in self.engine]

    def load_data(self):
        df=[]
        for tables,engine in zip(self.inspector,self.engine):
            for table in tables.get_table_names():
                data=pd.read_sql(f"SELECT * FROM {table}",engine)
                df.append(data)
        return df

    def save_tasks(self, df, table_name="strategic_tasks"):
        for engine in self.engine:
            df.to_sql(table_name, engine, if_exists="append", index=False)

def SearchSkill(query: str) -> str:
    """
    Searches for web content
    """
    ddgs = DDGS()
    results = ddgs.text(query, max_results=3)
    texts = [r["body"] for r in results]
    return "\n\n".join(texts)

class StrategicAgent:
    def __init__(self):
        self.llm = LangchainLLM(get_model())
        self.store = TaskStore()
        self.search =Skill(SearchSkill)

    def define_goals(self, goal_description):
        prompt = f"Break this high-level goal into strategic milestones and tasks: '{goal_description}'"
        return get_model().invoke(prompt)

    def analyze_plan(self, prompt="Optimize the plan for execution efficiency."):
        df=self.store.load_data()
        df=pd.DataFrame(df)
        sdf = SmartDataframe(df, config=Config(llm=llm))
        sdf.add_skills(self.search)
        return sdf.chat(prompt)


# Example use
if __name__ == '__main__':
    from config import SessionManager
    s=SessionManager()
    s.create_session("tdawood140@gmail.com")
    agent = StrategicAgent()
    goals_text = agent.define_goals("Launch a new AI-powered productivity app")
    print("\n--- Defined Goals ---\n", goals_text)

    strategy = agent.analyze_plan()
    print("\n--- Strategy Analysis ---\n", strategy)