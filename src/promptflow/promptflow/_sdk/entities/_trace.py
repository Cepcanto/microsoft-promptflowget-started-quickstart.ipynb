# ---------------------------------------------------------
# Copyright (c) Microsoft Corporation. All rights reserved.
# ---------------------------------------------------------

import copy
import datetime
import json
import typing
from dataclasses import dataclass

from google.protobuf.json_format import MessageToJson
from opentelemetry.proto.trace.v1.trace_pb2 import Span as PBSpan

from promptflow._constants import SpanAttributeFieldName, SpanContextFieldName, SpanFieldName, SpanStatusFieldName
from promptflow._sdk._orm.trace import Span as ORMSpan
from promptflow._sdk._utils import (
    convert_time_unix_nano_to_timestamp,
    flatten_pb_attributes,
    parse_otel_span_status_code,
)


class Span:
    """Span is exactly the same as OpenTelemetry Span."""

    def __init__(
        self,
        name: str,
        context: typing.Dict[str, str],
        kind: str,
        start_time: str,
        end_time: str,
        status: str,
        attributes: typing.Dict[str, str],
        resource: typing.Dict,
        # should come from attributes
        span_type: str,
        session_id: str,
        # optional fields
        parent_span_id: typing.Optional[str] = None,
        events: typing.Optional[typing.List] = None,
        links: typing.Optional[typing.List] = None,
        # prompt flow concepts
        path: typing.Optional[str] = None,
        run: typing.Optional[str] = None,
        experiment: typing.Optional[str] = None,
    ):
        self.name = name
        self.span_id = context[SpanContextFieldName.SPAN_ID]
        self.trace_id = context[SpanContextFieldName.TRACE_ID]
        self.span_type = span_type
        self.parent_span_id = parent_span_id
        self.session_id = session_id
        self.path = path
        self.run = run
        self.experiment = experiment
        self._content = {
            SpanFieldName.NAME: self.name,
            SpanFieldName.CONTEXT: copy.deepcopy(context),
            SpanFieldName.KIND: kind,
            SpanFieldName.PARENT_ID: self.parent_span_id,
            SpanFieldName.START_TIME: start_time,
            SpanFieldName.END_TIME: end_time,
            SpanFieldName.STATUS: status,
            SpanFieldName.ATTRIBUTES: copy.deepcopy(attributes),
            SpanFieldName.EVENTS: copy.deepcopy(events),
            SpanFieldName.LINKS: copy.deepcopy(links),
            SpanFieldName.RESOURCE: copy.deepcopy(resource),
        }

    def _persist(self) -> None:
        self._to_orm_object().persist()

    @staticmethod
    def _from_orm_object(obj: ORMSpan) -> "Span":
        content = json.loads(obj.content)
        return Span(
            name=obj.name,
            context=content[SpanFieldName.CONTEXT],
            kind=content[SpanFieldName.KIND],
            start_time=content[SpanFieldName.START_TIME],
            end_time=content[SpanFieldName.END_TIME],
            status=content[SpanFieldName.STATUS],
            attributes=content[SpanFieldName.ATTRIBUTES],
            resource=content[SpanFieldName.RESOURCE],
            span_type=obj.span_type,
            session_id=obj.session_id,
            parent_span_id=obj.parent_span_id,
            events=content[SpanFieldName.EVENTS],
            links=content[SpanFieldName.LINKS],
            path=obj.path,
            run=obj.run,
            experiment=obj.experiment,
        )

    def _to_orm_object(self) -> ORMSpan:
        return ORMSpan(
            name=self.name,
            trace_id=self.trace_id,
            span_id=self.span_id,
            parent_span_id=self.parent_span_id,
            span_type=self.span_type,
            session_id=self.session_id,
            content=json.dumps(self._content),
            path=self.path,
            run=self.run,
            experiment=self.experiment,
        )

    @staticmethod
    def _from_protobuf_object(obj: PBSpan, resource: typing.Dict) -> "Span":
        span_dict = json.loads(MessageToJson(obj))
        span_id = obj.span_id.hex()
        trace_id = obj.trace_id.hex()
        context = {
            SpanContextFieldName.TRACE_ID: trace_id,
            SpanContextFieldName.SPAN_ID: span_id,
            SpanContextFieldName.TRACE_STATE: obj.trace_state,
        }
        parent_span_id = obj.parent_span_id.hex()
        start_time = convert_time_unix_nano_to_timestamp(obj.start_time_unix_nano)
        end_time = convert_time_unix_nano_to_timestamp(obj.end_time_unix_nano)
        status = {
            SpanStatusFieldName.STATUS_CODE: parse_otel_span_status_code(obj.status.code),
        }
        attributes = flatten_pb_attributes(span_dict[SpanFieldName.ATTRIBUTES])
        return Span(
            name=obj.name,
            context=context,
            kind=obj.kind,
            start_time=start_time,
            end_time=end_time,
            status=status,
            attributes=attributes,
            resource=resource,
            span_type=attributes[SpanAttributeFieldName.SPAN_TYPE],
            session_id=attributes[SpanAttributeFieldName.SESSION_ID],
            parent_span_id=parent_span_id,
        )


