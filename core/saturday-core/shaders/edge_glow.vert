#version 330 core

layout(location = 0) in vec2 aPosition;
layout(location = 1) in vec2 aTexCoord;

out vec2 vTexCoord;
out vec2 vPosition;

void main() {
    vTexCoord = aTexCoord;
    vPosition = aPosition;
    gl_Position = vec4(aPosition, 0.0, 1.0);
}
