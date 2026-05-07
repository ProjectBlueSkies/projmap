from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


def _fmt(color, bold=False, italic=False):
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


_KEYWORDS = [
    "void", "float", "int", "uint", "bool",
    "vec2", "vec3", "vec4", "mat2", "mat3", "mat4",
    "ivec2", "ivec3", "ivec4", "bvec2", "bvec3", "bvec4",
    "sampler2D", "uniform", "in", "out", "inout",
    "if", "else", "for", "while", "do", "return", "discard",
    "const", "true", "false", "struct",
]

_BUILTINS = [
    "sin", "cos", "tan", "asin", "acos", "atan",
    "sqrt", "pow", "exp", "log", "abs", "sign",
    "floor", "ceil", "fract", "mod", "min", "max",
    "clamp", "mix", "step", "smoothstep",
    "length", "distance", "dot", "cross", "normalize",
    "reflect", "refract", "texture", "texture2D",
    "any", "all", "not", "lessThan", "greaterThan",
    "equal", "notEqual",
]


class GlslHighlighter(QSyntaxHighlighter):
    def __init__(self, document):
        super().__init__(document)
        kw = _fmt("#C792EA", bold=True)
        fn = _fmt("#82AAFF")
        num = _fmt("#F78C6C")
        pp = _fmt("#C3E88D")
        self._comment_fmt = _fmt("#546E7A", italic=True)

        self._rules = []
        for word in _KEYWORDS:
            self._rules.append((QRegularExpression(rf'\b{word}\b'), kw))
        for word in _BUILTINS:
            self._rules.append((QRegularExpression(rf'\b{word}\b'), fn))
        self._rules.append((QRegularExpression(r'\b\d+\.?\d*([eE][+-]?\d+)?\b'), num))
        self._rules.append((QRegularExpression(r'#\w+'), pp))
        self._rules.append((QRegularExpression(r'//[^\n]*'), self._comment_fmt))

    def highlightBlock(self, text):
        for pattern, fmt in self._rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
