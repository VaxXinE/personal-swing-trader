"""Typed, bounded, three-valued custom screener rules. Never use eval/SQL snippets."""
from __future__ import annotations
import math
from typing import Any
from pydantic import BaseModel, Field

FIELDS={'close','ema_20','ema_50','atr_14','atr_pct','rvol_20','roc_10','adv_20',
        'median_turnover_20','resistance_20','base_width_20','setup_score','entry_readiness','reward_risk'}
OPERATORS={'GT','GTE','LT','LTE','EQ','NE','BETWEEN','GT_FIELD','LT_FIELD'}

class RuleError(ValueError):pass

class ScreenerConfig(BaseModel):
    name: str = Field(default='Custom',min_length=1,max_length=80)
    markets: list[str] = Field(default_factory=lambda:['US','IDX','CRYPTO'],min_length=1,max_length=3)
    strategy: str = 'PULLBACK'
    rules: dict[str,Any] = Field(default_factory=lambda:{'op':'AND','children':[]})

    def model_post_init(self,__context:Any)->None:
        if self.strategy not in ('PULLBACK','BREAKOUT','BOTH'):raise ValueError('Invalid strategy')
        if any(m not in ('US','IDX','CRYPTO') for m in self.markets):raise ValueError('Invalid market')
        validate_rules(self.rules)


def validate_rules(rule:dict,depth:int=0,counter:list[int]|None=None)->int:
    if counter is None:counter=[0]
    counter[0]+=1
    if depth>5 or counter[0]>50:raise RuleError('Maximum depth=5, nodes=50')
    if not isinstance(rule,dict):raise RuleError('Rule must be object')
    if 'op' in rule:
        if rule['op'] not in ('AND','OR','NOT'):raise RuleError('Unsupported group operator')
        children=rule.get('children')
        if not isinstance(children,list) or (rule['op']=='NOT' and len(children)!=1) or len(children)>50:
            raise RuleError('Invalid child count')
        for child in children:validate_rules(child,depth+1,counter)
    else:
        field=rule.get('field');op=rule.get('operator');value=rule.get('value')
        if field not in FIELDS or op not in OPERATORS:raise RuleError('Invalid field/operator')
        if op in ('GT_FIELD','LT_FIELD'):
            if not isinstance(value,str) or value not in FIELDS:raise RuleError('Unrecognized comparison field')
        elif op=='BETWEEN':
            if not isinstance(value,list) or len(value)!=2 or not all(finite(v) for v in value) or value[0]>value[1]:
                raise RuleError('BETWEEN requires finite [min,max]')
        elif not finite(value):raise RuleError('Numeric finite literal required')
    return counter[0]


def finite(value:object)->bool:
    return type(value) in (float,int) and math.isfinite(value) and abs(value)<=1e15


def evaluate_rule(rule:dict,features:dict)->bool|None:
    if 'op' in rule:
        children=[evaluate_rule(c,features) for c in rule['children']]
        if rule['op']=='NOT':return None if children[0] is None else not children[0]
        if rule['op']=='AND':
            if False in children:return False
            return None if None in children else True
        if True in children:return True
        return None if None in children else False
    val=features.get(rule['field'])
    other=features.get(rule['value']) if rule['operator'] in ('GT_FIELD','LT_FIELD') else rule['value']
    if not finite(val) or (rule['operator']!='BETWEEN' and not finite(other)):return None
    op=rule['operator']
    return {'GT':lambda:val>other,'GTE':lambda:val>=other,'LT':lambda:val<other,
            'LTE':lambda:val<=other,'EQ':lambda:val==other,'NE':lambda:val!=other,
            'BETWEEN':lambda:other[0]<=val<=other[1],
            'GT_FIELD':lambda:val>other,'LT_FIELD':lambda:val<other}[op]()
