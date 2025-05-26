from newspaper import Article
from langchain_core.tools.base import BaseTool

class NewsScraper(BaseTool):
    name:str = "NewsScraper"
    description :str= "Collects and parses current news"

    def _run(self, url):
        article = Article(url)
        article.download()
        article.parse()
        return article.text



if __name__=="__main__":
    n=NewsScraper()
    print(n._run("https://pypi.org/project/sumy/"))