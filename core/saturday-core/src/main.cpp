#ifndef NOMINMAX
#define NOMINMAX
#endif
#include <GLFW/glfw3.h>
#include <cmath>
#include <vector>
#include <string>
#include <iostream>
#include <chrono>
#include <thread>
#include <algorithm>
#include <atomic>
#include <csignal>
#include <cstring>
#include <fstream>
#include <sstream>
#include <functional>
#include <mutex>
#include <array>

#include "core/logger.h"
#include "core/gl_loader.h"
#include "core/orbitalcore.h"
#include "audio/audioengine.h"
#include "state/aisstate.h"
#include "state/statemanager.h"
#include "rendering/shader.h"
#include "rendering/mesh.h"

#ifdef _WIN32
    #define WIN32_LEAN_AND_MEAN
    #include <windows.h>
    #include <mmsystem.h>
    #pragma comment(lib, "opengl32.lib")
    #pragma comment(lib, "glfw3.lib")
    #pragma comment(lib, "winmm.lib")
#endif

namespace {
    std::atomic<bool> g_running{true};
    void signal_handler(int) { g_running.store(false); }
}

static float smooth_step(float edge0, float edge1, float x) {
    float t = std::clamp((x - edge0) / (edge1 - edge0), 0.0f, 1.0f);
    return t * t * (3.0f - 2.0f * t);
}

static saturday::Color3 state_color(saturday::AIState s) {
    switch (s) {
        case saturday::AIState::Idle:      return saturday::Color3(1.0f, 0.7f, 0.0f);
        case saturday::AIState::Listening: return saturday::Color3(0.3f, 0.5f, 1.0f);
        case saturday::AIState::Speaking:  return saturday::Color3(1.0f, 0.85f, 0.0f);
        case saturday::AIState::Secure:    return saturday::Color3(0.6f, 0.2f, 0.8f);
        case saturday::AIState::Transfer:  return saturday::Color3(0.0f, 1.0f, 1.0f);
    }
    return saturday::Color3(1.0f, 0.7f, 0.0f);
}

#ifdef _WIN32
struct WinAudioCapture {
    WAVEFORMATEX format{};
    HWAVEIN device = nullptr;
    WAVEHDR headers[4]{};
    char buffers[4][4096]{};
    std::atomic<bool> capturing{false};
    float current_level = 0.0f;
    std::mutex mutex;

    bool initialize(int sample_rate = 44100) {
        format.wFormatTag = WAVE_FORMAT_PCM;
        format.nChannels = 1;
        format.wBitsPerSample = 16;
        format.nSamplesPerSec = sample_rate;
        format.nBlockAlign = 2;
        format.nAvgBytesPerSec = sample_rate * 2;

        MMRESULT result = waveInOpen(&device, WAVE_MAPPER, &format, 0, 0, CALLBACK_NULL);
        if (result != MMSYSERR_NOERROR) {
            SATURDAY_WARN("Audio", "No audio input device available - running without audio");
            device = nullptr;
            return false;
        }

        for (int i = 0; i < 4; i++) {
            headers[i].lpData = buffers[i];
            headers[i].dwBufferLength = 4096;
            waveInPrepareHeader(device, &headers[i], sizeof(WAVEHDR));
            waveInAddBuffer(device, &headers[i], sizeof(WAVEHDR));
        }

        SATURDAY_INFO("Audio", "Audio capture initialized (44100Hz, 16-bit mono)");
        return true;
    }

    void start() {
        if (!device) return;
        capturing.store(true);
        waveInStart(device);

        std::thread([this]() {
            while (capturing.load()) {
                for (int i = 0; i < 4; i++) {
                    if (headers[i].dwFlags & WHDR_DONE) {
                        process_buffer(headers[i].lpData, headers[i].dwBytesRecorded);
                        waveInUnprepareHeader(device, &headers[i], sizeof(WAVEHDR));
                        waveInPrepareHeader(device, &headers[i], sizeof(WAVEHDR));
                        waveInAddBuffer(device, &headers[i], sizeof(WAVEHDR));
                    }
                }
                std::this_thread::sleep_for(std::chrono::milliseconds(10));
            }
        }).detach();
    }

