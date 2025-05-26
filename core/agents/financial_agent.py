import json
import os.path

from crewai import Agent, Task, Crew, LLM
from crewai_tools import BaseTool
import numpy as np
import yfinance as yf
from langchain.prompts import PromptTemplate
from typing import List, Dict, Any
from core.Agent_models import get_model_from_database, get_model
from crewai_tools.tools.website_search.website_search_tool import WebsiteSearchTool
import re
from config import SESSION_PATH

import json
import os.path
import time
from typing import List, Dict, Any
import yfinance as yf
import numpy as np
from crewai_tools import BaseTool
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type
from requests.exceptions import HTTPError

class YahooFinanceDataTool(BaseTool):
    name: str = "Yahoo Finance Data Retrieval"
    description: str = "Fetches historical financial data for assets using Yahoo Finance API."

    @retry(
        stop=stop_after_attempt(5),  # Increase to 5 retries
        wait=wait_exponential(multiplier=2, min=5, max=30),  # Longer delays: 5s, 10s, 20s, 30s
        retry=retry_if_exception_type(HTTPError)
    )
    def _fetch_single_ticker(self, ticker: str, period: str) -> Dict:
        """Fetch data for a single ticker with retry logic."""
        try:
            asset = yf.Ticker(ticker)
            hist = asset.history(period=period)
            if hist.empty:
                raise ValueError(f"No data returned for ticker {ticker}")
            returns = hist['Close'].pct_change().dropna()
            annual_return = np.mean(returns) * 252  # Annualized return
            annual_volatility = np.std(returns) * np.sqrt(252)  # Annualized volatility
            return {
                "return": annual_return,
                "volatility": annual_volatility
            }
        except Exception as e:
            raise HTTPError(f"Failed to fetch data for {ticker}: {str(e)}")

    def _run(self, tickers: List[str], period: str = "1y") -> str:
        """Fetch historical financial data for given tickers with caching and rate limiting."""
        try:
            data = {}
            for ticker in tickers:
                # Fetch data with retry and rate limiting
                result = self._fetch_single_ticker(ticker, period)
                data[ticker] = result
                time.sleep(3)  # Add 1-second delay between requests to respect rate limits

            return json.dumps(data)
        except Exception as e:
            return json.dumps({"error": str(e)})


class PortfolioCalculatorTool(BaseTool):
    name: str = "Portfolio Calculator"
    description: str = "Calculates expected portfolio return and volatility based on allocations and asset data."

    def _run(self, allocations: List[float], returns: List[float], volatilities: List[float]) -> str:
        if len(allocations) != len(returns) or len(allocations) != len(volatilities):
            return json.dumps({"error": "All input lists must have the same length."})
        if abs(sum(allocations) - 1.0) > 0.01:
            return json.dumps({"error": "Allocations must sum to 1."})

        expected_return = sum(a * r for a, r in zip(allocations, returns))
        portfolio_volatility = np.sqrt(sum((a * v) ** 2 for a, v in zip(allocations, volatilities)))

        return json.dumps({
            "expected_return": expected_return,
            "portfolio_volatility": portfolio_volatility
        })

class MonteCarloSimulationTool(BaseTool):
    name: str = "Monte Carlo Simulation"
    description: str = "Performs Monte Carlo simulation for portfolio risk analysis."

    def _run(self, initial_investment: float, allocations: List[float], returns: List[float],
             volatilities: List[float], years: float, simulations: int = 1000) -> str:
        np.random.seed(42)
        dt = 1 / 252  # Daily time step (252 trading days per year)
        n_steps = int(years * 252)

        if len(allocations) != len(returns) or len(allocations) != len(volatilities):
            return json.dumps({"error": "All input lists must have the same length."})
        if abs(sum(allocations) - 1.0) > 0.01:
            return json.dumps({"error": "Allocations must sum to 1."})

        expected_return = sum(a * r for a, r in zip(allocations, returns))
        portfolio_volatility = np.sqrt(sum((a * v) ** 2 for a, v in zip(allocations, volatilities)))

        sim_returns = np.random.normal(
            loc=expected_return * dt,
            scale=portfolio_volatility * np.sqrt(dt),
            size=(n_steps, simulations)
        )
        price_paths = initial_investment * np.exp(np.cumsum(sim_returns, axis=0))

        final_values = price_paths[-1, :]
        mean_value = np.mean(final_values)
        std_value = np.std(final_values)
        var_95 = np.percentile(final_values, 5)

        return json.dumps({
            "expected_value": mean_value,
            "standard_deviation": std_value,
            "var_95": var_95,
            "potential_loss": initial_investment - var_95
        })

