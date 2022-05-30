from __future__ import annotations

from typing import TYPE_CHECKING

from boolean import (
    TOKEN_AND,
    TOKEN_FALSE,
    TOKEN_LPAR,
    TOKEN_NOT,
    TOKEN_OR,
    TOKEN_RPAR,
    TOKEN_SYMBOL,
    TOKEN_TRUE,
    BooleanAlgebra,
    Expression,
    ParseError,
    boolean,
)

if TYPE_CHECKING:
    from notifier_bot.filters import Rule


class BooleanRuleAlgebra(BooleanAlgebra):
    """
    Subclass of BooleanAlgebra to be used with filter rules.

    The subclass implements the following changes to the tokenize method:
        - Don't interpret '0' and '1' as true/false
        - Interpret sequences of multiple words as a single token
    """

    def tokenize(self, expr: str) -> list:
        """
        Return an iterable of 3-tuple describing each token given an expression
        unicode string.
        This 3-tuple contains (token, token string, position):
        - token: either a Symbol instance or one of TOKEN_* token types.
        - token string: the original token unicode string.
        - position: some simple object describing the starting position of the
          original token string in the `expr` string. It can be an int for a
          character offset, or a tuple of starting (row/line, column).
        The token position is used only for error reporting and can be None or
        empty.
        Raise ParseError on errors. The ParseError.args is a tuple of:
        (token_string, position, error message)
        You can use this tokenizer as a base to create specialized tokenizers
        for your custom algebra by subclassing BooleanAlgebra. See also the
        tests for other examples of alternative tokenizers.
        This tokenizer has these characteristics:
        - The `expr` string can span multiple lines,
        - Whitespace is not significant.
        - The returned position is the starting character offset of a token.
        - A TOKEN_SYMBOL is returned for valid identifiers which is a string
        without spaces. These are valid identifiers:
            - Python identifiers.
            - a string even if starting with digits
            - digits (except for 0 and 1).
            - dotted names : foo.bar consist of one token.
            - names with colons: foo:bar consist of one token.
            These are not identifiers:
            - quoted strings.
            - any punctuation which is not an operation
        - Recognized operators are (in any upper/lower case combinations):
            - for and:  '*', '&', 'and'
            - for or: '+', '|', 'or'
            - for not: '~', '!', 'not'
        - Recognized special symbols are (in any upper/lower case combinations):
            - True symbols: 1 and True
            - False symbols: 0, False and None
        """
        if not isinstance(expr, str):
            raise TypeError(f"expr must be string but it is {type(expr)}.")

        # mapping of lowercase token strings to a token type id for the standard
        # operators, parens and common true or false symbols, as used in the
        # default tokenizer implementation.
        TOKENS = {
            "*": TOKEN_AND,
            "&": TOKEN_AND,
            "and": TOKEN_AND,
            "AND": TOKEN_AND,
            "+": TOKEN_OR,
            "|": TOKEN_OR,
            "or": TOKEN_OR,
            "OR": TOKEN_OR,
            "~": TOKEN_NOT,
            "!": TOKEN_NOT,
            "not": TOKEN_NOT,
            "(": TOKEN_LPAR,
            ")": TOKEN_RPAR,
            "[": TOKEN_LPAR,
            "]": TOKEN_RPAR,
            "true": TOKEN_TRUE,
            "false": TOKEN_FALSE,
            "none": TOKEN_FALSE,
        }
        tokens = []

        position = 0
        length = len(expr)

        while position < length:
            tok = expr[position]

            sym = tok.isalnum() or tok == "_"
            if sym:
                position += 1
                while position < length:
                    char = expr[position]
                    if char.isalnum() or char in self.allowed_in_token:
                        position += 1
                        tok += char
                    else:
                        break
                position -= 1

            try:
                tokens.append((TOKENS[tok.lower()], tok, position))
            except KeyError as e:
                if sym:
                    tokens.append((TOKEN_SYMBOL, tok, position))
                elif tok not in (" ", "\t", "\r", "\n"):
                    raise ParseError(
                        token_string=tok, position=position, error_code=boolean.PARSE_UNKNOWN_TOKEN
                    ) from e

            position += 1

        i = len(tokens) - 1
        while i > 0:
            if tokens[i][1] in TOKENS:
                i -= 1
                continue

            pos = tokens[i][2]
            new_token = ""
            j = i - 1
            while j >= 0 and tokens[j][1] not in TOKENS:
                new_token = tokens[j + 1][1] + " " + new_token
                tokens.pop(j + 1)
                j -= 1
            new_token = (tokens[j + 1][1] + " " + new_token)[:-1]
            tokens.pop(j + 1)

            tokens.insert(j + 1, (TOKEN_SYMBOL, new_token, pos))
            i -= i - j

        return tokens


algebra = BooleanRuleAlgebra(allowed_in_token=(".", ":", "_", "-"))


def apply_rules(rules: list[Rule], text: str) -> bool:
    total_rule: Expression | None = None
    for rule in rules:
        if total_rule is None:
            total_rule = rule.expression
        else:
            total_rule = total_rule | rule.expression

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
