package com.medical.exception;

import org.springframework.http.HttpStatus;

public class AccessDeniedException extends BusinessException {
    public AccessDeniedException(String message) {
        super(message, HttpStatus.FORBIDDEN);
    }
}
