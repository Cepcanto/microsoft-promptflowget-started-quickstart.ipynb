# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

import os
from abc import abstractmethod
from enum import Enum

from azure.identity import DefaultAzureCredential
from opentelemetry.sdk.environment_variables import OTEL_EXPORTER_OTLP_ENDPOINT

from promptflow.core._serving.extension.extension_type import ExtensionType
from promptflow.core._serving.monitor.mdc_exporter import MdcExporter


class ExporterType(Enum):
    METRIC = "metric"
    TRACE = "trace"


class OTelExporterProvider:
    def __init__(self, logger, exporter_type: ExporterType) -> None:
        self.logger = logger
        self._exporter_type = exporter_type

    @abstractmethod
    def is_enabled(self, extension: ExtensionType):
        """check whether the exporter is enabled for given extension."""
        pass

    @abstractmethod
    def get_exporter(self, **kwargs):
        """get exporter instance."""
        pass

    @property
    def exporter_type(self) -> ExporterType:
        return self._exporter_type


class AppInsightExporterProvider(OTelExporterProvider):
    def __init__(self, logger, exporter_type: ExporterType) -> None:
        super().__init__(logger, exporter_type)
        self.app_insight_connection_string = try_get_app_insight_connection_string()
        if not self.app_insight_connection_string:
            self.logger.info(f"No connection string detected, app insight {exporter_type.value} exporter is disabled.")

    def is_enabled(self, extension: ExtensionType):
        return self.app_insight_connection_string is not None


class AppInsightTraceExporterProvider(AppInsightExporterProvider):
    def __init__(self, logger) -> None:
        super().__init__(logger, ExporterType.TRACE)

    def get_exporter(self, **kwargs):
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorTraceExporter

            return AzureMonitorTraceExporter.from_connection_string(self.app_insight_connection_string)
        except ImportError:
            self.logger.warning(
                "azure-monitor-opentelemetry-exporter(>=1.0.0b21,<2.0.0) is not installed, \
                                 AzureMonitorTraceExporter will not be enabled!"
            )
            return None


class MdcTraceExporterProvider(OTelExporterProvider):
    def __init__(self, logger) -> None:
        super().__init__(logger, ExporterType.TRACE)

    def is_enabled(self, extension: ExtensionType):
        return extension == ExtensionType.AZUREML

    def get_exporter(self, **kwargs):
        return MdcExporter(self.logger)


class AppInsightMetricsExporterProvider(AppInsightExporterProvider):
    def __init__(self, logger) -> None:
        super().__init__(logger, ExporterType.METRIC)

    def get_exporter(self, **kwargs):
        try:
            from azure.monitor.opentelemetry.exporter import AzureMonitorMetricExporter

            return AzureMonitorMetricExporter.from_connection_string(self.app_insight_connection_string)
        except ImportError:
            self.logger.warning(
                "azure-monitor-opentelemetry-exporter(>=1.0.0b21,<2.0.0) is not installed, \
                                 AzureMonitorMetricExporter will not be enabled!"
            )
            return None


OTEL_EXPORTER_OTLP_AAD_AUTH_ENABLE = "OTEL_EXPORTER_OTLP_AAD_AUTH_ENABLE"
OTEL_EXPORTER_OTLP_AAD_AUTH_SCOPE = "OTEL_EXPORTER_OTLP_AAD_AUTH_SCOPE"


class OTLPExporterProvider(OTelExporterProvider):
    def __init__(self, logger, exporter_type: ExporterType) -> None:
        super().__init__(logger, exporter_type)
        self.otel_exporter_endpoint = os.environ.get(OTEL_EXPORTER_OTLP_ENDPOINT, None)
        if not self.otel_exporter_endpoint:
            self.logger.info(
                f"No OTEL_EXPORTER_OTLP_ENDPOINT detected, OTLP {exporter_type.value} exporter is disabled."
            )  # noqa

    def is_enabled(self, extension: ExtensionType):
        return self.otel_exporter_endpoint is not None


