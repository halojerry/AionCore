#!/usr/bin/env python3
from __future__ import annotations

import json
from typing import Any


def make_output(success: bool, markdown: str = '', data: dict | None = None,
                error_code: str = '', details: dict | None = None) -> dict[str, Any]:
    result: dict[str, Any] = {'success': success}
    if markdown:
        result['markdown'] = markdown
    if data is not None:
        result['data'] = data
    if error_code:
        result['error_code'] = error_code
    if details is not None:
        result['details'] = details
    return result


def print_output(output: dict[str, Any]) -> None:
    print(json.dumps(output, ensure_ascii=False, indent=2))


def print_success(markdown: str = '', data: dict | None = None) -> None:
    print_output(make_output(True, markdown=markdown, data=data))


def print_failure(markdown: str, error_code: str = '', data: dict | None = None, details: dict | None = None) -> None:
    print_output(make_output(False, markdown=markdown, data=data, error_code=error_code, details=details))
