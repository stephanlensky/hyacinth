from boolean import Expression

from notifier_bot.boolean_rule_algebra import BooleanRuleAlgebra
from notifier_bot.models import FilterRules

algebra = BooleanRuleAlgebra()


def test(filter_rules: FilterRules, text: str) -> bool:
    for preremoval_rule in filter_rules.preremoval_rules:
        text = text.replace(preremoval_rule, "")
    for disallowed_word in filter_rules.disallowed_words:
        if disallowed_word in text:
            return False

    total_rule = None
    for _, rule in filter_rules.rules:
        if total_rule is None:
            total_rule = rule
        else:
            total_rule = total_rule | rule

    if total_rule is None:
        return False

    symbols = total_rule.get_symbols()
    subs = {}
    for sym in symbols:
        subs[sym] = algebra.TRUE if sym.obj in text else algebra.FALSE
    total_rule = total_rule.subs(subs)
    simplified_rule = total_rule.simplify()
    return bool(simplified_rule)


def parse_rule(rule_str: str) -> Expression:
    return algebra.parse(rule_str)
