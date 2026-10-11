#!/usr/bin/env python3
"""Shared payload validation and JSON CLI responses."""

import argparse
import hashlib
import json
import re


ID = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


class DiscoveryError(Exception):
    def __init__(self, code, message, exit_code=2):
        super().__init__(message)
        self.code = code
        self.exit_code = exit_code


def fail(code, message, exit_code=2):
    raise DiscoveryError(code, message, exit_code)


def text_value(value, label, empty=False):
    if not isinstance(value, str) or (not empty and not value.strip()):
        fail("INVALID_PAYLOAD", f"{label}: 문자열이 필요합니다.")
    if "\x00" in value:
        fail("INVALID_PAYLOAD", f"{label}: NUL은 허용하지 않습니다.")
    return value


def shape(value, required, optional=()):
    if not isinstance(value, dict):
        fail("INVALID_PAYLOAD", "JSON 객체가 필요합니다.")
    missing = set(required) - value.keys()
    extra = value.keys() - set(required) - set(optional)
    if missing or extra:
        fail("INVALID_PAYLOAD", f"누락 키: {sorted(missing)}, 알 수 없는 키: {sorted(extra)}")


def unique_strings(value, label, empty=False):
    if not isinstance(value, list) or (not empty and not value):
        fail("INVALID_PAYLOAD", f"{label}: 배열이 필요합니다.")
    for entry in value:
        text_value(entry, label)
    if len(value) != len(set(value)):
        fail("INVALID_PAYLOAD", f"{label}: 중복 항목이 있습니다.")
    return value


def identifier(value):
    text_value(value, "id")
    if not ID.fullmatch(value):
        fail("INVALID_PAYLOAD", f"안전한 소문자 ID가 필요합니다: {value}")
    return value


def digest_bytes(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def digest(value):
    return digest_bytes(canonical(value).encode("utf-8"))


def json_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            fail("INVALID_PAYLOAD", f"중복 JSON 키: {key}")
        result[key] = value
    return result


class Parser(argparse.ArgumentParser):
    def error(self, message):
        fail("MISSING_INPUT", message)


def run_cli(command, parser, handler, argv=None):
    response_command = None
    try:
        args = parser.parse_args(argv)
        response_command = command
        data = handler(args)
        print(json.dumps({"ok": True, "command": command, "data": data}, ensure_ascii=False))
        return 0
    except DiscoveryError as exc:
        response = {"ok": False, "command": response_command,
                    "error": {"code": exc.code, "message": str(exc)}}
        code = exc.exit_code
    except (OSError, ValueError) as exc:
        response = {"ok": False, "command": response_command,
                    "error": {"code": "IO_ERROR", "message": str(exc)}}
        code = 3
    print(json.dumps(response, ensure_ascii=False))
    return code
