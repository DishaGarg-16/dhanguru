import asyncio
import os
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field

from backend.app.models.signals import WatchlistDeltaReport, SessionDelta
from backend.app.models.watchlist import ExecutiveBriefing


class AIBriefingOutput(BaseModel):
    """
    Lightweight, flat response schema for LLM structured output.
    Avoids complex nested schema validation failures on local small models (e.g. llama3.2 3B).
    """
    headline: str = Field(description="Crisp 1-sentence macro headline summarizing key watchlist events")
    market_mood: Literal["BULLISH", "BEARISH", "VOLATILE", "CALM"] = Field(description="Overall mood of the watchlist")
    key_takeaways: list[str] = Field(description="2 to 3 concise bullet points highlighting notable market shifts")
    fomo_guard_notice: Optional[str] = Field(default=None, description="Responsible investing / capital preservation advice if high volatility")


class RuleEngineBriefingFallback:
    """
    Deterministic rule-based synthesizer that generates crisp, human-readable
    executive briefings when an external LLM is offline or unconfigured.
    Guarantees 100% uptime and resilience.
    """

    @staticmethod
    def synthesize(report: WatchlistDeltaReport) -> ExecutiveBriefing:
        anomalies = report.top_attention
        calm_count = len(report.calm_stocks)
        away_str = report.duration_away_human

        # Scenario 0: Watchlist is empty
        if report.total_tracked == 0:
            return ExecutiveBriefing(
                time_away_human=away_str,
                headline="Your watchlist is currently empty.",
                market_mood="CALM",
                key_takeaways=[
                    "No stocks are currently being monitored.",
                    "Click '+ Add Symbol' to add Indian equities and begin tracking structural shifts.",
                ],
                top_anomalies=[],
                calm_count=0,
                fomo_guard_notice=None,
                generated_by="RULE_ENGINE_FALLBACK",
            )

        # Scenario 1: Market was entirely calm while away
        if not anomalies:
            bench_sign = "+" if report.benchmark_change_pct >= 0 else ""
            headline = f"Calm session: All {report.total_tracked} stocks remained within normal daily volatility."
            mood = "CALM"
            takeaways = [
                f"NIFTY 50 moved {bench_sign}{report.benchmark_change_pct:.2f}% with balanced liquidity.",
                f"None of your {report.total_tracked} tracked symbols breached 14-day ATR volatility bands.",
                "Trading volume across your holdings tracked standard time-of-day baselines.",
            ]
            fomo_guard = "Your watchlist is in steady balance. No immediate decisions required."

            return ExecutiveBriefing(
                time_away_human=away_str,
                headline=headline,
                market_mood=mood,
                key_takeaways=takeaways,
                top_anomalies=[],
                calm_count=calm_count,
                fomo_guard_notice=fomo_guard,
                generated_by="RULE_ENGINE_FALLBACK",
            )

        # Scenario 2: Meaningful changes detected
        top_anomaly: SessionDelta = anomalies[0]
        circuit_movers = [a for a in anomalies if any(s.category == "CIRCUIT_ALERT" for s in a.signals)]

        # Determine Market Mood
        up_count = sum(1 for a in anomalies if a.price_change_pct > 0)
        down_count = sum(1 for a in anomalies if a.price_change_pct < 0)

        if len(anomalies) >= 3 and (up_count > 0 and down_count > 0):
            mood = "VOLATILE"
        elif up_count > down_count:
            mood = "BULLISH"
        elif down_count > up_count:
            mood = "BEARISH"
        else:
            mood = "VOLATILE"

        # Generate Headline
        if circuit_movers:
            c_stock = circuit_movers[0]
            headline = f"Attention: {c_stock.symbol} approached circuit limit while you were away for {away_str}."
        elif top_anomaly.price_change_pct >= 3.0:
            headline = f"Strong momentum: {top_anomaly.symbol} gained +{top_anomaly.price_change_pct:.1f}% on abnormal volume."
        elif top_anomaly.price_change_pct <= -3.0:
            headline = f"Sharp pullback: {top_anomaly.symbol} dropped {top_anomaly.price_change_pct:.1f}% on heavy selling."
        else:
            headline = f"{len(anomalies)} of your {report.total_tracked} stocks had structural shifts since you checked ({away_str} ago)."

        # Generate Key Takeaways
        takeaways = []
        for anom in anomalies[:3]:
            lead_signal = anom.signals[0].headline if anom.signals else "Unusual activity"
            sign = "+" if anom.price_change_pct >= 0 else ""
            takeaways.append(
                f"{anom.symbol} ({sign}{anom.price_change_pct:.1f}%): {lead_signal}."
            )

        if calm_count > 0:
            takeaways.append(f"{calm_count} other stock{'s' if calm_count > 1 else ''} traded within normal expected daily ranges.")

        # Responsible Investing / FOMO Guard
        fomo_guard = None
        if circuit_movers:
            c_sym = circuit_movers[0].symbol
            fomo_guard = f"Capital Protection Notice: {c_sym} is near its circuit band. Order execution and liquidity may be constrained."
        elif any(a.urgency_score >= 85 for a in anomalies):
            highest_urgency = max(anomalies, key=lambda x: x.urgency_score)
            fomo_guard = f"High Volatility Alert: {highest_urgency.symbol} is undergoing high retail turnover. Avoid chasing price extensions."

        return ExecutiveBriefing(
            time_away_human=away_str,
            headline=headline,
            market_mood=mood,
            key_takeaways=takeaways,
            top_anomalies=anomalies,
            calm_count=calm_count,
            fomo_guard_notice=fomo_guard,
            generated_by="RULE_ENGINE_FALLBACK",
        )


