import pytest
from app.rules import validate_rules,evaluate_rule,RuleError,ScreenerConfig

def test_typed_rule():
    r={'op':'AND','children':[{'field':'close','operator':'GT_FIELD','value':'ema_50'},
                              {'field':'rvol_20','operator':'GTE','value':1.5}]}
    assert validate_rules(r)==3
    assert evaluate_rule(r,{'close':100,'ema_50':95,'rvol_20':2}) is True
    assert evaluate_rule(r,{'close':93,'ema_50':95,'rvol_20':2}) is False

def test_unknown_not_cannot_pass():
    r={'op':'NOT','children':[{'field':'rvol_20','operator':'GT','value':1.5}]}
    assert evaluate_rule(r,{'rvol_20':None}) is None

def test_injection_and_unrecognized_field_rejected():
    with pytest.raises(RuleError):validate_rules({'field':'__import__("os")','operator':'GT','value':1})
    with pytest.raises(RuleError):validate_rules({'field':'close','operator':'GT','value':float('nan')})

def test_recursive_rule_limit():
    r={'field':'close','operator':'GT','value':5}
    for _ in range(7):r={'op':'AND','children':[r]}
    with pytest.raises(RuleError):validate_rules(r)

def test_invalid_market_rejected():
    with pytest.raises(ValueError):ScreenerConfig(markets=['FUTURES'])
