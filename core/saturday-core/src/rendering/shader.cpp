#include "shader.h"
#include "core/logger.h"
#include "core/gl_loader.h"
#include <fstream>
#include <sstream>
#include <iostream>
#include <algorithm>

namespace saturday {

Shader::Shader(const std::string& vertex_source, 
               const std::string& fragment_source,
               const std::string& geometry_source) {
    saturday_load_gl_functions();
    
    GLuint vertex = compile_shader(vertex_source, GL_VERTEX_SHADER);
    GLuint fragment = compile_shader(fragment_source, GL_FRAGMENT_SHADER);
    
    std::vector<GLuint> shaders;
    if (vertex) shaders.push_back(vertex);
    if (fragment) shaders.push_back(fragment);
    
    GLuint geometry = 0;
    if (!geometry_source.empty()) {
        geometry = compile_shader(geometry_source, GL_GEOMETRY_SHADER);
        if (geometry) shaders.push_back(geometry);
    }
    
    if (!shaders.empty()) {
        program_id_ = glCreateProgram();
        
        for (GLuint shader : shaders) {
            glAttachShader(program_id_, shader);
        }
        
        glLinkProgram(program_id_);
        
        GLint success;
        glGetProgramiv(program_id_, GL_LINK_STATUS, &success);
        if (!success) {
            char info_log[512];
            glGetProgramInfoLog(program_id_, 512, nullptr, info_log);
            SATURDAY_ERROR("Shader", "Shader program linking failed: " + std::string(info_log));
            glDeleteProgram(program_id_);
            program_id_ = 0;
        }
        
        for (GLuint shader : shaders) {
            glDeleteShader(shader);
        }
    }
}

Shader::~Shader() {
    if (program_id_ != 0) {
        glDeleteProgram(program_id_);
        program_id_ = 0;
    }
}

Shader::Shader(Shader&& other) noexcept 
    : program_id_(other.program_id_), uniform_cache_(std::move(other.uniform_cache_)) {
    other.program_id_ = 0;
}

Shader& Shader::operator=(Shader&& other) noexcept {
    if (this != &other) {
        if (program_id_ != 0) {
            glDeleteProgram(program_id_);
        }
        program_id_ = other.program_id_;
        uniform_cache_ = std::move(other.uniform_cache_);
        other.program_id_ = 0;
    }
    return *this;
}

void Shader::use() const {
    if (program_id_ != 0) {
        glUseProgram(program_id_);
    }
}

void Shader::unbind() {
    glUseProgram(0);
}

GLuint Shader::compile_shader(const std::string& source, GLenum type) {
    GLuint shader = glCreateShader(type);
    if (!shader) return 0;
    
    const char* src = source.c_str();
    glShaderSource(shader, 1, &src, nullptr);
    glCompileShader(shader);
    
    GLint success;
    glGetShaderiv(shader, GL_COMPILE_STATUS, &success);
    if (!success) {
        char info_log[512];
        glGetShaderInfoLog(shader, 512, nullptr, info_log);
        
        std::string shader_type = (type == GL_VERTEX_SHADER) ? "vertex" :
                                  (type == GL_FRAGMENT_SHADER) ? "fragment" : "geometry";
        SATURDAY_ERROR("Shader", "Shader compilation failed (" + shader_type + "): " + std::string(info_log));
        
        glDeleteShader(shader);
        return 0;
    }
    
    return shader;
}

GLint Shader::get_uniform_location(const std::string& name) {
    auto it = uniform_cache_.find(name);
    if (it != uniform_cache_.end()) {
        return it->second;
    }
    
    GLint location = glGetUniformLocation(program_id_, name.c_str());
    uniform_cache_[name] = location;
    return location;
}

void Shader::set_int(const std::string& name, int value) {
    glUniform1i(get_uniform_location(name), value);
}

void Shader::set_float(const std::string& name, float value) {
    glUniform1f(get_uniform_location(name), value);
}

void Shader::set_vec2(const std::string& name, float x, float y) {
    float values[2] = {x, y};
    glUniform2fv(get_uniform_location(name), 1, values);
}

void Shader::set_vec2(const std::string& name, const float* value) {
    glUniform2fv(get_uniform_location(name), 1, value);
}

void Shader::set_vec3(const std::string& name, float x, float y, float z) {
    float values[3] = {x, y, z};
    glUniform3fv(get_uniform_location(name), 1, values);
}

void Shader::set_vec3(const std::string& name, const float* value) {
    glUniform3fv(get_uniform_location(name), 1, value);
}

void Shader::set_vec4(const std::string& name, float x, float y, float z, float w) {
    float values[4] = {x, y, z, w};
    glUniform4fv(get_uniform_location(name), 1, values);
}

void Shader::set_vec4(const std::string& name, const float* value) {
    glUniform4fv(get_uniform_location(name), 1, value);
}

void Shader::set_mat3(const std::string& name, const float* value, bool transpose) {
    glUniformMatrix3fv(get_uniform_location(name), 1, transpose ? GL_TRUE : GL_FALSE, value);
}

void Shader::set_mat4(const std::string& name, const float* value, bool transpose) {
    glUniformMatrix4fv(get_uniform_location(name), 1, transpose ? GL_TRUE : GL_FALSE, value);
}

std::string ShaderManager::read_file(const std::string& path) {
    std::ifstream file(path);
    if (!file.is_open()) {
        SATURDAY_ERROR("ShaderManager", "Failed to open file: " + path);
        return "";
    }
    
    std::stringstream buffer;
    buffer << file.rdbuf();
    return buffer.str();
}

bool ShaderManager::load(const std::string& name,
                         const std::string& vertex_path,
                         const std::string& fragment_path,
                         const std::string& geometry_path) {
    std::string vertex_source = read_file(vertex_path);
    std::string fragment_source = read_file(fragment_path);
    std::string geometry_source = geometry_path.empty() ? "" : read_file(geometry_path);
    
    if (vertex_source.empty() || fragment_source.empty()) {
        SATURDAY_ERROR("ShaderManager", "Failed to load shader sources");
        return false;
    }
    
    return add_from_source(name, vertex_source, fragment_source, geometry_source);
}

bool ShaderManager::add_from_source(const std::string& name,
                                     const std::string& vertex_source,
                                     const std::string& fragment_source,
                                     const std::string& geometry_source) {
    try {
        Shader shader(vertex_source, fragment_source, geometry_source);
        if (shader.is_valid()) {
            shaders_[name] = std::move(shader);
            SATURDAY_INFO("ShaderManager", "Loaded shader: " + name);
            return true;
        }
    } catch (const std::exception& e) {
        SATURDAY_ERROR("ShaderManager", "Exception loading shader: " + std::string(e.what()));
    }
    return false;
}

Shader* ShaderManager::get(const std::string& name) {
    auto it = shaders_.find(name);
    if (it != shaders_.end()) {
        return &it->second;
    }
    return nullptr;
}

const Shader* ShaderManager::get(const std::string& name) const {
    auto it = shaders_.find(name);
    if (it != shaders_.end()) {
        return &it->second;
    }
    return nullptr;
}

bool ShaderManager::exists(const std::string& name) const {
    return shaders_.find(name) != shaders_.end();
}

void ShaderManager::remove(const std::string& name) {
    shaders_.erase(name);
}

void ShaderManager::clear() {
    shaders_.clear();
}

} // namespace saturday
