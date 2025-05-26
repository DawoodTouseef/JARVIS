import plotly.graph_objects as go
from langchain_core.tools.base import BaseTool


class ChartPlot(BaseTool):
    name :str="ChartPlot"
    description:str = "Visualizes financial or statistical data"

    def _run(self, data):
        fig = go.Figure(data=[go.Bar(x=list(data.keys()), y=list(data.values()))])
        return fig.to_json()



if __name__=="__main__":
    g=ChartPlot()
    print(g._run({"x":[1,2,3],"y":[2,4,6]}))
