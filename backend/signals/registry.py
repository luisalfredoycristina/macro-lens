"""
Signal registry — loads signal definitions from signals.yaml.
Each signal defines: name, conditions (series + thresholds), direction, conviction, trade_implication.
"""
import yaml
import os
from pathlib import Path
from dataclasses import dataclass


@dataclass
class SignalDefinition:
    name: str
    description: str
    direction: str           # BULLISH, BEARISH, NEUTRAL
    conviction: int          # 1-3
    trade_implication: str
    priority: str            # P0, P1, P2
    conditions: list[dict]   # raw condition dicts from YAML


def load_registry() -> list[SignalDefinition]:
    """Load signal definitions from signals.yaml at repo root."""
    yaml_path = Path(__file__).parent.parent.parent / "signals.yaml"
    if not yaml_path.exists():
        raise FileNotFoundError(f"signals.yaml not found at {yaml_path}")
    with open(yaml_path) as f:
        data = yaml.safe_load(f)
    signals = []
    for s in data.get("signals", []):
        signals.append(SignalDefinition(
            name=s["name"],
            description=s.get("description", ""),
            direction=s["direction"],
            conviction=s.get("conviction", 2),
            trade_implication=s.get("trade_implication", ""),
            priority=s.get("priority", "P1"),
            conditions=s.get("conditions", []),
        ))
    return signals
