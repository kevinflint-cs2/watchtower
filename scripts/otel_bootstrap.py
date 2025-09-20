# ./scripts/otel_bootstrap.py
import os
import logging
from dotenv import load_dotenv

from azure.core.settings import settings

# Azure ↔ OpenTelemetry bridge
try:
    from azure.core.tracing.ext.opentelemetry_span import OpenTelemetrySpan as _OTImpl
except Exception:
    from azure.core.tracing.ext.opentelemetry_tracing import OpenTelemetryTracing as _OTImpl  # older/newer compat

from opentelemetry import trace
from opentelemetry.sdk.resources import Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from azure.monitor.opentelemetry import configure_azure_monitor

load_dotenv()

# ---- App Insights connection string (required) ----
_conn = os.getenv("APPI_CONNECTION_STRING")
if not _conn:
    raise RuntimeError("APPI_CONNECTION_STRING not set")

# ---- Configure Azure Monitor (traces + logs + metrics) ----
# Sampling: for investigations you likely want 100% in dev
configure_azure_monitor(
    connection_string=_conn,
    # sampling_ratio=1.0,  # uncomment for full capture in non-prod
)

# ---- Make sure our process has a proper resource identity in AI ----
resource = Resource.create({
    "service.name": os.getenv("SERVICE_NAME", "ai-multiagent"),
    "service.version": os.getenv("SERVICE_VERSION", "0.1.0"),
    "deployment.environment": os.getenv("DEPLOY_ENV", "dev"),
})

provider = TracerProvider(resource=resource)
trace.set_tracer_provider(provider)

# Azure Monitor exporter was already configured by configure_azure_monitor(),
# we just add batching (the distro sets exporters/handlers under the hood).
# If you also installed the console exporter for local debugging, enable it:
try:
    from opentelemetry.sdk.trace.export import ConsoleSpanExporter
    provider.add_span_processor(BatchSpanProcessor(ConsoleSpanExporter()))
except Exception:
    pass

# Tell Azure SDKs to emit OTel spans
settings.tracing_implementation = _OTImpl

# Optional: turn on Azure SDK HTTP logs (headers/URLs)
logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s: %(message)s")
logging.getLogger("azure").setLevel(logging.INFO)
logging.getLogger("azure.core.pipeline.policies.http_logging_policy").setLevel(logging.INFO)

# Convenience tracer
tracer = trace.get_tracer("ai-agents")