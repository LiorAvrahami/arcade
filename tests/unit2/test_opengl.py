"""
Low level tests for OpenGL 3.3 wrappers.
"""
import array
import pytest
import arcade
from arcade.gl import BufferDescription
from arcade.gl.glsl import ShaderSource
from arcade.gl import ShaderException

from pyglet import gl

SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600


@pytest.fixture(scope="module")
def ctx():
    window = arcade.Window(SCREEN_WIDTH, SCREEN_HEIGHT, "Test OpenGL")
    yield window.ctx
    err_check(window.ctx)
    window.close()


def err_check(ctx):
    error = ctx.error
    if error:
        raise ValueError("Error", error)


def test_buffer_description(ctx):
    # TODO: components > 4
    # TODO: padding
    BufferDescription(
        ctx.buffer(reserve=4 * 8),
        '2f 2f',
        ['in_vert', 'in_uv'],
    )


def test_ctx(ctx):
    assert ctx.gl_version >= (3, 3)
    assert ctx.limits.MAX_TEXTURE_SIZE > 4096
    assert ctx.limits.MAX_ARRAY_TEXTURE_LAYERS >= 256


def test_geometry(ctx):
    """Test vertex_array"""
    program = ctx.load_program(
        vertex_shader=':resources:shaders/shapes/line/line_vertex_shader_vs.glsl',
        fragment_shader=':resources:shaders/shapes/line/line_vertex_shader_fs.glsl',
    )
    num_vertices = 100
    content = [
        BufferDescription(
            ctx.buffer(reserve=4 * num_vertices),
            '4f1',
            ['in_color'],
            normalized=['in_color'],
        ),
        BufferDescription(
            ctx.buffer(reserve=8 * num_vertices),
            '2f',
            ['in_vert']
        ),
    ]
    vao = ctx.geometry(content)
    assert vao.ctx == ctx
    assert vao.num_vertices == num_vertices
    assert vao.index_buffer is None
    vao.render(program, mode=ctx.TRIANGLES)
    vao.render(program, mode=ctx.POINTS)
    vao.render(program, mode=ctx.LINES)


def test_shader_source(ctx):
    """Test shader source parsing"""
    source_wrapper = ShaderSource(
        """
        #version 330
        #define TEST 10
        #define TEST2 20
        in vec2 in_pos;
        in vec2 in_velocity;
        out vec2 out_pos;
        out vec2 out_velocity;
        void main() {
            out_pos = in_pos;
            out_velocity = in_velocity;
        }
        """,
        gl.GL_VERTEX_SHADER,
    )
    assert source_wrapper.version == 330
    assert source_wrapper.out_attributes == ['out_pos', 'out_velocity']
    source = source_wrapper.get_source(defines={'TEST': 1, 'TEST2': '2'})
    assert '#define TEST 1' in source
    assert '#define TEST2 2' in source


def test_program(ctx):
    """Test program"""
    program = ctx.program(
        vertex_shader="""
        #version 330

        uniform vec2 pos_offset;

        in vec2 in_vert;
        in vec2 in_uv;
        out vec2 v_uv;

        void main() {
            gl_Position = vec4(in_vert + pos_offset, 0.0, 1.0);
            v_uv = in_uv;
        }
        """,
        fragment_shader="""
        #version 330

        out vec4 f_color;
        in vec2 v_uv;

        void main() {
            f_color = vec4(v_uv, 0.0, 1.0);
        }
        """,
    )
    assert program.ctx == ctx
    assert program.glo > 0
    program.use()
    assert ctx.active_program == program

    # TODO: Test all uniform types
    program['pos_offset'] = 1, 2
    assert program['pos_offset'] == (1.0, 2.0)
    with pytest.raises(ShaderException):
        program['this_uniform_do_not_exist'] = 0

    # Program with only vertex shader
    program = ctx.program(
        vertex_shader="""
        #version 330
        in vec2 in_pos;
        out vec2 out_pos;

        void main() {
            out_pos = in_pos + vec2(1.0);
        }
        """,
    )

    # Program with geometry shader
    program = ctx.program(
        vertex_shader="""
        #version 330
        in vec2 pos;
        void main() {
            gl_Position = vec4(pos, 0.0, 1.0);
        }
        """,
        geometry_shader="""
        #version 330

        layout (points) in;
        layout (triangle_strip, max_vertices = 2) out;

        void main() {
            gl_Position = gl_in[0].gl_Position + vec4(-0.1, 0.0, 0.0, 0.0);
            EmitVertex();

            gl_Position = gl_in[0].gl_Position + vec4( 0.1, 0.0, 0.0, 0.0);
            EmitVertex();

            EndPrimitive();
        }
        """,
    )
    assert program.geometry_input == ctx.POINTS
    assert program.geometry_output == ctx.TRIANGLE_STRIP
    assert program.geometry_vertices == 2

    # Uniform testing
    # .. mother of all uniform programs trying to cram in as many as possible!
    program = ctx.program(
        vertex_shader="""
        #version 330
        in vec2 in_pos;
        in vec2 in_velocity;
        out vec2 out_pos;
        out vec2 out_velocity;

        void main() {
            out_pos = in_pos + vec2(1.0);
            out_velocity = in_pos * 0.99;
        }
        """,
    )
    assert program.out_attributes == ['out_pos', 'out_velocity']