@dataclass
class _LineRunData:
    """Basic data structure for line run, no matter if it is a main or evaluation."""

    line_run_id: str
    trace_id: str
    root_span_id: str
    inputs: typing.Dict
    outputs: typing.Dict
    start_time: datetime.datetime
    end_time: datetime.datetime
    status: str
    latency: float
    name: str
    kind: str
    cumulative_token_count: typing.Optional[typing.Dict[str, int]]

    @staticmethod
    def _from_root_span(span: Span) -> "_LineRunData":
        attributes: dict = span._content[SpanFieldName.ATTRIBUTES]
        if SpanAttributeFieldName.LINE_RUN_ID in attributes:
            line_run_id = attributes[SpanAttributeFieldName.LINE_RUN_ID]
        elif SpanAttributeFieldName.REFERENCED_LINE_RUN_ID in attributes:
            line_run_id = attributes[SpanAttributeFieldName.REFERENCED_LINE_RUN_ID]
        else:
            # eager flow/arbitrary script
            line_run_id = span.trace_id
        start_time = datetime.datetime.fromisoformat(span._content[SpanFieldName.START_TIME])
        end_time = datetime.datetime.fromisoformat(span._content[SpanFieldName.END_TIME])
        # calculate `cumulative_token_count`
        completion_token_count = int(attributes.get(SpanAttributeFieldName.COMPLETION_TOKEN_COUNT, 0))
        prompt_token_count = int(attributes.get(SpanAttributeFieldName.PROMPT_TOKEN_COUNT, 0))
        total_token_count = int(attributes.get(SpanAttributeFieldName.TOTAL_TOKEN_COUNT, 0))
        # if there is no token usage, set `cumulative_token_count` to None
        if total_token_count > 0:
            cumulative_token_count = {
                "completion": completion_token_count,
                "prompt": prompt_token_count,
                "total": total_token_count,
            }
        else:
            cumulative_token_count = None
        return _LineRunData(
            line_run_id=line_run_id,
            trace_id=span.trace_id,
            root_span_id=span.span_id,
            inputs=json.loads(attributes[SpanAttributeFieldName.INPUTS]),
            outputs=json.loads(attributes[SpanAttributeFieldName.OUTPUT]),
            start_time=start_time,
            end_time=end_time,
            status=span._content[SpanFieldName.STATUS][SpanStatusFieldName.STATUS_CODE],
            latency=(end_time - start_time).total_seconds(),
            name=span.name,
            kind=attributes[SpanAttributeFieldName.SPAN_TYPE],
            cumulative_token_count=cumulative_token_count,
        )


@dataclass
class LineRun:
    """Line run is an abstraction of spans related to prompt flow."""

    line_run_id: str
    trace_id: str
    root_span_id: str
    inputs: typing.Dict
    outputs: typing.Dict
    start_time: str
    end_time: str
    status: str
    latency: float
    name: str
    kind: str
    cumulative_token_count: typing.Optional[typing.Dict[str, int]] = None
    evaluations: typing.Optional[typing.List[typing.Dict]] = None

    @staticmethod
    def _from_spans(spans: typing.List[Span]) -> typing.List["LineRun"]:
        line_run_data_list: typing.List[_LineRunData] = []
        evaluation_line_run_data_dict = dict()  # line run id -> {evaluation name -> eval line run data}
        for span in spans:
            if span.parent_span_id:
                continue
            data = _LineRunData._from_root_span(span)
            attributes = span._content[SpanFieldName.ATTRIBUTES]
            if SpanAttributeFieldName.REFERENCED_LINE_RUN_ID not in attributes:
                # No parent span, no referenced span, it is a main line run
                # e.g. main run/eager flow/arbitrary script
                line_run_data_list.append(data)
                continue
            if SpanAttributeFieldName.LINE_RUN_ID not in attributes:
                # Aggregation node span only has referenced line run id, skip it for now.
                continue
            referenced_line_run_id = attributes[SpanAttributeFieldName.REFERENCED_LINE_RUN_ID]
            if referenced_line_run_id not in evaluation_line_run_data_dict:
                evaluation_line_run_data_dict[referenced_line_run_id] = {}
            evaluation_line_run_data_dict[referenced_line_run_id][span.name] = data
        line_runs = []
        for line_run_data in line_run_data_list:
            evaluations = evaluation_line_run_data_dict.get(line_run_data.line_run_id, {})
            # Use line run for evaluations as line run data not json serializable
            evaluations = {k: LineRun._from_line_run_data(v, None) for k, v in evaluations.items()}
            line_runs.append(LineRun._from_line_run_data(line_run_data, evaluations))
        return line_runs

    @staticmethod
    def _from_line_run_data(data: _LineRunData, evaluations=None) -> "LineRun":
        return LineRun(
            line_run_id=data.line_run_id,
            trace_id=data.trace_id,
            root_span_id=data.root_span_id,
            inputs=data.inputs,
            outputs=data.outputs,
            start_time=data.start_time.isoformat(),
            end_time=data.end_time.isoformat(),
            status=data.status,
            latency=data.latency,
            name=data.name,
            kind=data.kind,
            cumulative_token_count=data.cumulative_token_count,
            evaluations=evaluations,
        )
