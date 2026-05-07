_HEADER = """
#version 330
uniform float time;
uniform vec2 resolution;
in vec2 uv;
out vec4 f_color;
"""

BUILTIN_SHADERS = []


def _shader(name):
    def decorator(fn):
        code = _HEADER + fn()
        BUILTIN_SHADERS.append(ShaderSource(name, code))
        return fn
    return decorator


class ShaderSource:
    def __init__(self, name, frag_code):
        self.name = name
        self.frag_code = frag_code

    def __repr__(self):
        return f"ShaderSource({self.name!r})"


@_shader("Plasma")
def _():
    return """
void main() {
    vec2 p = uv * 6.28318;
    float v = sin(p.x + time)
            + sin(p.y + time * 0.7)
            + sin((p.x + p.y) * 0.5 + time * 1.3)
            + sin(length(uv - 0.5) * 8.0 - time * 2.0);
    vec3 col = 0.5 + 0.5 * cos(time + vec3(0.0, 2.094, 4.189) + v * 1.5);
    f_color = vec4(col, 1.0);
}"""


@_shader("Tunnel")
def _():
    return """
void main() {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= resolution.x / resolution.y;
    float r = length(p);
    float a = atan(p.y, p.x);
    float u = a / 6.28318 + 0.5;
    float v2 = 0.3 / r + time * 0.3;
    float grid = step(0.5, fract(u * 12.0)) * step(0.5, fract(v2 * 12.0));
    vec3 col = mix(vec3(0.0, 0.02, 0.1), vec3(0.1, 0.5, 1.0), grid);
    col *= 1.0 / (r * 2.5 + 0.2);
    f_color = vec4(col, 1.0);
}"""


@_shader("Noise")
def _():
    return """
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i + vec2(1,0)), f.x),
               mix(hash(i + vec2(0,1)), hash(i + vec2(1,1)), f.x), f.y);
}
void main() {
    float n = 0.0;
    vec2 p = uv * 4.0;
    n += 0.500 * noise(p + time * 0.4); p *= 2.01;
    n += 0.250 * noise(p - time * 0.3); p *= 2.01;
    n += 0.125 * noise(p + time * 0.6); p *= 2.01;
    n += 0.063 * noise(p);
    vec3 col = mix(vec3(0.0, 0.0, 0.15), vec3(0.3, 0.7, 1.0), n);
    f_color = vec4(col, 1.0);
}"""


@_shader("Ripple")
def _():
    return """
void main() {
    vec2 p = uv - 0.5;
    p.x *= resolution.x / resolution.y;
    float r = length(p);
    float wave = sin(r * 24.0 - time * 5.0) * exp(-r * 3.5);
    float a = atan(p.y, p.x) / 6.28318;
    vec3 col = 0.5 + 0.5 * cos(vec3(0.0, 2.094, 4.189) + wave * 6.0 + a * 3.14 + time * 0.5);
    col *= smoothstep(0.7, 0.3, r);
    f_color = vec4(col, 1.0);
}"""


@_shader("Kaleidoscope")
def _():
    return """
void main() {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= resolution.x / resolution.y;
    float a = atan(p.y, p.x);
    float r = length(p);
    float n = 6.0;
    a = mod(a + time * 0.1, 6.28318 / n);
    a = abs(a - 3.14159 / n);
    p = vec2(cos(a), sin(a)) * r;
    float v = sin(p.x * 5.0 + time) * sin(p.y * 5.0 + time * 0.7);
    vec3 col = 0.5 + 0.5 * cos(vec3(0.0, 2.094, 4.189) + v * 3.14 + time * 0.3);
    f_color = vec4(col, 1.0);
}"""


@_shader("Scan Lines")
def _():
    return """
void main() {
    float scan = step(0.5, fract(uv.y * 60.0 - time * 1.5));
    float glow = sin(uv.x * 3.14159) * sin((uv.y + time * 0.05) * 3.14159 * 4.0);
    glow = max(glow, 0.0);
    vec3 col = vec3(0.1, 0.9, 0.3) * glow * (0.4 + 0.6 * scan);
    col += vec3(0.02, 0.12, 0.05) * (1.0 - scan);
    f_color = vec4(col, 1.0);
}"""


@_shader("Lissajous")
def _():
    return """
void main() {
    vec2 p = uv * 2.0 - 1.0;
    p.x *= resolution.x / resolution.y;
    float d = 1.0;
    for (int i = 1; i <= 6; i++) {
        float fi = float(i);
        vec2 lp = vec2(sin(fi * 1.13 * time + fi * 0.7),
                       cos(fi * 0.91 * time + fi * 1.1));
        d = min(d, length(p - lp * 0.85) - 0.025 / fi);
    }
    float glow = exp(-max(d, 0.0) * 25.0);
    vec3 col = glow * (0.5 + 0.5 * cos(vec3(0.0, 2.094, 4.189) + time + uv.x * 6.28));
    f_color = vec4(col, 1.0);
}"""


@_shader("Grid Pulse")
def _():
    return """
void main() {
    vec2 p = uv * 12.0;
    vec2 f = fract(p + time * 0.15);
    float line = min(f.x, 1.0 - f.x) * min(f.y, 1.0 - f.y);
    float pulse = sin(length(uv - 0.5) * 18.0 - time * 3.0) * 0.5 + 0.5;
    vec3 col = mix(vec3(0.03, 0.03, 0.06),
                   vec3(0.15, 0.5, 1.0),
                   smoothstep(0.04, 0.1, line) * pulse);
    f_color = vec4(col, 1.0);
}"""


@_shader("Voronoi")
def _():
    return """
vec2 hash2(vec2 p) {
    p = vec2(dot(p, vec2(127.1, 311.7)), dot(p, vec2(269.5, 183.3)));
    return fract(sin(p) * 43758.5453);
}
void main() {
    vec2 p = uv * 6.0;
    vec2 i = floor(p);
    vec2 f = fract(p);
    float minD = 1.0;
    vec2 minCell;
    for (int y = -1; y <= 1; y++)
    for (int x = -1; x <= 1; x++) {
        vec2 nb = vec2(float(x), float(y));
        vec2 pt = hash2(i + nb);
        pt = 0.5 + 0.5 * sin(time * 0.8 + 6.28318 * pt);
        float d = length(nb + pt - f);
        if (d < minD) { minD = d; minCell = i + nb; }
    }
    vec3 col = 0.5 + 0.5 * cos(vec3(0.0, 2.094, 4.189) + dot(minCell, vec2(0.3, 0.7)) + time * 0.4);
    col *= smoothstep(0.0, 0.05, minD - 0.02);
    f_color = vec4(col, 1.0);
}"""


@_shader("Aurora")
def _():
    return """
float hash(vec2 p) { return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453); }
float noise(vec2 p) {
    vec2 i = floor(p), f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    return mix(mix(hash(i), hash(i+vec2(1,0)), f.x),
               mix(hash(i+vec2(0,1)), hash(i+vec2(1,1)), f.x), f.y);
}
void main() {
    vec2 p = uv;
    float band = noise(vec2(p.x * 3.0 + time * 0.2, time * 0.1));
    float dist = abs(p.y - 0.5 - band * 0.3);
    float glow = exp(-dist * 12.0);
    float hue = p.x * 0.6 + band * 0.4 + time * 0.05;
    vec3 col = 0.5 + 0.5 * cos(vec3(0.0, 2.094, 4.189) + hue * 6.28);
    col *= glow * 1.5;
    col += vec3(0.0, 0.05, 0.1) * (1.0 - glow);
    f_color = vec4(col, 1.0);
}"""