    void process_buffer(char* data, DWORD length) {
        int16_t* samples = reinterpret_cast<int16_t*>(data);
        int count = static_cast<int>(length / sizeof(int16_t));
        if (count <= 0) return;

        float sum = 0.0f;
        for (int i = 0; i < count; i++) {
            float s = samples[i] / 32768.0f;
            sum += s * s;
        }
        float rms = std::sqrt(sum / count);
        std::lock_guard<std::mutex> lock(mutex);
        current_level = current_level * 0.7f + rms * 0.3f;
    }

    float get_level() {
        std::lock_guard<std::mutex> lock(mutex);
        return current_level;
    }

    void stop() {
        capturing.store(false);
        if (device) {
            waveInStop(device);
            for (int i = 0; i < 4; i++) {
                waveInUnprepareHeader(device, &headers[i], sizeof(WAVEHDR));
            }
            waveInClose(device);
            device = nullptr;
        }
    }
};
#else
struct WinAudioCapture {
    bool initialize(int = 0) { return false; }
    void start() {}
    void stop() {}
    float get_level() { return 0.0f; }
};
#endif

struct EdgeGlowRenderer {
    GLuint program = 0;
    GLuint vao = 0;
    GLuint vbo = 0;
    GLuint ebo = 0;
    GLint loc_time = -1;
    GLint loc_resolution = -1;
    GLint loc_edge_color = -1;
    GLint loc_inner_color = -1;
    GLint loc_glow_width = -1;
    GLint loc_audio_level = -1;
    GLint loc_bass_level = -1;
    GLint loc_treble_level = -1;
    GLint loc_pulse_phase = -1;
    GLint loc_intensity = -1;

    bool initialize() {
        const char* vert_src = R"(
            #version 330 core
            layout(location = 0) in vec2 aPosition;
            layout(location = 1) in vec2 aTexCoord;
            out vec2 vTexCoord;
            void main() {
                vTexCoord = aTexCoord;
                gl_Position = vec4(aPosition, 0.0, 1.0);
            }
        )";

        const char* frag_src = R"(
            #version 330 core
            in vec2 vTexCoord;
            out vec4 fragColor;

            uniform float uTime;
            uniform vec2 uResolution;
            uniform vec3 uEdgeColor;
            uniform vec3 uInnerColor;
            uniform float uGlowWidth;
            uniform float uAudioLevel;
            uniform float uBassLevel;
            uniform float uTrebleLevel;
            uniform float uPulsePhase;
            uniform float uIntensity;

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

                float glowL = exp(-max(edgeL, 0.0) / breathWidth);
                float glowR = exp(-max(edgeR, 0.0) / breathWidth);
                float glowB = exp(-max(edgeB, 0.0) / breathWidth);
                float glowT = exp(-max(edgeT, 0.0) / breathWidth);

                float edgeGlow = max(max(glowL, glowR), max(glowB, glowT));

                float cd1 = length(vec2(uv.x, uv.y));
                float cd2 = length(vec2(1.0 - uv.x, uv.y));
                float cd3 = length(vec2(uv.x, 1.0 - uv.y));
                float cd4 = length(vec2(1.0 - uv.x, 1.0 - uv.y));
                float cDist = min(min(cd1, cd2), min(cd3, cd4));
                float cornerGlow = exp(-cDist / (breathWidth * 1.5));

                float glow = max(edgeGlow, cornerGlow * 1.2);

                float n1 = fbm(uv * 3.0 + uTime * 0.15);
                float n2 = fbm(uv * 8.0 - uTime * 0.3);
                glow += n1 * 0.06 * glow;
                glow += n2 * 0.03 * edgeGlow;

                float pulse = sin(uPulsePhase) * 0.15 + 0.85;
                float shimmer = uTrebleLevel * sin(uTime * 12.0 + uv.x * 20.0) * 0.08;
                glow *= pulse + shimmer;
                glow *= uIntensity;

                float innerFade = smoothstep(0.0, 0.5, glow);
                vec3 color = mix(uInnerColor * 0.15, uEdgeColor, innerFade);

                float coreBright = pow(glow, 1.5);
                color *= 0.5 + coreBright * 0.8;

                float whiteCore = pow(glow, 4.0) * 0.3;
                color += vec3(whiteCore);

                vec3 bg = uEdgeColor * 0.008;
                color = max(color, bg);

