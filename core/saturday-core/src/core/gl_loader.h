#pragma once

#ifdef _WIN32
    #ifndef NOMINMAX
    #define NOMINMAX
    #endif
    #include <windows.h>
    #include <GL/gl.h>

    typedef ptrdiff_t GLsizeiptr;
    typedef ptrdiff_t GLintptr;
    typedef char GLchar;

    #ifndef GL_VERTEX_SHADER
    #define GL_VERTEX_SHADER                  0x8B31
    #define GL_FRAGMENT_SHADER                0x8B30
    #define GL_COMPILE_STATUS                 0x8B81
    #define GL_LINK_STATUS                    0x8B82
    #define GL_INFO_LOG_LENGTH                0x8B84
    #define GL_ARRAY_BUFFER                   0x8892
    #define GL_ELEMENT_ARRAY_BUFFER           0x8893
    #define GL_STATIC_DRAW                    0x88E4
    #define GL_DYNAMIC_DRAW                   0x88E8
    #define GL_STREAM_DRAW                    0x88E0
    #define GL_FRAMEBUFFER                    0x8D40
    #define GL_READ_FRAMEBUFFER               0x8CA8
    #define GL_DRAW_FRAMEBUFFER               0x8CA9
    #define GL_RENDERBUFFER                   0x8D41
    #define GL_COLOR_ATTACHMENT0              0x8CE0
    #define GL_DEPTH_ATTACHMENT               0x8D00
    #define GL_STENCIL_ATTACHMENT             0x8D20
    #define GL_DEPTH_STENCIL_ATTACHMENT       0x821A
    #define GL_DEPTH24_STENCIL8               0x88F0
    #define GL_CLAMP_TO_EDGE                  0x812F
    #define GL_TEXTURE0                       0x84C0
    #define GL_ACTIVE_TEXTURE                 0x84E0
    #define GL_MULTISAMPLE                    0x809D
    #define GL_FUNC_ADD                       0x8006
    #define GL_DRAW_FRAMEBUFFER_BINDING       0x8CA6
    #define GL_READ_FRAMEBUFFER_BINDING       0x8CAA
    #define GL_DEPTH_STENCIL                  0x84F9
    #define GL_DEPTH_COMPONENT24              0x81A6
    #define GL_GEOMETRY_SHADER                0x8DD9
    #endif

    #ifndef APIENTRYP
    #define APIENTRYP __stdcall *
    #endif

    typedef void (APIENTRYP PFNGLGENVERTEXARRAYSPROC)(GLsizei, GLuint*);
    typedef void (APIENTRYP PFNGLDELETEVERTEXARRAYSPROC)(GLsizei, const GLuint*);
    typedef void (APIENTRYP PFNGLBINDVERTEXARRAYPROC)(GLuint);
    typedef void (APIENTRYP PFNGLGENBUFFERSPROC)(GLsizei, GLuint*);
    typedef void (APIENTRYP PFNGLDELETEBUFFERSPROC)(GLsizei, const GLuint*);
    typedef void (APIENTRYP PFNGLBINDBUFFERPROC)(GLenum, GLuint);
    typedef void (APIENTRYP PFNGLBUFFERDATAPROC)(GLenum, GLsizeiptr, const void*, GLenum);
    typedef void (APIENTRYP PFNGLBUFFERSUBDATAPROC)(GLenum, GLintptr, GLsizeiptr, const void*);
    typedef void (APIENTRYP PFNGLENABLEVERTEXATTRIBARRAYPROC)(GLuint);
    typedef void (APIENTRYP PFNGLDISABLEVERTEXATTRIBARRAYPROC)(GLuint);
    typedef void (APIENTRYP PFNGLVERTEXATTRIBPOINTERPROC)(GLuint, GLint, GLenum, GLboolean, GLsizei, const void*);
    typedef void (APIENTRYP PFNGLDRAWARRAYSPROC)(GLenum, GLint, GLsizei);
    typedef void (APIENTRYP PFNGLDRAWELEMENTSPROC)(GLenum, GLsizei, GLenum, const void*);
    typedef GLuint (APIENTRYP PFNGLCREATESHADERPROC)(GLenum);
    typedef void (APIENTRYP PFNGLDELETESHADERPROC)(GLuint);
    typedef void (APIENTRYP PFNGLSHADERSOURCEPROC)(GLuint, GLsizei, const GLchar* const*, const GLint*);
    typedef void (APIENTRYP PFNGLCOMPILESHADERPROC)(GLuint);
    typedef void (APIENTRYP PFNGLGETSHADERIVPROC)(GLuint, GLenum, GLint*);
    typedef void (APIENTRYP PFNGLGETSHADERINFOLOGPROC)(GLuint, GLsizei, GLsizei*, GLchar*);
    typedef GLuint (APIENTRYP PFNGLCREATEPROGRAMPROC)(void);
    typedef void (APIENTRYP PFNGLDELETEPROGRAMPROC)(GLuint);
    typedef void (APIENTRYP PFNGLATTACHSHADERPROC)(GLuint, GLuint);
    typedef void (APIENTRYP PFNGLDETACHSHADERPROC)(GLuint, GLuint);
    typedef void (APIENTRYP PFNGLLINKPROGRAMPROC)(GLuint);
    typedef void (APIENTRYP PFNGLVALIDATEPROGRAMPROC)(GLuint);
    typedef void (APIENTRYP PFNGLGETPROGRAMIVPROC)(GLuint, GLenum, GLint*);
    typedef void (APIENTRYP PFNGLGETPROGRAMINFOLOGPROC)(GLuint, GLsizei, GLsizei*, GLchar*);
    typedef void (APIENTRYP PFNGLUSEPROGRAMPROC)(GLuint);
    typedef GLint (APIENTRYP PFNGLGETUNIFORMLOCATIONPROC)(GLuint, const GLchar*);
    typedef void (APIENTRYP PFNGLUNIFORM1FPROC)(GLint, GLfloat);
    typedef void (APIENTRYP PFNGLUNIFORM2FPROC)(GLint, GLfloat, GLfloat);
    typedef void (APIENTRYP PFNGLUNIFORM3FPROC)(GLint, GLfloat, GLfloat, GLfloat);
    typedef void (APIENTRYP PFNGLUNIFORM4FPROC)(GLint, GLfloat, GLfloat, GLfloat, GLfloat);
    typedef void (APIENTRYP PFNGLUNIFORM1IPROC)(GLint, GLint);
    typedef void (APIENTRYP PFNGLUNIFORM2FVPROC)(GLint, GLsizei, const GLfloat*);
    typedef void (APIENTRYP PFNGLUNIFORM3FVPROC)(GLint, GLsizei, const GLfloat*);
    typedef void (APIENTRYP PFNGLUNIFORM4FVPROC)(GLint, GLsizei, const GLfloat*);
    typedef void (APIENTRYP PFNGLUNIFORMMATRIX3FVPROC)(GLint, GLsizei, GLboolean, const GLfloat*);
    typedef void (APIENTRYP PFNGLUNIFORMMATRIX4FVPROC)(GLint, GLsizei, GLboolean, const GLfloat*);
    typedef void (APIENTRYP PFNGLBINDATTRIBLOCATIONPROC)(GLuint, GLuint, const GLchar*);
    typedef void (APIENTRYP PFNGLGETACTIVEATTRIBPROC)(GLuint, GLuint, GLsizei, GLsizei*, GLint*, GLenum*, GLchar*);
    typedef void (APIENTRYP PFNGLGETACTIVEUNIFORMPROC)(GLuint, GLuint, GLsizei, GLsizei*, GLint*, GLenum*, GLchar*);
    typedef GLint (APIENTRYP PFNGLGETATTRIBLOCATIONPROC)(GLuint, const GLchar*);
    typedef void (APIENTRYP PFNGLGENFRAMEBUFFERSPROC)(GLsizei, GLuint*);
    typedef void (APIENTRYP PFNGLDELETEFRAMEBUFFERSPROC)(GLsizei, const GLuint*);
    typedef void (APIENTRYP PFNGLBINDFRAMEBUFFERPROC)(GLenum, GLuint);
    typedef void (APIENTRYP PFNGLFRAMEBUFFERTEXTURE2DPROC)(GLenum, GLenum, GLenum, GLuint, GLint);
    typedef GLenum (APIENTRYP PFNGLCHECKFRAMEBUFFERSTATUSPROC)(GLenum);
    typedef void (APIENTRYP PFNGLGENRENDERBUFFERSPROC)(GLsizei, GLuint*);
    typedef void (APIENTRYP PFNGLDELETERENDERBUFFERSPROC)(GLsizei, const GLuint*);
    typedef void (APIENTRYP PFNGLBINDRENDERBUFFERPROC)(GLenum, GLuint);
    typedef void (APIENTRYP PFNGLRENDERBUFFERSTORAGEPROC)(GLenum, GLenum, GLsizei, GLsizei);
    typedef void (APIENTRYP PFNGLFRAMEBUFFERRENDERBUFFERPROC)(GLenum, GLenum, GLenum, GLuint);
    typedef void (APIENTRYP PFNGLGENERATEMIPMAPPROC)(GLenum);
    typedef void (APIENTRYP PFNGLACTIVETEXTUREPROC)(GLenum);
    typedef void (APIENTRYP PFNGLBLENDEQUATIONPROC)(GLenum);

    #define glGenVertexArrays    saturday_glGenVertexArrays
    #define glDeleteVertexArrays saturday_glDeleteVertexArrays
    #define glBindVertexArray    saturday_glBindVertexArray
    #define glGenBuffers         saturday_glGenBuffers
    #define glDeleteBuffers      saturday_glDeleteBuffers
    #define glBindBuffer         saturday_glBindBuffer
    #define glBufferData         saturday_glBufferData
    #define glBufferSubData      saturday_glBufferSubData
    #define glEnableVertexAttribArray  saturday_glEnableVertexAttribArray
    #define glDisableVertexAttribArray saturday_glDisableVertexAttribArray
    #define glVertexAttribPointer     saturday_glVertexAttribPointer
    #define glDrawArrays              saturday_glDrawArrays
    #define glDrawElements            saturday_glDrawElements
    #define glCreateShader            saturday_glCreateShader
    #define glDeleteShader            saturday_glDeleteShader
    #define glShaderSource            saturday_glShaderSource
    #define glCompileShader           saturday_glCompileShader
    #define glGetShaderiv             saturday_glGetShaderiv
    #define glGetShaderInfoLog        saturday_glGetShaderInfoLog
    #define glCreateProgram           saturday_glCreateProgram
    #define glDeleteProgram           saturday_glDeleteProgram
    #define glAttachShader            saturday_glAttachShader
    #define glDetachShader            saturday_glDetachShader
    #define glLinkProgram             saturday_glLinkProgram
    #define glValidateProgram         saturday_glValidateProgram
    #define glGetProgramiv            saturday_glGetProgramiv
    #define glGetProgramInfoLog       saturday_glGetProgramInfoLog
    #define glUseProgram              saturday_glUseProgram
    #define glGetUniformLocation      saturday_glGetUniformLocation
    #define glUniform1f               saturday_glUniform1f
    #define glUniform2f               saturday_glUniform2f
    #define glUniform3f               saturday_glUniform3f
    #define glUniform4f               saturday_glUniform4f
    #define glUniform1i               saturday_glUniform1i
    #define glUniform2fv              saturday_glUniform2fv
    #define glUniform3fv              saturday_glUniform3fv
    #define glUniform4fv              saturday_glUniform4fv
    #define glUniformMatrix3fv        saturday_glUniformMatrix3fv
    #define glUniformMatrix4fv        saturday_glUniformMatrix4fv
    #define glBindAttribLocation      saturday_glBindAttribLocation
    #define glGetActiveAttrib         saturday_glGetActiveAttrib
    #define glGetActiveUniform        saturday_glGetActiveUniform
    #define glGetAttribLocation       saturday_glGetAttribLocation
    #define glGenFramebuffers         saturday_glGenFramebuffers
    #define glDeleteFramebuffers      saturday_glDeleteFramebuffers
    #define glBindFramebuffer         saturday_glBindFramebuffer
    #define glFramebufferTexture2D    saturday_glFramebufferTexture2D
    #define glCheckFramebufferStatus  saturday_glCheckFramebufferStatus
    #define glGenRenderbuffers        saturday_glGenRenderbuffers
    #define glDeleteRenderbuffers     saturday_glDeleteRenderbuffers
    #define glBindRenderbuffer        saturday_glBindRenderbuffer
    #define glRenderbufferStorage     saturday_glRenderbufferStorage
    #define glFramebufferRenderbuffer saturday_glFramebufferRenderbuffer
    #define glGenerateMipmap          saturday_glGenerateMipmap
    #define glActiveTexture           saturday_glActiveTexture
    #define glBlendEquation           saturday_glBlendEquation

    static PFNGLGENVERTEXARRAYSPROC    saturday_glGenVertexArrays    = nullptr;
    static PFNGLDELETEVERTEXARRAYSPROC saturday_glDeleteVertexArrays = nullptr;
    static PFNGLBINDVERTEXARRAYPROC    saturday_glBindVertexArray    = nullptr;
    static PFNGLGENBUFFERSPROC         saturday_glGenBuffers         = nullptr;
    static PFNGLDELETEBUFFERSPROC      saturday_glDeleteBuffers      = nullptr;
    static PFNGLBINDBUFFERPROC         saturday_glBindBuffer         = nullptr;
    static PFNGLBUFFERDATAPROC         saturday_glBufferData         = nullptr;
    static PFNGLBUFFERSUBDATAPROC      saturday_glBufferSubData      = nullptr;
    static PFNGLENABLEVERTEXATTRIBARRAYPROC  saturday_glEnableVertexAttribArray  = nullptr;
    static PFNGLDISABLEVERTEXATTRIBARRAYPROC saturday_glDisableVertexAttribArray = nullptr;
    static PFNGLVERTEXATTRIBPOINTERPROC     saturday_glVertexAttribPointer     = nullptr;
    static PFNGLDRAWARRAYSPROC              saturday_glDrawArrays              = nullptr;
    static PFNGLDRAWELEMENTSPROC            saturday_glDrawElements            = nullptr;
    static PFNGLCREATESHADERPROC            saturday_glCreateShader            = nullptr;
    static PFNGLDELETESHADERPROC            saturday_glDeleteShader            = nullptr;
    static PFNGLSHADERSOURCEPROC            saturday_glShaderSource            = nullptr;
    static PFNGLCOMPILESHADERPROC           saturday_glCompileShader           = nullptr;
    static PFNGLGETSHADERIVPROC             saturday_glGetShaderiv             = nullptr;
    static PFNGLGETSHADERINFOLOGPROC        saturday_glGetShaderInfoLog        = nullptr;
    static PFNGLCREATEPROGRAMPROC           saturday_glCreateProgram           = nullptr;
    static PFNGLDELETEPROGRAMPROC           saturday_glDeleteProgram           = nullptr;
    static PFNGLATTACHSHADERPROC            saturday_glAttachShader            = nullptr;
    static PFNGLDETACHSHADERPROC            saturday_glDetachShader            = nullptr;
    static PFNGLLINKPROGRAMPROC             saturday_glLinkProgram             = nullptr;
    static PFNGLVALIDATEPROGRAMPROC         saturday_glValidateProgram         = nullptr;
    static PFNGLGETPROGRAMIVPROC            saturday_glGetProgramiv            = nullptr;
    static PFNGLGETPROGRAMINFOLOGPROC       saturday_glGetProgramInfoLog       = nullptr;
    static PFNGLUSEPROGRAMPROC              saturday_glUseProgram              = nullptr;
    static PFNGLGETUNIFORMLOCATIONPROC      saturday_glGetUniformLocation      = nullptr;
    static PFNGLUNIFORM1FPROC               saturday_glUniform1f               = nullptr;
    static PFNGLUNIFORM2FPROC               saturday_glUniform2f               = nullptr;
    static PFNGLUNIFORM3FPROC               saturday_glUniform3f               = nullptr;
    static PFNGLUNIFORM4FPROC               saturday_glUniform4f               = nullptr;
    static PFNGLUNIFORM1IPROC               saturday_glUniform1i               = nullptr;
    static PFNGLUNIFORM2FVPROC              saturday_glUniform2fv              = nullptr;
    static PFNGLUNIFORM3FVPROC              saturday_glUniform3fv              = nullptr;
    static PFNGLUNIFORM4FVPROC              saturday_glUniform4fv              = nullptr;
    static PFNGLUNIFORMMATRIX3FVPROC        saturday_glUniformMatrix3fv        = nullptr;
    static PFNGLUNIFORMMATRIX4FVPROC        saturday_glUniformMatrix4fv        = nullptr;
    static PFNGLBINDATTRIBLOCATIONPROC      saturday_glBindAttribLocation      = nullptr;
    static PFNGLGETACTIVEATTRIBPROC         saturday_glGetActiveAttrib         = nullptr;
    static PFNGLGETACTIVEUNIFORMPROC        saturday_glGetActiveUniform        = nullptr;
    static PFNGLGETATTRIBLOCATIONPROC       saturday_glGetAttribLocation       = nullptr;
    static PFNGLGENFRAMEBUFFERSPROC         saturday_glGenFramebuffers         = nullptr;
    static PFNGLDELETEFRAMEBUFFERSPROC      saturday_glDeleteFramebuffers      = nullptr;
    static PFNGLBINDFRAMEBUFFERPROC         saturday_glBindFramebuffer         = nullptr;
    static PFNGLFRAMEBUFFERTEXTURE2DPROC    saturday_glFramebufferTexture2D    = nullptr;
    static PFNGLCHECKFRAMEBUFFERSTATUSPROC  saturday_glCheckFramebufferStatus  = nullptr;
    static PFNGLGENRENDERBUFFERSPROC        saturday_glGenRenderbuffers        = nullptr;
    static PFNGLDELETERENDERBUFFERSPROC     saturday_glDeleteRenderbuffers     = nullptr;
    static PFNGLBINDRENDERBUFFERPROC        saturday_glBindRenderbuffer        = nullptr;
    static PFNGLRENDERBUFFERSTORAGEPROC     saturday_glRenderbufferStorage     = nullptr;
    static PFNGLFRAMEBUFFERRENDERBUFFERPROC saturday_glFramebufferRenderbuffer = nullptr;
    static PFNGLGENERATEMIPMAPPROC          saturday_glGenerateMipmap          = nullptr;
    static PFNGLACTIVETEXTUREPROC           saturday_glActiveTexture           = nullptr;
    static PFNGLBLENDEQUATIONPROC           saturday_glBlendEquation           = nullptr;

    static inline void saturday_load_gl_functions() {
        static bool loaded = false;
        if (loaded) return;

        HMODULE gl_module = GetModuleHandleA("opengl32.dll");
        if (!gl_module) return;

    #define SATURDAY_LOAD(var, name) var = reinterpret_cast<decltype(var)>(GetProcAddress(gl_module, name))

        SATURDAY_LOAD(saturday_glGenVertexArrays,          "glGenVertexArrays");
        SATURDAY_LOAD(saturday_glDeleteVertexArrays,       "glDeleteVertexArrays");
        SATURDAY_LOAD(saturday_glBindVertexArray,          "glBindVertexArray");
        SATURDAY_LOAD(saturday_glGenBuffers,               "glGenBuffers");
        SATURDAY_LOAD(saturday_glDeleteBuffers,            "glDeleteBuffers");
        SATURDAY_LOAD(saturday_glBindBuffer,               "glBindBuffer");
        SATURDAY_LOAD(saturday_glBufferData,               "glBufferData");
        SATURDAY_LOAD(saturday_glBufferSubData,            "glBufferSubData");
        SATURDAY_LOAD(saturday_glEnableVertexAttribArray,  "glEnableVertexAttribArray");
        SATURDAY_LOAD(saturday_glDisableVertexAttribArray, "glDisableVertexAttribArray");
        SATURDAY_LOAD(saturday_glVertexAttribPointer,      "glVertexAttribPointer");
        SATURDAY_LOAD(saturday_glDrawArrays,               "glDrawArrays");
        SATURDAY_LOAD(saturday_glDrawElements,             "glDrawElements");
        SATURDAY_LOAD(saturday_glCreateShader,             "glCreateShader");
        SATURDAY_LOAD(saturday_glDeleteShader,             "glDeleteShader");
        SATURDAY_LOAD(saturday_glShaderSource,             "glShaderSource");
        SATURDAY_LOAD(saturday_glCompileShader,            "glCompileShader");
        SATURDAY_LOAD(saturday_glGetShaderiv,              "glGetShaderiv");
        SATURDAY_LOAD(saturday_glGetShaderInfoLog,         "glGetShaderInfoLog");
        SATURDAY_LOAD(saturday_glCreateProgram,            "glCreateProgram");
        SATURDAY_LOAD(saturday_glDeleteProgram,            "glDeleteProgram");
        SATURDAY_LOAD(saturday_glAttachShader,             "glAttachShader");
        SATURDAY_LOAD(saturday_glDetachShader,             "glDetachShader");
        SATURDAY_LOAD(saturday_glLinkProgram,              "glLinkProgram");
        SATURDAY_LOAD(saturday_glValidateProgram,          "glValidateProgram");
        SATURDAY_LOAD(saturday_glGetProgramiv,             "glGetProgramiv");
        SATURDAY_LOAD(saturday_glGetProgramInfoLog,        "glGetProgramInfoLog");
        SATURDAY_LOAD(saturday_glUseProgram,               "glUseProgram");
        SATURDAY_LOAD(saturday_glGetUniformLocation,       "glGetUniformLocation");
        SATURDAY_LOAD(saturday_glUniform1f,                "glUniform1f");
        SATURDAY_LOAD(saturday_glUniform2f,                "glUniform2f");
        SATURDAY_LOAD(saturday_glUniform3f,                "glUniform3f");
        SATURDAY_LOAD(saturday_glUniform4f,                "glUniform4f");
        SATURDAY_LOAD(saturday_glUniform1i,                "glUniform1i");
        SATURDAY_LOAD(saturday_glUniform2fv,               "glUniform2fv");
        SATURDAY_LOAD(saturday_glUniform3fv,               "glUniform3fv");
        SATURDAY_LOAD(saturday_glUniform4fv,               "glUniform4fv");
        SATURDAY_LOAD(saturday_glUniformMatrix3fv,         "glUniformMatrix3fv");
        SATURDAY_LOAD(saturday_glUniformMatrix4fv,         "glUniformMatrix4fv");
        SATURDAY_LOAD(saturday_glBindAttribLocation,       "glBindAttribLocation");
        SATURDAY_LOAD(saturday_glGetActiveAttrib,          "glGetActiveAttrib");
        SATURDAY_LOAD(saturday_glGetActiveUniform,         "glGetActiveUniform");
        SATURDAY_LOAD(saturday_glGetAttribLocation,        "glGetAttribLocation");
        SATURDAY_LOAD(saturday_glGenFramebuffers,          "glGenFramebuffers");
        SATURDAY_LOAD(saturday_glDeleteFramebuffers,       "glDeleteFramebuffers");
        SATURDAY_LOAD(saturday_glBindFramebuffer,          "glBindFramebuffer");
        SATURDAY_LOAD(saturday_glFramebufferTexture2D,     "glFramebufferTexture2D");
        SATURDAY_LOAD(saturday_glCheckFramebufferStatus,   "glCheckFramebufferStatus");
        SATURDAY_LOAD(saturday_glGenRenderbuffers,         "glGenRenderbuffers");
        SATURDAY_LOAD(saturday_glDeleteRenderbuffers,      "glDeleteRenderbuffers");
        SATURDAY_LOAD(saturday_glBindRenderbuffer,         "glBindRenderbuffer");
        SATURDAY_LOAD(saturday_glRenderbufferStorage,      "glRenderbufferStorage");
        SATURDAY_LOAD(saturday_glFramebufferRenderbuffer,  "glFramebufferRenderbuffer");
        SATURDAY_LOAD(saturday_glGenerateMipmap,           "glGenerateMipmap");
        SATURDAY_LOAD(saturday_glActiveTexture,            "glActiveTexture");
        SATURDAY_LOAD(saturday_glBlendEquation,            "glBlendEquation");

    #undef SATURDAY_LOAD

        loaded = true;
    }

#else
    #include <GL/gl.h>
    static inline void saturday_load_gl_functions() {}
#endif
