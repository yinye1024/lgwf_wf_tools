import json

import lgwf_dsl.diagnostics as diagnostics_module
import lgwf_dsl.errors as errors_module
import lgwf_dsl.tokens as tokens_module


class Lexer:
    def __init__(self, text: str, source_name: str | None = None) -> None:
        self.text = text
        self.source_name = source_name
        self.index = 0
        self.line = 1
        self.column = 1

    def tokenize(self) -> list[tokens_module.Token]:
        tokens: list[tokens_module.Token] = []
        while self.index < len(self.text):
            char = self.text[self.index]
            if char.isspace():
                self._advance()
                continue
            if char == "#":
                self._skip_comment()
                continue
            if char == "/" and self._peek_next() == "/":
                self._skip_comment()
                continue
            if char == '"':
                tokens.append(self._read_string())
                continue
            if char in "{}[]:;,":
                location = self._location()
                self._advance()
                tokens.append(tokens_module.Token(tokens_module.TokenKind.SYMBOL, char, location))
                continue
            if self._is_ident_start(char):
                tokens.append(self._read_ident())
                continue
            if char.isdigit() or char == "-":
                tokens.append(self._read_number_like())
                continue
            raise errors_module.DSLParseError(f"Unexpected character: {char}", self._location())

        tokens.append(tokens_module.Token(tokens_module.TokenKind.EOF, "", self._location()))
        return tokens

    def _read_string(self) -> tokens_module.Token:
        location = self._location()
        start = self.index
        self._advance()
        escaped = False
        while self.index < len(self.text):
            char = self.text[self.index]
            self._advance()
            if escaped:
                escaped = False
            elif char == "\\":
                escaped = True
            elif char == '"':
                raw = self.text[start:self.index]
                try:
                    value = json.loads(raw)
                except json.JSONDecodeError as exc:
                    raise errors_module.DSLParseError("Invalid string literal.", location) from exc
                return tokens_module.Token(tokens_module.TokenKind.STRING, value, location)
        raise errors_module.DSLParseError("Unterminated string literal.", location)

    def _read_ident(self) -> tokens_module.Token:
        location = self._location()
        start = self.index
        while self.index < len(self.text) and self._is_ident_part(self.text[self.index]):
            self._advance()
        return tokens_module.Token(
            tokens_module.TokenKind.IDENT,
            self.text[start:self.index],
            location,
        )

    def _read_number_like(self) -> tokens_module.Token:
        location = self._location()
        start = self.index
        while self.index < len(self.text) and self.text[self.index] in "-+0123456789.eE":
            self._advance()
        return tokens_module.Token(
            tokens_module.TokenKind.IDENT,
            self.text[start:self.index],
            location,
        )

    def _skip_comment(self) -> None:
        while self.index < len(self.text) and self.text[self.index] != "\n":
            self._advance()

    def _advance(self) -> None:
        char = self.text[self.index]
        self.index += 1
        if char == "\n":
            self.line += 1
            self.column = 1
        else:
            self.column += 1

    def _location(self) -> diagnostics_module.SourceLocation:
        return diagnostics_module.SourceLocation(self.source_name, self.line, self.column, self.index)

    def _peek_next(self) -> str | None:
        next_index = self.index + 1
        if next_index >= len(self.text):
            return None
        return self.text[next_index]

    def _location_for_offset(self, offset: int) -> diagnostics_module.SourceLocation:
        line = 1
        column = 1
        for char in self.text[:offset]:
            if char == "\n":
                line += 1
                column = 1
            else:
                column += 1
        return diagnostics_module.SourceLocation(self.source_name, line, column, offset)

    @staticmethod
    def _is_ident_start(char: str) -> bool:
        return char.isalpha() or char == "_"

    @staticmethod
    def _is_ident_part(char: str) -> bool:
        return char.isalnum() or char in "._-"
