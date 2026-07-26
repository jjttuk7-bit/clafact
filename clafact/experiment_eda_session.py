"""검증 실험실 EDA의 파일·범위·세션 상태 규칙."""
from __future__ import annotations

import csv
import hashlib
import io
import json
from dataclasses import dataclass
from typing import BinaryIO, MutableMapping


MAX_EDA_ROWS = 1000
# Python csv의 기본 128KiB 제한은 정상 뉴스 본문을 거부할 수 있다. 프로세스 전체에
# 동일한 5MiB 문자 상한을 모듈 import 시 한 번만 설정하며 호출별 변경/복원은 하지 않는다.
MAX_EDA_CSV_FIELD_CHARS = 5 * 1024 * 1024
csv.field_size_limit(MAX_EDA_CSV_FIELD_CHARS)


class EdaCsvReadError(ValueError):
    def __init__(self, user_message: str):
        super().__init__(user_message)
        self.user_message = user_message

EDA_FILE_SIGNATURE_KEY = "experiment_eda_file_signature"
EDA_UPLOAD_METADATA_KEY = "experiment_eda_upload_metadata"
COMPARISON_INPUT_SIGNATURE_KEY = "experiment_lab_comparison_input_signature"
EDA_CACHE_KEY = "experiment_eda_cache_key"
EDA_RANGE_KEY = "experiment_eda_range"
EDA_RANGE_START_KEY = "experiment_eda_range_start"
EDA_RANGE_END_KEY = "experiment_eda_range_end"
EDA_REPORT_KEY = "experiment_eda_report"
EDA_VIEW_KEY = "experiment_eda_view"
EDA_SELECTED_ARTICLE_KEY = "experiment_eda_selected_article"
EDA_FILTER_STATE_KEYS = (
    "experiment_eda_filter_quality",
    "experiment_eda_filter_body",
    "experiment_eda_filter_min_candidates",
    "experiment_eda_filter_max_candidates",
)

_INVALIDATED_KEYS = (
    EDA_UPLOAD_METADATA_KEY,
    EDA_CACHE_KEY,
    EDA_RANGE_KEY,
    EDA_RANGE_START_KEY,
    EDA_RANGE_END_KEY,
    EDA_REPORT_KEY,
    EDA_VIEW_KEY,
    EDA_SELECTED_ARTICLE_KEY,
    *EDA_FILTER_STATE_KEYS,
)


@dataclass(frozen=True)
class EdaRange:
    """1부터 시작하는 원본 행 범위. ``end``는 화면에서는 포함 값이다."""

    start: int
    end: int

    @property
    def span(self) -> int:
        return self.end - self.start + 1

    @property
    def slice_bounds(self) -> tuple[int, int]:
        """Python 슬라이스의 0-based start, exclusive end."""

        return self.start - 1, self.end


def payload_signature(payload: bytes) -> str:
    """원본 바이트를 보관하지 않고 파일 정체성만 계산한다."""

    return hashlib.sha256(payload).hexdigest()


def resolve_eda_range(
    total_rows: int,
    requested: EdaRange | None = None,
    *,
    confirmed: bool = False,
) -> EdaRange | None:
    """작은 파일은 전체, 큰 파일은 명시적으로 확정된 최대 1,000행만 반환한다."""

    if total_rows < 0:
        raise ValueError("전체 행 수는 음수일 수 없습니다.")
    if total_rows <= MAX_EDA_ROWS:
        return EdaRange(1, total_rows) if total_rows else None
    if not confirmed:
        return None
    if requested is None:
        raise ValueError("분석 범위를 선택해 주세요.")
    if (
        requested.start < 1
        or requested.end < requested.start
        or requested.end > total_rows
        or requested.span > MAX_EDA_ROWS
    ):
        raise ValueError("분석 범위는 원본 안의 연속된 최대 1,000행이어야 합니다.")
    return requested


def analysis_scope_caption(total_rows: int, selected: EdaRange) -> str:
    """업로드 전체 모집단과 현재 선택 분석 구간을 함께 표시한다."""

    if total_rows < 1 or selected.start < 1 or selected.end > total_rows:
        raise ValueError("분석 구간은 업로드 전체 행 범위 안에 있어야 합니다.")
    return (
        f"전체 {total_rows:,}행 중 "
        f"{selected.start:,}–{selected.end:,}행 분석"
    )


def cache_key(signature: str, selected: EdaRange) -> tuple[str, int, int]:
    return signature, selected.start, selected.end


def invalidate_for_payload(
    state: MutableMapping[str, object],
    signature: str,
) -> bool:
    """새 파일이면 EDA 파생 상태만 제거하고 서명만 저장한다."""

    if state.get(EDA_FILE_SIGNATURE_KEY) == signature:
        return False
    for key in _INVALIDATED_KEYS:
        state.pop(key, None)
    state[EDA_FILE_SIGNATURE_KEY] = signature
    return True


@dataclass(frozen=True)
class UploadIdentity:
    """업로드 객체를 바이트 보관 없이 식별하는 안정 메타데이터."""

    file_id: str
    name: str
    size: int


@dataclass(frozen=True)
class UploadMetadata:
    identity: UploadIdentity
    signature: str
    row_count: int


@dataclass(frozen=True)
class CsvScan:
    row_count: int
    rows: tuple[dict[str, object], ...]
    retained_during_scan: int
    exceeded_limit: bool


def hash_seekable_stream(stream: BinaryIO, *, chunk_size: int = 64 * 1024) -> str:
    """seek 가능한 업로드를 청크 해시하고 호출자의 위치를 복원한다."""

    if chunk_size <= 0:
        raise ValueError("chunk_size must be positive")
    original_position = stream.tell()
    digest = hashlib.sha256()
    try:
        stream.seek(0)
        while chunk := stream.read(chunk_size):
            digest.update(chunk)
        return digest.hexdigest()
    finally:
        stream.seek(original_position)


