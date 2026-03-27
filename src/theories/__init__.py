from typing import Any, Callable, Dict

from .gallow import evaluate_gallow_causal, evaluate_gallow_prelim, evaluate_gallow_productive
from .hp2005 import evaluate_hp2005
from .hp2015 import evaluate_hp2015


THEORY_EVALUATORS: Dict[str, Callable[..., Dict[str, Any]]] = {
    "HP2005": evaluate_hp2005,
    "HP2015": evaluate_hp2015,
    "gallow_prelim": evaluate_gallow_prelim,
    "gallow_causal": evaluate_gallow_causal,
    "gallow_productive": evaluate_gallow_productive,
}