                fragColor = vec4(color, clamp(glow * 1.5 + 0.01, 0.0, 1.0));
            }
        )";

        GLuint vs = compile_shader(vert_src, GL_VERTEX_SHADER);
        GLuint fs = compile_shader(frag_src, GL_FRAGMENT_SHADER);
        if (!vs || !fs) {
            SATURDAY_ERROR("EdgeGlow", "Failed to compile shaders");
            return false;
        }

        program = saturday_glCreateProgram();
        saturday_glAttachShader(program, vs);
        saturday_glAttachShader(program, fs);
        saturday_glLinkProgram(program);

        GLint ok = 0;
        saturday_glGetProgramiv(program, GL_LINK_STATUS, &ok);
        if (!ok) {
            char log[512];
            saturday_glGetProgramInfoLog(program, 512, nullptr, log);
            SATURDAY_ERROR("EdgeGlow", std::string("Link failed: ") + log);
            return false;
        }

        saturday_glDeleteShader(vs);
        saturday_glDeleteShader(fs);

        loc_time = saturday_glGetUniformLocation(program, "uTime");
        loc_resolution = saturday_glGetUniformLocation(program, "uResolution");
        loc_edge_color = saturday_glGetUniformLocation(program, "uEdgeColor");
        loc_inner_color = saturday_glGetUniformLocation(program, "uInnerColor");
        loc_glow_width = saturday_glGetUniformLocation(program, "uGlowWidth");
        loc_audio_level = saturday_glGetUniformLocation(program, "uAudioLevel");
        loc_bass_level = saturday_glGetUniformLocation(program, "uBassLevel");
        loc_treble_level = saturday_glGetUniformLocation(program, "uTrebleLevel");
        loc_pulse_phase = saturday_glGetUniformLocation(program, "uPulsePhase");
        loc_intensity = saturday_glGetUniformLocation(program, "uIntensity");

        float quad[] = {
            -1.f, -1.f,  0.f, 0.f,
             1.f, -1.f,  1.f, 0.f,
             1.f,  1.f,  1.f, 1.f,
            -1.f,  1.f,  0.f, 1.f,
        };
        uint32_t indices[] = { 0, 1, 2, 0, 2, 3 };

        saturday_glGenVertexArrays(1, &vao);
        saturday_glGenBuffers(1, &vbo);
        saturday_glGenBuffers(1, &ebo);

        saturday_glBindVertexArray(vao);
        saturday_glBindBuffer(GL_ARRAY_BUFFER, vbo);
        saturday_glBufferData(GL_ARRAY_BUFFER, sizeof(quad), quad, GL_STATIC_DRAW);
        saturday_glBindBuffer(GL_ELEMENT_ARRAY_BUFFER, ebo);
        saturday_glBufferData(GL_ELEMENT_ARRAY_BUFFER, sizeof(indices), indices, GL_STATIC_DRAW);

        saturday_glEnableVertexAttribArray(0);
        saturday_glVertexAttribPointer(0, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)0);
        saturday_glEnableVertexAttribArray(1);
        saturday_glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 4 * sizeof(float), (void*)(2 * sizeof(float)));

        saturday_glBindVertexArray(0);

        SATURDAY_INFO("EdgeGlow", "Edge glow renderer initialized");
        return true;
    }

    void render(float time, float audio, float bass, float treble, float pulse_phase,
                const float* edge_color, const float* inner_color,
                float width, float intensity, float w, float h) {
        saturday_glUseProgram(program);
        saturday_glUniform1f(loc_time, time);
        saturday_glUniform2f(loc_resolution, w, h);
        saturday_glUniform3fv(loc_edge_color, 1, edge_color);
        saturday_glUniform3fv(loc_inner_color, 1, inner_color);
        saturday_glUniform1f(loc_glow_width, width);
        saturday_glUniform1f(loc_audio_level, audio);
        saturday_glUniform1f(loc_bass_level, bass);
        saturday_glUniform1f(loc_treble_level, treble);
        saturday_glUniform1f(loc_pulse_phase, pulse_phase);
        saturday_glUniform1f(loc_intensity, intensity);

        saturday_glBindVertexArray(vao);
        saturday_glDrawElements(GL_TRIANGLES, 6, GL_UNSIGNED_INT, 0);
        saturday_glBindVertexArray(0);

        saturday_glUseProgram(0);
    }