def _csv_reader(stream: BinaryIO) -> tuple[io.TextIOWrapper, csv.DictReader]:
    stream.seek(0)
    wrapper = io.TextIOWrapper(stream, encoding="utf-8-sig", newline="")
    return wrapper, csv.DictReader(wrapper, strict=True)


def _detach_and_restore(
    wrapper: io.TextIOWrapper,
    stream: BinaryIO,
    original_position: int,
) -> None:
    try:
        wrapper.detach()
    finally:
        stream.seek(original_position)


def _typed_csv_error(error: csv.Error) -> EdaCsvReadError:
    if "field larger than field limit" in str(error):
        return EdaCsvReadError(
            f"CSV 셀은 최대 {MAX_EDA_CSV_FIELD_CHARS:,}자까지 지원합니다. "
            "내용을 줄이거나 파일을 나누어 주세요. 데이터는 줄이지 않고 분석을 중단했습니다."
        )
    return EdaCsvReadError(
        "CSV 형식을 읽을 수 없습니다. 따옴표와 열 구분자를 확인해 주세요."
    )


def scan_csv_stream(stream: BinaryIO) -> CsvScan:
    """전체 행 수는 세되 초기 메모리 보유량은 1,001행으로 제한한다."""

    original_position = stream.tell()
    wrapper, reader = _csv_reader(stream)
    retained: list[dict[str, object]] = []
    row_count = 0
    try:
        for row_count, row in enumerate(reader, start=1):
            if len(retained) < MAX_EDA_ROWS + 1:
                retained.append(dict(row))
    except csv.Error as error:
        raise _typed_csv_error(error) from error
    finally:
        _detach_and_restore(wrapper, stream, original_position)
    exceeded = row_count > MAX_EDA_ROWS
    return CsvScan(
        row_count=row_count,
        rows=() if exceeded else tuple(retained),
        retained_during_scan=len(retained),
        exceeded_limit=exceeded,
    )


def read_csv_range(stream: BinaryIO, selected: EdaRange) -> tuple[dict[str, object], ...]:
    """확정된 1-based 포함 범위만 두 번째 스트리밍 패스로 읽는다."""

    if selected.start < 1 or selected.end < selected.start or selected.span > MAX_EDA_ROWS:
        raise ValueError("분석 범위는 연속된 최대 1,000행이어야 합니다.")
    original_position = stream.tell()
    wrapper, reader = _csv_reader(stream)
    rows: list[dict[str, object]] = []
    try:
        for row_number, row in enumerate(reader, start=1):
            if row_number < selected.start:
                continue
            if row_number > selected.end:
                break
            rows.append(dict(row))
    except csv.Error as error:
        raise _typed_csv_error(error) from error
    finally:
        _detach_and_restore(wrapper, stream, original_position)
    return tuple(rows)


def cached_upload_metadata(
    state: MutableMapping[str, object],
    identity: UploadIdentity,
) -> UploadMetadata | None:
    metadata = state.get(EDA_UPLOAD_METADATA_KEY)
    return (
        metadata
        if isinstance(metadata, UploadMetadata) and metadata.identity == identity
        else None
    )


def store_upload_metadata(
    state: MutableMapping[str, object],
    metadata: UploadMetadata,
) -> bool:
    """새 업로드 객체만 EDA 파생 상태를 비우고 메타데이터를 저장한다."""

    if state.get(EDA_UPLOAD_METADATA_KEY) == metadata:
        return False
    for key in (*_INVALIDATED_KEYS, EDA_FILE_SIGNATURE_KEY):
        state.pop(key, None)
    state[EDA_UPLOAD_METADATA_KEY] = metadata
    return True


def prepare_cache_scope(
    state: MutableMapping[str, object],
    new_cache_key: tuple[str, int, int],
) -> bool:
    """범위가 바뀌면 위젯 생성 전에 이전 필터·선택·보고서를 제거한다."""

    if state.get(EDA_CACHE_KEY) == new_cache_key:
        return False
    for key in (
        EDA_REPORT_KEY,
        EDA_VIEW_KEY,
        EDA_SELECTED_ARTICLE_KEY,
        *EDA_FILTER_STATE_KEYS,
    ):
        state.pop(key, None)
    state[EDA_CACHE_KEY] = new_cache_key
    return True


def comparison_input_signature(
    *,
    text: str,
    article_date: str,
    title: str,
    source_row: int | None,
    file_signature: str = "",
    upload_identity: UploadIdentity | None = None,
    analysis_range: EdaRange | None = None,
) -> str:
    """현재 비교에 실제 사용되는 입력을 정확한 문자열 값으로 식별한다."""

    material = json.dumps(
        [
            text,
            article_date,
            title,
            source_row,
            file_signature,
            (
                [upload_identity.file_id, upload_identity.name, upload_identity.size]
                if upload_identity
                else None
            ),
            [analysis_range.start, analysis_range.end] if analysis_range else None,
        ],
        ensure_ascii=False,
        separators=(",", ":"),
    ).encode("utf-8")
    return hashlib.sha256(material).hexdigest()


def invalidate_comparison_for_input(
    state: MutableMapping[str, object],
    signature: str,
) -> bool:
    """현재 입력과 다른 실행 결과가 화면에 남지 않게 한다."""

    if state.get(COMPARISON_INPUT_SIGNATURE_KEY) == signature:
        return False
    for key in (
        "experiment_lab_result",
        "experiment_lab_mode_result",
        "experiment_lab_run_context",
        "experiment_lab_saved_run_id",
    ):
        state.pop(key, None)
    state[COMPARISON_INPUT_SIGNATURE_KEY] = signature
    return True