class ScenarioSimulationTool(BaseTool):
    name: str = "Scenario Simulation"
    description: str = "Simulates scenarios to compare investment strategies."

    def _run(self, strategy_params: Dict[str, Any], baseline_params: Dict[str, Any], years: float) -> str:
        monte_carlo = MonteCarloSimulationTool()

        strategy_result = json.loads(monte_carlo._run(
            strategy_params["initial_investment"],
            strategy_params["allocations"],
            strategy_params["returns"],
            strategy_params["volatilities"],
            years
        ))

        baseline_result = json.loads(monte_carlo._run(
            baseline_params["initial_investment"],
            baseline_params["allocations"],
            baseline_params["returns"],
            baseline_params["volatilities"],
            years
        ))

        return json.dumps({
            "strategy_result": strategy_result,
            "baseline_result": baseline_result,
            "comparison": {
                "risk_difference": strategy_result["potential_loss"] - baseline_result["potential_loss"],
                "return_difference": strategy_result["expected_value"] - baseline_result["expected_value"]
            }
        })


class FinancialAgent:
    def __init__(self):
        """Initialize the Financial Agent with LLM and tools."""
        self.llm = LLM(
            model=f"openai/{get_model_from_database().name}",
            api_key=get_model_from_database().api_key,
            base_url=get_model_from_database().url
        )

        # Instantiate tools
        self.yahoo_finance = YahooFinanceDataTool()
        self.portfolio_calculator = PortfolioCalculatorTool()
        config = dict(
            llm=dict(
                provider="openai",
                config=dict(
                    model=get_model_from_database().name,
                    api_key=get_model_from_database().api_key,
                    base_url=get_model_from_database().url
                ),
            ),
            embedder=dict(
                provider="huggingface",
                config=dict(
                    model="multi-qa-MiniLM-L6-cos-v1"
                )
            ),
            vectordb=dict(
                provider="chroma",
                config=dict(
                    dir=os.path.join(SESSION_PATH, "financial")
                )
            )
        )
        self.web_search = WebsiteSearchTool(config=config)
        self.monte_carlo_simulation = MonteCarloSimulationTool()
        self.scenario_simulation = ScenarioSimulationTool()

        # Define Agents with tools
        self.financial_analyst = Agent(
            role="Financial Analyst",
            goal="Perform financial calculations and retrieve real-time data",
            backstory="Expert in quantitative finance with extensive experience in investment analysis.",
            llm=self.llm,
            tools=[self.yahoo_finance, self.portfolio_calculator],
            verbose=True
        )

        self.marketing_strategist = Agent(
            role="Marketing Strategist",
            goal="Analyze market trends and suggest marketing strategies",
            backstory="Seasoned marketer with expertise in digital campaigns and consumer behavior.",
            llm=self.llm,
            tools=[self.web_search],
            verbose=True
        )

        self.risk_analyst = Agent(
            role="Risk Analyst",
            goal="Conduct risk analysis using Monte Carlo simulations",
            backstory="Specialist in risk management with a PhD in statistics.",
            llm=self.llm,
            tools=[self.monte_carlo_simulation],
            verbose=True
        )

        self.strategy_advisor = Agent(
            role="Strategy Advisor",
            goal="Suggest strategies and simulate scenarios",
            backstory="Consultant with 15 years of experience in strategic planning.",
            llm=self.llm,
            tools=[self.scenario_simulation, self.monte_carlo_simulation],
            verbose=True
        )

        # Prompt for parsing natural language query
        self.parse_prompt = PromptTemplate(
            input_variables=["query"],
            template="""
You are a financial assistant parsing a user query to check if it describes an investment portfolio for a Monte Carlo simulation. If the query contains investment details (e.g., amount, allocations, time horizon), extract:
- Initial investment amount (in dollars)
- Portfolio allocations (as fractions or percentages for assets: stocks, bonds, cash)
- Time horizon in years

If returns or volatilities are not provided, leave them empty to fetch from Yahoo Finance (tickers: SPY for stocks, IEF for bonds, BIL for cash). If parameters are missing, infer reasonable values and note assumptions. Ensure allocations sum to 100% (or 1.0). Return a JSON object with keys: `initial_investment`, `allocations`, `tickers`, `years`, and `assumptions`.

If the query lacks simulation details (e.g., "Should I invest in stocks?"), return an empty object.

Query: {query}

Example output for simulation query:
{{
    "initial_investment": 50000,
    "allocations": [0.5, 0.4, 0.1],
    "tickers": ["SPY", "IEF", "BIL"],
    "years": 3,
    "assumptions": ["Fetched returns and volatilities from Yahoo Finance"]
}}
Example output for non-simulation query:
{{}}
"""
        )

    def parse_natural_language_query(self, query: str) -> Dict[str, Any]:
        """Parse query to extract simulation parameters."""
        prompt = self.parse_prompt.format(query=query)
        try:
            response = get_model().invoke(prompt)
            # Log raw response for debugging
            print(f"Raw LLM response: {response.content}")
            # Handle empty or invalid response
            if not response.content or response.content.strip() == "":
                print("LLM returned an empty response, using fallback parsing")
                return self._fallback_parse_query(query)
            # Extract JSON from response
            content = response.content.strip()
            # Try to find JSON block
            json_match = re.search(r'```json\s*([\s\S]*?)\s*```', content, re.DOTALL)
            if json_match:
                json_content = json_match.group(1).strip()
                print(f"Extracted JSON content: {json_content}")
                try:
                    return json.loads(json_content)
                except json.JSONDecodeError as e:
                    print(f"Failed to parse extracted JSON: {e}, falling back to regex parsing")
                    return self._fallback_parse_query(query)
            # Fallback: Try parsing the entire content as JSON
            try:
                print(f"Attempting to parse entire content as JSON: {content}")
                return json.loads(content)
            except json.JSONDecodeError:
                print("Entire content is not valid JSON, falling back to regex parsing")
                return self._fallback_parse_query(query)
        except Exception as e:
            print(f"Error invoking LLM: {e}, falling back to regex parsing")
            return self._fallback_parse_query(query)

    def _fallback_parse_query(self, query: str) -> Dict[str, Any]:
        """Fallback method to parse query using regex if LLM fails."""
        # Check if query is for simulation
        if not re.search(r'\$?\d+(?:,\d+)*(?:\.\d+)?', query) or not re.search(r'allocation|invest', query,
                                                                               re.IGNORECASE):
            return {}

        # Extract initial investment
        initial_investment_match = re.search(r'\$?(\d+(?:,\d+)*(?:\.\d+)?)', query)
        if not initial_investment_match:
            return {}
        initial_investment = float(initial_investment_match.group(1).replace(',', ''))

        # Extract allocations
        allocations = []
        allocation_matches = re.findall(r'(\d+(?:\.\d+)?)\s*%\s*(?:in|to)\s*(stocks|bonds|cash)', query, re.IGNORECASE)
        for value, _ in allocation_matches:
            allocations.append(float(value) / 100)

        # Validate allocations
        if len(allocations) != 3 or abs(sum(allocations) - 1.0) > 0.01:
            return {}

        # Extract time horizon
        years_match = re.search(r'(\d+)\s*(?:year|years)', query, re.IGNORECASE)
        if not years_match:
            return {}
        years = int(years_match.group(1))

        # Default tickers and assumptions
        tickers = ["SPY", "IEF", "BIL"]
        assumptions = ["Fetched returns and volatilities from Yahoo Finance"]

        return {
            "initial_investment": initial_investment,
            "allocations": allocations,
            "tickers": tickers,
            "years": years,
            "assumptions": assumptions
        }

    def fetch_asset_data(self, tickers: List[str]) -> tuple[List[float], List[float]]:
        """Fetch returns and volatilities for given tickers."""
        data = json.loads(self.yahoo_finance._run(tickers))
        if "error" in data:
            raise ValueError(f"Failed to fetch Yahoo Finance data: {data['error']}")
        returns = []
        volatilities = []
        for ticker in tickers:
            if ticker not in data:
                raise ValueError(f"No data returned for ticker {ticker}")
            returns.append(data[ticker]["return"])
            volatilities.append(data[ticker]["volatility"])
        return returns, volatilities

    def run_simulation_task(self, parsed_params: Dict[str, Any]) -> Dict[str, Any]:
        """Run a Monte Carlo simulation task based on parsed parameters."""
        initial_investment = parsed_params["initial_investment"]
        allocations = parsed_params["allocations"]
        tickers = parsed_params["tickers"]
        years = parsed_params["years"]
        assumptions = parsed_params.get("assumptions", [])

        # Fetch real-time data
        returns, volatilities = self.fetch_asset_data(tickers)

        # Validate inputs
        if len(allocations) != len(returns) or len(allocations) != len(volatilities):
            raise ValueError("Allocations, returns, and volatilities must have the same length.")
        if abs(sum(allocations) - 1.0) > 0.01:
            raise ValueError("Allocations must sum to 1.")

        # Define risk analysis task
        risk_task = Task(
            description=(
                f"Use the Monte Carlo Simulation tool to analyze a ${initial_investment:,.2f} portfolio over {years} years. "
                f"Portfolio allocation: {allocations} (stocks, bonds, cash) with tickers {tickers}, "
                f"returns {returns}, and volatilities {volatilities}. "
                f"Assumptions: {', '.join(assumptions) if assumptions else 'None'}. "
                "Provide expected value, standard deviation, and 95% Value at Risk."
            ),
            agent=self.risk_analyst,
            expected_output="Risk analysis report with Monte Carlo simulation results."
        )

        # Run crew
        crew = Crew(agents=[self.risk_analyst], tasks=[risk_task], verbose=2)
        risk_result = crew.kickoff()

        # Run simulation
        sim_result = json.loads(self.monte_carlo_simulation._run(
            initial_investment, allocations, returns, volatilities, years
        ))

        return {
            "task_output": risk_result,
            "simulation_results": sim_result,
            "assumptions": assumptions
        }

    def handle_user_query(self, query: str) -> Dict[str, Any]:
        """Handle user query with chain-of-thought reasoning and optional simulation."""
        parsed_params = self.parse_natural_language_query(query)
        simulation_results = None
        assumptions = []

        # Define strategy task
        strategy_task_description = (
            f"Respond to the user query: '{query}' using chain-of-thought reasoning. "
            "Steps: 1) Assess the query's context and risks; 2) Evaluate strategies; "
            "3) Recommend an approach with justification. Include a diversified portfolio strategy if relevant."
        )

        if parsed_params:  # If query contains simulation parameters
            strategy_task_description += (
                f" Use the Scenario Simulation tool to simulate the portfolio with parameters: {parsed_params}. "
                "Compare with a single-stock strategy (ticker: SPY)."
            )
            simulation_results = self.run_simulation_task(parsed_params)
            assumptions = simulation_results["assumptions"]

        strategy_task = Task(
            description=strategy_task_description,
            agent=self.strategy_advisor,
            expected_output="Detailed response with reasoning, recommendation, and simulation results if applicable."
        )

        crew = Crew(agents=[self.strategy_advisor], tasks=[strategy_task], verbose=True)
        strategy_result = crew.kickoff()

        if simulation_results:
            return {
                "strategy_output": strategy_result,
                "simulation_output": simulation_results["simulation_results"],
                "assumptions": assumptions
            }

        return {"strategy_output": strategy_result}

# Example usage
if __name__ == "__main__":
    from config import SessionManager
    s=SessionManager()
    s.create_session("tdawood140@gmail.com")
    # Initialize agent
    agent = FinancialAgent()
    # Example 1: Query with simulation
    query = "Should I invest $50,000 with 50% in stocks, 40% in bonds, and 10% in cash over 3 years?"
    result = agent.handle_user_query(query)
    print("\nStrategy Response with Simulation:")
    print(result["strategy_output"])
    print("\nSimulation Results:")
    sim_results = result["simulation_output"]
    print(f"Expected Portfolio Value: ${sim_results['expected_value']:,.2f}")
    print(f"Standard Deviation: ${sim_results['standard_deviation']:,.2f}")
    print(f"95% Value at Risk: ${sim_results['potential_loss']:,.2f} (potential loss)")
    print("\nAssumptions:")
    for assumption in result["assumptions"]:
        print(f"- {assumption}")