private:
    GLuint compile_shader(const char* src, GLenum type) {
        GLuint s = saturday_glCreateShader(type);
        saturday_glShaderSource(s, 1, &src, nullptr);
        saturday_glCompileShader(s);
        GLint ok = 0;
        saturday_glGetShaderiv(s, GL_COMPILE_STATUS, &ok);
        if (!ok) {
            char log[512];
            saturday_glGetShaderInfoLog(s, 512, nullptr, log);
            SATURDAY_ERROR("EdgeGlow", std::string("Shader compile failed: ") + log);
            saturday_glDeleteShader(s);
            return 0;
        }
        return s;
    }
};

struct OrbitalRenderer {
    saturday::Shader core_shader;
    saturday::Mesh sphere_mesh;
    saturday::Mesh ring_mesh1;
    saturday::Mesh ring_mesh2;
    saturday::Mesh particle_mesh;
    GLuint sphere_vao = 0;
    GLuint sphere_vbo = 0;
    bool initialized = false;

    bool initialize() {
        sphere_mesh = saturday::Mesh::create_sphere(0.35f, 48, 24);
        ring_mesh1 = saturday::Mesh::create_torus(0.55f, 0.012f, 64, 8);
        ring_mesh2 = saturday::Mesh::create_torus(0.72f, 0.008f, 64, 8);

        initialized = true;
        SATURDAY_INFO("Orbital", "Orbital core renderer initialized");
        return true;
    }

    void render(float time, float audio_level, float bass,
                const float* core_color, float pulse_speed, float rotation_speed) {
        if (!initialized) return;

        float pulse = 0.35f + 0.05f * std::sin(time * pulse_speed * 2.0f)
                      + bass * 0.08f;
        float rot = time * rotation_speed;

        glEnable(GL_BLEND);
        glBlendFunc(GL_SRC_ALPHA, GL_ONE);

        glPushMatrix();
        glRotatef(rot * 57.2958f, 0.0f, 0.0f, 1.0f);

        float cr = core_color[0], cg = core_color[1], cb = core_color[2];

        int segments = 120;
        glBegin(GL_TRIANGLE_STRIP);
        for (int i = 0; i <= segments; ++i) {
            float angle = 6.28318f * i / segments;
            float c = std::cos(angle);
            float s = std::sin(angle);
            float inner = pulse * 0.6f;
            float outer = pulse * 1.2f + bass * 0.15f;
            glColor4f(cr, cg, cb, 0.55f);
            glVertex2f(inner * c, inner * s);
            glColor4f(cr * 0.6f, cg * 0.6f, cb * 0.6f, 0.08f);
            glVertex2f(outer * c, outer * s);
        }
        glEnd();

        float ring_pulse1 = pulse + 0.02f * std::sin(time * 3.0f);
        draw_ring(0.55f * ring_pulse1 * 2.0f, 0.008f, 140, cr, cg, cb, 0.35f + bass * 0.15f);

        float ring_pulse2 = pulse + 0.015f * std::cos(time * 2.5f);
        draw_ring(0.72f * ring_pulse2 * 2.0f, 0.005f, 140, cr, cg, cb, 0.22f + audio_level * 0.1f);

        draw_core_spiral(time, pulse * 1.8f, cr, cg, cb);
        draw_radials(time * 0.8f, pulse * 1.5f, cr, cg, cb);
        draw_orbiting_fragments(time, 0.55f, cr, cg, cb);

        glPopMatrix();

        glBlendFunc(GL_SRC_ALPHA, GL_ONE_MINUS_SRC_ALPHA);
    }

    void shutdown() {
        initialized = false;
    }

private:
    void draw_ring(float radius, float thickness, int segments,
                   float cr, float cg, float cb, float alpha) {
        float inner = radius - thickness;
        float outer = radius + thickness;
        glBegin(GL_TRIANGLE_STRIP);
        for (int i = 0; i <= segments; ++i) {
            float angle = 6.28318f * i / segments;
            float c = std::cos(angle);
            float s = std::sin(angle);
            glColor4f(cr, cg, cb, alpha);
            glVertex2f(inner * c, inner * s);
            glColor4f(cr, cg, cb, alpha * 0.3f);
            glVertex2f(outer * c, outer * s);
        }
        glEnd();
    }

    void draw_core_spiral(float time, float radius, float cr, float cg, float cb) {
        glBegin(GL_LINE_STRIP);
        int steps = 200;
        for (int i = 0; i <= steps; ++i) {
            float t = static_cast<float>(i) / steps;
            float a = 6.0f * 3.14159f * t + time * 1.2f;
            float r = radius * (0.05f + 0.95f * t);
            float alpha = 0.65f * (1.0f - t * 0.7f);
            glColor4f(cr, cg * 0.9f, cb * 0.5f, alpha);
            glVertex2f(r * std::cos(a), r * std::sin(a));
        }
        glEnd();
    }

