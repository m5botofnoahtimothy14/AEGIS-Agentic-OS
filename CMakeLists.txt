cmake_minimum_required(VERSION 3.12)

# Project name and version
project(SATURDAY_AI_OS VERSION 1.0.0 DESCRIPTION "Self-Aware Task Undertaking Robot Delegate for Autonomy and Yield")

# Define C++ standard
set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

# Find required packages
find_package(PkgConfig REQUIRED)
find_package(Threads REQUIRED)

# If building with Python bindings
find_package(Python3 COMPONENTS Interpreter Development REQUIRED)

# Add executable for the main application
add_executable(saturday_ai_os
    src/main.cpp
    src/core/ai_core.cpp
    src/core/task_manager.cpp
    src/core/thread_manager.cpp
    src/core/audio_processor.cpp
    src/core/nlp_processor.cpp
    src/core/vision_processor.cpp
    src/core/memory_manager.cpp
    src/utils/config_loader.cpp
    src/utils/logger.cpp
    src/utils/file_handler.cpp
    src/interfaces/cli_interface.cpp
    src/interfaces/web_interface.cpp
    src/interfaces/api_server.cpp
)

# Add library for core functionality
add_library(saturday_core
    src/core/ai_core.cpp
    src/core/task_manager.cpp
    src/core/thread_manager.cpp
    src/core/audio_processor.cpp
    src/core/nlp_processor.cpp
    src/core/vision_processor.cpp
    src/core/memory_manager.cpp
)

# Add library for utilities
add_library(saturday_utils
    src/utils/config_loader.cpp
    src/utils/logger.cpp
    src/utils/file_handler.cpp
)

# Add library for interfaces
add_library(saturday_interfaces
    src/interfaces/cli_interface.cpp
    src/interfaces/web_interface.cpp
    src/interfaces/api_server.cpp
)

# Link libraries to the main executable
target_link_libraries(saturday_ai_os
    saturday_core
    saturday_utils
    saturday_interfaces
    Threads::Threads
    ${CMAKE_DL_LIBS}
)

# Include directories
target_include_directories(saturday_ai_os PRIVATE
    ${CMAKE_CURRENT_SOURCE_DIR}/include
    ${CMAKE_CURRENT_SOURCE_DIR}/src
    ${CMAKE_CURRENT_SOURCE_DIR}/src/core
    ${CMAKE_CURRENT_SOURCE_DIR}/src/utils
    ${CMAKE_CURRENT_SOURCE_DIR}/src/interfaces
)

# Compiler-specific options
if(CMAKE_CXX_COMPILER_ID STREQUAL "GNU" OR CMAKE_CXX_COMPILER_ID STREQUAL "Clang")
    target_compile_options(saturday_ai_os PRIVATE -Wall -Wextra)
elseif(CMAKE_CXX_COMPILER_ID STREQUAL "MSVC")
    target_compile_options(saturday_ai_os PRIVATE /W4)
endif()

# Installation rules
install(TARGETS saturday_ai_os
    RUNTIME DESTINATION bin
    LIBRARY DESTINATION lib
    ARCHIVE DESTINATION lib
)

# Create a custom target to run the Python-based SATURDAY AI OS
add_custom_target(run_saturday
    COMMAND ${Python3_EXECUTABLE} -m core.main
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Running SATURDAY AI OS"
)

# Create a custom target for testing
add_custom_target(test_saturday
    COMMAND ${Python3_EXECUTABLE} -m pytest tests/
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Running SATURDAY AI OS tests"
)

# Create a custom target for verification
add_custom_target(verify_saturday
    COMMAND ${Python3_EXECUTABLE} ${CMAKE_CURRENT_SOURCE_DIR}/comprehensive_test.py
    WORKING_DIRECTORY ${CMAKE_CURRENT_SOURCE_DIR}
    COMMENT "Verifying SATURDAY AI OS"
)