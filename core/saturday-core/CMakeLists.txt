cmake_minimum_required(VERSION 3.16)
project(SATURDAY VERSION 2.0.0 LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 20)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

find_package(OpenGL REQUIRED)

set(GLFW_ROOT "${CMAKE_CURRENT_SOURCE_DIR}/third_party/glfw/glfw-3.4.bin.WIN64")
set(GLFW_INCLUDE_DIR "${GLFW_ROOT}/include")
set(GLFW_LIBRARY "${GLFW_ROOT}/lib-vc2022/glfw3.lib")

set(SOURCES
    src/main.cpp
    src/core/orbitalcore.cpp
    src/core/logger.cpp
    src/rendering/renderer.cpp
    src/rendering/shader.cpp
    src/rendering/mesh.cpp
    src/rendering/postprocess.cpp
    src/audio/audioengine.cpp
    src/networking/websocketclient.cpp
    src/networking/serialization.cpp
    src/state/statemanager.cpp
    src/state/aisstate.cpp
)

add_executable(SATURDAY ${SOURCES})

target_include_directories(SATURDAY PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${GLFW_INCLUDE_DIR}
)

target_link_libraries(SATURDAY PRIVATE
    ${GLFW_LIBRARY}
    OpenGL::GL
)

if(WIN32)
    target_link_libraries(SATURDAY PRIVATE
        winmm.lib
        ws2_32.lib
        opengl32.lib
    )
endif()

target_compile_options(SATURDAY PRIVATE /W3 /utf-8)

set_target_properties(SATURDAY PROPERTIES
    RUNTIME_OUTPUT_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}/bin
    OUTPUT_NAME "SATURDAY"
    VS_DEBUGGER_WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
)

message(STATUS "SATURDAY Build System")
message(STATUS "  GLFW: ${GLFW_LIBRARY}")
message(STATUS "  Sources: ${CMAKE_SOURCE_DIR}/src")
message(STATUS "  Output: ${CMAKE_CURRENT_SOURCE_DIR}/bin/SATURDAY.exe")