    void draw_radials(float time, float radius, float cr, float cg, float cb) {
        int rays = 80;
        glBegin(GL_LINES);
        for (int i = 0; i < rays; ++i) {
            float baseAngle = 6.28318f * i / rays;
            float hash_val = std::fmod(std::sin(static_cast<float>(i) * 13.37f) * 43758.5453f, 1.0f);
            float jitter = (hash_val - 0.5f) * 0.08f;
            float angle = baseAngle + jitter;
            float hash2 = std::fmod(std::sin(static_cast<float>(i) * 3.1f + time * 2.0f) * 43758.5453f, 1.0f);
            float len = 0.15f + 0.35f * hash2;
            float hash3 = std::fmod(std::sin(static_cast<float>(i) * 7.77f + time * 1.3f) * 43758.5453f, 1.0f);
            float fade = 0.25f + 0.55f * hash3;
            glColor4f(cr, cg, cb, 0.06f * fade);
            glVertex2f(0.0f, 0.0f);
            glColor4f(cr, cg, cb, 0.0f);
            glVertex2f(len * std::cos(angle), len * std::sin(angle));
        }
        glEnd();
    }

    void draw_orbiting_fragments(float time, float radius, float cr, float cg, float cb) {
        int fragments = 60;
        glPointSize(2.5f);
        glBegin(GL_POINTS);
        for (int i = 0; i < fragments; ++i) {
            float hash_val = std::fmod(std::sin(static_cast<float>(i) * 12.989f) * 43758.5453f, 1.0f);
            float angle = 6.28318f * hash_val + time * (0.5f + 0.15f * (i % 3));
            float r = radius * (0.7f + 0.3f * hash_val);
            float flicker = 0.5f + 0.5f * std::sin(time * 8.0f + static_cast<float>(i));
            glColor4f(cr, cg * 0.85f, cb * 0.4f, 0.35f * flicker);
            glVertex2f(r * std::cos(angle), r * std::sin(angle));
        }
        glEnd();
    }
};

struct AppState {
    saturday::AIState current = saturday::AIState::Idle;
    saturday::AIState target = saturday::AIState::Idle;
    saturday::Color3 current_color = state_color(saturday::AIState::Idle);
    saturday::Color3 target_color = state_color(saturday::AIState::Idle);
    float transition_t = 1.0f;
    float transition_speed = 2.0f;
    float audio_level = 0.0f;
    float bass = 0.0f;
    float treble = 0.0f;
    float pulse_phase = 0.0f;
    float glow_width = 0.045f;

    void set_state(saturday::AIState s) {
        if (s == target) return;
        current = target;
        target = s;
        current_color = target_color;
        target_color = state_color(s);
        transition_t = 0.0f;
    }

    void update(float dt, float audio, float bass_val, float treble_val) {
        audio_level = audio_level * 0.85f + audio * 0.15f;
        bass = bass * 0.85f + bass_val * 0.15f;
        treble = treble * 0.85f + treble_val * 0.15f;
        pulse_phase += dt * 1.5f;

        if (transition_t < 1.0f) {
            transition_t = std::min(transition_t + dt * transition_speed, 1.0f);
            float t = transition_t * transition_t * (3.0f - 2.0f * transition_t);
            current_color.r = current_color.r + (target_color.r - current_color.r) * t * dt * 3.0f;
            current_color.g = current_color.g + (target_color.g - current_color.g) * t * dt * 3.0f;
            current_color.b = current_color.b + (target_color.b - current_color.b) * t * dt * 3.0f;
        }
    }
};

void print_banner() {
    std::cout << "\n";
    std::cout << "  ===============================================\n";
    std::cout << "     S A T U R D A Y   A I   O S   v2.0\n";
    std::cout << "     Unified Visual Core with Edge Lighting\n";
    std::cout << "  ===============================================\n";
    std::cout << "\n";
    std::cout << "  Controls:\n";
    std::cout << "    [1] Idle       [2] Listening   [3] Speaking\n";
    std::cout << "    [4] Secure     [5] Transfer    [ESC] Quit\n";
    std::cout << "\n";
}

