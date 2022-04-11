def perform_async(signature, countdown=0, **kwargs):
    return signature.apply_async(countdown=countdown, **kwargs)