class OTLPTraceExporterProvider(OTLPExporterProvider):
    def __init__(self, logger) -> None:
        super().__init__(logger, ExporterType.TRACE)

    def get_exporter(self, **kwargs):
        try:
            from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter

            class AADAuthOTLPSpanExporter(OTLPSpanExporter):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.aad_auth = os.environ.get(OTEL_EXPORTER_OTLP_AAD_AUTH_ENABLE, "false").lower() == "true"
                    self.aad_auth_scope = os.environ.get(
                        OTEL_EXPORTER_OTLP_AAD_AUTH_SCOPE, "https://management.azure.com/.default"
                    )  # noqa
                    self.credential = DefaultAzureCredential() if self.aad_auth else None

                def _export(self, serialized_data: str):
                    if self.aad_auth:
                        token = self.credential.get_token(self.aad_auth_scope).token
                        auth_header = {"Authorization": f"Bearer {token}"}
                        self._session.headers.update(auth_header)
                    return super()._export(serialized_data)

            return AADAuthOTLPSpanExporter(endpoint=self.otel_exporter_endpoint)
        except ImportError:
            self.logger.warning(
                "opentelemetry-exporter-otlp-proto-http(>=1.22.0,<2.0.0) is not installed, \
                                 OTLPSpanExporter will not be enabled!"
            )
            return None


class OTLPMetricsExporterProvider(OTLPExporterProvider):
    def __init__(self, logger) -> None:
        super().__init__(logger, ExporterType.METRIC)

    def get_exporter(self, **kwargs):
        try:
            from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter

            class AADAuthOTLPMetricExporter(OTLPMetricExporter):
                def __init__(self, *args, **kwargs):
                    super().__init__(*args, **kwargs)
                    self.aad_auth = os.environ.get(OTEL_EXPORTER_OTLP_AAD_AUTH_ENABLE, "false").lower() == "true"
                    self.aad_auth_scope = os.environ.get(
                        OTEL_EXPORTER_OTLP_AAD_AUTH_SCOPE, "https://management.azure.com/.default"
                    )  # noqa
                    self.credential = DefaultAzureCredential() if self.aad_auth else None

                def _export(self, serialized_data: str):
                    if self.aad_auth:
                        token = self.credential.get_token(self.aad_auth_scope).token
                        auth_header = {"Authorization": f"Bearer {token}"}
                        self._session.headers.update(auth_header)
                    return super()._export(serialized_data)

            return AADAuthOTLPMetricExporter(endpoint=self.otel_exporter_endpoint)
        except ImportError:
            self.logger.warning(
                "opentelemetry-exporter-otlp-proto-http(>=1.22.0,<2.0.0) is not installed, \
                                 OTLPMetricExporter will not be enabled!"
            )
            return None


class OTelExporterProviderFactory:
    """Factory to create OTel trace and metric exporters based on extension type."""

    @staticmethod
    def get_trace_exporters(logger, extension: ExtensionType, **kwargs):
        trace_providers = [
            AppInsightTraceExporterProvider(logger),
            MdcTraceExporterProvider(logger),
            OTLPTraceExporterProvider(logger),
        ]
        exporters = []
        for provider in trace_providers:
            if provider.is_enabled(extension):
                exporter = provider.get_exporter(**kwargs)
                if exporter:
                    exporters.append(exporter)
        return exporters

    @staticmethod
    def get_metrics_exporters(logger, extension: ExtensionType, **kwargs):
        metric_providers = [AppInsightMetricsExporterProvider(logger), OTLPMetricsExporterProvider(logger)]
        exporters = []
        for provider in metric_providers:
            if provider.is_enabled(extension):
                exporter = provider.get_exporter(**kwargs)
                if exporter:
                    exporters.append(exporter)
        return exporters


def try_get_app_insight_connection_string():
    """
    Try to get application insight connection string from environment variable.
    app insight base exporter support these environment variables:
    - "APPINSIGHTS_INSTRUMENTATIONKEY"
    - "APPLICATIONINSIGHTS_CONNECTION_STRING"
    """
    instrumentation_key = os.getenv("AML_APP_INSIGHTS_KEY") or os.getenv("APPINSIGHTS_INSTRUMENTATIONKEY")
    if instrumentation_key:
        return f"InstrumentationKey={instrumentation_key}"
    connection_str = os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    return connection_str