int main() {
    print_banner();
    SATURDAY_INFO("Core", "SATURDAY Unified Core starting...");

    std::signal(SIGINT, signal_handler);
    std::signal(SIGTERM, signal_handler);

    saturday_load_gl_functions();

    if (!glfwInit()) {
        SATURDAY_ERROR("Core", "Failed to initialize GLFW");
        return 1;
    }

    glfwWindowHint(GLFW_DECORATED, GLFW_FALSE);
    glfwWindowHint(GLFW_RESIZABLE, GLFW_FALSE);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MAJOR, 3);
    glfwWindowHint(GLFW_CONTEXT_VERSION_MINOR, 3);
    glfwWindowHint(GLFW_OPENGL_PROFILE, GLFW_OPENGL_CORE_PROFILE);
    glfwWindowHint(GLFW_SAMPLES, 4);

    GLFWmonitor* monitor = glfwGetPrimaryMonitor();
    const GLFWvidmode* mode = glfwGetVideoMode(monitor);
    int screen_w = mode->width;
    int screen_h = mode->height;

    GLFWwindow* window = glfwCreateWindow(screen_w, screen_h, "SATURDAY AI OS", monitor, nullptr);
    if (!window) {
        SATURDAY_ERROR("Core", "Failed to create fullscreen window, trying windowed");
        glfwWindowHint(GLFW_DECORATED, GLFW_TRUE);
        screen_w = 1280;
        screen_h = 720;
        window = glfwCreateWindow(screen_w, screen_h, "SATURDAY AI OS", nullptr, nullptr);
        if (!window) {
            SATURDAY_ERROR("Core", "Failed to create window");
            glfwTerminate();
            return 1;
        }
    }

    glfwMakeContextCurrent(window);
    glfwSwapInterval(1);

    saturday_load_gl_functions();

    SATURDAY_INFO("Core", "OpenGL Version: " + std::string((const char*)glGetString(GL_VERSION)));
    SATURDAY_INFO("Core", "GPU: " + std::string((const char*)glGetString(GL_RENDERER)));

    EdgeGlowRenderer edge_glow;
    OrbitalRenderer orbital;

    bool edge_ok = edge_glow.initialize();
    bool orbital_ok = orbital.initialize();

    WinAudioCapture audio;
    bool audio_ok = audio.initialize(44100);
    if (audio_ok) audio.start();

    AppState state;

    SATURDAY_INFO("Core", "All subsystems initialized. Running startup sequence...");

    // ==================== STARTUP SEQUENCE ====================
    auto startup_start = std::chrono::steady_clock::now();
    float startup_elapsed = 0.0f;
    const float STARTUP_DURATION = 4.0f; // seconds
    
    SATURDAY_INFO("Core", "Initiating SATURDAY AI OS startup sequence...");
    
    // Phase 1: Core initialization glow (0-1s)
    float phase1_end = 1.0f;
    while (startup_elapsed < phase1_end && g_running.load()) {
        auto now = std::chrono::steady_clock::now();
        float dt = std::chrono::duration<float>(now - startup_start).count();
        startup_elapsed = dt;
        
        glfwPollEvents();
        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) g_running.store(false);
        
        glViewport(0, 0, screen_w, screen_h);
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        
        float t = startup_elapsed / phase1_end;
        float pulse = 0.5f + 0.5f * std::sin(startup_elapsed * 8.0f);
        float intensity = smooth_step(0.0f, phase1_end, startup_elapsed) * pulse;
        
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        
        if (edge_ok) {
            glDisable(GL_DEPTH_TEST);
            saturday::Color3 warm_gold(1.0f, 0.7f, 0.0f);
            edge_glow.render(
                startup_elapsed,
                intensity, 0.3f, 0.1f,
                startup_elapsed * 2.0f,
                &warm_gold.r, &warm_gold.r,
                0.045f + intensity * 0.02f,
                1.0f - t * 0.3f,
                static_cast<float>(screen_w),
                static_cast<float>(screen_h)
            );
        }
        
        // Draw "INITIALIZING CORE..." text using points
        glPointSize(3.0f);
        glColor4f(1.0f, 0.7f, 0.0f, 0.8f);
        glBegin(GL_POINTS);
        for (int i = 0; i < 200; ++i) {
            float angle = (i / 200.0f) * 6.28318f + startup_elapsed * 0.5f;
            float r = 0.15f + intensity * 0.1f;
            glVertex2f(r * std::cos(angle), r * std::sin(angle));
        }
        glEnd();
        
        glfwSwapBuffers(window);
        
        // Small sleep to not max CPU
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    
    // Phase 2: Subsystem boot sequence (1-2.5s)
    SATURDAY_INFO("Core", "Booting subsystems...");
    float phase2_end = 2.5f;
    while (startup_elapsed < phase2_end && g_running.load()) {
        auto now = std::chrono::steady_clock::now();
        float dt = std::chrono::duration<float>(now - startup_start).count();
        startup_elapsed = dt;
        
        glfwPollEvents();
        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) g_running.store(false);
        
        glViewport(0, 0, screen_w, screen_h);
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        
        float phase2_t = (startup_elapsed - phase1_end) / (phase2_end - phase1_end);
        
        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        
        if (edge_ok) {
            glDisable(GL_DEPTH_TEST);
            saturday::Color3 cyan(0.3f, 1.0f, 1.0f);
            edge_glow.render(
                startup_elapsed,
                0.4f + phase2_t * 0.3f,
                0.5f + phase2_t * 0.2f,
                0.2f,
                startup_elapsed * 3.0f,
                &cyan.r, &cyan.r,
                0.05f,
                0.8f + phase2_t * 0.2f,
                static_cast<float>(screen_w),
                static_cast<float>(screen_h)
            );
        }
        
        if (orbital_ok) {
            orbital.render(
                startup_elapsed,
                0.4f + phase2_t * 0.3f,
                0.5f + phase2_t * 0.2f,
                &cyan.r,
                1.0f,
                0.3f + phase2_t * 0.3f
            );
        }
        
        // Draw subsystem status rings
        static const char* subsystems[] = {
            "EVENT BUS", "CONFIG", "STATE", "IDENTITY", "VOICE", 
            "VISION", "BRAIN", "ML CORE", "GOVERNANCE", "HOMEBOT"
        };
        int num_sub = 10;
        for (int i = 0; i < num_sub; ++i) {
            float angle = (i / (float)num_sub) * 6.28318f + startup_elapsed * 0.3f;
            float r = 0.3f + 0.15f * std::sin(startup_elapsed * 2.0f + i * 0.6f);
            float alpha = 0.3f + 0.7f * std::min(1.0f, phase2_t * num_sub / (i + 1));
            glColor4f(0.3f, 1.0f, 1.0f, alpha);
            glPointSize(4.0f);
            glBegin(GL_POINTS);
            glVertex2f(r * std::cos(angle), r * std::sin(angle));
            glEnd();
        }
        
        glfwSwapBuffers(window);
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    
    // Phase 3: AI Core activation (2.5-4s)
    SATURDAY_INFO("Core", "Activating AI Core...");
    float phase3_end = 4.0f;
    while (startup_elapsed < phase3_end && g_running.load()) {
        auto now = std::chrono::steady_clock::now();
        float dt = std::chrono::duration<float>(now - startup_start).count();
        startup_elapsed = dt;
        
        glfwPollEvents();
        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS) g_running.store(false);
        
        glViewport(0, 0, screen_w, screen_h);
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);
        
        float phase3_t = (startup_elapsed - phase2_end) / (phase3_end - phase2_end);
        
        glMatrixMode(GL_PROJJECTION);
        glLoadIdentity();
        glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();
        
        if (edge_ok) {
            glDisable(GL_DEPTH_TEST);
            saturday::Color3 gold(1.0f, 0.85f, 0.0f);
            edge_glow.render(
                startup_elapsed,
                0.6f + phase3_t * 0.4f,
                0.7f + phase3_t * 0.3f,
                0.3f + phase3_t * 0.2f,
                startup_elapsed * 4.0f,
                &gold.r, &gold.r,
                0.04f + phase3_t * 0.03f,
                1.0f,
                static_cast<float>(screen_w),
                static_cast<float>(screen_h)
            );
        }
        
        if (orbital_ok) {
            orbital.render(
                startup_elapsed,
                0.6f + phase3_t * 0.4f,
                0.7f + phase3_t * 0.3f,
                &gold.r,
                1.0f + phase3_t * 0.5f,
                0.4f + phase3_t * 0.3f
            );
        }
        
        // Expanding activation wave
        for (int ring = 0; ring < 5; ++ring) {
            float wave_t = phase3_t * 5.0f + ring * 0.2f;
            float r = 0.1f + wave_t * 0.8f;
            float alpha = 0.8f * (1.0f - wave_t);
            if (alpha > 0) {
                glColor4f(1.0f, 0.85f, 0.0f, alpha);
                glLineWidth(2.0f + ring * 0.5f);
                glBegin(GL_LINE_LOOP);
                for (int i = 0; i < 100; ++i) {
                    float a = (i / 100.0f) * 6.28318f;
                    glVertex2f(r * std::cos(a), r * std::sin(a));
                }
                glEnd();
            }
        }
        
        glfwSwapBuffers(window);
        std::this_thread::sleep_for(std::chrono::milliseconds(2));
    }
    
    SATURDAY_INFO("Core", "Startup sequence complete. SATURDAY AI OS online.");
    state.set_state(saturday::AIState::Idle);
    
    // ==================== END STARTUP SEQUENCE ====================
    
    auto last_time = std::chrono::steady_clock::now();
    float elapsed = 0.0f;
    int frame_count = 0;

    while (!glfwWindowShouldClose(window) && g_running.load()) {
        auto now = std::chrono::steady_clock::now();
        float dt = std::chrono::duration<float>(now - last_time).count();
        last_time = now;
        elapsed += dt;
        frame_count++;

        if (dt > 0.0f && frame_count % 120 == 0) {
            float fps = 1.0f / dt;
            std::string title = "SATURDAY AI OS | FPS: " + std::to_string(static_cast<int>(fps))
                              + " | State: ";
            switch (state.target) {
                case saturday::AIState::Idle:      title += "Idle"; break;
                case saturday::AIState::Listening: title += "Listening"; break;
                case saturday::AIState::Speaking:  title += "Speaking"; break;
                case saturday::AIState::Secure:    title += "Secure"; break;
                case saturday::AIState::Transfer:  title += "Transfer"; break;
            }
            glfwSetWindowTitle(window, title.c_str());
        }

        glfwPollEvents();

        if (glfwGetKey(window, GLFW_KEY_ESCAPE) == GLFW_PRESS)
            g_running.store(false);
        if (glfwGetKey(window, GLFW_KEY_1) == GLFW_PRESS) state.set_state(saturday::AIState::Idle);
        if (glfwGetKey(window, GLFW_KEY_2) == GLFW_PRESS) state.set_state(saturday::AIState::Listening);
        if (glfwGetKey(window, GLFW_KEY_3) == GLFW_PRESS) state.set_state(saturday::AIState::Speaking);
        if (glfwGetKey(window, GLFW_KEY_4) == GLFW_PRESS) state.set_state(saturday::AIState::Secure);
        if (glfwGetKey(window, GLFW_KEY_5) == GLFW_PRESS) state.set_state(saturday::AIState::Transfer);

        float raw_audio = audio.get_level();
        float sim_bass = raw_audio * 1.2f;
        float sim_treble = raw_audio * 0.8f + std::sin(elapsed * 5.0f) * 0.05f;
        state.update(dt, raw_audio, sim_bass, sim_treble);

        glViewport(0, 0, screen_w, screen_h);
        glClearColor(0.0f, 0.0f, 0.0f, 1.0f);
        glClear(GL_COLOR_BUFFER_BIT);

        glMatrixMode(GL_PROJECTION);
        glLoadIdentity();
        glOrtho(-1.0, 1.0, -1.0, 1.0, -1.0, 1.0);
        glMatrixMode(GL_MODELVIEW);
        glLoadIdentity();

        if (edge_ok) {
            glDisable(GL_DEPTH_TEST);
            edge_glow.render(
                elapsed,
                state.audio_level,
                state.bass,
                state.treble,
                state.pulse_phase,
                &state.current_color.r,
                &state.current_color.r,
                state.glow_width,
                1.0f,
                static_cast<float>(screen_w),
                static_cast<float>(screen_h)
            );
        }

        if (orbital_ok) {
            orbital.render(
                elapsed,
                state.audio_level,
                state.bass,
                &state.current_color.r,
                1.0f + state.bass * 2.0f,
                0.2f + state.audio_level * 0.3f
            );
        }

        glfwSwapBuffers(window);
    }

    SATURDAY_INFO("Core", "Shutting down...");

    audio.stop();
    orbital.shutdown();

    glfwDestroyWindow(window);
    glfwTerminate();

    SATURDAY_INFO("Core", "SATURDAY Unified Core shutdown complete");
    return 0;
}
