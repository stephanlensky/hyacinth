from hyacinth.filters import Rule
from hyacinth.util.boolean_rule_algebra import apply_rules


def test_apply_rules__complex_rule__returns_expected() -> None:
    rules = list(
        map(
            lambda r: Rule(rule_str=r),
            (
                "klx",
                "ktm and not (duke or sx or rc)",
                "exc",
                "husqvarna",
                "wr",
                "yz and not 65 and not 85 and not yzf",
                "yamaha and dual",
                "yamaha and xt",
                "xr",
                "klr",
                "dr and suzuki",
                "drz and not drz50 and not drz 50",
                "crf and not crf80 and not crf 80 and not crf50 and not crf 50",
                "beta",
                "swm",
                "tw200 or tw 200",
            ),
        )
    )

    assert apply_rules(rules, "ktm exc 500")
    assert not apply_rules(rules, "crf 80")
    assert apply_rules(rules, "crf250")
