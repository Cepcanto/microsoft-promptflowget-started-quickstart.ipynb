import pytest

from promptflow._core.generator_proxy import GeneratorProxy
from promptflow._core.tracer import Tracer, _create_trace_from_function_call
from promptflow.connections import AzureOpenAIConnection
from promptflow.contracts.trace import Trace, TraceType


def generator():
    for i in range(3):
        yield i


@pytest.mark.unittest
class TestTracer:
    def test_push_tool(self):
        # Define a mock tool function
        def mock_tool(a, b, c: AzureOpenAIConnection):
            return a + b + str(c)

        Tracer.start_tracing("test_run_id")
        # Push the tool to the tracer with some argument
        conn = AzureOpenAIConnection("test_key", "test_base")
        trace = Tracer.push_tool(mock_tool, (1, 2), {"c": conn})

        # Assert that the trace has the correct attributes
        assert trace.name == mock_tool.__qualname__
        assert trace.type == TraceType.TOOL
        assert trace.inputs == {"a": 1, "b": 2, "c": "AzureOpenAIConnection"}
        assert trace.output is None
        assert trace.start_time is not None
        assert trace.end_time is None
        assert trace.children is None
        assert trace.error is None

        Tracer.end_tracing()

    def test_end_tracing(self):
        # Activate the tracer in the current context
        tracer = Tracer("test_run_id")
        tracer._activate_in_context()

        # Assert that there is an active tracer instance
        assert Tracer.active_instance() is tracer

        # End tracing and get the traces as a JSON string
        traces = Tracer.end_tracing()

        # Assert that the traces is a list
        assert isinstance(traces, list)

        # Assert that there is no active tracer instance after ending tracing
        assert Tracer.active_instance() is None

        # Test the raise_ex argument of the end_tracing method
        with pytest.raises(Exception):
            # Try to end tracing again with raise_ex=True
            Tracer.end_tracing(raise_ex=True)

        # Try to end tracing again with raise_ex=False
        traces = Tracer.end_tracing(raise_ex=False)

        # Assert that the traces are empty
        assert not traces

    def test_start_tracing(self):
        # Assert that there is no active tracer instance before starting tracing
        assert Tracer.active_instance() is None

        # Start tracing with a mock run_id
        Tracer.start_tracing("test_run_id")

        # Assert that there is an active tracer instance after starting tracing
        assert Tracer.active_instance() is not None

        # Assert that the active tracer instance has the correct run_id
        assert Tracer.active_instance()._run_id == "test_run_id"

        Tracer.end_tracing()

    def test_push_pop(self, caplog):
        # test the push method with a single trace
        Tracer.start_tracing("test_run_id")
        tracer = Tracer.active_instance()

        trace1 = Trace("test1", inputs=[1, 2, 3], type=TraceType.TOOL)
        trace2 = Trace("test2", inputs=[4, 5, 6], type=TraceType.TOOL)

        Tracer.push(trace1)
        assert tracer._traces == [trace1]
        assert tracer._trace_stack == [trace1]

        # test the push method with a nested trace
        Tracer.push(trace2)
        assert tracer._traces == [trace1]  # check if the tracer still has only the first trace in its _traces list
        assert tracer._trace_stack == [trace1, trace2]  # check if the tracer has both traces in its _trace_stack list
        assert trace1.children == [trace2]  # check if the first trace has the second trace as its child

        # test the pop method with generator output
        tool_output = generator()
        error1 = ValueError("something went wrong")
        output = Tracer.pop(output=tool_output, error=error1)

        # check output iterator
        for i in range(3):
            assert next(output) == i

        assert len(tracer._trace_stack) == 1
        assert tracer._trace_stack[-1].name == "test1"
        assert isinstance(trace2.output, GeneratorProxy)
        assert trace2.error == {
            "message": str(error1),
            "type": type(error1).__qualname__,
        }

        # test the pop method with no arguments
        output = Tracer.pop()

        assert len(tracer._trace_stack) == 0
        assert trace1.output is None
        assert output is None

        Tracer.end_tracing()

        # test the push method with no active tracer
        Tracer.push(trace1)
        # assert that the warning message is logged
        assert "Try to push trace but no active tracer in current context." in caplog.text

    def test_unserializable_obj_to_serializable(self):
        # assert that the function returns a str object for unserializable objects
        assert Tracer.to_serializable(generator) == str(generator)

    @pytest.mark.parametrize("obj", [({"name": "Alice", "age": 25}), ([1, 2, 3]), (GeneratorProxy(generator())), (42)])
    def test_to_serializable(self, obj):
        assert Tracer.to_serializable(obj) == obj


