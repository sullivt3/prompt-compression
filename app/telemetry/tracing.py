from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import ConsoleSpanExporter, SimpleSpanProcessor
from opentelemetry.trace import Tracer


def create_tracer(console_export: bool = False) -> tuple[TracerProvider, Tracer]:
    provider = TracerProvider(resource=Resource.create({"service.name": "prompt-gateway"}))
    if console_export:
        provider.add_span_processor(SimpleSpanProcessor(ConsoleSpanExporter()))
    return provider, provider.get_tracer("prompt-gateway")
