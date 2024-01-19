import asyncio
import contextvars
import os
from concurrent.futures import ThreadPoolExecutor

from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter
from opentelemetry import trace
from opentelemetry.sdk.resources import SERVICE_NAME, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, SimpleSpanProcessor, SpanExporter, SpanExportResult

# from opentelemetry.exporter.jaeger.thrift import JaegerExporter
# from opentelemetry.exporter.zipkin.json import ZipkinExporter
# jaeger_exporter = JaegerExporter(
#    agent_host_name="localhost",
#    agent_port=6831,
# )
# Service name is required for most backends,
# and although it's not necessary for console export,
# it's good to set service name anyways.
resource = Resource(attributes={SERVICE_NAME: "your-service-name"})


class FileExporter(SpanExporter):
    def __init__(self, file_name="traces.json"):
        self.file_name = file_name
        # Open the file in append mode
        self.file = open(file_name, "a")

    def export(self, spans):
        # Convert spans to a format suitable for JSON serialization
        span_data = [span.to_json() for span in spans]
        # Write the JSON serialized span data to the file
        for span_json in span_data:
            self.file.write(span_json + "\n")
        self.file.flush()
        return SpanExportResult.SUCCESS

    def shutdown(self):
        # Close the file when shutting down the exporter
        self.file.close()


tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)
# traceProvider = get_tracer_provider()
# processor = BatchSpanProcessor(ConsoleSpanExporter())
# traceProvider.add_span_processor(processor)
connection_string = os.environ.get("APPINSIGHTS_CONNECTION_STRING")
if connection_string:
    # raise ValueError("No connection string provided")
    processor = BatchSpanProcessor(AzureMonitorTraceExporter(connection_string=connection_string))
    tracer_provider.add_span_processor(processor)
# processor = BatchSpanProcessor(jaeger_exporter)
# traceProvider.add_span_processor(processor)

file_exporter = FileExporter("traces.json")
tracer_provider.add_span_processor(SimpleSpanProcessor(file_exporter))


# zipkin_exporter = ZipkinExporter(
# Optional: configure the endpoint
# endpoint="http://localhost:9411/api/v2/spans",
# Optional: configure the service name
# service_name="my-service",
# )

# tracer_provider = trace.get_tracer_provider()
# tracer_provider.add_span_processor(BatchSpanProcessor(zipkin_exporter))

# reader = PeriodicExportingMetricReader(ConsoleMetricExporter())
# meterProvider = MeterProvider(resource=resource, metric_readers=[reader])
# metrics.set_meter_provider(meterProvider)
tracer = trace.get_tracer(__name__)

tracer2 = trace.get_tracer("tracer2")


async def wait_task(name: str, wait_seconds: int = 1):
    with tracer2.start_as_current_span(name) as span:
        span.set_attribute("wait_seconds", wait_seconds)
        await asyncio.sleep(wait_seconds)
        print(f"Task {name} finished")


async def main():
    with tracer.start_as_current_span("main") as span:
        span.set_attribute("attribute", "value")
        task1 = asyncio.create_task(wait_task("task1", 2))
        task2 = asyncio.create_task(wait_task("task2", 1))
        span.add_event("Start Await", {"name": "value", "my_key": "my_value"})
        await task2
        await task1
        await wait_task("task3", 1)
        span.add_event("End Await", {"name": "value", "my_key": "my_value"})

    # tracer.get_current_span()
    first_span_context = span.get_span_context()
    link_to_first_span = trace.Link(first_span_context)

    with tracer.start_as_current_span("linked", links=[link_to_first_span]) as linked:
        linked.set_attribute("my_attribute", "my_value")
        await wait_task("task4", 1)


def sync_task(name: str, wait_seconds: int = 1):
    with tracer.start_as_current_span(name) as span:
        span.set_attribute("wait_seconds", wait_seconds)
        import time

        time.sleep(wait_seconds)
        print(f"Task {name} finished")


def set_context(context: contextvars.Context):
    for var, value in context.items():
        var.set(value)


def sync_main():
    with tracer.start_as_current_span("sync_main") as span:
        span.set_attribute("attribute", "value")
        with ThreadPoolExecutor(
            max_workers=2, initializer=set_context, initargs=(contextvars.copy_context(),)
        ) as executor:
            # Submit tasks to the executor
            executor.submit(sync_task, "sync_task1")
        sync_task("sync_task2", 2)


if __name__ == "__main__":
    asyncio.run(main())
    # sync_main()
    # with tracer2.start_as_current_span("test"):
    #    print("yes")