class ExecutiveBriefingService:
    """
    Unified briefing service with Pydantic AI agent support,
    direct Ollama fallback, and zero-dependency deterministic rule engine.
    """

    def __init__(self):
        self._llm_configured = False
        self._agent = None
        self._provider_name = "none"
        self._model_name = ""
        self._base_url = ""
        self._last_error = None
        self._init_agent()

    def _init_agent(self):
        """
        Check for configured LLM provider and initialize agent.
        Supports:
          - Local: Ollama (zero API key, 100% offline)
          - Cloud: Google Gemini, Groq, OpenAI
          - Fallback: Deterministic rule engine
        """
        # Ensure fresh .env reload
        env_path = Path(__file__).resolve().parents[3] / ".env"
        if env_path.exists():
            load_dotenv(dotenv_path=env_path, override=True)

        provider = os.getenv("LLM_PROVIDER", "").lower().strip()
        self._provider_name = provider
        self._last_error = None

        if provider in ("none", "fallback"):
            self._llm_configured = False
            self._agent = None
            return

        # 1. Local Ollama (100% Offline, zero API key)
        if provider == "ollama" or (os.getenv("OLLAMA_MODEL") and not provider):
            try:
                from pydantic_ai import Agent
                from pydantic_ai.models.ollama import OllamaModel
                from pydantic_ai.providers.ollama import OllamaProvider

                model_name = os.getenv("OLLAMA_MODEL", "llama3.2").strip()
                raw_url = os.getenv("OLLAMA_BASE_URL") or "http://127.0.0.1:11434/v1"
                # Normalize localhost -> 127.0.0.1 for Windows IPv6 compatibility
                base_url = raw_url.replace("localhost", "127.0.0.1").rstrip("/")
                if not base_url.endswith("/v1"):
                    base_url = f"{base_url}/v1"

                self._model_name = model_name
                self._base_url = base_url
                self._provider_name = "ollama"

                ollama_provider = OllamaProvider(base_url=base_url)
                ollama_model = OllamaModel(model_name, provider=ollama_provider)

                self._agent = Agent(
                    ollama_model,
                    output_type=AIBriefingOutput,
                    system_prompt=(
                        "You are Dhanguru's senior market intelligence analyst for Indian equities (NSE/BSE). "
                        "Analyze the quantitative delta report between the user's last session and now. "
                        "Deliver a concise, executive briefing with clear human language, zero unnecessary jargon, "
                        "and responsible capital preservation guidance."
                    ),
                )
                self._llm_configured = True
                print(f"[Dhanguru AI]: Local Ollama configured ({model_name} @ {base_url})")
                return
            except Exception as e:
                self._last_error = str(e)
                print(f"[Dhanguru Ollama Init]: {e}")
                self._llm_configured = False
                return

        # 2. Cloud APIs (Gemini, Groq, OpenAI)
        gemini_key = os.getenv("GEMINI_API_KEY")
        groq_key = os.getenv("GROQ_API_KEY")
        openai_key = os.getenv("OPENAI_API_KEY")

        if not (gemini_key or groq_key or openai_key or provider in ("gemini", "groq", "openai")):
            self._llm_configured = False
            return

        try:
            from pydantic_ai import Agent

            if provider == "gemini" or gemini_key:
                model_spec = os.getenv("GEMINI_MODEL", "gemini-1.5-flash")
                self._provider_name = "gemini"
            elif provider == "groq" or groq_key:
                model_spec = os.getenv("GROQ_MODEL", "groq:llama-3.3-70b-versatile")
                self._provider_name = "groq"
            else:
                model_spec = os.getenv("OPENAI_MODEL", "openai:gpt-4o-mini")
                self._provider_name = "openai"

            self._model_name = model_spec
            self._agent = Agent(
                model_spec,
                output_type=AIBriefingOutput,
                system_prompt=(
                    "You are Dhanguru's senior market intelligence analyst for Indian equities (NSE/BSE). "
                    "Analyze the quantitative delta report between the user's last session and now. "
                    "Deliver a concise, executive briefing with clear human language, zero unnecessary jargon, "
                    "and responsible capital preservation guidance."
                ),
            )
            self._llm_configured = True
            print(f"[Dhanguru AI]: Cloud LLM configured ({self._provider_name}: {model_spec})")
        except Exception as e:
            self._last_error = str(e)
            print(f"[Dhanguru Cloud Init Error]: {e}")
            self._llm_configured = False

    async def _query_ollama_direct(
        self,
        base_url: str,
        model_name: str,
        prompt: str,
        report: WatchlistDeltaReport,
    ) -> Optional[ExecutiveBriefing]:
        """
        Direct lightweight call to Ollama's native JSON endpoint.
        Uses grammar-constrained decoding (format='json') to guarantee clean JSON output
        without brittle tool-calling retry errors on small models like llama3.2.
        """
        try:
            import httpx
            import json

            # Use native Ollama /api/chat endpoint (base_url: http://127.0.0.1:11434/v1 -> root: http://127.0.0.1:11434)
            root_url = base_url.replace("/v1", "").rstrip("/")
            endpoint = f"{root_url}/api/chat"

            sys_msg = (
                "You are Dhanguru's senior market intelligence analyst for Indian equities (NSE/BSE). "
                "Analyze the session delta report and respond strictly with valid JSON only in this exact format:\n"
                '{"headline": "1 crisp sentence summary", "market_mood": "BULLISH"|"BEARISH"|"VOLATILE"|"CALM", "key_takeaways": ["point 1", "point 2"], "fomo_guard_notice": null}\n'
                "Only provide a string for fomo_guard_notice if there is an explicit capital preservation risk or circuit proximity; otherwise set it to null."
            )

            payload = {
                "model": model_name,
                "messages": [
                    {"role": "system", "content": sys_msg},
                    {"role": "user", "content": prompt},
                ],
                "format": "json",
                "options": {
                    "temperature": 0.2,
                },
                "stream": False,
            }

            async with httpx.AsyncClient(timeout=12.0) as client:
                res = await client.post(endpoint, json=payload)
                if res.status_code == 200:
                    data = res.json()
                    content = data.get("message", {}).get("content", "").strip()
                    if content:
                        parsed = json.loads(content)
                        validated = AIBriefingOutput.model_validate(parsed)

                        fomo_note = validated.fomo_guard_notice
                        if fomo_note and fomo_note.strip().lower() in ("null", "none", "nil", "n/a", ""):
                            fomo_note = None

                        return ExecutiveBriefing(
                            time_away_human=report.duration_away_human,
                            headline=validated.headline,
                            market_mood=validated.market_mood,
                            key_takeaways=validated.key_takeaways or [validated.headline],
                            top_anomalies=report.top_attention,
                            calm_count=len(report.calm_stocks),
                            fomo_guard_notice=fomo_note,
                            generated_by="AI_AGENT",
                        )
        except Exception as err:
            self._last_error = f"Direct Ollama call failed: {repr(err)}"
            print(f"[Dhanguru Direct Ollama Error]: {repr(err)}")
        return None

    def get_status(self) -> dict:
        """Return diagnostic status of the LLM configuration"""
        return {
            "provider": self._provider_name,
            "model": self._model_name,
            "base_url": self._base_url,
            "llm_configured": self._llm_configured,
            "last_error": self._last_error,
        }

    async def generate_briefing(self, report: WatchlistDeltaReport) -> ExecutiveBriefing:
        """
        Generate executive briefing using AI agent if available,
        falling back to direct Ollama HTTP, then rule engine.
        """
        # Dynamic check: if not configured, re-attempt initialization in case .env was edited
        if not self._llm_configured:
            self._init_agent()

        # Scenario 0: Watchlist is empty
        if report.total_tracked == 0:
            return ExecutiveBriefing(
                time_away_human=report.duration_away_human,
                headline="Your watchlist is currently empty.",
                market_mood="CALM",
                key_takeaways=[
                    "No stocks are currently being monitored.",
                    "Click '+ Add Symbol' to add Indian equities and begin tracking structural shifts.",
                ],
                top_anomalies=[],
                calm_count=0,
                fomo_guard_notice=None,
                generated_by="RULE_ENGINE_FALLBACK",
            )

        # Instant fast-path: if user just acknowledged (<15s ago) and no anomalies exist
        if report.duration_away_seconds < 15 and report.meaningful_changes_count == 0:
            return ExecutiveBriefing(
                time_away_human=report.duration_away_human,
                headline=f"All caught up. Monitoring {report.total_tracked} stocks in real time.",
                market_mood="CALM",
                key_takeaways=[
                    f"Session checkpoint acknowledged at {datetime.now().strftime('%H:%M:%S IST')}.",
                    f"Live market ticks streaming across all {report.total_tracked} watchlist symbols.",
                ],
                top_anomalies=report.top_attention,
                calm_count=len(report.calm_stocks),
                fomo_guard_notice="Watchlist state is in sync with latest market tick.",
                generated_by="AI_AGENT",
            )

        prompt = (
            f"User was away for: {report.duration_away_human}.\n"
            f"Benchmark NIFTY 50 Change: {report.benchmark_change_pct:+.2f}%.\n"
            f"Total Tracked: {report.total_tracked}, Anomalies: {report.meaningful_changes_count}.\n"
            f"Top Anomalies Data:\n"
        )
        if report.top_attention:
            for anom in report.top_attention[:3]:
                prompt += f"- {anom.symbol}: {anom.price_change_pct:+.2f}%, Vol Added: {anom.volume_accumulated_while_away:,}, Urgency: {anom.urgency_score}, Signals: {[s.headline for s in anom.signals]}\n"
        else:
            prompt += "All stocks remained within normal ATR daily volatility drift.\n"

        if self._llm_configured:
            # 1. Local Ollama: use native format='json' (bypasses tool-calling retries on llama3.2)
            if self._provider_name == "ollama":
                direct = await self._query_ollama_direct(
                    self._base_url, self._model_name, prompt, report
                )
                if direct:
                    return direct

            # 2. Cloud LLM (Gemini, Groq, OpenAI): use Pydantic AI agent
            elif self._agent:
                try:
                    result = await asyncio.wait_for(self._agent.run(prompt), timeout=8.0)
                    payload: AIBriefingOutput = getattr(result, "output", getattr(result, "data", None))

                    if payload and hasattr(payload, "headline"):
                        fomo_note = payload.fomo_guard_notice
                        if fomo_note and fomo_note.strip().lower() in ("null", "none", "nil", "n/a", ""):
                            fomo_note = None

                        return ExecutiveBriefing(
                            time_away_human=report.duration_away_human,
                            headline=payload.headline,
                            market_mood=payload.market_mood,
                            key_takeaways=payload.key_takeaways or [payload.headline],
                            top_anomalies=report.top_attention,
                            calm_count=len(report.calm_stocks),
                            fomo_guard_notice=fomo_note,
                            generated_by="AI_AGENT",
                        )
                except Exception as e:
                    self._last_error = f"Agent run error: {e}"
                    print(f"[Dhanguru Agent Run Error]: {e}")

        # Deterministic rule engine fallback
        return RuleEngineBriefingFallback.synthesize(report)


briefing_service = ExecutiveBriefingService()
