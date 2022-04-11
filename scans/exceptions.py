class ScanError(Exception):
    pass


class PostScanOperationError(ScanError):
    pass


class InvalidPostScanOperation(PostScanOperationError):
    pass


class PostScanOperationFailed(PostScanOperationError):
    pass
