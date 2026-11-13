import pytest

from app.telemetry.sse import SSEUsageCollector


@pytest.mark.parametrize("separator", [b"\n", b"\r", b"\r\n"])
@pytest.mark.parametrize("fragmented", [False, True])
def test_usage_with_sse_line_endings(separator: bytes, fragmented: bool) -> None:
    content = separator.join(
        [
            b": heartbeat",
            b"event: message",
            b'data:{"choices":[],',
            b'data: "usage":{"prompt_tokens":8,"completion_tokens":1}}',
            b"",
            b"",
        ]
    )
    collector = SSEUsageCollector()
    for chunk in [bytes([byte]) for byte in content] if fragmented else [content]:
        collector.feed(chunk)
    assert collector.usage == {"prompt_tokens": 8, "completion_tokens": 1}


def test_oversized_frames_are_discarded_without_losing_next_event() -> None:
    collector = SSEUsageCollector(max_frame_bytes=100)
    collector.feed(b"data: " + b"x" * 100000)
    assert len(collector._line) <= 100
    assert not collector._data
    collector.feed(b'\n\ndata: {"usage":{"prompt_tokens":9}}\n\n')
    assert collector.usage == {"prompt_tokens": 9}
    collector.feed(b'data: [DONE]\n\ndata: {broken}\n\ndata: {"usage":null}\n\n')
    assert collector.usage == {"prompt_tokens": 9}
