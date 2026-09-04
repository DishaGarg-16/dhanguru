import os
from datetime import datetime
from typing import Optional
from backend.app.models.signals import WatchlistDeltaReport, SessionDelta
from backend.app.models.watchlist import ExecutiveBriefing


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
        breakout_movers = [a for a in anomalies if any(s.category == "LEVEL_BREACH" for s in a.signals)]
        vol_movers = [a for a in anomalies if any(s.category == "VOLUME_SURGE" for s in a.signals)]

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
            # Use the headline of the highest severity signal
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
            fomo_guard = f"⚠️ Capital Protection Notice: {c_sym} is near its circuit band. Order execution and liquidity may be constrained."
        elif any(a.urgency_score >= 85 for a in anomalies):
            highest_urgency = max(anomalies, key=lambda x: x.urgency_score)
            fomo_guard = f"🛡️ High Volatility Alert: {highest_urgency.symbol} is undergoing high retail turnover. Avoid chasing price extensions."

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
    Unified briefing service with Pydantic AI agent support and
    zero-dependency deterministic fallback.
    """

    def __init__(self):
        self._llm_configured = False
        self._agent = None
        self._init_agent()

    def _init_agent(self):
        """
        Check for configured LLM provider and initialize Pydantic AI agent.
        Supports:
          - Local: Ollama (zero API key, 100% offline)
          - Cloud: Google Gemini, Groq, OpenAI
          - Fallback: Deterministic rule engine
        """
        provider = os.getenv("LLM_PROVIDER", "").lower()

        # Check for local Ollama
        if provider == "ollama" or os.getenv("OLLAMA_MODEL"):
            try:
                from pydantic_ai import Agent
                from pydantic_ai.models.openai import OpenAIModel

                model_name = os.getenv("OLLAMA_MODEL", "llama3.2")
                base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1")
                ollama_model = OpenAIModel(
                    model_name=model_name,
                    base_url=base_url,
                    api_key="ollama",
                )
                self._agent = Agent(
                    ollama_model,
                    result_type=ExecutiveBriefing,
                    system_prompt=(
                        "You are Dhanguru's senior market intelligence analyst for Indian equities (NSE/BSE). "
                        "Analyze the quantitative delta report between the user's last session and now. "
                        "Deliver a concise, executive briefing with clear human language, zero unnecessary jargon, "
                        "and responsible capital preservation guidance."
                    ),
                )
                self._llm_configured = True
                return
            except Exception:
                self._llm_configured = False
                return

        # Check for Cloud APIs (Gemini, Groq, OpenAI)
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
            elif provider == "groq" or groq_key:
                model_spec = os.getenv("GROQ_MODEL", "groq:llama-3.3-70b-versatile")
            else:
                model_spec = os.getenv("OPENAI_MODEL", "openai:gpt-4o-mini")

            self._agent = Agent(
                model_spec,
                result_type=ExecutiveBriefing,
                system_prompt=(
                    "You are Dhanguru's senior market intelligence analyst for Indian equities (NSE/BSE). "
                    "Analyze the quantitative delta report between the user's last session and now. "
                    "Deliver a concise, executive briefing with clear human language, zero unnecessary jargon, "
                    "and responsible capital preservation guidance."
                ),
            )
            self._llm_configured = True
        except Exception:
            self._llm_configured = False

    async def generate_briefing(self, report: WatchlistDeltaReport) -> ExecutiveBriefing:
        """
        Generate executive briefing using AI agent if available,
        or graceful deterministic fallback.
        """
        if self._llm_configured and self._agent:
            try:
                # Format quantitative summary for agent
                prompt = (
                    f"User was away for: {report.duration_away_human}.\n"
                    f"Benchmark NIFTY 50 Change: {report.benchmark_change_pct:+.2f}%.\n"
                    f"Total Tracked: {report.total_tracked}, Anomalies: {report.meaningful_changes_count}.\n"
                    f"Top Anomalies Data:\n"
                )
                for anom in report.top_attention[:3]:
                    prompt += f"- {anom.symbol}: {anom.price_change_pct:+.2f}%, Vol Added: {anom.volume_accumulated_while_away:,}, Urgency: {anom.urgency_score}, Signals: {[s.headline for s in anom.signals]}\n"

                result = await self._agent.run(prompt)
                briefing: ExecutiveBriefing = result.data
                briefing.generated_by = "AI_AGENT"
                briefing.top_anomalies = report.top_attention
                briefing.calm_count = len(report.calm_stocks)
                briefing.time_away_human = report.duration_away_human
                return briefing
            except Exception:
                # Graceful degradation on network timeout or quota limit
                pass

        # Use deterministic rule fallback
        return RuleEngineBriefingFallback.synthesize(report)


briefing_service = ExecutiveBriefingService()
