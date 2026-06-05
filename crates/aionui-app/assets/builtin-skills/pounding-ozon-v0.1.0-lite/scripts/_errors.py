#!/usr/bin/env python3
from __future__ import annotations


class SkillError(Exception):
    def __init__(self, message: str, error_code: str = 'SKILL_ERROR'):
        super().__init__(message)
        self.message = message
        self.error_code = error_code


class ConfigError(SkillError):
    def __init__(self, message: str):
        super().__init__(message, 'CONFIG_ERROR')


class ValidationError(SkillError):
    def __init__(self, message: str):
        super().__init__(message, 'VALIDATION_ERROR')
