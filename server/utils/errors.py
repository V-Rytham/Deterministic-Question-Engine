from __future__ import annotations


class BadInputError(ValueError):
    pass


class BookNotFoundError(RuntimeError):
    pass


class PipelineInProgressError(RuntimeError):
    pass


class EmptyResultError(RuntimeError):
    pass

