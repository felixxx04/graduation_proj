package com.medical.exception;

import org.springframework.http.HttpStatus;

public class ModelServiceException extends BusinessException {
    public ModelServiceException(String message) {
        super(message, HttpStatus.BAD_GATEWAY);
    }

    public ModelServiceException(String message, Throwable cause) {
        super(message, HttpStatus.BAD_GATEWAY);
        initCause(cause);
    }
}
