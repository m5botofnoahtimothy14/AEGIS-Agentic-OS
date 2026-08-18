#version 330 core

/**
 * SATURDAY Edge Glow Shader - Gemini-style animated border lighting
 *
 * Multi-layer Fresnel edge glow with:
 * - Audio-reactive width and brightness
 * - AI state color transitions
 * - Animated breathing/pulsing
 * - Corner accent glow
 * - Simplex noise organic texture
 */

in vec2 vTexCoord;
in vec2 vPosition;

out vec4 fragColor;

uniform float uTime;
uniform float uDeltaTime;

uniform vec3 uEdgeColor;
uniform vec3 uInnerColor;
uniform float uGlowWidth;
uniform float uAudioLevel;
uniform float uBassLevel;
uniform float uTrebleLevel;
uniform float uPulsePhase;
uniform float uIntensity;
uniform vec2 uResolution;

float hash(vec2 p) {
    return fract(sin(dot(p, vec2(127.1, 311.7))) * 43758.5453123);
}

float noise(vec2 p) {
    vec2 i = floor(p);
    vec2 f = fract(p);
    f = f * f * (3.0 - 2.0 * f);
    float a = hash(i);
    float b = hash(i + vec2(1.0, 0.0));
    float c = hash(i + vec2(0.0, 1.0));
    float d = hash(i + vec2(1.0, 1.0));
    return mix(mix(a, b, f.x), mix(c, d, f.x), f.y);
}

float fbm(vec2 p) {
    float v = 0.0;
    float a = 0.5;
    vec2 shift = vec2(100.0);
    for (int i = 0; i < 4; i++) {
        v += a * noise(p);
        p = p * 2.0 + shift;
        a *= 0.5;
    }
    return v;
}

void main() {
    vec2 uv = vTexCoord;
    vec2 aspect = vec2(uResolution.x / uResolution.y, 1.0);
    vec2 p = uv * aspect;

    float baseWidth = uGlowWidth;
    float audioExpand = uAudioLevel * 0.15 + uBassLevel * 0.12;
    float breathWidth = baseWidth + audioExpand;

    float wave1 = sin(uTime * 1.2 + uv.x * 12.0) * 0.008;
    float wave2 = sin(uTime * 0.8 + uv.y * 8.0) * 0.01;
    float wave3 = cos(uTime * 1.7 + (uv.x + uv.y) * 6.0) * 0.005;
    float waveOffset = wave1 + wave2 + wave3;

    float edgeL = uv.x + waveOffset;
    float edgeR = (1.0 - uv.x) + waveOffset;
    float edgeB = uv.y + waveOffset;
    float edgeT = (1.0 - uv.y) + waveOffset;

    float glowL = exp(-edgeL / breathWidth);
    float glowR = exp(-edgeR / breathWidth);
    float glowB = exp(-edgeB / breathWidth);
    float glowT = exp(-edgeT / breathWidth);

    float edgeGlow = max(max(glowL, glowR), max(glowB, glowT));

    float cornerDist1 = length(vec2(uv.x, uv.y)) * 0.7;
    float cornerDist2 = length(vec2(1.0 - uv.x, uv.y)) * 0.7;
    float cornerDist3 = length(vec2(uv.x, 1.0 - uv.y)) * 0.7;
    float cornerDist4 = length(vec2(1.0 - uv.x, 1.0 - uv.y)) * 0.7;
    float cornerGlow = exp(-min(min(cornerDist1, cornerDist2), min(cornerDist3, cornerDist4)) / (breathWidth * 1.4));

    float glow = max(edgeGlow, cornerGlow * 1.3);

    float noiseTex = fbm(uv * 3.0 + uTime * 0.15);
    float noiseEdge = fbm(uv * 8.0 - uTime * 0.3);
    glow += noiseTex * 0.08 * glow;
    glow += noiseEdge * 0.04 * edgeGlow;

    float pulse = sin(uPulsePhase) * 0.15 + 0.85;
    float trebleShimmer = uTrebleLevel * sin(uTime * 12.0 + uv.x * 20.0) * 0.1;
    glow *= pulse + trebleShimmer;

    glow *= uIntensity;

    float innerFade = smoothstep(0.0, 0.5, glow);
    vec3 color = mix(uInnerColor, uEdgeColor, innerFade);

    float coreBright = pow(glow, 1.5);
    color *= 0.6 + coreBright * 0.8;

    float whiteCore = pow(glow, 4.0) * 0.35;
    color += vec3(whiteCore);

    float centerDist = length((uv - 0.5) * 2.0);
    float centerDark = smoothstep(0.3, 1.2, centerDist);
    float centerBrightness = mix(0.015, 0.0, centerDark * (1.0 - glow));
    vec3 bgColor = uEdgeColor * 0.02 + vec3(centerBrightness);

    color = max(color, bgColor);

    float alpha = clamp(glow * 1.5 + 0.02, 0.0, 1.0);

    fragColor = vec4(color, alpha);
}