def func_with_no_parameters():
    pass


def func_with_args_and_kwargs(arg1, arg2=None, *, kwarg1=None, kwarg2=None):
    _ = (arg1, arg2, kwarg1, kwarg2)


def func_with_connection_parameter(a: int, conn: AzureOpenAIConnection):
    _ = (a, conn)


class MyClass:
    def my_method(self, a: int):
        _ = a


@pytest.mark.unittest
class TestCreateTraceFromFunctionCall:
    def test_basic_fields_are_filled_and_others_are_not(self):
        trace = _create_trace_from_function_call(func_with_no_parameters)

        # These fields should be filled in this method call.
        assert trace.name == "func_with_no_parameters"
        assert trace.type == TraceType.FUNCTION
        assert trace.inputs == {}
        # start_time should be a timestamp, which is a float value currently.
        assert isinstance(trace.start_time, float)

        # These should be left empty in this method call.
        # They will be filled by the tracer later.
        assert trace.output is None
        assert trace.end_time is None
        assert trace.children is None
        assert trace.error is None

    def test_trace_name_should_contain_class_name_for_class_methods(self):
        obj = MyClass()
        trace = _create_trace_from_function_call(obj.my_method, args=[obj, 1])
        assert trace.name == "MyClass.my_method"

    def test_trace_type_can_be_set_correctly(self):
        trace = _create_trace_from_function_call(func_with_no_parameters, trace_type=TraceType.TOOL)
        assert trace.type == TraceType.TOOL

    def test_args_and_kwargs_are_filled_correctly(self):
        trace = _create_trace_from_function_call(
            func_with_args_and_kwargs, args=[1, 2], kwargs={"kwarg1": 3, "kwarg2": 4}
        )
        assert trace.inputs == {"arg1": 1, "arg2": 2, "kwarg1": 3, "kwarg2": 4}

    def test_args_called_with_name_should_be_filled_correctly(self):
        trace = _create_trace_from_function_call(func_with_args_and_kwargs, args=[1], kwargs={"arg2": 2, "kwarg2": 4})
        assert trace.inputs == {"arg1": 1, "arg2": 2, "kwarg2": 4}

    def test_kwargs_called_without_name_should_be_filled_correctly(self):
        trace = _create_trace_from_function_call(func_with_args_and_kwargs, args=[1, 2, 3], kwargs={"kwarg2": 4})
        assert trace.inputs == {"arg1": 1, "arg2": 2, "kwarg1": 3, "kwarg2": 4}

    def test_empty_args_should_be_excluded_from_inputs(self):
        trace = _create_trace_from_function_call(func_with_args_and_kwargs, args=[1])
        assert trace.inputs == {"arg1": 1}

    def test_empty_kwargs_should_be_excluded_from_inputs(self):
        trace = _create_trace_from_function_call(func_with_args_and_kwargs, kwargs={"kwarg1": 1})
        assert trace.inputs == {"kwarg1": 1}
        trace = _create_trace_from_function_call(func_with_args_and_kwargs, kwargs={"kwarg2": 2})
        assert trace.inputs == {"kwarg2": 2}

    def test_args_and_kwargs_should_be_filled_in_called_order(self):
        trace = _create_trace_from_function_call(
            func_with_args_and_kwargs, args=[1, 2], kwargs={"kwarg2": 4, "kwarg1": 3}
        )
        assert list(trace.inputs.keys()) == ["arg1", "arg2", "kwarg2", "kwarg1"]

    def test_connections_should_be_serialized(self):
        conn = AzureOpenAIConnection("test_name", "test_secret")
        trace = _create_trace_from_function_call(func_with_connection_parameter, args=[1, conn])
        assert trace.inputs == {"a": 1, "conn": "AzureOpenAIConnection"}

    def test_self_arg_should_be_excluded_from_inputs(self):
        obj = MyClass()
        trace = _create_trace_from_function_call(obj.my_method, args=[1])
        assert trace.inputs == {"a": 1}
